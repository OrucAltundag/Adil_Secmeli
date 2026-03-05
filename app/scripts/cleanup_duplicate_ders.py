#!/usr/bin/env python3
# Aynı isim/özellikte tekrarlayan derslerden küçük ID'li olanı tutar, büyük ID'lileri siler.
# Tüm FK referansları güncellenir.

import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "adil_secmeli.db")

# ders_id referansı veren tablolar (tablo, sütun)
FK_TABLES = [
    ("kayit", "ders_id"),
    ("performans", "ders_id"),
    ("populerlik", "ders_id"),
    ("ders_kriterleri", "ders_id"),
    ("mufredat_ders", "ders_id"),
    ("kontenjan", "ders_id"),
    ("anket", "ders_id"),
    ("havuz", "ders_id"),  # havuz.ders_id TEXT olabilir
]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    if not os.path.exists(path):
        print(f"Hata: Veritabanı bulunamadı: {path}")
        sys.exit(1)

    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = OFF")
    cur = conn.cursor()

    # Ders tablosu sütunlarını al (ad, kod, fakulte_id vb. karşılaştırma için)
    cur.execute("PRAGMA table_info(ders)")
    cols = [r[1] for r in cur.fetchall()]
    if "ad" not in cols:
        print("Ders tablosunda 'ad' sütunu yok.")
        conn.close()
        sys.exit(1)

    # Aynı ad + fakulte_id + kod (varsa) ile grupla; aynı özellikleri olanları bul
    cur.execute("""
        SELECT ders_id, ad, COALESCE(fakulte_id,0), COALESCE(kod,''),
               COALESCE(kredi,0), COALESCE(akts,0), COALESCE(tur,'')
        FROM ders ORDER BY ad, ders_id
    """)
    rows = cur.fetchall()

    # Grupla: (ad, fakulte_id, kod, kredi, akts, tur) -> [ders_id listesi]
    from collections import defaultdict
    groups = defaultdict(list)
    for r in rows:
        key = (str(r[1]).strip(), r[2], str(r[3]).strip(), r[4], r[5], str(r[6]).strip())
        groups[key].append(r[0])

    dup_groups = [(k, v) for k, v in groups.items() if len(v) > 1]
    if not dup_groups:
        print("Tekrarlayan ders bulunamadı.")
        conn.close()
        sys.exit(0)

    print(f"Toplam {len(dup_groups)} grup tekrarlayan ders bulundu.")
    silinen = 0

    for (ad, fid, kod, kredi, akts, tur), ids in dup_groups:
        ids_sorted = sorted(ids)
        keep_id = ids_sorted[0]
        del_ids = ids_sorted[1:]
        print(f"  '{ad}' -> Tutulacak: {keep_id}, Silinecek: {del_ids}")

        for del_id in del_ids:
            for tbl, col in FK_TABLES:
                try:
                    cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tbl,))
                    if not cur.fetchone():
                        continue
                    cur.execute(f"PRAGMA table_info({tbl})")
                    if not any(r[1] == col for r in cur.fetchall()):
                        continue
                    cur.execute(f"UPDATE {tbl} SET {col}=? WHERE {col}=?", (keep_id, del_id))
                    if cur.rowcount:
                        print(f"    {tbl}: {cur.rowcount} satır güncellendi")
                except Exception as e:
                    print(f"    {tbl} güncelleme hatası: {e}")

            try:
                cur.execute("DELETE FROM ders WHERE ders_id=?", (del_id,))
                if cur.rowcount:
                    silinen += 1
            except Exception as e:
                print(f"    Ders silme hatası (id={del_id}): {e}")

    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()
    print(f"\nTamamlandı. {silinen} tekrar ders silindi.")


if __name__ == "__main__":
    main()
