import sqlite3
import os

def recreate_havuz_table():
    # Veritabanı dosyasını bul
    db_name = "adil_secmeli.db"
    base_dir = os.getcwd()
    db_path = os.path.join(base_dir, "data", db_name)
    if not os.path.exists(db_path):
        db_path = os.path.join(base_dir, db_name)

    print(f"📂 Veritabanı: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        print("🧹 Eski 'havuz' tablosu siliniyor...")
        cur.execute("DROP TABLE IF EXISTS havuz")

        print("🏗️ Yeni 'havuz' tablosu oluşturuluyor...")
        # Senin kurallarına uygun, eksiksiz tablo yapısı
        cur.execute("""
        CREATE TABLE havuz (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id TEXT,        -- Örn: F2B1D15
            yil INTEGER,         -- Örn: 2022
            fakulte_id INTEGER,  -- Örn: 2
            bolum_id INTEGER,    -- Örn: 1 (Eksik olan buydu)
            alan TEXT,           -- Örn: Yazılım
            statu INTEGER,       -- 1: Müfredatta, 0: Havuzda, -1: Yasaklı
            sayac INTEGER,       -- Seçilmeme sayısı
            skor INTEGER,        -- Seçilme performansı
            ders_adi TEXT        -- Kontrol için ders adı
        )
        """)
        
        conn.commit()
        print("✅ Başarılı! 'havuz' tablosu 'bolum_id' sütunuyla birlikte yeniden kuruldu.")

    except Exception as e:
        print(f"❌ Hata: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    recreate_havuz_table()