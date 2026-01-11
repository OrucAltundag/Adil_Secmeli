import sqlite3
import pandas as pd
import os
import re

# -------------------------------------------------------
# PATH'leri CWD'ye değil, dosyanın konumuna göre bul (daha sağlam)
# -------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(HERE))  # app/etl -> proje kökü varsayımı
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

db_candidates = [
    os.path.join(DATA_DIR, "adil_secmeli.db"),
    os.path.join(DATA_DIR, "adil_secmeli.sqlite"),
    os.path.join(PROJECT_ROOT, "adil_secmeli.db"),
    os.path.join(PROJECT_ROOT, "adil_secimli.db"),
]
DB_PATH = next((p for p in db_candidates if os.path.exists(p)), None)

EXCEL_PATH = os.path.join(DATA_DIR, "2022_mufredat.xlsx")

# -------------------------------------------------------
# Yardımcılar
# -------------------------------------------------------
def normalize_col(s: str) -> str:
    return str(s).strip().lower().replace("ı", "i").replace("ğ", "g").replace("ş", "s").replace("ö", "o").replace("ü", "u").replace("ç", "c")

def find_col(df: pd.DataFrame, *names):
    """Kolon adını esnek şekilde bulur (Türkçe/İngilizce/underscore varyasyonları)."""
    norm_map = {normalize_col(c): c for c in df.columns}
    for n in names:
        key = normalize_col(n)
        if key in norm_map:
            return norm_map[key]
    return None

def clean_year(val, base_year_if_class=None):
    """
    - 2022, 2022.0, '2022/2023', '2022-2023 Güz' -> 2022
    - Eğer 1-4 gibi sınıf geldiyse ve base_year_if_class verilirse:
        1 -> base_year, 2 -> base_year+1 ...
    """
    if pd.isna(val):
        return None
    s = str(val).strip()

    # 4 haneli yıl bul
    m = re.search(r"(19|20)\d{2}", s)
    if m:
        return int(m.group())

    # sınıf (1-4) gibi bir şey mi?
    m2 = re.fullmatch(r"\d+", s)
    if m2 and base_year_if_class is not None:
        cls = int(s)
        if 1 <= cls <= 8:  # güvenlik payı
            return int(base_year_if_class + (cls - 1))

    return None

def get_fakulte_id(cur, fak_adi):
    """Fakülte adını kullanarak fakülte ID'sini bulur."""
    cur.execute("SELECT fakulte_id FROM fakulte WHERE ad = ?", (fak_adi,))
    res = cur.fetchone()
    if res:
        return res[0]
    else:
        print(f"⚠️ Fakülte bulunamadı: {fak_adi}")
        return None

def get_bolum_id(cur, bol_adi, fakulte_id):
    """Bölüm adını kullanarak bölüm ID'sini bulur (fakülteye bağlı)."""
    cur.execute("SELECT bolum_id FROM bolum WHERE ad = ? AND fakulte_id = ?", (bol_adi, fakulte_id))
    res = cur.fetchone()
    if res:
        return res[0]
    else:
        print(f"⚠️ Bölüm bulunamadı: {bol_adi} - Fakülte ID: {fakulte_id}")
        return None

def find_course_id(cur, ders_adi: str):
    """
    Ders adını daha toleranslı eşleştirir:
    1) lower(trim(ad)) == lower(trim(?))
    2) LIKE %...% fallback
    """
    d = str(ders_adi).strip()
    if not d:
        return None

    # 1) birebir (case/space toleranslı)
    cur.execute("SELECT ders_id FROM ders WHERE lower(trim(ad)) = lower(trim(?))", (d,))
    r = cur.fetchone()
    if r:
        return r[0]

    # 2) LIKE fallback
    cur.execute("SELECT ders_id FROM ders WHERE lower(ad) LIKE lower(?)", (f"%{d}%",))
    r = cur.fetchone()
    if r:
        return r[0]

    return None

