import random
import time
from datetime import date, datetime
from faker import Faker
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine, Base
from app.db.models import (
    Okul, Fakulte, Bolum, Ogrenci, Ders, Kayit, 
    AnketForm, AnketCevap, AnketSonuclari, Skor, 
    Mufredat, Performans, Populerlik
)

# --- AYARLAR ---
OGRENCI_SAYISI = 1500    # Toplam Öğrenci
GECMIS_YIL_SAYISI = 3    # 2022, 2023, 2024
ANKET_KATILIM_ORANI = 0.75

fake = Faker('tr_TR')
db: Session = SessionLocal()

def log(msg):
    print(f"[GİBTÜ-BigData] {msg}")

def clean_db():
    log("Veritabanı temizleniyor...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

# --- GERÇEKÇİ GİBTÜ VERİLERİ ---
GIBTU_YAPI = {
    "Mühendislik ve Doğa Bilimleri Fakültesi": {
        "Bilgisayar Mühendisliği": [
            "Yapay Zeka Temelleri", "Veri Madenciliği", "Siber Güvenlik", "Bulut Bilişim",
            "Mobil Uygulama Geliştirme", "Oyun Programlama", "Görüntü İşleme", "Nesnelerin İnterneti (IoT)"
        ],
        "Elektrik-Elektronik Mühendisliği": [
            "Yenilenebilir Enerji", "Gömülü Sistemler", "Robotik", "Sinyal İşleme",
            "Otomasyon Sistemleri", "Güç Elektroniği"
        ],
        "Endüstri Mühendisliği": [
            "Yöneylem Araştırması", "Tedarik Zinciri Yönetimi", "Kalite Kontrol", "Ergonomi",
            "Proje Yönetimi", "Verimlilik Analizi"
        ]
    },
    "Sağlık Bilimleri Fakültesi": {
        "Hemşirelik": [
            "İlk Yardım", "Halk Sağlığı", "İletişim Becerileri", "Sağlık Psikolojisi",
            "Hasta Güvenliği", "Geriatri"
        ],
        "Fizyoterapi ve Rehabilitasyon": [
            "Sporcu Sağlığı", "Manuel Terapi", "Egzersiz Fizyolojisi", "Hidroterapi",
            "Kinezyoloji"
        ]
    },
    "İslami İlimler Fakültesi": {
        "İslami İlimler": [
            "Osmanlı Türkçesi", "Hat Sanatı", "Din Psikolojisi", "Din Sosyolojisi",
            "İslam Tarihi", "Arapça Metin Okumaları"
        ]
    },
    "Güzel Sanatlar ve Tasarım Fakültesi": {
        "Gastronomi ve Mutfak Sanatları": [
            "Dünya Mutfakları", "Gıda Hijyeni", "Yiyecek İçecek İşletmeciliği", "Türk Mutfağı",
            "Mutfak Kültürü", "Menü Planlama"
        ]
    }
}

# Ortak Seçmeli Dersler (Rektörlük Servis Dersleri gibi)
ORTAK_SECMELILER = [
    "Gönüllülük Çalışmaları", "Kariyer Planlama", "Dijital Okuryazarlık",
    "Girişimcilik Kültürü", "Bilim Tarihi", "İş Sağlığı ve Güvenliği",
    "Eleştirel Düşünme", "Etkili Sunum Teknikleri"
]

def run():
    start_time = time.time()
    clean_db()

    # ---------------------------------------------------------
    # 1. OKUL, FAKÜLTE VE BÖLÜMLER
    # ---------------------------------------------------------
    log("GİBTÜ Akademik Birimleri kuruluyor...")
    okul = Okul(ad="Gaziantep İslam Bilim ve Teknoloji Üniversitesi", kampus="Merkez Kampüs")
    db.add(okul)
    db.commit()

    fakulte_objeleri = {} # İsim -> Obje
    bolum_objeleri = []   # Tüm bölümler listesi
    ders_havuzu = []      # Oluşturulan tüm dersler

    for fak_ad, bolumler_dict in GIBTU_YAPI.items():
        fak = Fakulte(ad=fak_ad, okul_id=okul.school_id, tip="Lisans", kampus="Merkez")
        db.add(fak)
        db.commit()
        fakulte_objeleri[fak_ad] = fak

        for bolum_ad, ders_listesi in bolumler_dict.items():
            bol = Bolum(ad=bolum_ad, fakulte_id=fak.fakulte_id)
            db.add(bol)
            db.commit()
            bolum_objeleri.append(bol)

            # --- DERSLERİ OLUŞTUR (Bölüme Özel) ---
            for d_ad in ders_listesi:
                # Rastgele zorluk ve popülerlik katsayısı
                zorluk = random.uniform(0.3, 0.9)
                pop_katsayi = random.uniform(0.2, 0.95)
                
                # Ders kodunu bölüm baş harflerinden üret (örn: BLM301)
                prefix = bolum_ad[:3].upper().replace("İ", "I").replace("Ü", "U").replace("Ş", "S")
                kod = f"{prefix}{random.randint(200, 499)}"

                ders = Ders(
                    kod=kod,
                    ad=d_ad,
                    kredi=random.choice([3, 4]),
                    akts=random.choice([4, 5, 6]),
                    tip="Seçmeli",
                    fakulte_id=fak.fakulte_id,
                    bilgi=f"Bölüm:{bolum_ad}|Zorluk:{zorluk:.2f}"
                )
                ders.zorluk = zorluk # RAM'de sakla
                ders.pop_katsayi = pop_katsayi
                ders.bolum_id_ref = bol.bolum_id # İlişkilendirme için tutuyoruz
                
                db.add(ders)
                ders_havuzu.append(ders)
    
    # --- ORTAK SEÇMELİ DERSLERİ EKLE ---
    genel_fakulte = list(fakulte_objeleri.values())[0] # Rastgele birine bağlayalım şimdilik
    for d_ad in ORTAK_SECMELILER:
        ders = Ders(
            kod=f"OSD{random.randint(100, 900)}",
            ad=d_ad,
            kredi=2,
            akts=3,
            tip="Genel Seçmeli",
            fakulte_id=genel_fakulte.fakulte_id,
            bilgi="Zorluk:0.3|Ortak"
        )
        ders.zorluk = 0.3 # Ortak dersler genelde kolaydır
        ders.pop_katsayi = 0.9 # Ve popülerdir
        ders.bolum_id_ref = None # Tüm bölümler alabilir
        db.add(ders)
        ders_havuzu.append(ders)

    db.commit()
    log(f"Toplam {len(ders_havuzu)} adet ders tanımlandı.")

    # ---------------------------------------------------------
    # 2. ÖĞRENCİLER
    # ---------------------------------------------------------
    log(f"{OGRENCI_SAYISI} adet öğrenci oluşturuluyor...")
    ogrenciler = []
    
    # 2021 girişli 4. sınıflar, 2022 3. sınıflar vb.
    giris_yillari = [2021, 2022, 2023, 2024]
    
    for i in range(OGRENCI_SAYISI):
        # Öğrenciye bir bölüm ata
        bolum = random.choice(bolum_objeleri)
        giris_yili = random.choice(giris_yillari)
        
        # Potansiyel (GANO benzeri etki için)
        potansiyel = random.gauss(0.65, 0.15) # Ortalaması biraz yüksek olsun
        potansiyel = max(0.2, min(0.98, potansiyel))

        ogr = Ogrenci(
            ad=fake.first_name(),
            soyad=fake.last_name(),
            ogrenci_no=f"{giris_yili}{str(bolum.bolum_id).zfill(2)}{str(i).zfill(3)}",
            fakulte_id=bolum.fakulte_id,
            email=fake.email()
        )
        # RAM'de sakla
        ogr.potansiyel = potansiyel
        ogr.bolum = bolum
        ogr.giris_yili = giris_yili
        
        db.add(ogr)
        ogrenciler.append(ogr)
    
    db.commit()

    # ---------------------------------------------------------
    # 3. TARİHSEL VERİ (TRANSKRİPT)
    # ---------------------------------------------------------
    log("Geçmiş dönem notları simüle ediliyor...")
    
    yillar = [2022, 2023, 2024] # İşlenecek akademik yıllar
    donemler = ["Güz", "Bahar"]
    kayitlar = []
    performans_cache = {}

    for yil in yillar:
        for donem in donemler:
            log(f"   -> {yil} {donem} işleniyor...")
            
            for ogr in ogrenciler:
                # Öğrenci henüz okula başlamadıysa ders alamaz
                if ogr.giris_yili > yil:
                    continue
                
                # Hangi dersleri alabilir? 
                # 1. Kendi bölümünün seçmelileri
                # 2. Ortak seçmeliler
                uygun_dersler = [d for d in ders_havuzu if d.bolum_id_ref == ogr.bolum.bolum_id or d.bolum_id_ref is None]
                
                # O dönem kaç ders aldı?
                ders_sayisi = random.randint(2, 4)
                secilenler = random.sample(uygun_dersler, k=min(len(uygun_dersler), ders_sayisi))
                
                for ders in secilenler:
                    # NOT FORMÜLÜ: (Potansiyel * 70) + (Ders Kolaylığı * 20) + Şans
                    # Not: Ders.zorluk 0.9 ise kolaylık 0.1'dir.
                    base_score = (ogr.potansiyel * 75) + ((1 - ders.zorluk) * 20)
                    noise = random.uniform(-10, 10)
                    final_grade = int(base_score + noise)
                    
                    # 100'ü geçmesin, 0'ın altına düşmesin
                    final_grade = max(15, min(100, final_grade))
                    
                    durum = "Geçti" if final_grade >= 50 else "Kaldı"
                    
                    k = Kayit(
                        ogr_id=ogr.ogr_id,
                        ders_id=ders.ders_id,
                        akademik_yil=yil,
                        donem=donem,
                        kayit_turu="Öğrenci",
                        durum=durum,
                    )
                    k.not_degeri = final_grade # Performans hesaplaması için geçici
                    kayitlar.append(k)
                    
                    # Performans cache
                    key = (ders.ders_id, yil, donem)
                    if key not in performans_cache: performans_cache[key] = []
                    performans_cache[key].append(final_grade)
            
            # Dönem sonu kaydet
            db.bulk_save_objects(kayitlar)
            kayitlar = []
    
    db.commit()

    # ---------------------------------------------------------
    # 4. PERFORMANS ÖZETLERİ (TREND İÇİN KRİTİK)
    # ---------------------------------------------------------
    log("Ders performans özetleri oluşturuluyor...")
    perf_objs = []
    for (d_id, yil, dnm), notlar in performans_cache.items():
        avg = sum(notlar) / len(notlar)
        gecen = len([n for n in notlar if n >= 50])
        
        p = Performans(
            ders_id=d_id,
            akademik_yil=yil,
            donem=dnm,
            ortalama_not=avg,
            basari_orani=gecen / len(notlar),
            katilimci_sayisi=len(notlar)
        )
        perf_objs.append(p)
    db.bulk_save_objects(perf_objs)
    db.commit()

    # ---------------------------------------------------------
    # 5. GELECEK DÖNEM ANKETİ
    # ---------------------------------------------------------
    log("2025 Güz Dönemi anketleri toplanıyor...")
    
    # Öğrenciler kendi bölümlerine ve popüler derslere oy verir
    form = AnketForm(ad="2025 Güz Ön Talep", akademik_yil=2025, donem="Güz", aktif_mi=True)
    db.add(form)
    db.commit()

    anketler = []
    pop_map = {}
    
    katilimcilar = [o for o in ogrenciler if o.giris_yili <= 2024] # Aktif öğrenciler
    # %75 katılım
    katilimcilar = random.sample(katilimcilar, int(len(katilimcilar) * ANKET_KATILIM_ORANI))

    for ogr in katilimcilar:
        uygun = [d for d in ders_havuzu if d.bolum_id_ref == ogr.bolum.bolum_id or d.bolum_id_ref is None]
        # Popülerlik katsayısına göre ağırlıklı seçim
        weights = [d.pop_katsayi for d in uygun]
        secilenler = random.choices(uygun, weights=weights, k=3)
        secilenler = list(set(secilenler)) # Tekrarı önle

        for rank, ders in enumerate(secilenler, 1):
            ac = AnketCevap(
                form_id=form.form_id,
                ogr_id=ogr.ogr_id,
                ders_id=ders.ders_id,
                rank=rank,
                puan=100 - (rank * 20),
                cevap_tarihi=datetime.now()
            )
            anketler.append(ac)
            pop_map[ders.ders_id] = pop_map.get(ders.ders_id, 0) + 1
            
    db.bulk_save_objects(anketler)
    
    # Popülerlik tablosunu doldur
    pops = []
    for d_id, count in pop_map.items():
        po = Populerlik(
            ders_id=d_id,
            akademik_yil=2025,
            donem="Güz",
            tercih_sayisi=count,
            tercih_orani=count/len(katilimcilar)
        )
        pops.append(po)
    db.bulk_save_objects(pops)
    db.commit()

    end_time = time.time()
    log(f"✅ GİBTÜ VERİ SETİ TAMAMLANDI! Süre: {end_time - start_time:.2f}sn")

if __name__ == "__main__":
    run()