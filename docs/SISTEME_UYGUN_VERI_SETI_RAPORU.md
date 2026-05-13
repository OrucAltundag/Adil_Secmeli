# Sisteme Uygun Veri Seti Raporu

Tarih: 2026-05-12  
Kapsam: AHP/TOPSIS karar hattı, veri kalitesi, kriter tamlığı, dönem planlama, destekleyici ML/benchmark veri seti.

## 1. Yönetici Özeti

Adil Seçmeli sistemi yalnızca ders listesiyle doğru karar üretemez. Sistem; fakülte, bölüm, ders, müfredat, havuz, başarı, popülerlik, anket, kontenjan, tercih, dönem planlama ve karar sonrası sonuç verilerini birlikte kullanır.

Mevcut veritabanı temel hacim açısından güçlüdür:

| Veri | Mevcut kayıt |
|---|---:|
| Ders | 557 |
| Öğrenci | 1500 |
| Kayıt/geçmiş ders alma | 20244 |
| Havuz kaydı | 2329 |
| Fakülte | 5 |
| Bölüm | 9 |

Ancak karar kalitesi için kritik veri kapsaması düşüktür:

| Kritik tablo | Mevcut kayıt | Yorum |
|---|---:|---|
| `ders_kriterleri` | 24 | Karar kriteri kapsaması yetersiz |
| `performans` | 16 | Başarı/trend verisi düşük |
| `populerlik` | 16 | Talep/doluluk verisi düşük |
| `course_data_confidence` | 0 | Karar güveni henüz oluşmamış |
| `decision_runs` | 0 | Karar çalışması üretilmemiş |

Bu nedenle ilk hedef sentetik veri üretmek değil, gerçek kurumsal veriyi sisteme uygun formatta tamamlamaktır. Öncelik sırası: kriter verisi, geçmiş başarı ve popülerlik, anket/tercih, dönem planlama kısıtları, ardından ML/benchmark veri setidir.

## 2. Sistem Hangi Veri Katmanlarını Bekliyor?

Sistemin ana karar hattı şu akışla çalışır:

```text
Temel kurumsal veri
  -> Müfredat ve aday ders havuzu
  -> Kriter tamlığı
  -> AHP ağırlık profili
  -> TOPSIS skor/kırılım
  -> Trend ve veri güven skoru
  -> Kural motoru ve havuz state machine
  -> Dönem planlama
  -> Raporlama ve karar sonrası izleme
```

Bu akış için veri katmanları aşağıdaki gibi tasarlanmalıdır.

| Katman | Amaç | Ana tablolar / dosyalar |
|---|---|---|
| Kurumsal temel veri | Fakülte, bölüm, ders, öğretim elemanı ve öğrenci kimliğini tutar | `fakulte`, `bolum`, `ders`, `ogrenci`, `ogretim_gorevlisi` |
| Akademik yapı | Hangi dersin hangi yıl/dönem/bölüm için aday olduğunu belirler | `mufredat`, `mufredat_ders`, `havuz` |
| Karar kriterleri | AHP/TOPSIS kararının ana girdisini verir | `ders_kriterleri`, `performans`, `populerlik`, `anket_sonuclari` |
| Tercih ve anket | Öğrenci talebini ve memnuniyet sinyalini üretir | `anket_form`, `anket_cevap`, survey import dosyaları |
| Planlama verisi | Güz/bahar dağılımı, kaynak, öğretim üyesi ve ön koşul kısıtlarını verir | `course_semester_availability`, `course_prerequisites`, `course_instructor_assignments`, `teaching_resources` |
| Sonuç izleme | Kararın gerçek hayattaki etkisini ölçer | `kayit`, `post_decision_outcomes`, fairness/coverage raporları |
| ML/benchmark | Nihai karara destek ve deneysel karşılaştırma sağlar | `data/benchmark/raw_real/*.csv`, `ml_feature_snapshots` |

Önemli ilke: ML ve benchmark çıktıları nihai karar verici değildir. Nihai karar hattı AHP/TOPSIS + kural motoru + state machine yapısıdır. ML yalnızca destekleyici analiz, tahmin ve karşılaştırma amacıyla kullanılmalıdır.

## 3. Minimum Üretim Veri Seti

Sistemin güvenilir karar çalıştırabilmesi için her aday ders-yıl-dönem satırı için aşağıdaki veri seti tamamlanmalıdır.