# -------------------------------------------------------
# Main
# -------------------------------------------------------
def run_import():
    print("🚀 Müfredat aktarımı başlıyor...")
    print(f"📂 DB   : {DB_PATH}")
    print(f"📂 Excel: {EXCEL_PATH}")

    if not DB_PATH or not os.path.exists(DB_PATH):
        print("❌ DB bulunamadı. data klasörünü ve dosya adını kontrol et.")
        return
    if not os.path.exists(EXCEL_PATH):
        print("❌ Excel bulunamadı. data/2022_mufredat.xlsx yolunu kontrol et.")
        return

    df = pd.read_excel(EXCEL_PATH)
    df.columns = [c.strip() for c in df.columns]

    # Kolonları esnek bul
    col_fak = find_col(df, "Fakülte", "Fakulte", "faculty")
    col_bol = find_col(df, "Bölüm", "Bolum", "department")
    col_yil = find_col(df, "Akademik Yıl", "akademik_yil", "Yıl", "Yil", "year")
    col_don = find_col(df, "Dönem", "Donem", "term")

    print("🔎 Kolon eşleşmeleri:")
    print("  Fakülte :", col_fak)
    print("  Bölüm   :", col_bol)
    print("  Yıl     :", col_yil)
    print("  Dönem   :", col_don)

    if not (col_fak and col_bol and col_yil):
        print("❌ Gerekli kolonlar bulunamadı. Excel başlıklarını kontrol et.")
        print("   Beklenen: Fakülte, Bölüm, (Akademik Yıl/Yıl), (Dönem opsiyonel)")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        # 1) tabloları temizle (DROP yok)
        cur.execute("PRAGMA foreign_keys = OFF;")
        cur.execute("DELETE FROM mufredat_ders;")
        cur.execute("DELETE FROM mufredat;")
        cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('mufredat','mufredat_ders');")
        cur.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
        print("🧹 mufredat / mufredat_ders temizlendi.")

        count_muf = 0
        count_link = 0
        skipped_year = 0

        for idx, row in df.iterrows():
            fak_adi = row.get(col_fak)
            bol_adi = row.get(col_bol)
            yil_raw = row.get(col_yil)
            donem = str(row.get(col_don) if col_don else "Güz").strip() or "Güz"

            if pd.isna(fak_adi) or pd.isna(bol_adi) or pd.isna(yil_raw):
                continue

            # Eğer Excel’de yıl yerine sınıf yazıyorsa (1-4) bunu 2022 tabanlı akademik yıla çevirebilir:
            yil = clean_year(yil_raw, base_year_if_class=2022)
            if not yil:
                skipped_year += 1
                print(f"⚠️ Satır {idx}: Yıl parse edilemedi -> {yil_raw!r}")
                continue

            # Fakülte/Bölüm
            f_id = get_fakulte_id(cur, fak_adi)
            b_id = get_bolum_id(cur, bol_adi, f_id)

            if not f_id or not b_id:
                continue  # Eğer fakülte veya bölüm bulunamazsa, satırı atla

            # Müfredat
            cur.execute(
                "SELECT mufredat_id FROM mufredat WHERE fakulte_id=? AND bolum_id=? AND akademik_yil=? AND donem=?",
                (f_id, b_id, yil, donem),
            )
            res = cur.fetchone()
            if res:
                m_id = res[0]
            else:
                cur.execute(
                    "INSERT INTO mufredat (fakulte_id, bolum_id, akademik_yil, donem) VALUES (?, ?, ?, ?)",
                    (f_id, b_id, yil, donem),
                )
                m_id = cur.lastrowid
                count_muf += 1

            # Ders kolonları: Seçmeli Ders 1..10 / Ders 1..10 / Ders1..Ders10
            for i in range(1, 11):
                candidates = [f"Seçmeli Ders {i}", f"Secmeli Ders {i}", f"Ders {i}", f"Ders{i}"]
                ders_col = None
                for c in candidates:
                    if c in df.columns:
                        ders_col = c
                        break
                if not ders_col:
                    continue

                ders_adi = row.get(ders_col)
                if pd.isna(ders_adi):
                    continue

                d_id = find_course_id(cur, str(ders_adi))
                if not d_id:
                    print(f"⚠️ Ders Bulunamadı (satır {idx}): {ders_adi!r}")
                    continue

                # ilişki ekle (tekrarları engelle)
                cur.execute(
                    "SELECT 1 FROM mufredat_ders WHERE mufredat_id=? AND ders_id=?",
                    (m_id, d_id),
                )
                if not cur.fetchone():
                    cur.execute(
                        "INSERT INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?)",
                        (m_id, d_id),
                    )
                    count_link += 1

        conn.commit()

        print("\n" + "=" * 44)
        print("🎉 AKTARIM TAMAMLANDI")
        print(f"📘 Eklenen Müfredat : {count_muf}")
        print(f"🔗 Bağlanan Ders    : {count_link}")
        print(f"⚠️ Yıl atlanan satır: {skipped_year}")
        print("=" * 44)

        if count_muf == 0:
            print("💡 Not: Müfredat 0 ise genelde 'Yıl' kolonunu yanlış yakalıyoruz demektir.")
            print("   Excel’de yıl başlığını 'Akademik Yıl' yapmayı veya scriptteki kolon eşleşmesini kontrol etmeyi dene.")
        if count_link == 0:
            print("💡 Not: Bağlanan ders 0 ise ders adları DB’deki 'ders.ad' ile uyuşmuyor olabilir.")
            print("   (Büyük/küçük harf, boşluk, farklı yazım) — bu script LIKE fallback ile bile bulamadıysa isimler çok farklıdır.")

    finally:
        conn.close()

if __name__ == "__main__":
    run_import()
