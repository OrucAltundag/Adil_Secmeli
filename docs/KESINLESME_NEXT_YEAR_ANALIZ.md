# Kesinleşme Puanı ve Next Year Algoritması – Analiz Raporu

## 1. İlgili Dosyalar

| Dosya | Rol |
|-------|-----|
| `app/services/calculation.py` | Kesinleşme puanı: `get_faculty_year_topsis_results`, `_read_course_metrics`, `topsis_calistir`, `persist_faculty_year_topsis_scores`. Next year: `generate_next_year_curricula`, `_has_generation_criteria`, `_get_curriculum_course_ids`. |
| `app/services/course_analyzer.py` | Tek ders analizi: `_run_topsis_single` → `get_faculty_year_topsis_results` çağrısı; skor buradan gelir. |
| `app/ui/tabs/pool_tab.py` | Havuz sekmesi: `get_faculty_year_topsis_results` + `persist_faculty_year_topsis_scores` ile yıl bazlı skor hesaplatır ve yazar. |
| `app/main.py` | `fill_pool_table_for_years`: Havuz seed (skor=NULL). Açılışta otomatik üretim. |

---

## 2. Mevcut Akış

### 2.1 Kesinleşme puanının hesaplandığı yerler

- **Toplu hesap (fakülte + yıl):**  
  `get_faculty_year_topsis_results(cur, fakulte_id, akademik_yil, donem)`  
  - Fakültedeki seçmeli dersler + o yıl müfredattaki dersler “aday” olur.  
  - Her aday için `_read_course_metrics` (basari, trend, populerlik, anket, ortalama_not).  
  - Tüm adaylar tek DataFrame’de `topsis_calistir` ile işlenir → Kesinlesme_Puani = ci * 100.  
  - Sonuç `skor_map` olarak döner; `persist_faculty_year_topsis_scores` havuz.skor’a yazar.

- **Tek ders analizi:**  
  `course_analyzer._run_topsis_single` → yine `get_faculty_year_topsis_results(..., include_course_ids={course_id})` çağrılır; skor bu paketten alınır.

- **Müfredatta / havuzda bilgisi:**  
  `_get_curriculum_course_ids(cur, fakulte_id, akademik_yil, donem)`  
  → Müfredat tablosundan (mufredat + mufredat_ders + bolum) o fakülte/yıl/dönem dersleri döner.  
  Bu set dışındaki seçmeli dersler “müfredatta değil / havuzda bekleyen” kabul edilir.

### 2.2 Next year akışı ve validasyon

- **generate_next_year_curricula:**  
  - Fakülte + yıl için bölümler alınır.  
  - Her bölüm için o yıl müfredatı (mevcut_mufredatlar) yüklenir.  
  - **Eksik kriter kontrolü:** Sadece `mevcut_mufredatlar` içindeki derslerde yapılır; `_effective_prev_state` ile “müfredatta kabul edilen” (prev_curriculum_ids) derslerde `_has_generation_criteria` çağrılır.  
  - `_has_generation_criteria`: Sadece `ders_kriterleri` içinden toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, kontenjan, kayitli_ogrenci kontrol eder; **anket alanlarına bakmaz.**  
  - Müfredatta olmayan dersler zaten mevcut_mufredatlar’da yok → validasyona dahil değil.

Sonuç: Next year validasyonu fiilen “fakülte bazlı, sadece müfredattaki derslerin zorunlu kriterleri” ile çalışıyor; anket zorunlu değil. Metin/uyarılar netleştirilebilir; mantık değişikliği minimal.

---

## 3. Sorunun Kaynağı (İstenen Kurallara Göre)

1. **2022 başlangıç 50:**  
   Şu an havuz satırları `fill_pool_table_for_years` ile skor=NULL ekleniyor; skor ilk kez TOPSIS çalışınca atanıyor. Müfredatta olmayan dersler de tam TOPSIS’e giriyor; 50 başlangıç kuralı yok.

2. **Müfredat dışı derslerde tek etken anket:**  
   Şu an müfredat dışı dersler de aynı TOPSIS pipeline’ında (basari, trend, populerlik, anket). İstenen: müfredat dışında **sadece anket** puanı etkilesin, etki küçük ve kontrollü olsun.

3. **Küçük ve kontrollü değişim:**  
   Tam TOPSIS 0–100 aralığında dağıtıyor. Müfredat dışı için 50 merkezli, dar band (örn. 50 ± 10) isteniyor.

4. **Next year / validasyon:**  
   Zaten sadece müfredat dersleri kontrol ediliyor ve anket zorunlu değil. Sadece hata mesajları ve dokümantasyon “sadece müfredat dersleri, anket zorunlu değil” diye netleştirilebilir.

---