| Alan | Zorunluluk | Açıklama | Örnek |
|---|---|---|---|
| `ders_kodu` | Zorunlu önerilir | Ders eşleştirmede en güvenilir anahtar | `BLM412` |
| `ders_adi` | Zorunlu önerilir | Kod yoksa ders adıyla eşleştirme yapılır | `Veri Madenciliği` |
| `fakulte` | Zorunlu | Kapsam doğrulama ve raporlama için gerekir | `Mühendislik ve Doğa Bilimleri Fakültesi` |
| `bolum` | Zorunlu | Bölüm bazlı kriter tamlığı ve AHP profili için gerekir | `Bilgisayar Mühendisliği` |
| `yil` | Zorunlu | Akademik yıl | `2024` |
| `donem` | Zorunlu | Güz/Bahar planlama için gerekir | `Güz` |
| `toplam_ogrenci` | Zorunlu | Dersi alan toplam öğrenci | `80` |
| `gecen_ogrenci` | Zorunlu | Başarı oranı hesabı | `65` |
| `basari_ortalamasi` | Zorunlu | Ortalama başarı/not sinyali | `72.5` |
| `kontenjan` | Zorunlu | Doluluk ve planlama hesabı | `50` |
| `kayitli_ogrenci` | Zorunlu | Talep/doluluk hesabı | `45` |
| `anket_katilimci` | Opsiyonel ama kritik | Anket güveni ve örneklem kontrolü | `120` |
| `anket_dersi_secen` | Opsiyonel ama kritik | Öğrenci talep sinyali | `38` |

Bu alanlar repo içindeki kriter import akışıyla uyumludur. Özellikle `criteria_import_service` tarafında aktif kullanılan çekirdek kolonlar şunlardır:

```text
ders_kodu / ders adi
toplam_ogrenci
gecen_ogrenci
basari_ortalamasi / ortalama_not / ortalama
kontenjan
kayitli_ogrenci / talep_sayisi
fakulte
bolum
yil
donem
```

Minimum veri seti yalnızca tek yıl için değil, mümkünse en az üç akademik yıl için hazırlanmalıdır. Mevcut DB'de `kayit` verisi 2022, 2023 ve 2024 yıllarını içerdiğinden başarı, popülerlik ve trend değerleri bu yıllardan üretilebilir.

## 4. Excel Veri Şablonları

### 4.1 Kriter Veri Seti

Kriter dosyası her satırda bir ders-yıl-dönem kaydı taşımalıdır.

| fakulte | bolum | yil | donem | ders_kodu | ders_adi | toplam_ogrenci | gecen_ogrenci | basari_ortalamasi | kontenjan | kayitli_ogrenci | anket_katilimci | anket_dersi_secen |
|---|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Mühendislik ve Doğa Bilimleri Fakültesi | Bilgisayar Mühendisliği | 2024 | Güz | BLM412 | Veri Madenciliği | 80 | 65 | 72.5 | 50 | 45 | 120 | 38 |

Validasyon kuralları:

- `ders_kodu` veya `ders_adi` alanlarından en az biri dolu olmalıdır.
- `gecen_ogrenci`, `toplam_ogrenci` değerini aşmamalıdır.
- `basari_ortalamasi` 0-100 aralığında tutulmalıdır.
- `toplam_ogrenci`, `gecen_ogrenci`, `kontenjan`, `kayitli_ogrenci`, `anket_katilimci`, `anket_dersi_secen` negatif olamaz.
- Aynı `fakulte + bolum + yil + donem + ders_kodu` tekrarlanmamalıdır.

### 4.2 Müfredat Veri Seti

Müfredat dosyası her satırda tek ders taşımalıdır.

| fakulte | bolum | akademik_yil | donem | ders_kodu | ders_adi | kredi | akts | zorunlu_secmeli |
|---|---|---:|---|---|---|---:|---:|---|
| Mühendislik ve Doğa Bilimleri Fakültesi | Bilgisayar Mühendisliği | 2024 | Bahar | BLM430 | Bulut Bilişim | 3 | 5 | Seçmeli |

Mevcut import akışının aktif kullandığı alanlar:

- `Fakulte`
- `Bolum`
- `Akademik Yil`
- `Donem`
- `Ders Kodu` veya `Ders Adi`

`Kredi`, `AKTS` ve `Zorunlu_Seçmeli` alanları raporda korunmalıdır; mevcut sistemin tamamı bu alanları her akışta kullanmasa bile akademik veri kalitesi için gereklidir.

