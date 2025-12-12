import random
from datetime import date, datetime
from faker import Faker
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, engine, Base
from app.db.models import (
    Okul, Fakulte, Bolum, Ogrenci, Ders, Kayit, 
    AnketForm, AnketCevap, AnketSonuclari, Skor, 
    Mufredat, Performans, Populerlik
)

# Tabloları sıfırdan oluştur (Temiz başlangıç)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

fake = Faker('tr_TR')  # Türkçe veri üretici
db: Session = SessionLocal()

print("🚀 Veri üretimi başladı...")

# ---------------------------------------------------------
# 1. OKUL, FAKÜLTE, BÖLÜM OLUŞTURMA
# ---------------------------------------------------------
print("🏫 Okul yapısı kuruluyor...")
okul = Okul(ad="Gaziantep İslam Bilim ve Teknoloji Üniversitesi", kampus="Merkez Kampüs")
db.add(okul)
db.commit()

fakulteler_list = ["Mühendislik Fakültesi", "Sağlık Bilimleri Fakültesi", "İktisadi İdari Bilimler"]
bolumler_map = {
    "Mühendislik Fakültesi": ["Bilgisayar Mühendisliği", "Elektrik-Elektronik Müh.", "Endüstri Müh."],
    "Sağlık Bilimleri Fakültesi": ["Hemşirelik", "Fizyoterapi"],
    "İktisadi İdari Bilimler": ["İşletme", "İktisat"]
}

db_fakulteler = []
db_bolumler = []

for f_ad in fakulteler_list:
    fak = Fakulte(ad=f_ad, okul_id=okul.school_id, tip="Lisans", kampus="Merkez")
    db.add(fak)
    db.commit()
    db_fakulteler.append(fak)
    
    for b_ad in bolumler_map[f_ad]:
        bol = Bolum(ad=b_ad, fakulte_id=fak.fakulte_id)
        db.add(bol)
        db_bolumler.append(bol)

db.commit()

# ---------------------------------------------------------
# 2. DERSLERİ OLUŞTURMA
# ---------------------------------------------------------
print("📚 Dersler ekleniyor...")
ders_isimleri = [
    "Yapay Zeka", "Veri Madenciliği", "Nesne Yönelimli Programlama", 
    "Veritabanı Yönetimi", "İşletim Sistemleri", "Bilgisayar Ağları",
    "Yazılım Mühendisliği", "Web Programlama", "Mobil Uygulama", "Siber Güvenlik",
    "Girişimcilik", "İletişim Becerileri", "Proje Yönetimi", "İş Sağlığı ve Güvenliği"
]

db_dersler = []
muh_fakulte = db_fakulteler[0] # Mühendislik fakültesi

for i, d_ad in enumerate(ders_isimleri):
    ders = Ders(
        kod=f"BİL{300+i}",
        ad=d_ad,
        kredi=random.choice([3, 4, 5]),
        akts=random.choice([4, 5, 6]),
        bilgi=fake.text(max_nb_chars=50),
        tip="Seçmeli" if i > 3 else "Zorunlu", # İlk 4 ders zorunlu olsun
        fakulte_id=muh_fakulte.fakulte_id
    )
    db.add(ders)
    db_dersler.append(ders)

db.commit()

# ---------------------------------------------------------
# 3. ÖĞRENCİLERİ OLUŞTURMA
# ---------------------------------------------------------
print("🎓 Öğrenciler kaydediliyor (300 adet)...")
db_ogrenciler = []

# Öğrenci numarası üretici (Örn: 2020555001)
def generate_student_no(yil, index):
    return f"{yil}555{str(index).zfill(3)}"

for i in range(300):
    giris_yili = random.choice([2020, 2021, 2022, 2023])
    ogr = Ogrenci(
        ad=fake.first_name(),
        soyad=fake.last_name(),
        email=fake.email(),
        ogrenci_no=generate_student_no(giris_yili, i+1),
        fakulte_id=muh_fakulte.fakulte_id
    )
    db.add(ogr)
    db_ogrenciler.append(ogr)

db.commit()

