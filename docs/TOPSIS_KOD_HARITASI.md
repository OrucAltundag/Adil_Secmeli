# TOPSIS Kod Haritasi

Bu dokuman, sistemde TOPSIS ile ilgili calisan tum ana kod yollarini tek yerde toplar.
Odak noktasi, hangi dosyanin ne yaptigi ve hesaplamanin hangi akistan gectigidir.

## 1. Ana cekirdek dosya

TOPSIS'in esas uretim kodu su dosyadadir:

- `app/services/calculation.py`

Bu dosyada kritik fonksiyonlar:

- `KararMotoru.ahp_calistir()`
  - 4 kriter icin sabit AHP karsilastirma matrisi kurar.
  - Kriterler: `basari`, `trend`, `populerlik`, `anket`
- `KararMotoru.ahp_tutarlilik_kontrolu()`
  - AHP agirliklarinin tutarlilik oranini `CR` olarak hesaplar.
- `KararMotoru.gecmis_trend_hesapla()`
  - Son 3 yil icin agirlikli trend uretir.
  - Agirliklar: `0.50`, `0.30`, `0.20`
- `KararMotoru.topsis_calistir(df, agirliklar)`
  - Gercek TOPSIS hesaplamasini yapar.
  - Adimlar:
    1. Vector normalization
    2. Agirlikli normalize matris
    3. Pozitif ideal cozum
    4. Negatif ideal cozum
    5. `S+`, `S-`, yakinlik katsayisi
  - Sonuc kolonlari:
    - `AHP_TOPSIS_Skor`
    - `Kesinlesme_Puani`
    - `S+`
    - `S-`

## 2. TOPSIS girdileri hangi tablolardan geliyor

Bir ders icin TOPSIS girdileri `_read_course_metrics(...)` fonksiyonunda derlenir.

Kullanilan tablolar:

- `ders_kriterleri`
  - `toplam_ogrenci`
  - `gecen_ogrenci`
  - `basari_ortalamasi`
  - `kontenjan`
  - `kayitli_ogrenci`
  - `anket_katilimci`
  - `anket_dersi_secen`
- `performans`
  - `ortalama_not`
  - `basari_orani`
- `populerlik`
  - `doluluk_orani`

Bu fonksiyonun urettigi TOPSIS girdileri:

- `basari`
- `trend`
- `populerlik`
- `anket`
- `ortalama_not`

Oncelik mantigi:

- Mevcut yil verisi varsa onu kullanir.
- Eksikse onceki yildan geri besleme yapar.
- Trend icin son 3 yil `performans.basari_orani` verisini kullanir.

## 3. Fakulte + yil bazli TOPSIS evreni nasil kuruluyor

Merkezi fonksiyon:

- `get_faculty_year_topsis_results(cur, fakulte_id, akademik_yil, donem="G", include_course_ids=None)`

Bu fonksiyon once aday ders evrenini kurar.
Kapsama girenler:

- Secili fakulte + yil + donem icin mufredatta bulunan secmeli dersler
- Fakulteye bagli secmeli dersler
- `havuz` tablosunda bulunan secmeli dersler
- Gerekirse `include_course_ids` ile zorla dahil edilen dersler

Bu asamada `course_type` servisindeki secmeli filtreleme kullanilir:

- `build_elective_predicate(...)`
- `filter_elective_course_ids(...)`

## 4. Uretim kurali: mufredat ve havuz ayrimi

Bu sistemde cok kritik bir kural var:

- Mufredatta olan secmeli dersler gercek TOPSIS pipeline'ina girer.
- Mufredat disi havuz dersleri TOPSIS'e girmez.

Havuz icin kullanilan ozel kural:

- `_pool_course_score_anket_only(anket)`

Formul:

- `50 + (anket - 0.5) * 2 * 10`

Yani:

- `anket = 0.5` ise skor `50`
- `anket = 1.0` ise skor `60`
- `anket = 0.0` ise skor `40`

Bu nedenle sistem iki farkli yol kullanir:

- `curriculum_courses` -> AHP + TOPSIS
- `pool_courses` -> sadece anket bazli skor

## 5. Hesap sonucu nereye yaziliyor

TOPSIS sonucu su fonksiyonla `havuz` tablosuna yazilir:

- `persist_faculty_year_topsis_scores(...)`

Is kurali:

- Ilgili fakulte + yil (+ donem) icin secmeli derslerin eski `havuz.skor` degerleri `NULL` yapilir.
- Sonra yeni skorlar `UPDATE` edilir.
- Kayit yoksa `INSERT` edilir.

Yazilan alanlar:

- `havuz.ders_id`
- `havuz.yil`
- `havuz.fakulte_id`
- `havuz.bolum_id`
- `havuz.donem` varsa o da
- `havuz.statu`
- `havuz.skor`
- `havuz.ders_adi`

Baslangic statu kurali:

- Ders aktif mufredatta ise `statu = 1`
- Degilse `statu = 0`

## 6. Sonraki yil mufredat uretiminde TOPSIS nerede kullaniliyor

Sonraki yil uretim hattinin ana fonksiyonu:

- `generate_next_year_curricula(...)`

Bu akista:

1. Fakulte + yil icin aday dersler ve skorlar `get_faculty_year_topsis_results(...)` ile uretilir.
2. Sonuclar `persist_faculty_year_topsis_scores(...)` ile `havuz` tablosuna yazilir.
3. Dusmesi gereken dersler belirlenir.
4. Bosalan yerlere en yuksek uygun adaylar eklenir.

Dusme kurallari:

- `DROP_SCORE_THRESHOLD = 40.0`
- `DROP_AVERAGE_GRADE_THRESHOLD = 45.0`

