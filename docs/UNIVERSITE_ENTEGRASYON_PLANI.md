# Üniversite Entegrasyonu — Adım Adım Plan

Bu belge, Adil Seçmeli sisteminin gerçek bir üniversite ortamına entegre edilmesi için adım adım planı içerir. Her adım: **Ekle → Test et → Hata varsa sınıflandır** mantığıyla ilerler.

---

## Genel Strateji

1. **Önce ekle, sonra test et** — Değişiklikleri küçük adımlarla yapın.
2. **Her adımda test** — Değişiklikten sonra uygulamayı çalıştırıp hata olup olmadığını kontrol edin.
3. **Hata sınıflandırması** — Hataları kritik / orta / düşük olarak sınıflandırın; önce kritikleri giderin.

---

## Faz 1: Temel Altyapı (Tamamlandı)

| Adım | İşlem | Durum | Test |
|------|-------|-------|------|
| 1.1 | `requirements.txt` oluşturma | ✅ | `pip install -r requirements.txt` |
| 1.2 | REST API endpoint'leri (dersler, skorlar, havuz, mufredat, fakulteler) | ✅ | `uvicorn app.api.main:app` → http://localhost:8000/docs |
| 1.3 | SQL injection düzeltmeleri (tools_tab, pool_tab, course_analysis_tab) | ✅ | Masaüstü uygulamasını çalıştır, Rapor/Havuz sekmelerini kullan |
| 1.4 | test_db.py düzeltme | ✅ | `python -m pytest app/tests/test_db.py -v` |

---

## Faz 2: Kimlik Doğrulama ve Roller (Öncelik: Yüksek)

| Adım | İşlem | Tahmini süre | Test |
|------|-------|--------------|------|
| 2.1 | Basit API auth (API Key veya Bearer token) | 2–4 saat | API'ye token ile istek at |
| 2.2 | Rol tablosu ve model (Öğrenci, Danışman, Admin) | 2 saat | ORM ile rol sorgula |
| 2.3 | Endpoint bazlı rol kontrolü (örn. `/admin/*` sadece Admin) | 2–3 saat | Farklı rollerle istek dene |

**Hata sınıflandırması (Faz 2):**
- Kritik: Token doğrulanmıyor, yanlış rol erişimi
- Orta: Token süresi, refresh token
- Düşük: Rate limiting, loglama

---

## Faz 3: Veri Entegrasyonu (Öncelik: Yüksek)

| Adım | İşlem | Tahmini süre | Test |
|------|-------|--------------|------|
| 3.1 | Excel şablonu oluştur (data/ ornek_import.xlsx) | 1 saat | Şablonu doldur, import et |
| 3.2 | Toplu kriter Excel import (criteria_page'e "Excel'den Yükle" butonu) | 3–4 saat | Excel yükle, performans/popülerlik kontrol et |
| 3.3 | OBS export formatı dokümantasyonu | 1 saat | OBS'den export al, şablonla karşılaştır |

**Hata sınıflandırması (Faz 3):**
- Kritik: Kolon eşleşmezse import bozulur
- Orta: Encoding, tarih formatı
- Düşük: Boş satır, tekrarlanan ders

---

## Faz 4: API Genişletme (Öncelik: Orta)

| Adım | İşlem | Tahmini süre | Test |
|------|-------|--------------|------|
| 4.1 | POST /api/v1/dersler (yeni ders ekleme) | 2 saat | Swagger'dan POST dene |
| 4.2 | PUT /api/v1/skorlar (skor güncelleme) | 1–2 saat | Skor güncelle, doğrula |
| 4.3 | GET /api/v1/oneri/{ogrenci_id} (öğrenciye öneri) | 4–6 saat | assignment_engine ile entegre |

**Hata sınıflandırması (Faz 4):**
- Kritik: FK ihlali, null constraint
- Orta: Validasyon (alan adı, sayı aralığı)
- Düşük: Pagination, sıralama

---

## Faz 5: Denetim ve Loglama (Öncelik: Orta)

| Adım | İşlem | Tahmini süre | Test |
|------|-------|--------------|------|
| 5.1 | Kritik işlemlerde log (skor güncelleme, atama, config değişikliği) | 2–3 saat | İşlem yap, log dosyasını kontrol et |
| 5.2 | API istek loglama (middleware) | 1–2 saat | İstek at, logda görünsün |
| 5.3 | Audit tablosu (kim, ne zaman, ne yaptı) | 3–4 saat | Değişiklik sonrası audit kaydı kontrol |

---

## Faz 6: Masaüstü Uygulaması İyileştirmeleri (Öncelik: Düşük)

| Adım | İşlem | Tahmini süre | Test |
|------|-------|--------------|------|
| 6.1 | Hata mesajlarını Türkçeleştir | 1–2 saat | Bilinçli hata tetikle |
| 6.2 | Kurulum sihirbazı (ilk çalıştırmada DB oluştur) | 2–3 saat | Yeni ortamda çalıştır |
| 6.3 | Güncelleme kontrolü | 1 saat | Versiyon karşılaştır |

---

## Test Kontrol Listesi (Her Faz Sonrası)

- [ ] Masaüstü uygulaması açılıyor mu? (`python -m app.main` veya `python app/main.py`)
- [ ] Veritabanı seçip tablolar görüntüleniyor mu?
- [ ] Hesaplama sekmesi çalışıyor mu? (Algoritma çalıştır)
- [ ] Kriter sayfası kaydetme çalışıyor mu?
- [ ] API çalışıyor mu? (`uvicorn app.api.main:app` → /docs)
- [ ] Testler geçiyor mu? (`pytest app/tests/ -v`)

---

## Hata Sınıflandırma Şablonu

| Seviye | Açıklama | Örnek |
|--------|----------|-------|
| **Kritik** | Uygulama çalışmıyor, veri kaybı riski | Import hatası, DB bağlantı hatası |
| **Orta** | Özellik bozuk, geçici çözüm var | API 500 hatası, UI donması |
| **Düşük** | Görsel/kullanım sorunu | Yazım hatası, yavaş açılış |

---

## Önerilen Çalışma Sırası

1. **Faz 2** (Auth) — Üniversite güvenlik gereksinimi
2. **Faz 3** (Veri) — OBS ile veri alışverişi
3. **Faz 4** (API genişletme) — Dış sistem entegrasyonu
4. **Faz 5** (Loglama) — Denetim ihtiyacı
5. **Faz 6** (Masaüstü) — Kullanıcı deneyimi

Her fazdan sonra test kontrol listesini uygulayın; kritik hata varsa sonraki faza geçmeyin.