### 4.3 Anket/Tercih Veri Seti

Anket import akışı ders bazlı tercih sayısını bekler.

| fakulte_adi | yil | ders_kodu | ders_adi | oy_miktari |
|---|---:|---|---|---:|
| Mühendislik ve Doğa Bilimleri Fakültesi | 2024 | BLM412 | Veri Madenciliği | 38 |

Kurallar:

- `oy_miktari` negatif olamaz.
- Aynı belge içinde aynı ders iki kez yer almamalıdır.
- Toplam katılımcı değeri veriliyorsa satır toplamlarıyla tutarlı olmalıdır.
- Düşük anket sayısı karar çalışmasını tamamen durdurmak yerine veri güven skorunu düşürmelidir.

## 5. İdeal Veri Seti

Minimum veri seti karar çalıştırmak için yeterlidir; ideal veri seti ise açıklanabilir, denetlenebilir ve dönem planlamaya hazır karar üretir.

| Veri grubu | İdeal alanlar | Neden gerekli? |
|---|---|---|
| Ders metadata | Kod, ad, fakülte, bölüm, kredi, AKTS, ders tipi, alan, açıklama | Ders eşleştirme ve akademik raporlama |
| Başarı geçmişi | Yıl, dönem, toplam öğrenci, geçen öğrenci, ortalama not, başarı oranı | `basari` ve `trend` kriterleri |
| Popülerlik | Talep sayısı, kontenjan, fakülte mevcudu, doluluk oranı, ilgi oranı | `populerlik` kriteri ve kontenjan dengesi |
| Anket | Katılımcı sayısı, dersi seçen sayısı, tercih oranı, memnuniyet | `anket` kriteri ve veri güveni |
| Havuz durumu | Eski statü, önerilen statü, final statü, sayaç, koruma bayrakları | State machine ve akademik onay |
| AHP profili | Kriter anahtarları, pairwise matrix, ağırlıklar, consistency ratio, onay durumu | Ağırlıkların savunulabilir olması |
| Planlama | Dönem uygunluğu, öğretim üyesi, kaynak, ön koşul, saat çakışması | Güz/Bahar planının uygulanabilirliği |
| Sonuç izleme | Gerçek kayıt, gerçek başarı, gerçek doluluk, karar etkili miydi? | Feedback loop ve karar kalitesi ölçümü |

İdeal hedef, her fakülte/bölüm/yıl/dönem kapsamı için zorunlu kriter alanlarında en az %95 tamlıktır. `completed` veya `completed_with_warnings` seviyesine ulaşmadan final kararların akademik kurul kararı gibi sunulmaması gerekir.

## 6. ML ve Benchmark İçin Genişletilmiş Veri Seti

ML tarafı ayrı bir veri sözleşmesi kullanır. Bu veri seti `data/benchmark/raw_real` klasöründeki örnek yapıyla uyumlu olmalıdır.

### 6.1 `students.csv`

| Alan | Açıklama |
|---|---|
| `student_id` | Anonim öğrenci kimliği |
| `faculty_id` | Fakülte kimliği |
| `department_id` | Bölüm kimliği |
| `gender` | Opsiyonel demografik alan; mümkünse anonim/gruplu tutulmalı |
| `term` | Öğrencinin dönem/sınıf bilgisi |
| `gpa` | Genel akademik başarı |

Örnek:

```csv
student_id,faculty_id,department_id,gender,term,gpa
1,10,101,F,Guz,3.70
```

### 6.2 `courses.csv`

| Alan | Açıklama |
|---|---|
| `course_id` | Ders kimliği |
| `code` | Ders kodu |
| `name` | Ders adı |
| `faculty_id` | Fakülte kimliği |
| `department_id` | Bölüm kimliği |
| `capacity` | Kontenjan |
| `difficulty_score` | Ders zorluğu sinyali |
| `instructor_effect_score` | Öğretim üyesi etkisi sinyali |

Örnek:

```csv
course_id,code,name,faculty_id,department_id,capacity,difficulty_score,instructor_effect_score
1001,OSD101,Data Analytics,10,101,5,0.62,0.78
```

### 6.3 `preferences.csv`

| Alan | Açıklama |
|---|---|
| `student_id` | Öğrenci kimliği |
| `course_id` | Ders kimliği |
| `rank` | Tercih sırası; düşük değer daha güçlü tercih |
| `preference_score` | 0-1 arası tercih gücü |

