import random
import sqlite3

DB_PATH = "data/adil_secmeli.db"

def baglanti_kur():
    return sqlite3.connect(DB_PATH)

def tablolari_yenile():
    """Performans, Popülerlik ve Skor tablolarını sıfırlar ve 4 kriterli yeni şemayı uygular."""
    conn = baglanti_kur()
    cursor = conn.cursor()
    
    print("🧹 Tablolar temizleniyor ve 4 kriterli şema güncelleniyor...")
    
    # Eski tabloları uçur
    tablolar = ["performans", "populerlik", "skor"]
    for t in tablolar:
        cursor.execute(f"DROP TABLE IF EXISTS {t}")
    
    # 1. PERFORMANS TABLOSU
    cursor.execute("""
        CREATE TABLE performans (
            pfrs_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER NOT NULL,
            akademik_yil INTEGER NOT NULL,
            donem TEXT DEFAULT 'Güz',
            ortalama_not REAL,
            basari_orani REAL,
            ham_puan REAL,
            FOREIGN KEY(ders_id) REFERENCES ders(ders_id)
        )
    """)

    # 2. POPÜLERLİK TABLOSU
    cursor.execute("""
        CREATE TABLE populerlik (
            pop_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER NOT NULL,
            akademik_yil INTEGER NOT NULL,
            donem TEXT DEFAULT 'Güz',
            talep_sayisi INTEGER,
            kontenjan INTEGER,
            fakulte_mevcudu INTEGER,
            doluluk_orani REAL,
            ilgi_orani REAL,
            ham_puan REAL,
            FOREIGN KEY(ders_id) REFERENCES ders(ders_id)
        )
    """)

    # 3. SKOR TABLOSU (Trend ve Anket Dahil)
    cursor.execute("""
        CREATE TABLE skor (
            skor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER NOT NULL,
            akademik_yil INTEGER NOT NULL,
            donem TEXT DEFAULT 'Güz',
            skor_top REAL,
            b_norm REAL, -- Başarı
            p_norm REAL, -- Popülerlik
            t_norm REAL, -- Trend
            a_norm REAL, -- Anket
            FOREIGN KEY(ders_id) REFERENCES ders(ders_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Tabloların yapısı (4 Kriter) güncellendi.")

def veri_uret_ve_hesapla():
    """Sadece Mühendislik Müfredatındaki dersler için veri üretir."""
    conn = baglanti_kur()
    cursor = conn.cursor()

    print("\n🔍 Sadece Mühendislik Fakültesi 2022 Müfredatı aranıyor...")

    # --- KRİTİK DÜZELTME BURADA ---
    # Eskiden 'SELECT * FROM ders' yapıyorduk, hepsini alıyordu.
    # Şimdi sadece müfredat tablosunda kaydı olan Mühendislik derslerini çekiyoruz.
    query = """
        SELECT DISTINCT d.ders_id, d.ad 
        FROM mufredat m
        JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
        JOIN ders d ON md.ders_id = d.ders_id
        JOIN bolum b ON m.bolum_id = b.bolum_id
        JOIN fakulte f ON b.fakulte_id = f.fakulte_id
        WHERE m.akademik_yil = 2022
          AND f.ad LIKE '%Mühendislik%'
    """
    cursor.execute(query)
    dersler = cursor.fetchall()
    
    if not dersler:
        print("⚠️ HATA: 2022 yılına ait Mühendislik dersi bulunamadı!")
        print("   Lütfen önce CSV verilerini 'import_real_data.py' ile yüklediğinden emin ol.")
        return

    print(f"📊 Toplam {len(dersler)} mühendislik dersi bulundu. Hesaplama başlıyor...")

    FAKULTE_OGRENCI_SAYISI = 1000
    SABIT_TREND_PUANI = 50.0
    SABIT_ANKET_PUANI = 50.0

    count_elendi = 0

    for ders_id, ders_adi in dersler:
        # 1. PERFORMANS (%15 ihtimalle elenme notu)
        if random.random() < 0.15:
            ortalama_not = random.uniform(30, 49.9)
        else:
            ortalama_not = random.uniform(50, 95)
        
        basari_orani = ortalama_not / 100.0
        perf_puan = ortalama_not 

        cursor.execute("""
            INSERT INTO performans (ders_id, akademik_yil, ortalama_not, basari_orani, ham_puan)
            VALUES (?, 2022, ?, ?, ?)
        """, (ders_id, ortalama_not, basari_orani, perf_puan))

        # 2. POPÜLERLİK
        kontenjan = random.choice([30, 40, 50, 60])
        talep = int(kontenjan * random.uniform(0.2, 1.5))
        doluluk = talep / kontenjan
        if doluluk > 1.0: doluluk = 1.0
        
        ilgi = talep / FAKULTE_OGRENCI_SAYISI
        pop_puan = (doluluk * 70) + (ilgi * 10 * 30)
        if pop_puan > 100: pop_puan = 100

        cursor.execute("""
            INSERT INTO populerlik (ders_id, akademik_yil, talep_sayisi, kontenjan, fakulte_mevcudu, doluluk_orani, ilgi_orani, ham_puan)
            VALUES (?, 2022, ?, ?, ?, ?, ?, ?)
        """, (ders_id, talep, kontenjan, FAKULTE_OGRENCI_SAYISI, doluluk, ilgi, pop_puan))

        # 3. SKOR
        if ortalama_not < 50:
            final_skor = 0
            print(f"❌ {ders_adi[:30]:<30} -> ELENDİ! (Not: {ortalama_not:.1f})")
            count_elendi += 1
        else:
            # Basit Ağırlıklı Ortalama (Main.py'deki AHP öncesi veri doldurma)
            final_skor = (perf_puan * 0.5) + (pop_puan * 0.3) + (SABIT_TREND_PUANI * 0.1) + (SABIT_ANKET_PUANI * 0.1)
        
        cursor.execute("""
            INSERT INTO skor (ders_id, akademik_yil, skor_top, b_norm, p_norm, t_norm, a_norm)
            VALUES (?, 2022, ?, ?, ?, ?, ?)
        """, (ders_id, final_skor, perf_puan, pop_puan, SABIT_TREND_PUANI, SABIT_ANKET_PUANI))

        # Havuz Güncelleme
        cursor.execute("UPDATE havuz SET skor = ? WHERE ders_id = ? AND yil=2022", (final_skor, ders_id))

    conn.commit()
    conn.close()
    print(f"\n✅ İşlem Tamamlandı. {len(dersler)} ders işlendi. ({count_elendi} tanesi baraja takıldı)")

if __name__ == "__main__":
    tablolari_yenile()
    veri_uret_ve_hesapla()