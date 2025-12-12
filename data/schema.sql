
-- Veritabanı şeması
CREATE TABLE IF NOT EXISTS fakulte (
    fakulte_id INTEGER PRIMARY KEY,
    ad TEXT NOT NULL,
    kampus TEXT NOT NULL,
    tur TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ders (
    ders_id INTEGER PRIMARY KEY,
    fakulte_id INTEGER,
    kod TEXT NOT NULL,
    ad TEXT NOT NULL,
    kredi INTEGER,
    akts INTEGER,
    tur TEXT CHECK(tur IN ('seçmeli', 'zorunlu')),
    onkosul INTEGER,
    aciklama TEXT,
    FOREIGN KEY(fakulte_id) REFERENCES fakulte(fakulte_id),
    FOREIGN KEY(onkosul) REFERENCES ders(ders_id)
);

CREATE TABLE IF NOT EXISTS ogrenci (
    ogr_id INTEGER PRIMARY KEY,
    fakulte_id INTEGER,
    giris_yili INTEGER,
    durum TEXT CHECK(durum IN ('aktif', 'mezun', 'donuk')),
    FOREIGN KEY(fakulte_id) REFERENCES fakulte(fakulte_id)
);

CREATE TABLE IF NOT EXISTS kayit (
    kayit_id INTEGER PRIMARY KEY,
    ogr_id INTEGER,
    ders_id INTEGER,
    akademik_yil INTEGER,
    donem TEXT CHECK(donem IN ('güz', 'bahar')),
    kayit_turu TEXT CHECK(kayit_turu IN ('otomatik atanmis', 'ogrenci secmis')),
    durum TEXT CHECK(durum IN ('basarili', 'basarisiz', 'cikmis')),
    harf_notu TEXT,
    puan FLOAT,
    FOREIGN KEY(ogr_id) REFERENCES ogrenci(ogr_id),
    FOREIGN KEY(ders_id) REFERENCES ders(ders_id)
);

CREATE TABLE IF NOT EXISTS ders_performans_ozeti (
    ders_id INTEGER,
    akademik_yil INTEGER,
    donem TEXT CHECK(donem IN ('güz', 'bahar')),
    ortalama_not FLOAT,
    basari_orani FLOAT,
    katilimci_sayisi INTEGER,
    PRIMARY KEY (ders_id, akademik_yil, donem),
    FOREIGN KEY(ders_id) REFERENCES ders(ders_id)
);

CREATE TABLE IF NOT EXISTS popuarlik_olcumu (
    ders_id INTEGER,
    akademik_yil INTEGER,
    donem TEXT CHECK(donem IN ('güz', 'bahar')),
    tercih_sayisi INTEGER,
    tercih_orani FLOAT,
    PRIMARY KEY (ders_id, akademik_yil, donem),
    FOREIGN KEY(ders_id) REFERENCES ders(ders_id)
);

CREATE TABLE IF NOT EXISTS anket (
    ders_id INTEGER,
    akademik_yil INTEGER,
    donem TEXT CHECK(donem IN ('güz', 'bahar')),
    oy_1 INTEGER,
    oy_2 INTEGER,
    oy_3 INTEGER,
    ortalama_oy FLOAT,
    PRIMARY KEY (ders_id, akademik_yil, donem),
    FOREIGN KEY(ders_id) REFERENCES ders(ders_id)
);

CREATE TABLE IF NOT EXISTS uygunluk_engel (
    ogr_id INTEGER,
    ders_id INTEGER,
    engel_baslangic INTEGER,
    engel_bitis INTEGER,
    PRIMARY KEY (ogr_id, ders_id),
    FOREIGN KEY(ogr_id) REFERENCES ogrenci(ogr_id),
    FOREIGN KEY(ders_id) REFERENCES ders(ders_id)
);

CREATE TABLE IF NOT EXISTS kontenjan (
    ders_id INTEGER,
    donem TEXT CHECK(donem IN ('güz', 'bahar')),
    kontenjan INTEGER,
    PRIMARY KEY (ders_id, donem),
    FOREIGN KEY(ders_id) REFERENCES ders(ders_id)
);
