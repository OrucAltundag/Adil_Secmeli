import sqlite3

def reset_database_stats(db_path='proje_veritabani.db'):
    try:
        # Veritabanına bağlan
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # SQL Sorgusu: Şartsız (WHERE olmadan) güncelleme tüm satırları etkiler
        update_query = """
        UPDATE havuz 
        SET statu = 0, 
            sayac = 0, 
            skor = 0;
        """
        
        cursor.execute(update_query)
        conn.commit() # Değişiklikleri kaydet
        
        print(f"✅ İşlem Başarılı: Tüm derslerin statu, sayaç ve skor değerleri 0landı.")
        print(f"Etkilenen satır sayısı: {cursor.rowcount}")

    except sqlite3.Error as e:
        print(f"❌ Bir hata oluştu: {e}")
        
    finally:
        if conn:
            conn.close()

# Kullanımı: Kendi veritabanı dosya adını yaz
# reset_database_stats('okul_projesi.db')