Yani ders su durumda dusmeye aday olur:

- `Kesinlesme_Puani < 40`
- veya `ortalama_not < 45`

Bu mantik su yardimci fonksiyonlarda bulunur:

- `evaluate_drop_reasons(...)`
- `should_drop_course(...)`

## 7. Toplu algoritma calistirma

Kullanici tarafindan toplu calistirma girisi:

- `run_all_algorithms_for_year(...)`

Bu fonksiyonun amaci:

- yil bazli uygun fakulteleri bulmak
- kriterleri tam olanlari secmek
- sonraki yil mufredat uretimini tetiklemek
- workflow durum kayitlarini guncellemek

API uzerinden cagrildigi yer:

- `app/api/routes.py`
- endpoint: `POST /algoritma/tumunu-calistir`

## 8. Tek ders analizinde TOPSIS

Tek ders inceleme ekraninda TOPSIS su servis uzerinden kullanilir:

- `app/services/course_analyzer.py`

Ana fonksiyon:

- `_run_topsis_single(...)`

Mantik:

- Tek dersi dogrudan izole hesaplamaz.
- Ayni fakulte + yil evreninde merkezi `get_faculty_year_topsis_results(...)` fonksiyonunu calistirir.
- Sonra secilen dersin skorunu genel evrenden ceker.

Bu cok onemli cunku:

- Tek ders sonucu ile toplu TOPSIS sonucu birbiriyle tutarli kalir.

## 9. Raporlama tarafinda TOPSIS

Rapor ekranlari icin ilgili servis:

- `app/services/reporting_service.py`

Ana akista:

- `ensure_report_scores(...)`

Bu fonksiyon:

1. Gerekirse pool gorunurlugunu hizalar.
2. Fakulte + yil icin skorlarin hazir olup olmadigini kontrol eder.
3. `get_faculty_year_topsis_results(...)` ile skor uretir.
4. `persist_faculty_year_topsis_scores(...)` ile havuza yazar.
5. Ayrica `skor` tablosuna kaynak skor kaydi dusurur.

Rapor mantiginda kaynak ayrimi:

- Mufredattaki dersler: `TOPSIS`
- Mufredat disi dersler: `Anket (50+-10)`

## 10. UI tarafinda TOPSIS

Arayuzde ilgili ana yerler:

- `app/ui/tabs/calc_tab.py`
- `app/ui/tabs/course_analysis_tab.py`

`calc_tab.py` icinde iki farkli kullanim vardir:

- Algoritma kontrol ekraninda ornek/preview TOPSIS hesaplamasi
- Sonraki yil uretimi icin `run_all_algorithms_for_year(...)` cagrisi

Not:

- `calc_tab.py` icindeki preview hesap, uretim akisinin kendisi degil.
- Uretim icin asil referans yine `calculation.py` icindeki merkezi akistir.

## 11. Cift donem yardimci kullanim

Su dosyada TOPSIS skoru blok doldurma siralamasi icin tekrar kullanilir:

- `app/services/dual_semester.py`

Burada:

- `_scores_for_term(...)`

fonksiyonu ilgili fakulte + yil + donem icin merkezi TOPSIS skorlarini alip sira uretir.

## 12. Testler

TOPSIS ile dogrudan ilgili test dosyalari:

- `app/tests/test_curriculum_generation.py`
  - Toplu TOPSIS ile tek ders analizinin ayni skoru urettigini kontrol eder.
- `app/tests/test_pool_rules.py`
  - Havuz ve mufredat kurallarinin TOPSIS skor yazimi ile uyumunu kontrol eder.
- `app/tests/test_single_analysis.py`
  - Tek ders TOPSIS skorunun `0-100` araliginda oldugunu kontrol eder.
- `app/tests/test_reporting.py`
  - Rapor kaynagi olarak `TOPSIS` ve `Anket` ayrimini kontrol eder.
- `app/tests/test_yearly_criteria_workflow.py`
  - Yillik algoritma calistirma akisini kontrol eder.

## 13. Kisa akis ozeti

Tam akis su sekildedir:

1. Fakulte + yil + donem secilir.
2. Aday secmeli dersler bulunur.
3. Her ders icin `ders_kriterleri`, `performans`, `populerlik` verileri toplanir.
4. AHP agirliklari hesaplanir.
5. Mufredattaki dersler icin TOPSIS calisir.
6. Mufredat disi dersler icin sadece anket bazli skor hesaplanir.
7. Sonuclar `havuz.skor` alanina yazilir.
8. Sonraki yil mufredat uretilecekse bu skorlar dusme/ekleme kararlarinda kullanilir.

## 14. En kritik dosya listesi

Kod okumaya su sirayla baslamak en verimlisidir:

1. `app/services/calculation.py`
2. `app/services/course_analyzer.py`
3. `app/services/reporting_service.py`
4. `app/services/dual_semester.py`
5. `app/ui/tabs/calc_tab.py`
6. `app/api/routes.py`
7. `app/tests/test_curriculum_generation.py`
8. `app/tests/test_pool_rules.py`
9. `app/tests/test_single_analysis.py`

## 15. Ozet not

Sistemde TOPSIS tek bir merkezi motor etrafinda kurulmus durumda.
Uretim davranisini belirleyen ana nokta `app/services/calculation.py` dosyasidir.
Eger algoritmada degisiklik yapilacaksa once bu dosyadaki su bolumler incelenmelidir:

- `KararMotoru`
- `_read_course_metrics(...)`
- `get_faculty_year_topsis_results(...)`
- `persist_faculty_year_topsis_scores(...)`
- `generate_next_year_curricula(...)`
- `run_all_algorithms_for_year(...)`