Örnek:

```csv
student_id,course_id,rank,preference_score
1,1002,1,0.95
```

### 6.4 `survey_responses.csv`

| Alan | Açıklama |
|---|---|
| `student_id` | Öğrenci kimliği |
| `course_id` | Ders kimliği |
| `satisfaction` | Memnuniyet skoru |
| `contribution` | Dersin katkı skoru |
| `general_sentiment` | Genel olumlu/olumsuz sinyal |

Örnek:

```csv
student_id,course_id,satisfaction,contribution,general_sentiment
1,1002,4.8,4.6,4.7
```

### 6.5 `allocations.csv`

| Alan | Açıklama |
|---|---|
| `student_id` | Öğrenci kimliği |
| `course_id` | Atanan/alınan ders |
| `allocated` | Atama gerçekleşti mi? |
| `rank_received` | Öğrencinin kaçıncı tercihini aldığı |

Örnek:

```csv
student_id,course_id,allocated,rank_received
1,1002,1,1
```

ML için minimum örnek eşiği algoritmaya göre değişir:

| Algoritma | Minimum önerilen örnek |
|---|---:|
| Historical Average Baseline | 10 |
| Linear Regression | 50 |
| Decision Tree | 100 |
| Logistic Regression | 100 |
| Naive Bayes | 100 |
| Clustering | 100 |
| Random Forest | 200 |
| XGBoost / GradientBoosting | 500 |

Bu eşikler sağlanmadan ML sonucu production kararına etki etmemelidir. Sistem bu durumda modeli `advisory_only`, `benchmark_only`, `skipped` veya `fallback_used` davranışıyla sınırlandırmalıdır.

## 7. Veri Toplama Stratejisi

### Öncelik 1: Kriter Kapsamasını Tamamla

Her fakülte/bölüm/yıl/dönem için `ders_kriterleri` satırları tamamlanmalıdır. Mevcut 557 derslik yapı için yalnızca 24 kriter kaydı yeterli değildir.

Hedef:

- Her aktif aday ders için `toplam_ogrenci`, `gecen_ogrenci`, `basari_ortalamasi`, `kontenjan`, `kayitli_ogrenci` dolu olmalı.
- Zorunlu alan tamlığı en az %95 olmalı.
- Eksik kalan satırlar `criteria_completion_tasks` veya veri toplama öncelikleriyle takip edilmeli.

### Öncelik 2: 2022-2024 Geçmiş Kayıtlardan Başarı/Popülerlik Üret

Mevcut `kayit` tablosunda 2022-2024 yılları için 20244 kayıt vardır. Bu veri aşağıdaki türetmeler için kullanılmalıdır:

- `toplam_ogrenci`: ders-yıl-dönem kayıt sayısı
- `gecen_ogrenci`: başarılı durumdaki öğrenci sayısı
- `basari_orani`: `gecen_ogrenci / toplam_ogrenci`
- `basari_ortalamasi`: varsa not/puan ortalaması
- `kayitli_ogrenci`: ilgili ders-yıl-dönem talebi
- `doluluk_orani`: `kayitli_ogrenci / kontenjan`

Bu üretimden sonra `performans`, `populerlik` ve `ders_kriterleri` tabloları güncel hale getirilmelidir.

### Öncelik 3: Anket ve Tercih Verisini Topla

Her aday ders için anket/tercih sayısı toplanmalıdır.

Hedef:

- Her fakülte/yıl için anket formu açılmalı.
- Ders bazında `oy_miktari` veya `anket_dersi_secen` değeri toplanmalı.
- Öğrenci düzeyinde tercih sırası tutulabiliyorsa `anket_cevap.rank` ve `anket_cevap.puan` doldurulmalı.
- Anket katılımı düşükse karar engellenmek yerine `course_data_confidence` düşük seviyeye çekilmeli.

### Öncelik 4: Dönem Planlama Verisini Ekle

Karar verilen derslerin uygulanabilir akademik plana dönüşmesi için şu veriler eklenmelidir:

- Ders hangi dönemde açılabilir: güz, bahar veya her ikisi.
- Dersi verebilecek öğretim üyeleri ve dönemsel uygunlukları.
- Dersin kaynak gereksinimi: laboratuvar, bilgisayar sınıfı, stüdyo vb.
- Ön koşul ilişkileri.
- Zorunlu ders yükü ve dönem yoğunluğu.
- Saat çakışması veya aynı öğrenci kitlesi çakışma grupları.

