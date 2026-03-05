#!/usr/bin/env python3
# Veritabanına anket sütunlarını ekler.
# Uygulama KAPALI iken çalıştırın.

import os
import sqlite3
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "adil_secmeli.db")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DB_PATH
    if not os.path.exists(path):
        print(f"Hata: Veritabanı bulunamadı: {path}")
        sys.exit(1)

    conn = sqlite3.connect(path, timeout=10)
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ders_kriterleri'")
    if not cur.fetchone():
        print("ders_kriterleri tablosu yok. Önce kriter sayfasını açıp tabloyu oluşturun.")
        conn.close()
        sys.exit(0)

    cur.execute("PRAGMA table_info(ders_kriterleri)")
    cols = {row[1] for row in cur.fetchall()}

    eklenen = []
    for col, default in [("anket_katilimci", "0"), ("anket_dersi_secen", "0")]:
        if col not in cols:
            cur.execute(f"ALTER TABLE ders_kriterleri ADD COLUMN {col} INTEGER DEFAULT {default}")
            conn.commit()
            eklenen.append(col)

    if eklenen:
        print(f"Eklendi: {', '.join(eklenen)}")
    else:
        print("Anket sütunları zaten mevcut.")

    conn.close()
    print("Tamamlandı.")


if __name__ == "__main__":
    main()
