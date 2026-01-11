import sqlite3
import os

def havuz_2022_doldur(fakulte_id=2):
    # Veritabanı yolu
    db_name = "adil_secmeli.db"
    base_dir = os.getcwd()
    db_path = os.path.join(base_dir, "data", db_name)
    if not os.path.exists(db_path):
        db_path = os.path.join(base_dir, db_name)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("⚙️ 2022 Yılı Havuz İşlemleri Başlatılıyor...")

    # ---------------------------------------------------------
    # 1. ADIM: 2022 Yılında Müfredatta Olan Dersler (REFERANS LİSTESİ)
    # ---------------------------------------------------------
    aktif_mufredat_2022 = [
        "Analog Elektronik", "Sinyaller ve Sistemler", "Mikroişlemciler", 
        "Elektrik Enerjisi İletim Sistemleri", "Elektromanyetik Alan Teorisi",
        "Gömülü Sistemler I", "Otomatik Kontrol Sistemleri I", 
        "Güç Elektroniği I", "Yenilenebilir Enerji Kaynakları", "Haberleşme I"
    ]
    
    # Karşılaştırma kolaylığı için hepsini küçük harfe çevirelim
    aktif_mufredat_lower = [d.lower().strip() for d in aktif_mufredat_2022]

    # ---------------------------------------------------------
    # 2. ADIM: Veritabanından İlgili Fakültenin Seçmeli Derslerini Çek
    # ---------------------------------------------------------
    print(f"📡 Fakülte ID: {fakulte_id} için 'Seçmeli' dersler çekiliyor...")
    
    # DÜZELTME BURADA YAPILDI: 'id' yerine 'rowid' kullanıldı.
    cur.execute("""
        SELECT rowid, ad, bolum_id, kredi, akts 
        FROM ders 
        WHERE fakulte_id = ? AND (DersTipi = 'Seçmeli' OR DersTipi = 'Secmeli')
    """, (fakulte_id,))
    
    tum_secmeli_dersler = cur.fetchall()
    
    if not tum_secmeli_dersler:
        print("⚠️ Hata: Bu kriterlere uygun hiç ders bulunamadı! 'ders' tablosunu kontrol et.")
        conn.close()
        return

    print(f"✅ Toplam {len(tum_secmeli_dersler)} adet seçmeli ders bulundu. Analiz başlıyor...\n")

    # ---------------------------------------------------------
    # 3. ADIM: Her Ders İçin Statü, Skor ve Sayaç Hesapla
    # ---------------------------------------------------------
    eklenen_sayisi = 0
    
    for ders in tum_secmeli_dersler:
        db_id = ders[0]      # Artık rowid (otomatik id)
        ders_adi = ders[1]   # Dersin Adı
        bolum_id = ders[2]
        
        # --- OTOMATİK KARAR MEKANİZMASI ---
        # Ders adı aktif listede var mı?
        if ders_adi.lower().strip() in aktif_mufredat_lower:
            # Durum 1: Ders Müfredatta VAR
            statu = 1
            sayac = 0   # Seçildiği için bekleme sayacı artmaz
            skor = 1    # Seçildiği için skor kazanır
            durum_mesaj = "🟢 SEÇİLDİ (Müfredatta Var)"
        else:
            # Durum 2: Ders Müfredatta YOK (Havuzda Bekliyor)
            statu = 0
            sayac = 1   # Seçilmedi, bekleme sayacı 1 oldu
            skor = 0    # Seçilmediği için skor alamaz
            durum_mesaj = "⚪ BEKLİYOR (Havuzda)"

        # Sabit ID oluşturma (Örn: F2B2D15 formatı)
        simulasyon_ders_id = f"F{fakulte_id}B{bolum_id}D{db_id}"

        # Alan Tahmini
        alan = "Genel"
        if "Mat" in ders_adi: alan = "Matematik"
        elif "Elek" in ders_adi: alan = "Elektronik"
        elif "Yazılım" in ders_adi or "Veri" in ders_adi: alan = "Yazılım"
        
        # ---------------------------------------------------------
        # 4. ADIM: Havuz Tablosuna Ekle
        # ---------------------------------------------------------
        # Önce bu ders o yıl için zaten ekli mi kontrol edelim
        cur.execute("SELECT count(*) FROM havuz WHERE ders_id = ? AND yil = ?", (simulasyon_ders_id, 2022))
        if cur.fetchone()[0] == 0:
            cur.execute("""
                INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, alan, statu, sayac, skor, ders_adi)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (simulasyon_ders_id, 2022, fakulte_id, bolum_id, alan, statu, sayac, skor, ders_adi))
            
            print(f"   -> {ders_adi:<35} : {durum_mesaj} | Sayaç:{sayac} Skor:{skor}")
            eklenen_sayisi += 1
        else:
            print(f"   -> {ders_adi:<35} : ⚠️ Zaten Ekli")

    conn.commit()
    conn.close()
    print(f"\n🎉 İşlem Tamamlandı! {eklenen_sayisi} ders 2022 havuzuna işlendi.")

if __name__ == "__main__":
    havuz_2022_doldur(fakulte_id=2)