import sqlite3
import pandas as pd
import os
import sys

# ==========================================
# 1. DOSYA YOLLARI VE AYARLAR
# ==========================================
def get_paths():
    base_dir = os.getcwd()
    
    # Veritabanı Yolu (Data klasöründe mi, ana dizinde mi?)
    db_paths = [
        os.path.join(base_dir, "data", "adil_secmeli.db"),
        os.path.join(base_dir, "adil_secimli.db"),
        os.path.join(base_dir, "adil_secmeli.db"),
    ]
    
    db_path = None
    for p in db_paths:
        if os.path.exists(p):
            db_path = p
            break
            
    # CSV Dosyası (İsmini buraya yaz)
    # NOT: İndirdiğin dosyanın adını 'dersler_master.csv' yaparsan daha kolay olur.
    csv_name = "dersler_master.xlsx - Bu tablo henüz çok az bizim büt.csv" 
    csv_path = None
    
    # CSV'yi ara
    search_dirs = [base_dir, os.path.join(base_dir, "data"), os.path.join(base_dir, "app", "etl")]
    for p in search_dirs:
        full_p = os.path.join(p, csv_name)
        if os.path.exists(full_p):
            csv_path = full_p
            break
            
    return db_path, csv_path

# ==========================================
# 2. ANA AKTARIM FONKSİYONU
# ==========================================
def run_import():
    print("🚀 Veri Aktarımı Başlatılıyor...")
    
    db_path, csv_path = get_paths()
    
    if not db_path:
        print("❌ HATA: Veritabanı (.db) dosyası bulunamadı!")
        return
    if not csv_path:
        print("❌ HATA: CSV dosyası bulunamadı! Dosya ismini kodun içinde kontrol et.")
        return

    print(f"📂 DB: {db_path}")
    print(f"📂 CSV: {csv_path}")

    # --- A. CSV OKUMA ---
    try:
        # Türkçe karakter sorunu olmaması için encoding='utf-8' veya 'utf-8-sig' kullanılır.
        df = pd.read_csv(csv_path, encoding='utf-8')
        print("✅ CSV başarıyla okundu.")
        
        # Sütun isimlerini temizle (Boşlukları sil, küçük harf yap)
        df.columns = [c.strip() for c in df.columns]
        print(f"   Sütunlar: {list(df.columns)}")
        
    except Exception as e:
        print(f"❌ CSV Okuma Hatası: {e}")
        return

    # --- B. VERİTABANI BAĞLANTISI ---
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # 1. TEMİZLİK (İsteğe bağlı: Mevcut verileri siler)
        print("🧹 Eski veriler temizleniyor...")
        cur.execute("DELETE FROM ders")
        cur.execute("DELETE FROM bolum")
        cur.execute("DELETE FROM fakulte")
        cur.execute("DELETE FROM sqlite_sequence WHERE name IN ('ders', 'bolum', 'fakulte')")
        conn.commit()

        # 2. ID EŞLEŞTİRME HARİTALARI (Tekrar eklemeyi önlemek için)
        fakulte_map = {} # {"Mühendislik": 1, "Tıp": 2}
        bolum_map = {}   # {"Bilgisayar Müh": 10}

        # İstatistikler
        stats = {"fakulte": 0, "bolum": 0, "ders": 0}

        print("🔄 Veriler işleniyor...")

        for index, row in df.iterrows():
            # --- VERİ HAZIRLIĞI (Sütun isimlerini CSV'ye göre ayarla) ---
            # .get() kullanarak hata almayı önleriz, bulamazsa varsayılan değer döner.
            
            fakulte_adi = str(row.get('FakülteAdı', row.get('Fakülte', 'Genel Fakülte'))).strip()
            # Eğer CSV'de Bölüm adı yoksa, Fakülte adını bölüm gibi kullanırız veya 'Genel' deriz.
            bolum_adi = str(row.get('BölümAdı', row.get('Bölüm', 'Genel Bölüm'))).strip()
            
            ders_adi = str(row.get('DersAdı', row.get('Ders', 'İsimsiz Ders'))).strip()
            ders_kodu = str(row.get('DersKodu', row.get('Kod', f'D-{index}'))).strip()
            
            # İçerik (Description)
            icerik = str(row.get('Icerik', row.get('İçerik', row.get('Aciklama', '')))).strip()
            if icerik.lower() == 'nan': icerik = "İçerik girilmemiş."

            # Kredi / AKTS
            try: kredi = int(float(row.get('Kredi', 3)))
            except: kredi = 3
            
            try: akts = int(float(row.get('AKTS', 5)))
            except: akts = 5

            # --- ADIM 1: FAKÜLTE EKLE ---
            if fakulte_adi not in fakulte_map:
                cur.execute("INSERT INTO fakulte (ad) VALUES (?)", (fakulte_adi,))
                fakulte_map[fakulte_adi] = cur.lastrowid
                stats["fakulte"] += 1
            
            f_id = fakulte_map[fakulte_adi]

            # --- ADIM 2: BÖLÜM EKLE ---
            # Bölüm adını Fakülte ID ile birleştirerek unique yapıyoruz (Farklı fakültede aynı bölüm adı olabilir)
            bolum_key = (f_id, bolum_adi) 
            
            if bolum_key not in bolum_map:
                cur.execute("INSERT INTO bolum (fakulte_id, ad) VALUES (?, ?)", (f_id, bolum_adi))
                bolum_map[bolum_key] = cur.lastrowid
                stats["bolum"] += 1
            
            b_id = bolum_map[bolum_key]

            # --- ADIM 3: DERS EKLE ---
            # Burada 'alan' sütununu 'Bölüm Adı' olarak atıyoruz ki %80 kuralında kullanabilelim.
            cur.execute("""
                INSERT INTO ders (fakulte_id, bolum_id, ad, kod, bilgi, kredi, akts, alan, status, count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            """, (f_id, b_id, ders_adi, ders_kodu, icerik, kredi, akts, bolum_adi))
            
            # Havuz tablosuna da başlangıç kaydı atalım (Algoritma için gerekli)
            d_id = cur.lastrowid
            cur.execute("""
                INSERT INTO havuz (ders_id, fakulte_id, yil, statu, sayac, skor)
                VALUES (?, ?, 2025, 0, 0, 0)
            """, (d_id, f_id))
            
            stats["ders"] += 1

        conn.commit()
        
        print("\n" + "="*40)
        print("🎉 İŞLEM BAŞARIYLA TAMAMLANDI")
        print(f"🏛️  Fakülte Sayısı : {stats['fakulte']}")
        print(f"🎓 Bölüm Sayısı   : {stats['bolum']}")
        print(f"📚 Ders Sayısı    : {stats['ders']}")
        print("="*40)

    except sqlite3.Error as e:
        print(f"🚨 SQL HATASI: {e}")
    except Exception as e:
        print(f"🚨 GENEL HATA: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_import()