## 4. Değişiklik Planı (Kısa Maddeler)

1. **calculation.py – Sabitler**  
   - Müfredat dışı dersler için: `POOL_DEFAULT_SCORE = 50.0`, `POOL_ANKET_SCORE_SPREAD = 10.0` (50 ± 10) gibi anlamlı sabitler ekle.

2. **calculation.py – Müfredat dışı puan fonksiyonu**  
   - `_pool_course_score_anket_only(anket_ratio)` ekle: anket 0–1; yoksa/None ise 0.5 kabul et; score = 50 + (anket - 0.5) * 2 * SPREAD → [50-SPREAD, 50+SPREAD] aralığında, deterministik.

3. **calculation.py – get_faculty_year_topsis_results**  
   - `_get_curriculum_course_ids` ile o yıl müfredat setini al.  
   - Metrikleri yine tüm adaylar için topla (anket değeri için; müfredat dışı için sadece anket kullanılacak).  
   - Curriculum setinde olanlar: mevcut gibi DataFrame’e koy, TOPSIS çalıştır.  
   - Curriculum dışında kalanlar: TOPSIS’e sokma; her biri için `_pool_course_score_anket_only(metric["anket"])` ile skor hesapla.  
   - İki skor haritasını birleştir; dönüşte tek `scores` / `skor_map` olarak ver.

4. **calculation.py – persist_faculty_year_topsis_scores**  
   - Değişiklik gerekmez; gelen `skor_map` içinde müfredat dışı dersler 50±SPREAD, müfredat içi TOPSIS skoru olacak.

5. **2022 başlangıç 50**  
   - “Başlangıç” = müfredat dışı dersler için ilk atanacak değer 50. Bu, yukarıdaki anket-only formülle zaten sağlanıyor (anket yoksa 0.5 → 50).  
   - İsteğe bağlı: `persist` öncesi veya havuz ilk doldurulurken 2022 için müfredat dışı satırlarda skor NULL ise 50 yazan bir adım eklenebilir; gerekirse tek seferlik migration. Önce sadece anket-only formülle ilerlemek yeterli.

6. **Next year validasyon**  
   - `_has_generation_criteria` anket kontrolü yapmıyor; dokunuş yok.  
   - `generate_next_year_curricula` içindeki hata mesajını “Sadece müfredatta olan derslerin zorunlu kriterleri eksik” gibi netleştir.  
   - Gerekirse kısa yorum: “Müfredat dışı dersler ve anket validasyona dahil değildir.”

7. **course_analyzer.py**  
   - Tek ders analizi zaten `get_faculty_year_topsis_results` kullanıyor; orada müfredat içi/dışı ayrımı yapıldığı için ek değişiklik gerekmez.

8. **Fakülte bağımlılığı**  
   - Hardcoded mühendislik yok; tüm fakülte/yıl için “müfredatta olan / olmayan” `_get_curriculum_course_ids` ve mevcut veri modeli ile belirlenir.

---

## 5. Edge Case’ler

- **Anket yok / null / boş:** `_read_course_metrics` anket default 0.5; `_pool_course_score_anket_only(0.5)` → 50. Hata üretilmez.  
- **Müfredatta ders:** Mevcut TOPSIS aynen; diğer kriterler etkiler.  
- **Müfredatta olmayan ders:** Sadece anket ile 50 ± SPREAD; deterministik, küçük sapma.  
- **2022’de müfredat yok (tüm seçmeliler havuzda):** Tümü anket-only skor alır; başlangıç merkezi 50.  
- **Next year’da müfredat dersi kriter eksik:** Mevcut davranış: bloklanır, missing_criteria döner.  
- **Next year’da sadece müfredat dışı derslerde kriter eksik:** Bunlar validasyonda yok; bloklama olmaz.

---

## 6. Kabul Kriterleri Eşlemesi

- 2022’de müfredatta olmayan seçmeli derslerin başlangıç kesinleşme puanı 50 → anket-only formül (anket nötr = 50).  
- Müfredat dışı derslerde puanı etkileyen tek etken anket → sadece `_pool_course_score_anket_only(anket)`.  
- Etki küçük ve kontrollü → SPREAD sabiti (örn. 10) ile 40–60 bandı.  
- Anket yoksa hata yok → 0.5 default → 50.  
- Müfredatta olan dersler mevcut kriter mantığı → TOPSIS aynen.  
- Next year fakülte bazlı, sadece müfredattaki derslerin zorunlu kriterleri → zaten öyle; mesaj netleştirilebilir.  
- Müfredat dışı / anket eksikliği bloklamıyor → zaten bloklamıyor; anket `_has_generation_criteria`’da yok.

Bu analiz doğrultusunda kod değişiklikleri uygulanacak.