Bu veri yoksa sistem varsayılan 4+4 planlama politikasına düşer; ancak kararın uygulanabilirliği sınırlı kalır.

### Öncelik 5: ML/Benchmark Veri Setini Büyüt

ML veri seti ana karar hattı hazırlandıktan sonra büyütülmelidir.

Hedef:

- En az 200 öğrenci-ders etkileşim örneğiyle Random Forest denenebilir.
- En az 500 örnekle XGBoost/GradientBoosting benzeri modeller benchmark için anlamlı hale gelir.
- Her öğrenci için birden fazla tercih satırı toplanmalıdır.
- Atama sonrası `rank_received` ve memnuniyet bilgisi tutulmalıdır.
- Öğrenci kimlikleri anonimleştirilmeli; gereksiz kişisel veri tutulmamalıdır.

## 8. Veri Kalitesi ve Kabul Kuralları

| Kontrol | Kabul kuralı |
|---|---|
| Ders eşleşmesi | `ders_kodu` ile doğrudan eşleşme tercih edilir; ad eşleşmesi belirsizse import uyarı vermelidir |
| Kriter tamlığı | Zorunlu alanlarda hedef en az %95 |
| Başarı verisi | `gecen_ogrenci <= toplam_ogrenci` |
| Not ortalaması | 0-100 veya kurumca belirlenmiş tek ölçek |
| Kontenjan | Negatif olamaz, sıfır ise doluluk hesabı güvenli biçimde 0 kabul edilir |
| Anket | Negatif oy yok, duplicate ders yok |
| Yıl/dönem | `Güz` ve `Bahar` normalizasyonu tutarlı olmalı |
| Veri soyu | Import batch, dosya hash, kalite skoru ve satır sorunları saklanmalı |
| Karar güveni | Eksik veri karar çalışmasını çökertmemeli; güven skoru ve açıklama üretmeli |

## 9. Veri Seti Seviyeleri

### 9.1 Minimum Veri Seti

Karar motorunu çalıştırmak için gerekir:

- Fakülte, bölüm, ders
- Müfredat ve havuz
- Ders-yıl-dönem bazlı kriter satırı
- Başarı: toplam öğrenci, geçen öğrenci, ortalama
- Popülerlik: kontenjan, kayıtlı öğrenci
- Anket: katılımcı ve dersi seçen sayısı
- Aktif AHP profili
- Aktif decision policy

### 9.2 İdeal Veri Seti

Akademik kurulda savunulabilir karar için gerekir:

- En az üç yıllık geçmiş başarı ve talep verisi
- Ders bazlı trend analizi
- Anket katılım güveni
- Veri güven skoru
- Hassasiyet analizi
- Ders koruma/akreditasyon/stratejik bayrakları
- Akademik onay kayıtları
- Dönem planlama kısıtları
- Karar sonrası gerçek sonuçlar

### 9.3 ML İçin Genişletilmiş Veri Seti

Destekleyici model ve benchmark için gerekir:

- Anonim öğrenci profilleri
- Öğrenci-ders tercih sıraları
- Tercih gücü skoru
- Memnuniyet/katkı/genel duygu skorları
- Atama sonuçları
- Öğrencinin kaçıncı tercihini aldığı
- Model eğitiminde kullanılacak feature snapshot kayıtları
- Veri sızıntısı ve minimum örnek kontrolleri

## 10. Sonuç

Bu sistem için doğru veri seti tek bir Excel dosyası değildir. Doğru veri seti, akademik kararın tamamını izlenebilir hale getiren çok katmanlı bir veri paketidir.

Kısa vadede yapılması gereken en doğru iş:

1. `ders_kriterleri` kapsamasını tüm aktif aday derslere yaymak.
2. 2022-2024 `kayit` verisinden başarı, popülerlik ve trend değerleri üretmek.
3. Fakülte/yıl bazlı anket dosyalarıyla tercih verisini tamamlamak.
4. Veri kalitesi ekranında readiness ve coverage değerlerini yükseltmek.
5. Ancak bu temel tamamlandıktan sonra ML/benchmark veri setini büyütmek.

Bu sıra izlendiğinde sistem, yalnızca çalışan bir yazılım olmaktan çıkıp, kararları veriye dayalı, açıklanabilir, denetlenebilir ve akademik olarak savunulabilir bir seçmeli ders karar platformuna dönüşür.
