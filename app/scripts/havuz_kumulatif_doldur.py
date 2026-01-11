import sqlite3
import os

def get_mufredat_listeleri():
    """
    Senin verdiğin metinden 2023 ve 2024 Elektrik-Elektronik derslerini çıkardım.
    """
    return {
        2023: [
            "Yenilenebilir Enerji Kaynakları", "Güç Elektroniği I", "Sayısal İşaret İşleme", 
            "Mikroişlemciler", "Elektrik Enerjisi Dağıtımı", "Otomatik Kontrol Sistemleri II", 
            "Gömülü Sistemler II", "Endüstriyel Otomasyon", "Haberleşme II", "Matlab ile Sayısal Analiz"
        ],
        2024: [
            "Elektrik Enerjisi Dağıtımı", "Güç Elektroniği II", "Sayısal İşaret İşleme", 
            "Yüksek Gerilim Tekniği", "Nanoelektronik", "Gömülü Sistemler II", "Robotik", 
            "Endüstriyel Otomasyon", "Bilgisayar Destekli Devre Analizi", "Antenler ve Propagasyon"
        ]
    }

def kumulatif_yil_doldur(hedef_yil, fakulte_id=2):
    db_name = "adil_secmeli.db"
    base_dir = os.getcwd()
    db_path = os.path.join(base_dir, "data", db_name)
    if not os.path.exists(db_path):
        db_path = os.path.join(base_dir, db_name)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    onceki_yil = hedef_yil - 1
    print(f"\n🔄 {hedef_yil} Yılı İşleniyor (Referans: {onceki_yil})...")
    
    # 1. ADIM: Önceki yılın verilerini çek (Havuz tablosundan)
    # Bize lazım olan: ders_id, sayac, skor (Geçmiş verisi)
    cur.execute("""
        SELECT ders_id, ders_adi, sayac, skor, bolum_id, alan 
        FROM havuz 
        WHERE yil = ? AND fakulte_id = ?
    """, (onceki_yil, fakulte_id))
    
    gecmis_veriler = cur.fetchall()
    
    if not gecmis_veriler:
        print(f"❌ Hata: {onceki_yil} yılına ait veri bulunamadı! Önce o yılı doldurmalısın.")
        return

    # 2. ADIM: Hedef Yılın Müfredatını Al
    mufredat_katalogu = get_mufredat_listeleri()
    aktif_dersler = [d.lower().strip() for d in mufredat_katalogu.get(hedef_yil, [])]
    
    eklenen = 0
    for veri in gecmis_veriler:
        # Veri Paketi: (ders_id, ders_adi, eski_sayac, eski_skor, bolum_id, alan)
        ders_kod = veri[0]
        ders_ad = veri[1]
        eski_sayac = veri[2]
        eski_skor = veri[3]
        bolum_id = veri[4]
        alan = veri[5]
        
        # --- KARAR MEKANİZMASI (BUSINESS LOGIC) ---
        if ders_ad.lower().strip() in aktif_dersler:
            # Ders SEÇİLDİ
            yeni_statu = 1
            yeni_skor = eski_skor + 1  # Skor artar
            yeni_sayac = eski_sayac    # Sayaç artmaz (veya kurala göre sıfırlanabilir, şimdilik sabit tutuyoruz)
            durum = "🟢 SEÇİLDİ"
        else:
            # Ders SEÇİLMEDİ (Havuza Gitti)
            yeni_statu = 0
            yeni_skor = eski_skor      # Skor değişmez
            yeni_sayac = eski_sayac + 1 # Bekleme süresi artar
            durum = "⚪ HAVUZDA"
            
        # 3. ADIM: Yeni Yılı Kaydet
        # Çift kaydı engellemek için önce kontrol
        cur.execute("SELECT count(*) FROM havuz WHERE ders_id = ? AND yil = ?", (ders_kod, hedef_yil))
        if cur.fetchone()[0] == 0:
            cur.execute("""
                INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, alan, statu, sayac, skor, ders_adi)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ders_kod, hedef_yil, fakulte_id, bolum_id, alan, yeni_statu, yeni_sayac, yeni_skor, ders_ad))
            
            # Sadece seçilenleri ve durumu değişenleri ekrana bas ki kalabalık olmasın
            if yeni_statu == 1 or yeni_sayac > 2:
                print(f"   -> {ders_ad:<35} : {durum} | Sayaç: {eski_sayac}->{yeni_sayac} | Skor: {eski_skor}->{yeni_skor}")
            eklenen += 1
            
    conn.commit()
    print(f"✅ {hedef_yil} tamamlandı. {eklenen} ders işlendi.")
    conn.close()

if __name__ == "__main__":
    # Zincirleme Çalıştırma
    # Not: 2022 zaten doluydu, o yüzden 2023 ve 2024'ü çalıştırıyoruz.
    kumulatif_yil_doldur(2023)
    kumulatif_yil_doldur(2024)