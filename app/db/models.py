# models.py
from sqlalchemy import (
    Column, Integer, String, ForeignKey, Date, DateTime, Boolean, Float, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.db.database import Base


# ---------------------------
# 1) OKUL
# ---------------------------
class Okul(Base):
    __tablename__ = "okul"

    school_id = Column(Integer, primary_key=True, index=True)
    ad = Column(String, nullable=False)
    kampus = Column(String)

    fakulteler = relationship("Fakulte", back_populates="okul")


# ---------------------------
# (Ek) BÖLÜM  -> Mufredat.Bolum_ID için asgari tablo
# ---------------------------
class Bolum(Base):
    __tablename__ = "bolum"

    bolum_id = Column(Integer, primary_key=True, index=True)
    ad = Column(String, nullable=False)
    fakulte_id = Column(Integer, ForeignKey("fakulte.fakulte_id"), nullable=False)

    fakulte = relationship("Fakulte", back_populates="bolumler")
    mufredatlar = relationship("Mufredat", back_populates="bolum")


# ---------------------------
# 2) FAKÜLTE
# ---------------------------
class Fakulte(Base):
    __tablename__ = "fakulte"

    fakulte_id = Column(Integer, primary_key=True, index=True)
    ad = Column(String, nullable=False)
    okul_id = Column(Integer, ForeignKey("okul.school_id"), nullable=False)
    tip = Column(String)                     # Lisans / Lisansüstü
    kampus = Column(String)

    okul = relationship("Okul", back_populates="fakulteler")
    bolumler = relationship("Bolum", back_populates="fakulte")
    dersler = relationship("Ders", back_populates="fakulte")
    ogretim_gorevlileri = relationship("OgretimGorevlisi", back_populates="fakulte")
    havuz_kayitlari = relationship("Havuz", back_populates="fakulte")


# ---------------------------
# (Ek) ÖĞRENCİ -> Ogr_ID referansları için asgari tablo
# ---------------------------
class Ogrenci(Base):
    __tablename__ = "ogrenci"

    ogr_id = Column(Integer, primary_key=True, index=True)
    ad = Column(String, nullable=False)
    soyad = Column(String, nullable=False)
    email = Column(String)
    ogrenci_no = Column(String, unique=True)
    fakulte_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))

    fakulte = relationship("Fakulte")
    kayitlar = relationship("Kayit", back_populates="ogrenci")
    anket_cevaplari = relationship("AnketCevap", back_populates="ogrenci")
    engeller = relationship("OgrenciEngel", back_populates="ogrenci")


# ---------------------------
# 3) DERS
# ---------------------------
class Ders(Base):
    __tablename__ = "ders"

    ders_id = Column(Integer, primary_key=True, index=True)
    kod = Column(String)
    ad = Column(String, nullable=False)
    kredi = Column(Integer)
    akts = Column(Integer)
    onkosul = Column(Integer, ForeignKey("ders.ders_id"), nullable=True)  # self-FK
    bilgi = Column(Text)            # açıklama/bilgi
    tip = Column(String)            # seçmeli / zorunlu vb.
    fakulte_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))

    fakulte = relationship("Fakulte", back_populates="dersler")
    havuz_kayitlari = relationship("Havuz", back_populates="ders")
    ders_ogretim   = relationship("DersOgretim", back_populates="ders")
    kayitlar       = relationship("Kayit", back_populates="ders")
    performanslar  = relationship("Performans", back_populates="ders")
    populerlikler  = relationship("Populerlik", back_populates="ders")
    skorlar        = relationship("Skor", back_populates="ders")
    anket_cevaplari = relationship("AnketCevap", back_populates="ders")


# ---------------------------
# 4) HAVUZ
# ---------------------------
class Havuz(Base):
    __tablename__ = "havuz"

    havuz_id = Column(Integer, primary_key=True, index=True)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    fakulte_id = Column(Integer, ForeignKey("fakulte.fakulte_id"), nullable=False)

    secilebilirlik_durumu = Column(Boolean, default=True)
    kontenjan_durumu = Column(String)        # 'Açık', 'Dolu', 'Bekleme' vb.
    on_kosul_durumu = Column(String)         # metin/flag (öğrenciye özel değil)
    ogrenci_dinlendirme_durumu = Column(String)  # metin/flag
    acilis_tarihi = Column(Date)
    kapanis_tarihi = Column(Date)
    durum_degeri = Column(Float)             # skor/öncelik gibi sayısal bir değer

    ders = relationship("Ders", back_populates="havuz_kayitlari")
    fakulte = relationship("Fakulte", back_populates="havuz_kayitlari")


