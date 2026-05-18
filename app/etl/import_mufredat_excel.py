# -*- coding: utf-8 -*-
# =============================================================================
# app/etl/import_mufredat_excel.py — Mufredat Excel Ice Aktarma
# =============================================================================
# Excel dosyasindan mufredat ve mufredat_ders iliskilerini SQLite veritabanina aktarir.
# =============================================================================

import os
import re
import sqlite3
from collections import defaultdict

import pandas as pd

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


def find_course_id_by_code_or_name(cur, ders_kodu=None, ders_adi=None):
    kod = str(ders_kodu or "").strip()
    if kod:
        cur.execute("SELECT ders_id FROM ders WHERE lower(trim(kod)) = lower(trim(?))", (kod,))
        row = cur.fetchone()
        if row:
            return row[0]
    return find_course_id(cur, ders_adi)


def collect_curriculum_rows(df: pd.DataFrame):
    col_fak = find_col(df, "Fakülte", "Fakulte", "faculty")
    col_bol = find_col(df, "Bölüm", "Bolum", "department")
    col_yil = find_col(df, "Akademik Yıl", "akademik_yil", "Yıl", "Yil", "year")
    col_don = find_col(df, "Dönem", "Donem", "term")
    col_ders_adi = find_col(df, "Ders Adı", "Ders Adi", "ders_adi", "course_name")
    col_ders_kodu = find_col(df, "Ders Kodu", "Ders Kodu/Kod", "ders_kodu", "kod", "course_code")

    if not (col_fak and col_bol and col_yil):
        return None, {
            "error": "Gerekli kolonlar bulunamadı: Fakülte, Bölüm, Yıl",
            "layout": None,
        }

    rows = []
    warnings = []

    # Yeni şablon: satır bazlı, her satır 1 ders
    if col_ders_adi or col_ders_kodu:
        for idx, row in df.iterrows():
            fakulte = row.get(col_fak)
            bolum = row.get(col_bol)
            yil_raw = row.get(col_yil)
            donem = str(row.get(col_don) if col_don else "Güz").strip() or "Güz"
            ders_adi = row.get(col_ders_adi) if col_ders_adi else None
            ders_kodu = row.get(col_ders_kodu) if col_ders_kodu else None

            if pd.isna(fakulte) or pd.isna(bolum) or pd.isna(yil_raw):
                warnings.append(f"Satır {idx}: fakülte/bölüm/yıl eksik")
                continue

            yil = clean_year(yil_raw, base_year_if_class=2022)
            if not yil:
                warnings.append(f"Satır {idx}: yıl parse edilemedi -> {yil_raw!r}")
                continue

            if (pd.isna(ders_adi) or str(ders_adi).strip() == "") and (pd.isna(ders_kodu) or str(ders_kodu).strip() == ""):
                warnings.append(f"Satır {idx}: ders kodu/adı eksik")
                continue

            rows.append(
                {
                    "fakulte": str(fakulte).strip(),
                    "bolum": str(bolum).strip(),
                    "yil": yil,
                    "donem": donem,
                    "ders_adi": None if pd.isna(ders_adi) else str(ders_adi).strip(),
                    "ders_kodu": None if pd.isna(ders_kodu) else str(ders_kodu).strip(),
                }
            )

        return rows, {"error": None, "layout": "normalized", "warnings": warnings}

    # Legacy geniş şablon: Seçmeli Ders 1..10 sütunları
    for idx, row in df.iterrows():
        fakulte = row.get(col_fak)
        bolum = row.get(col_bol)
        yil_raw = row.get(col_yil)
        donem = str(row.get(col_don) if col_don else "Güz").strip() or "Güz"

        if pd.isna(fakulte) or pd.isna(bolum) or pd.isna(yil_raw):
            warnings.append(f"Satır {idx}: fakülte/bölüm/yıl eksik")
            continue

        yil = clean_year(yil_raw, base_year_if_class=2022)
        if not yil:
            warnings.append(f"Satır {idx}: yıl parse edilemedi -> {yil_raw!r}")
            continue

        found_any_course = False
        for i in range(1, 11):
            candidates = [f"Seçmeli Ders {i}", f"Secmeli Ders {i}", f"Ders {i}", f"Ders{i}"]
            ders_col = next((c for c in candidates if c in df.columns), None)
            if not ders_col:
                continue

            ders_adi = row.get(ders_col)
            if pd.isna(ders_adi) or str(ders_adi).strip() == "":
                continue

            found_any_course = True
            rows.append(
                {
                    "fakulte": str(fakulte).strip(),
                    "bolum": str(bolum).strip(),
                    "yil": yil,
                    "donem": donem,
                    "ders_adi": str(ders_adi).strip(),
                    "ders_kodu": None,
                }
            )
        if not found_any_course:
            warnings.append(f"Satır {idx}: seçmeli ders kolonu dolu değil")

    return rows, {"error": None, "layout": "wide", "warnings": warnings}


