
-- Örnek veriler
-- Fakülteler
INSERT INTO fakulte (fakulte_id, ad, kampus, tur) VALUES (1, 'Mühendislik Fakültesi', 'İstanbul', 'lisans');
INSERT INTO fakulte (fakulte_id, ad, kampus, tur) VALUES (2, 'Fen Fakültesi', 'Ankara', 'lisans');
INSERT INTO fakulte (fakulte_id, ad, kampus, tur) VALUES (3, 'İktisat Fakültesi', 'İzmir', 'lisansüstü');

-- Dersler
INSERT INTO ders (ders_id, fakulte_id, kod, ad, kredi, akts, tur, onkosul, aciklama) VALUES (1, 1, 'MATH101', 'Matematik I', 4, 5, 'seçmeli', NULL, 'Temel matematik dersidir.');
INSERT INTO ders (ders_id, fakulte_id, kod, ad, kredi, akts, tur, onkosul, aciklama) VALUES (2, 1, 'ENGR101', 'Makine Mühendisliği', 3, 4, 'seçmeli', NULL, 'Makine mühendisliği temelleri.');
INSERT INTO ders (ders_id, fakulte_id, kod, ad, kredi, akts, tur, onkosul, aciklama) VALUES (3, 2, 'CHEM101', 'Kimya I', 4, 5, 'seçmeli', NULL, 'Kimya dersleri.');

-- Öğrenciler
INSERT INTO ogrenci (ogr_id, fakulte_id, giris_yili, durum) VALUES (101, 1, 2022, 'aktif');
INSERT INTO ogrenci (ogr_id, fakulte_id, giris_yili, durum) VALUES (102, 2, 2021, 'aktif');
INSERT INTO ogrenci (ogr_id, fakulte_id, giris_yili, durum) VALUES (103, 3, 2023, 'donuk');

-- Kayıtlar
INSERT INTO kayit (kayit_id, ogr_id, ders_id, akademik_yil, donem, kayit_turu, durum, harf_notu, puan) VALUES (1, 101, 1, 2025, 'güz', 'otomatik atanmis', 'basarili', 'A', 90.5);
INSERT INTO kayit (kayit_id, ogr_id, ders_id, akademik_yil, donem, kayit_turu, durum, harf_notu, puan) VALUES (2, 102, 2, 2025, 'bahar', 'ogrenci secmis', 'basarisiz', 'F', 45.0);

-- Anket
INSERT INTO anket (ders_id, akademik_yil, donem, oy_1, oy_2, oy_3, ortalama_oy) VALUES (1, 2025, 'güz', 3, 4, 5, 4.0);
