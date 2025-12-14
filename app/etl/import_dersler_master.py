import sqlite3
import pandas as pd
import os
import sys

# ==========================================
# AKILLI DOSYA BULUCU (PATH FINDER)
# ==========================================
def find_file(filename, search_paths):
    """Dosyayı belirtilen yollarda arar, bulursa tam yolunu döner."""
    for path in search_paths:
        full_path = os.path.join(path, filename)
        if os.path.exists(full_path):
            return full_path
    return None

# ==========================================
# AYARLAR VE BAŞLANGIÇ
# ==========================================
def run_import():
    print("🚀 Veri Aktarımı Başlatılıyor...")

    # Çalıştığın ana dizin (Adil_Secmeli_Python)
    base_dir = os.getcwd()
    print(f"📂 Çalışma Dizini: {base_dir}")

    # Dosya İsimleri (Eğer farklıysa buradan değiştir)
    db_name = "adil_secmeli.db"  # ✅ Doğru (e harfi ile)
    excel_name = "dersler_master.xlsx"

    # Nerelere bakılsın? (Ana dizin ve data klasörü)
    search_dirs = [base_dir, os.path.join(base_dir, "data")]

    # 1. DOSYALARI BUL
    db_path = find_file(db_name, search_dirs)
    excel_path = find_file(excel_name, search_dirs)

    # --- HATA KONTROLÜ ---
    if not db_path:
        print(f"\n❌ KRİTİK HATA: '{db_name}' dosyası bulunamadı!")
        print(f"🔍 Şu konumlara bakıldı:")
        for p in search_dirs: print(f"   - {os.path.join(p, db_name)}")
        print("💡 İPUCU: Dosya isminde harf hatası olabilir mi? (secimli vs secmeli)")
        return

    if not excel_path:
        print(f"\n❌ KRİTİK HATA: '{excel_name}' dosyası bulunamadı!")
        return

    print(f"✅ Veritabanı bulundu: {db_path}")
    print(f"✅ Excel bulundu: {excel_path}")

    # 2. EXCEL OKUMA
    print("\n📂 Excel okunuyor...")
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"❌ Excel okuma hatası: {e}")
        return

    # 3. VERİTABANI İŞLEMLERİ
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # --- AŞAMA 1: TEMİZLİK (SIFIRLAMA) ---
        print("🧹 Tablolar temizleniyor...")
        
        cur.execute("PRAGMA foreign_keys = OFF;")
        
        # Tabloları temizle
        cur.execute("DELETE FROM ders;")
        cur.execute("DELETE FROM fakulte;")
        
        # Sayaçları sıfırla
        try:
            cur.execute("DELETE FROM sqlite_sequence WHERE name='ders';")
            cur.execute("DELETE FROM sqlite_sequence WHERE name='fakulte';")
        except sqlite3.OperationalError:
            pass # Eğer sqlite_sequence yoksa sorun yok
        
        conn.commit()
        print("✅ Temizlik tamamlandı.")

        # --- AŞAMA 2: FAKÜLTELER ---
        print("🏛️  Fakülteler oluşturuluyor...")
        
        unique_fakulteler = df['FakülteAdı'].dropna().unique()
        unique_fakulteler.sort()

        fakulte_id_map = {} 

        for fak_adi in unique_fakulteler:
            fak_adi = str(fak_adi).strip()
            if not fak_adi: continue

            # Varsayılan değerlerle ekle
            cur.execute("""
                INSERT INTO fakulte (ad, okul_id, tip, kampus) 
                VALUES (?, ?, ?, ?)
            """, (fak_adi, 1, "Lisans", "Merkez"))
            
            new_id = cur.lastrowid
            fakulte_id_map[fak_adi] = new_id
            print(f"   -> Eklendi: {fak_adi} (ID: {new_id})")

        conn.commit()

        # --- AŞAMA 3: DERSLER ---
        print("\n📚 Dersler aktarılıyor...")
        
        added = 0
        skipped = 0

        for index, row in df.iterrows():
            fakulte_adi_excel = str(row.get('FakülteAdı')).strip()
            f_id = fakulte_id_map.get(fakulte_adi_excel)

            if f_id is None:
                skipped += 1
                continue

            # Verileri hazırla (Güvenli Dönüşüm)
            kod = str(row.get('DersID')).strip() if pd.notna(row.get('DersID')) else f"KOD-{index}"
            ad = str(row.get('DersAdı')).strip()
            
            # Kredi/AKTS Hesapla
            try:
                kredi = int(float(row.get('Kredi', 0)))
                if kredi == 0:
                    kredi = int(float(row.get('Teorik', 0))) + int(float(row.get('Uygulama', 0)))
            except: kredi = 0
            
            try: akts = int(float(row.get('AKTS', 0)))
            except: akts = 0
            
            tip = str(row.get('DersTipi', 'Seçmeli')).strip()
            bilgi = str(row.get('Icerik', '')).strip()
            if bilgi.lower() == 'nan': bilgi = ""

            # Veritabanına Ekle
            cur.execute("""
                INSERT INTO ders (kod, ad, kredi, akts, onkosul, bilgi, tip, fakulte_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (kod, ad, kredi, akts, 0, bilgi, tip, f_id))
            
            added += 1

        conn.commit()
        cur.execute("PRAGMA foreign_keys = ON;")

        print("\n" + "="*40)
        print("🎉 İŞLEM BAŞARIYLA TAMAMLANDI")
        print(f"🏛️  Fakülte Sayısı : {len(fakulte_id_map)}")
        print(f"📖 Eklenen Ders  : {added}")
        if skipped > 0:
            print(f"⚠️ Atlanan (Fakültesiz): {skipped}")
        print("="*40)

    except sqlite3.Error as e:
        print(f"🚨 SQL HATASI: {e}")
        conn.rollback()
    except Exception as e:
        print(f"🚨 GENEL HATA: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    run_import()