def replace_scope_curriculum(cur, f_id, b_id, yil, donem, ders_ids):
    cur.execute(
        """
        SELECT mufredat_id
        FROM mufredat
        WHERE fakulte_id = ? AND bolum_id = ? AND akademik_yil = ? AND donem = ?
        ORDER BY COALESCE(versiyon, 0) DESC, mufredat_id DESC
        """,
        (f_id, b_id, yil, donem),
    )
    existing_ids = [int(row[0]) for row in cur.fetchall() if row and row[0] is not None]
    keep_id = existing_ids[0] if existing_ids else None

    if keep_id is not None:
        cur.execute("DELETE FROM mufredat_ders WHERE mufredat_id = ?", (keep_id,))
        for extra_id in existing_ids[1:]:
            cur.execute("DELETE FROM mufredat_ders WHERE mufredat_id = ?", (extra_id,))
            cur.execute("DELETE FROM mufredat WHERE mufredat_id = ?", (extra_id,))
    else:
        cur.execute(
            "INSERT INTO mufredat (fakulte_id, bolum_id, akademik_yil, donem, durum, versiyon) VALUES (?, ?, ?, ?, ?, ?)",
            (f_id, b_id, yil, donem, "Excel Import", 1),
        )
        keep_id = cur.lastrowid

    linked = 0
    seen = set()
    for ders_id in ders_ids:
        if ders_id in seen:
            continue
        seen.add(ders_id)
        cur.execute(
            "INSERT OR IGNORE INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?)",
            (keep_id, int(ders_id)),
        )
        linked += 1

    return keep_id, linked

# -------------------------------------------------------
# Main
# -------------------------------------------------------
def run_import(excel_path=None, db_path=None):
    """
    Excel'den müfredat verisi aktarır.
    excel_path: Excel dosya yolu (None ise data/2022_mufredat.xlsx)
    db_path: Veritabanı yolu (None ise DB_PATH)
    Returns: (ok: bool, msg: str, counts: dict)
    """
    db = db_path or DB_PATH
    excel = excel_path or EXCEL_PATH
    result = {"mufredat": 0, "link": 0, "skipped_year": 0, "scopes": 0, "warnings": 0, "layout": None}

    if not db or not os.path.exists(db):
        return False, "Veritabanı bulunamadı.", result
    if not excel or not os.path.exists(excel):
        return False, "Excel dosyası bulunamadı.", result

    df = pd.read_excel(excel)
    df.columns = [c.strip() for c in df.columns]
    rows, parse_info = collect_curriculum_rows(df)
    result["layout"] = parse_info.get("layout")
    result["warnings"] = len(parse_info.get("warnings", []))

    if parse_info.get("error"):
        return False, parse_info["error"], result
    if not rows:
        return False, "Excel içinde aktarılabilir müfredat satırı bulunamadı.", result

    conn = sqlite3.connect(db)
    cur = conn.cursor()

    try:
        count_muf = 0
        count_link = 0
        skipped_year = result["warnings"]
        grouped = defaultdict(list)

        for idx, item in enumerate(rows):
            f_id = get_fakulte_id(cur, item["fakulte"])
            b_id = get_bolum_id(cur, item["bolum"], f_id) if f_id else None
            if not f_id or not b_id:
                skipped_year += 1
                print(f"⚠️ Satır {idx}: fakülte/bölüm eşleşmedi -> {item['fakulte']} / {item['bolum']}")
                continue

            d_id = find_course_id_by_code_or_name(cur, item.get("ders_kodu"), item.get("ders_adi"))
            if not d_id:
                skipped_year += 1
                print(
                    f"⚠️ Satır {idx}: ders bulunamadı -> kod={item.get('ders_kodu')!r}, ad={item.get('ders_adi')!r}"
                )
                continue

            grouped[(f_id, b_id, item["yil"], item["donem"])].append(int(d_id))

        if not grouped:
            return False, "Aktarılabilir geçerli müfredat kaydı bulunamadı.", result

        for (f_id, b_id, yil, donem), ders_ids in grouped.items():
            _, linked = replace_scope_curriculum(cur, f_id, b_id, yil, donem, ders_ids)
            count_muf += 1
            count_link += linked

        conn.commit()
        result = {
            "mufredat": count_muf,
            "link": count_link,
            "skipped_year": skipped_year,
            "scopes": len(grouped),
            "warnings": skipped_year,
            "layout": result["layout"],
        }
        msg = (
            f"Aktarım tamamlandı. Güncellenen kapsam: {len(grouped)}, "
            f"Müfredat: {count_muf}, Bağlanan ders: {count_link}, Şablon: {result['layout']}"
        )
        if skipped_year:
            msg += f", Uyarı/atlanan satır: {skipped_year}"
        return True, msg, result

    finally:
        conn.close()


def _main():
    ok, msg, counts = run_import()
    print("Müfredat aktarımı...")
    print(msg)
    if not ok:
        exit(1)


if __name__ == "__main__":
    _main()