# ---------------------------
# 5) ÖĞRETİM GÖREVLİSİ
# ---------------------------
class OgretimGorevlisi(Base):
    __tablename__ = "ogretim_gorevlisi"

    ogrt_id = Column(Integer, primary_key=True, index=True)
    ad = Column(String, nullable=False)
    soyad = Column(String, nullable=False)
    unvan = Column(String)
    email = Column(String)
    tel = Column(String)
    durum = Column(String)           # Aktif/Pasif/İzinli vb.
    bilgi = Column(Text)
    memnuniyet_puani = Column(Float)
    kidem_yil = Column(Integer)
    atanma_tarihi = Column(Date)

    school_id = Column(Integer, ForeignKey("okul.school_id"))
    fakulte_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    basarim_ort = Column(Float)

    okul = relationship("Okul")
    fakulte = relationship("Fakulte", back_populates="ogretim_gorevlileri")
    ders_gorevleri = relationship("DersOgretim", back_populates="ogretim_gorevlisi")
    kayitlar = relationship("Kayit", back_populates="ogretim_gorevlisi")
    performanslar = relationship("Performans", back_populates="ogretim_gorevlisi")


# ---------------------------
# 6) DERS_ÖĞRETİM
# ---------------------------
class DersOgretim(Base):
    __tablename__ = "ders_ogretim"

    ders_ogrt_id = Column(Integer, primary_key=True, index=True)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    ogrt_id = Column(Integer, ForeignKey("ogretim_gorevlisi.ogrt_id"), nullable=False)

    rol = Column(String)           # Ana Eğitmen / Yardımcı / Asistan
    donem = Column(String)         # Güz/Bahar
    akademik_yil = Column(Integer)
    ders_saati = Column(Integer)
    katki_oran = Column(Float)     # %0-100
    not_ortalaması = Column(Float) # eğitmenin bu dersteki ortalaması
    kontenjan = Column(Integer)

    ders = relationship("Ders", back_populates="ders_ogretim")
    ogretim_gorevlisi = relationship("OgretimGorevlisi", back_populates="ders_gorevleri")

    __table_args__ = (
        UniqueConstraint("ders_id", "ogrt_id", "akademik_yil", "donem",
                         name="uq_ders_ogrt_yil_donem"),
    )


# ---------------------------
# 7) MÜFREDAT
# ---------------------------
class Mufredat(Base):
    __tablename__ = "mufredat"

    mufredat_id = Column(Integer, primary_key=True, index=True)
    fakulte_id = Column(Integer, ForeignKey("fakulte.fakulte_id"), nullable=False)
    akademik_yil = Column(Integer, nullable=False)
    bolum_id = Column(Integer, ForeignKey("bolum.bolum_id"))
    donem = Column(String)         # Güz/Bahar
    durum = Column(String)         # Taslak/Onaylı vb.
    versiyon = Column(Integer, default=1)

    fakulte = relationship("Fakulte")
    bolum = relationship("Bolum", back_populates="mufredatlar")
    dersler = relationship("MufredatDers", back_populates="mufredat")


# ---------------------------
# 8) MÜFREDAT–DERS
# ---------------------------
class MufredatDers(Base):
    __tablename__ = "mufredat_ders"

    mders_id = Column(Integer, primary_key=True, index=True)
    mufredat_id = Column(Integer, ForeignKey("mufredat.mufredat_id"), nullable=False)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)

    mufredat = relationship("Mufredat", back_populates="dersler")
    ders = relationship("Ders")

    __table_args__ = (
        UniqueConstraint("mufredat_id", "ders_id", name="uq_mufredat_ders"),
    )


# ---------------------------
# 9) KAYIT
# ---------------------------
class Kayit(Base):
    __tablename__ = "kayit"

    kayit_id = Column(Integer, primary_key=True, index=True)
    ogr_id = Column(Integer, ForeignKey("ogrenci.ogr_id"), nullable=False)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    akademik_yil = Column(Integer, nullable=False)
    donem = Column(String, nullable=False)
    kayit_turu = Column(String)     # otomatik / ogrenci
    kayit_tarih = Column(DateTime)
    durum = Column(String)          # basarili/basarisiz/cikmis vb.
    ogrt_id = Column(Integer, ForeignKey("ogretim_gorevlisi.ogrt_id"))

    ogrenci = relationship("Ogrenci", back_populates="kayitlar")
    ders = relationship("Ders", back_populates="kayitlar")
    ogretim_gorevlisi = relationship("OgretimGorevlisi", back_populates="kayitlar")


# ---------------------------
# 10) PERFORMANS
# ---------------------------
class Performans(Base):
    __tablename__ = "performans"

    pfrs_id = Column(Integer, primary_key=True, index=True)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    akademik_yil = Column(Integer, nullable=False)
    donem = Column(String, nullable=False)
    ogrt_id = Column(Integer, ForeignKey("ogretim_gorevlisi.ogrt_id"))

    ortalama_not = Column(Float)
    basari_orani = Column(Float)     # 0..1 ya da yüzde
    katilimci_sayisi = Column(Integer)

    ders = relationship("Ders", back_populates="performanslar")
    ogretim_gorevlisi = relationship("OgretimGorevlisi", back_populates="performanslar")

    __table_args__ = (
        UniqueConstraint("ders_id", "akademik_yil", "donem", "ogrt_id",
                         name="uq_performans_dersterm_ogrt"),
    )


