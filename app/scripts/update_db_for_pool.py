# -*- coding: utf-8 -*-
# =============================================================================
# app/scripts/update_db_for_pool.py — Havuz için veritabanı güncelleme
# =============================================================================
# Proje klasöründe SQLite veritabanını bular; havuz ve ders tablolarına havuz
# yönetimi için gerekli sütunları (statu, sayaç, skor, yıl, alan vb.) ekler.
# =============================================================================

import os
import sqlite3


def find_database_and_upgrade():
    # Terminalin açık olduğu ana klasör
    base_dir = os.getcwd()
    print(f"📂 Arama Başlatılıyor: {base_dir} konumunda taranıyor...")

    target_db_path = None

    # REKÜRSİF ARAMA: Alt klasörlerin hepsine bakar (data, db, app, vb.)
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".db"):
                # Bulunan dosyanın tam yolu
                full_path = os.path.join(root, file)
                print(f"🔎 Veritabanı bulundu: {full_path}")
                target_db_path = full_path
                break # İlk bulduğunu al ve döngüden çık
        if target_db_path:
            break

    if not target_db_path:
        print("❌ HATA: Proje klasörünün hiçbir yerinde .db dosyası bulunamadı!")
        print("   Lütfen .db dosyanı oluşturduğundan emin ol.")
        return

    # --- GÜNCELLEME İŞLEMİ ---
    print(f"🛠️ {os.path.basename(target_db_path)} güncelleniyor...")
    conn = sqlite3.connect(target_db_path)
    cur = conn.cursor()

    try:
        # --- HAVUZ TABLOSU ---
        try:
            cur.execute("ALTER TABLE havuz ADD COLUMN statu INTEGER DEFAULT 0")
            print("✅ Havuz: 'statu' eklendi.")
        except sqlite3.OperationalError:
            pass

        try:
            cur.execute("ALTER TABLE havuz ADD COLUMN sayac INTEGER DEFAULT 0")
            print("✅ Havuz: 'sayac' eklendi.")
        except sqlite3.OperationalError:
            pass

        try:
            cur.execute("ALTER TABLE havuz ADD COLUMN skor REAL DEFAULT 0.0")
            print("✅ Havuz: 'skor' eklendi.")
        except sqlite3.OperationalError:
            pass

        try:
            cur.execute("ALTER TABLE havuz ADD COLUMN yil INTEGER")
            print("✅ Havuz: 'yil' eklendi.")
        except sqlite3.OperationalError:
            pass

        # --- DERS TABLOSU ---
        try:
            cur.execute("ALTER TABLE ders ADD COLUMN alan TEXT DEFAULT 'Genel'")
            print("✅ Ders: 'alan' eklendi.")
        except sqlite3.OperationalError:
            pass

    except Exception as e:
        print(f"⚠️ Bir hata oluştu: {e}")

    conn.commit()
    conn.close()
    print("🏁 İşlem Başarıyla Tamamlandı.")

if __name__ == "__main__":
    find_database_and_upgrade()
