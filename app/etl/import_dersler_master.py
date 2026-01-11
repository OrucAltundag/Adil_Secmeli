import sqlite3
import pandas as pd
import os

# ==========================================
# DOSYA BULUCU
# ==========================================
def find_file(filename, search_paths):
    for path in search_paths:
        full_path = os.path.join(path, filename)
        if os.path.exists(full_path):
            return full_path
    return None


def run_import():
    print("🚀 Veri Aktarımı Başlatılıyor...")

    base_dir = os.getcwd()
    db_name = "adil_secmeli.db"
    excel_name = "dersler_master.xlsx"

    search_dirs = [base_dir, os.path.join(base_dir, "data")]

    db_path = find_file(db_name, search_dirs)
    excel_path = find_file(excel_name, search_dirs)

    if not db_path or not excel_path:
        print("❌ DB veya Excel bulunamadı")
        return

    print(f"✅ DB: {db_path}")
    print(f"✅ Excel: {excel_path}")

    # Excel dosyasını oku
    df = pd.read_excel(excel_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        print("🧹 Tablolar temizleniyor...")
        cur.execute("PRAGMA foreign_keys = OFF;")
        # Tablo isimlerinin doğru olduğundan emin ol (ders mi dersler mi?)
        cur.execute("DELETE FROM ders;")
        cur.execute("DELETE FROM bolum;")
        cur.execute("DELETE FROM fakulte;")
        cur.execute("DELETE FROM sqlite_sequence;")
        conn.commit()

        # ===============================
        # 1️⃣ FAKÜLTELER
        # ===============================
        print("🏛️ Fakülteler ekleniyor...")
        fakulte_map = {}

        for fak in df['FakülteAdı'].dropna().unique():
            fak = fak.strip()
            cur.execute(
                "INSERT INTO fakulte (ad) VALUES (?)",
                (fak,)
            )
            fakulte_map[fak] = cur.lastrowid

        conn.commit()

        # ===============================
        # 2️⃣ BÖLÜMLER (TEKİL)
        # ===============================
        print("🏫 Bölümler ekleniyor...")
        bolum_map = {}

        bolum_df = df[['BölümAdı', 'FakülteAdı']].dropna().drop_duplicates()

        for _, row in bolum_df.iterrows():
            bolum = row['BölümAdı'].strip()
            fak = row['FakülteAdı'].strip()
            fak_id = fakulte_map[fak]

            cur.execute(
                "INSERT INTO bolum (ad, fakulte_id) VALUES (?, ?)",
                (bolum, fak_id)
            )
            bolum_map[(bolum, fak)] = cur.lastrowid

        conn.commit()

        # ===============================
        # 3️⃣ DERSLER
        # ===============================
        print("📚 Dersler ekleniyor...")
        added = 0

        for _, row in df.iterrows():
            fak = str(row['FakülteAdı']).strip()
            bolum = str(row['BölümAdı']).strip()

            fak_id = fakulte_map.get(fak)
            bolum_id = bolum_map.get((bolum, fak))

            if not fak_id or not bolum_id:
                continue

            # İçerik (Bilgi) Temizleme
            bilgi = str(row.get('Icerik', '')).strip()
            if bilgi.lower() == 'nan':
                bilgi = ""

            # Ders Tipi Okuma ve Temizleme
            ders_tipi = str(row.get('DersTipi', 'Zorunlu')).strip()
            if ders_tipi.lower() == 'nan' or not ders_tipi:
                ders_tipi = 'Zorunlu'

            cur.execute("""
                INSERT INTO ders (
                    ad, fakulte_id, bolum_id,
                    kredi, akts, bilgi, DersTipi, alan, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Genel', 1)
            """, (
                row['DersAdı'].strip(),
                fak_id,      # <--- DÜZELTİLDİ (Eskiden fakulte_id yazıyordu)
                bolum_id,
                int(row.get('Kredi', 0)),
                int(row.get('AKTS', 0)),
                bilgi,
                ders_tipi
            ))

            added += 1

        conn.commit()
        cur.execute("PRAGMA foreign_keys = ON;")

        print("\n🎉 AKTARIM TAMAMLANDI")
        print(f"🏛️ Fakülte: {len(fakulte_map)}")
        print(f"🏫 Bölüm: {len(bolum_map)}")
        print(f"📚 Ders: {added}")

    except Exception as e:
        conn.rollback()
        print("🚨 HATA:", e)

    finally:
        conn.close()


if __name__ == "__main__":
    run_import()