# ---------------------------
# 11) POPÜLERLİK
# ---------------------------
class Populerlik(Base):
    __tablename__ = "populerlik"

    pop_id = Column(Integer, primary_key=True, index=True)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    akademik_yil = Column(Integer, nullable=False)
    donem = Column(String, nullable=False)

    tercih_sayisi = Column(Integer)
    tercih_orani = Column(Float)

    ders = relationship("Ders", back_populates="populerlikler")

    __table_args__ = (
        UniqueConstraint("ders_id", "akademik_yil", "donem", name="uq_pop_dersterm"),
    )


# ---------------------------
# 12) ANKET_FORM
# ---------------------------
class AnketForm(Base):
    __tablename__ = "anket_form"

    form_id = Column(Integer, primary_key=True, index=True)
    ad = Column(String)
    akademik_yil = Column(Integer, nullable=False)
    donem = Column(String, nullable=False)
    fakulte_id = Column(Integer, ForeignKey("fakulte.fakulte_id"))
    baslangic_tarih = Column(Date)
    bitis_tarih = Column(Date)
    aktif_mi = Column(Boolean, default=True)
    aciklama = Column(Text)

    fakulte = relationship("Fakulte")
    cevaplar = relationship("AnketCevap", back_populates="form")
    sonuclar = relationship("AnketSonuclari", back_populates="form")


# ---------------------------
# 13) ANKET_CEVAP  (Top-3/Borda)
# ---------------------------
class AnketCevap(Base):
    __tablename__ = "anket_cevap"

    cevap_id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("anket_form.form_id"), nullable=False)
    ogr_id = Column(Integer, ForeignKey("ogrenci.ogr_id"), nullable=False)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)

    rank = Column(Integer)           # 1,2,3
    siddet = Column(Integer)         # 1..5 (opsiyonel)
    puan = Column(Float)             # hesaplanan (Borda * siddet/5)
    cevap_tarihi = Column(DateTime)
    ip_hash = Column(String(128))

    form = relationship("AnketForm", back_populates="cevaplar")
    ogrenci = relationship("Ogrenci", back_populates="anket_cevaplari")
    ders = relationship("Ders", back_populates="anket_cevaplari")

    __table_args__ = (
        UniqueConstraint("form_id", "ogr_id", "ders_id", name="uq_anket_tekoy"),
    )


# ---------------------------
# 14) ANKET_SONUCLARI (özet)
# ---------------------------
class AnketSonuclari(Base):
    __tablename__ = "anket_sonuclari"

    anketsonuc_id = Column(Integer, primary_key=True, index=True)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    form_id = Column(Integer, ForeignKey("anket_form.form_id"), nullable=False)

    toplam_puan = Column(Float)
    oy_sayisi = Column(Integer)
    ortalama_siddet = Column(Float)
    a_norm = Column(Float)
    hesaplanma_tarihi = Column(DateTime)

    ders = relationship("Ders")
    form = relationship("AnketForm", back_populates="sonuclar")

    __table_args__ = (
        UniqueConstraint("form_id", "ders_id", name="uq_anket_sonuc_form_ders"),
    )


# ---------------------------
# 15) SKOR
# ---------------------------
class Skor(Base):
    __tablename__ = "skor"

    skor_id = Column(Integer, primary_key=True, index=True)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    akademik_yil = Column(Integer, nullable=False)
    donem = Column(String, nullable=False)

    b_norm = Column(Float)     # Başarı
    p_norm = Column(Float)     # Popülerlik
    a_norm = Column(Float)     # Anket
    g_norm = Column(Float)     # Geçmiş (varsa)
    skor_top = Column(Float)
    hesap_tarih = Column(DateTime)

    ders = relationship("Ders", back_populates="skorlar")

    __table_args__ = (
        UniqueConstraint("ders_id", "akademik_yil", "donem", name="uq_skor_dersterm"),
    )


# ---------------------------
# 16) ÖĞRENCİ_ENGEL
# ---------------------------
class OgrenciEngel(Base):
    __tablename__ = "ogrenci_engel"

    engel_id = Column(Integer, primary_key=True, index=True)
    ogr_id = Column(Integer, ForeignKey("ogrenci.ogr_id"), nullable=False)
    ders_id = Column(Integer, ForeignKey("ders.ders_id"), nullable=False)
    engel_baslangic = Column(Date)
    engel_bitis = Column(Date)
    neden = Column(Text)

    ogrenci = relationship("Ogrenci", back_populates="engeller")
    ders = relationship("Ders")
