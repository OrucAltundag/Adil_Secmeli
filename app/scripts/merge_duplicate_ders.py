#!/usr/bin/env python3
# =============================================================================
# Tekrarlayan Dersleri Birleştir (merge_duplicate_ders.py)
# =============================================================================
# Aynı isimde (ve aynı fakültede) birden fazla ders kaydı varsa, en küçük ID'yi
# tutar ve diğerlerini siler. Tüm FK referansları güncellenir. Unique constraint
# çakışmaları çözülür.
#
# Kullanım: python -m app.scripts.merge_duplicate_ders [db_path]
# Örnek:   python -m app.scripts.merge_duplicate_ders data/adil_secmeli.db
# =============================================================================

import json
import os
import sqlite3
import sys
from collections import defaultdict

# Varsayılan DB yolu
BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB = os.path.join(BASE, "data", "adil_secmeli.db")

# ders_id referansı olan tablolar
FK_TABLES = [
    ("kayit", "ders_id", None),
    ("performans", "ders_id", ["ders_id", "akademik_yil", "donem"]),  # unique key
    ("populerlik", "ders_id", ["ders_id", "akademik_yil", "donem"]),
    ("skor", "ders_id", ["ders_id", "akademik_yil", "donem"]),
    ("ders_kriterleri", "ders_id", ["ders_id", "yil"]),
    ("mufredat_ders", "ders_id", ["mufredat_id", "ders_id"]),
    ("anket_cevap", "ders_id", ["form_id", "ogr_id", "ders_id"]),
    ("anket_sonuclari", "ders_id", ["form_id", "ders_id"]),
    ("ders_ogretim", "ders_id", ["ders_id", "ogrt_id", "akademik_yil", "donem"]),
    ("ogrenci_engel", "ders_id", None),
    ("havuz", "ders_id", None),  # ders_id TEXT - ozel islem
]

# Kontrol edilecek tablolar (yoksa atla)
OPTIONAL_TABLES = ["kontenjan", "anket"]


def table_exists(cur, name):
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None


def column_exists(cur, table, col):
    cur.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cur.fetchall())


def get_dup_groups(cur, by_name_only=False):
    """Tekrarlayan ders gruplarını döner. (ad, fakulte_id) veya sadece (ad) ile grupla."""
    if by_name_only:
        cur.execute("""
            SELECT ad, NULL as fid, COUNT(*), GROUP_CONCAT(ders_id)
            FROM ders GROUP BY ad HAVING COUNT(*) > 1
        """)
        return [(r[0], r[1], r[2], [int(x) for x in r[3].split(",")]) for r in cur.fetchall()]
    else:
        cur.execute("""
            SELECT ad, COALESCE(fakulte_id,0), COUNT(*), GROUP_CONCAT(ders_id)
            FROM ders GROUP BY ad, COALESCE(fakulte_id,0) HAVING COUNT(*) > 1
        """)
        return [(r[0], r[1], r[2], [int(x) for x in r[3].split(",")]) for r in cur.fetchall()]


