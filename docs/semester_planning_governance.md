# Dönem Planlama Governance

Bu doküman, Adil Seçmeli projesindeki Güz/Bahar dönem dengeleme yapısının sabit 4+4 kuralından policy tabanlı akademik planlama motoruna taşınmasını açıklar.

## Amaç

Eski davranışta Güz ve Bahar dönemleri 4+4 bloklarla dengeleniyordu. Bu varsayılan hâlâ korunur; ancak artık kod içinde sabit değildir. Varsayılan 4+4 davranışı `semester_planning_policies` tablosundaki global policy’den gelir.

## Dönem Planlama Politikası

`semester_planning_policies` tablosu fakülte, bölüm, yıl ve curriculum year bağlamında çözümlenir. Policy şu kararları yönetir:

- `total_elective_target`
- `fall_min`, `fall_max`
- `spring_min`, `spring_max`
- `same_course_repeat_policy`
- ders uygunluğu, öğretim üyesi, kaynak, ön koşul, talep, kontenjan ve saat çakışması kontrollerinin aktif olup olmadığı
- hard constraint davranışı: `strict`, `warn_only`, `allow_with_approval`
- soft constraint ağırlıkları

Çözümleme sırası:

1. bölüm + yıl
2. fakülte + yıl
3. bölüm genel
4. fakülte genel
5. global + yıl
6. global default

## Varsayılan 4+4

Varsayılan global policy:

- toplam seçmeli hedefi: 8
- güz minimum/maksimum: 4/4
- bahar minimum/maksimum: 4/4
- aynı ders tekrarı: `disallow`
- ders uygunluğu ve ön koşul kontrolü açık
- öğretim üyesi, kaynak, zorunlu yük ve saat çakışması kontrolleri veri yoksa eski akışı bozmamak için kapalı

## Ders Dönem Uygunluğu

`course_semester_availability` tablosu dersin sadece güz, sadece bahar veya her iki dönemde açılıp açılamayacağını tutar. Kayıt yoksa ders iki döneme de uygun kabul edilir. `preferred_semester` soft constraint olarak değerlendirilir.

## Öğretim Üyesi Uygunluğu

`instructors`, `course_instructor_assignments` ve `instructor_semester_availability` tabloları bir dersi verebilecek öğretim üyelerini, dönemsel uygunluğu ve maksimum seçmeli yükünü tutar. Policy’de `consider_instructor_availability=true` ise motor bu kısıtı uygular.

## Kaynak Kısıtları

`teaching_resources`, `course_resource_requirements` ve `semester_resource_capacity` tabloları laboratuvar, bilgisayar sınıfı, stüdyo ve benzeri kaynakları izler. Kaynak verisi yoksa ve kontrol kapalıysa eski davranış korunur. Kontrol açıksa uygun kaynak bulunmadığında violation üretilir.

## Ön Koşul İlişkileri

`course_prerequisites` tablosu hard, recommended ve soft ön koşulları saklar. Hard ön koşul sonraki döneme düşerse error seviyesinde ihlal oluşur; recommended ilişkiler warning olarak raporlanır.

## Zorunlu Ders Yükü

`semester_required_course_loads` tablosu bölüm/yıl/dönem bazlı zorunlu ders yoğunluğunu tutar. Policy’de aktifse yüksek zorunlu yük dönem hedeflerini uyarılı biçimde etkileyebilir.

## Talep, Kontenjan ve Workload Dengesi

Plan motoru her plan için şu metrikleri üretir:

- güz/bahar ders sayısı
- güz/bahar beklenen talep
- güz/bahar toplam kontenjan
- demand imbalance
- capacity imbalance
- workload imbalance
- total plan score

Talep `ders_kriterleri.anket_dersi_secen` veya `populerlik.talep_sayisi`, kontenjan ise `ders_kriterleri`, `populerlik` veya `ders.kontenjan` üzerinden tahmin edilir.

## Aynı Ders Tekrar Politikası

Desteklenen tekrar politikaları:

- `disallow`
- `allow_if_high_demand`
- `allow_if_capacity_needed`
- `allow_with_approval`

Varsayılan `disallow` olduğu için aynı ders iki döneme otomatik yerleşmez.

## Plan Motoru

`semester_planning_engine.generate_semester_plan` greedy + constraint repair yaklaşımı kullanır:

1. aday dersleri skor/talep bilgisiyle hazırlar
2. aktif policy’yi çözer
3. dönem uygunluğu ve min/max hedeflerini uygular
4. tekrar, öğretim üyesi, kaynak ve ön koşul kontrollerini değerlendirir
5. güz/bahar planını üretir
6. metrikleri ve kısıt ihlallerini hesaplar
7. her ders için insan okunabilir açıklama üretir
8. plan run, assignment, violation ve scenario kayıtlarını yazar

## Alternatif Plan Senaryoları

Motor en az üç senaryo üretir:

- skor öncelikli
- dönem dengesi öncelikli
- talep/kontenjan dengesi öncelikli

Her senaryoda güz/bahar dersleri, plan skoru, denge metrikleri, ihlaller ve açıklamalar saklanır.

## Audit Trail

Planlama çıktıları şu tablolarda saklanır:

- `semester_plan_runs`
- `semester_plan_course_assignments`
- `semester_plan_constraint_violations`
- `semester_plan_scenarios`

Bu sayede hangi policy ile hangi dersin neden güz veya bahara atandığı izlenebilir.

## UI

Tkinter içinde `Dönem Planlama` paneli eklenmiştir. Karar Merkezi içinde de aynı panel alt sekme olarak kullanılabilir. Panelde policy özeti, plan üretme, güz/bahar planı, kısıt ihlalleri, alternatif senaryolar ve plan geçmişi görüntülenir.

## API Endpointleri

Temel endpointler:

- `GET /api/v1/semester-planning/policies`
- `POST /api/v1/semester-planning/policies`
- `PATCH /api/v1/semester-planning/policies/{policy_id}`
- `POST /api/v1/semester-planning/policies/{policy_id}/activate`
- `GET /api/v1/semester-planning/course-availability`
- `POST /api/v1/semester-planning/course-availability`
- `GET /api/v1/semester-planning/instructors`
- `POST /api/v1/semester-planning/instructors`
- `GET /api/v1/semester-planning/resources`
- `POST /api/v1/semester-planning/resources`
- `GET /api/v1/semester-planning/prerequisites`
- `POST /api/v1/semester-planning/prerequisites`
- `POST /api/v1/semester-planning/generate`
- `POST /api/v1/semester-planning/generate-alternatives`
- `GET /api/v1/semester-planning/runs`
- `GET /api/v1/semester-planning/runs/{run_id}`
- `GET /api/v1/semester-planning/runs/{run_id}/assignments`
- `GET /api/v1/semester-planning/runs/{run_id}/violations`
- `GET /api/v1/semester-planning/runs/{run_id}/scenarios`
- `GET /api/v1/semester-planning/runs/{run_id}/report`

## Net İlke

Dönem dengeleme sistemi başlangıçta 4+4 varsayılan politikasıyla çalışır; ancak bu kural sabit değildir. Fakülte/bölüm/yıl bazlı dönem planlama politikalarıyla güz ve bahar için minimum-maksimum ders hedefleri, ders uygunluğu, öğretim üyesi uygunluğu, kaynak kısıtları, ön koşullar, kontenjan ve talep dengesi dikkate alınır.