# ---------------------------------------------------------
# 4. GEÇMİŞ DÖNEM NOTLARI (Transkript Simülasyonu)
# ---------------------------------------------------------
print("📝 Notlar giriliyor (Bu biraz sürebilir)...")

# Dönemler
donemler = [
    (2022, "Güz"), (2022, "Bahar"), 
    (2023, "Güz"), (2023, "Bahar")
]

for ogr in db_ogrenciler:
    # Her öğrenci rastgele 5-8 ders almış olsun
    alinan_dersler = random.sample(db_dersler, k=random.randint(5, 8))
    
    for ders in alinan_dersler:
        yil, dnm = random.choice(donemler)
        
        # Not üretimi (Çan eğrisi benzeri: çoğunluk 50-80 arası)
        not_degeri = int(random.triangular(20, 100, 70)) 
        durum = "Geçti" if not_degeri >= 50 else "Kaldı"
        
        kayit = Kayit(
            ogr_id=ogr.ogr_id,
            ders_id=ders.ders_id,
            akademik_yil=yil,
            donem=dnm,
            kayit_turu="Öğrenci",
            kayit_tarih=datetime.now(),
            durum=durum
        )
        db.add(kayit)

db.commit()

# ---------------------------------------------------------
# 5. ANKET VERİLERİ (Gelecek dönem tahmini için)
# ---------------------------------------------------------
print("📊 Anket verileri simüle ediliyor...")

# Aktif bir anket formu
anket_form = AnketForm(
    ad="2024-Güz Dönemi Seçmeli Ders Talep Anketi",
    akademik_yil=2024,
    donem="Güz",
    fakulte_id=muh_fakulte.fakulte_id,
    baslangic_tarih=date.today(),
    aktif_mi=True
)
db.add(anket_form)
db.commit()

# Öğrencilerin %60'ı anket doldurmuş olsun
ankete_katilanlar = random.sample(db_ogrenciler, k=int(len(db_ogrenciler)*0.6))

for ogr in ankete_katilanlar:
    # Öğrenci 3 ders seçsin (Tercih sırasına göre)
    tercihler = random.sample(db_dersler, k=3)
    for rank, ders in enumerate(tercihler, 1):
        cevap = AnketCevap(
            form_id=anket_form.form_id,
            ogr_id=ogr.ogr_id,
            ders_id=ders.ders_id,
            rank=rank, # 1. tercih, 2. tercih...
            puan=100 - (rank * 20), # Basit puanlama: 1.tercih=80p, 2.=60p...
            cevap_tarihi=datetime.now()
        )
        db.add(cevap)

db.commit()

# ---------------------------------------------------------
# 6. PERFORMANS ve POPÜLERLİK ÖZETLERİ (Batch İşlem Simülasyonu)
# ---------------------------------------------------------
print("⚙️ Ders analizleri hesaplanıyor...")

for ders in db_dersler:
    # Bu dersin tüm kayıtlarını bul
    notlar = [k.durum == "Geçti" for k in ders.kayitlar] # Basit başarı kontrolü
    if notlar:
        basari_orani = sum(notlar) / len(notlar)
        ortalama_not = sum([80 for _ in notlar]) / len(notlar) # (Basitleştirilmiş)
    else:
        basari_orani = 0.5
        ortalama_not = 50.0

    perf = Performans(
        ders_id=ders.ders_id,
        akademik_yil=2023,
        donem="Bahar",
        ortalama_not=ortalama_not,
        basari_orani=basari_orani,
        katilimci_sayisi=len(notlar)
    )
    db.add(perf)
    
    # Popülerlik (Anket sonuçlarına göre)
    talep_sayisi = len(ders.anket_cevaplari)
    pop = Populerlik(
        ders_id=ders.ders_id,
        akademik_yil=2024,
        donem="Güz",
        tercih_sayisi=talep_sayisi,
        tercih_orani=talep_sayisi / len(ankete_katilanlar) if ankete_katilanlar else 0
    )
    db.add(pop)

db.commit()

print("✅ TAMAMLANDI! Veritabanı başarıyla dolduruldu.")