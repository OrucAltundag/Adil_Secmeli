import sqlite3
import os

DB_PATH = "data/adil_secmeli.db"

def havuzu_doldur():
    if not os.path.exists(DB_PATH):
        print("❌ Veritabanı dosyası bulunamadı!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("🚀 Mühendislik Fakültesi (ID=2) Havuz Doldurma İşlemi Başladı...")

    # 1. Fakülte Kontrolü
    cursor.execute("SELECT ad FROM fakulte WHERE fakulte_id = 2")
    res = cursor.fetchone()
    if res:
        print(f"✅ Hedef Fakülte: {res[0]} (ID: 2)")
    else:
        print("⚠️ UYARI: Fakülte ID=2 veritabanında bulunamadı! İşlem boş dönebilir.")

    # 2. Temizlik
    print("🧹 Eski havuz kayıtları temizleniyor...")
    cursor.execute("DELETE FROM havuz WHERE fakulte_id = 2 AND yil BETWEEN 2022 AND 2025")

    # 3. Seçmeli Dersleri Çek
    print("🔍 Seçmeli dersler aranıyor...")
    
    # HATA ÇÖZÜMÜ: Kolon adı 'tip' yerine 'DersTipi' yapıldı.
    # Her ihtimale karşı try-except ile kontrol ediyoruz.
    try:
        cursor.execute("""
            SELECT ders_id, ad 
            FROM ders 
            WHERE fakulte_id = 2 AND (DersTipi = 'Seçmeli' OR DersTipi = 'Secmeli')
        """)
        dersler = cursor.fetchall()
    except sqlite3.OperationalError:
        # Eğer DersTipi de yoksa, kolon adlarını yazdırıp kullanıcıya gösterelim
        print("❌ HATA: 'DersTipi' kolonu da bulunamadı.")
        print("   Mevcut kolonlar şunlar:")
        cursor.execute("PRAGMA table_info(ders)")
        cols = [info[1] for info in cursor.fetchall()]
        print(f"   👉 {cols}")
        conn.close()
        return

    if not dersler:
        print("❌ HATA: Fakülte ID=2 için hiç 'Seçmeli' ders bulunamadı.")
        conn.close()
        return

    print(f"📊 Toplam {len(dersler)} adet seçmeli ders bulundu. Yıllara dağıtılıyor...")

    kayit_sayisi = 0
    yillar = [2022, 2023, 2024, 2025]

    for yil in yillar:
        for ders_id, ders_adi in dersler:
            # Varsayılan değerler: Statü 0 (Havuzda), Sayaç 0, Skor 0
            cursor.execute("""
                INSERT INTO havuz (ders_id, fakulte_id, yil, statu, sayac, skor)
                VALUES (?, 2, ?, 0, 0, 0)
            """, (ders_id, yil))
            kayit_sayisi += 1

    conn.commit()
    conn.close()
    
    print("-" * 40)
    print(f"✅ İŞLEM TAMAMLANDI!")
    print(f"Toplam {kayit_sayisi} satır havuza eklendi.")
    print("-" * 40)
    print("👉 Şimdi uygulamayı açıp 'Pool' sekmesinden her yılı kontrol edebilirsin.")

if __name__ == "__main__":
    havuzu_doldur()