def merge_duplicates(conn, dup_groups, dry_run=False, verbose=False):
    cur = conn.cursor()
    silinen_ders = 0
    guncellenen = defaultdict(int)

    for ad, fakulte_id, count, ids in dup_groups:
        ids_sorted = sorted(ids)
        keep_id = ids_sorted[0]
        del_ids = ids_sorted[1:]

        if verbose:
            print(f"  '{ad}' (fakulte={fakulte_id}) -> Tut: {keep_id}, Sil: {del_ids}")

        for del_id in del_ids:
            # 1. ders.onkosul - del_id'ye referans varsa keep_id'ye cevir
            try:
                cur.execute("UPDATE ders SET onkosul=? WHERE onkosul=?", (keep_id, del_id))
                if cur.rowcount:
                    guncellenen["ders(onkosul)"] += cur.rowcount
            except Exception as e:
                if verbose:
                    print(f"    ders onkosul: {e}")

            # 2. FK tablolar
            for tbl, col, unique_cols in FK_TABLES:
                if not table_exists(cur, tbl) or not column_exists(cur, tbl, col):
                    continue
                try:
                    if tbl == "havuz":
                        # havuz.ders_id TEXT - hem str hem int eslesebilir
                        cur.execute(
                            f"UPDATE {tbl} SET {col}=? WHERE CAST({col} AS TEXT)=?",
                            (str(keep_id), str(del_id))
                        )
                    else:
                        cur.execute(f"UPDATE {tbl} SET {col}=? WHERE {col}=?", (keep_id, del_id))

                    updated = cur.rowcount
                    if updated:
                        guncellenen[tbl] += updated

                    # Unique constraint: Guncelleme sonrasi duplicate satirlari sil
                    if unique_cols and updated:
                        # SQLite: Ayni unique key'e sahip fazla satirdan birini tut
                        cols_str = ", ".join(unique_cols)
                        cur.execute(f"""
                            DELETE FROM {tbl} WHERE rowid NOT IN (
                                SELECT MIN(rowid) FROM {tbl} GROUP BY {cols_str}
                            )
                        """)
                        if cur.rowcount:
                            guncellenen[f"{tbl}(dup)"] += cur.rowcount
                except Exception as e:
                    if verbose:
                        print(f"    {tbl}: {e}")

            # Opsiyonel tablolar
            for tbl in OPTIONAL_TABLES:
                if not table_exists(cur, tbl) or not column_exists(cur, tbl, "ders_id"):
                    continue
                try:
                    cur.execute(f"UPDATE {tbl} SET ders_id=? WHERE ders_id=?", (keep_id, del_id))
                    if cur.rowcount:
                        guncellenen[tbl] += cur.rowcount
                except Exception:
                    pass

            # 3. Duplicate dersi sil
            if not dry_run:
                cur.execute("DELETE FROM ders WHERE ders_id=?", (del_id,))
                if cur.rowcount:
                    silinen_ders += 1

    return silinen_ders, dict(guncellenen)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    by_name = "--name-only" in sys.argv
    verbose = "-v" in sys.argv or "--verbose" in sys.argv

    # DB yolu
    if args:
        path = args[0]
    else:
        os.chdir(BASE)
        if os.path.exists("config.json"):
            try:
                with open("config.json", encoding="utf-8") as f:
                    path = json.load(f).get("db_path", DEFAULT_DB)
            except Exception:
                path = DEFAULT_DB
        else:
            path = DEFAULT_DB

    if not os.path.exists(path):
        print(f"Hata: Veritabanı bulunamadı: {path}")
        sys.exit(1)

    print(f"Veritabanı: {path}")
    if dry_run:
        print("(Dry-run: Değişiklik yapılmayacak)")

    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = OFF")
    cur = conn.cursor()

    dup_groups = get_dup_groups(cur, by_name_only=by_name)
    if not dup_groups:
        print("Tekrarlayan ders bulunamadı.")
        conn.close()
        sys.exit(0)

    total_dup = sum(g[2] - 1 for g in dup_groups)  # Silinecek ders sayisi
    print(f"Toplam {len(dup_groups)} grup tekrarlayan ders ({total_dup} adet silinecek)")

    if dry_run:
        for ad, fid, count, ids in dup_groups[:10]:
            print(f"  '{ad}': tutulacak {min(ids)}, silinecek {sorted(ids)[1:]}")
        if len(dup_groups) > 10:
            print(f"  ... ve {len(dup_groups)-10} grup daha")
        conn.close()
        sys.exit(0)

    silinen, guncellenen = merge_duplicates(conn, dup_groups, dry_run=False, verbose=verbose)
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()

    print(f"\nTamamlandı.")
    print(f"  Silinen ders: {silinen}")
    for tbl, cnt in sorted(guncellenen.items()):
        if cnt:
            print(f"  {tbl}: {cnt} satır güncellendi")


if __name__ == "__main__":
    main()
