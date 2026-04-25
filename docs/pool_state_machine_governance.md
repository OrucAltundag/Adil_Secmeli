# Havuz State Machine Governance

Bu doküman, Adil Seçmeli projesinde havuz karar yaşam döngüsünün nasıl yönetildiğini açıklar.

## Amaç

Havuz state machine artık yalnızca sayaç artıran mekanik bir yapı değildir. Dersin skoru, trendi, veri güveni, akademik koruma bayrakları, ders yaşı, revizyon durumu ve fakülte/bölüm/yıl bazlı policy birlikte değerlendirilir.

## Korunan Statü Kodları

- `1`: Müfredatta
- `0`: Havuzda
- `-1`: Dinlenmede
- `-2`: Kalıcı iptal

Eski akış bu kodları kullanmaya devam eder. Yeni alanlar kararın açıklanabilir ve denetlenebilir olmasını sağlar:

- `recommended_status`: Algoritmanın önerdiği statü.
- `final_status`: Policy, onay ve override sonrası uygulanacak statü.
- `lifecycle_label`: Kullanıcı dostu durum etiketi.
- `approval_required`: Akademik onay gerekip gerekmediği.
- `approval_status`: `not_required`, `pending`, `approved`, `rejected`.
- `explanation`: İnsan okunabilir geçiş gerekçesi.

## Lifecycle Label Değerleri

- `curriculum`: Müfredat
- `pool`: Havuz
- `resting`: Dinlenmede
- `cancel_candidate`: İptal adayı
- `permanently_cancelled`: Kalıcı iptal
- `under_review`: İncelemede
- `protected`: Korumalı
- `reactivation_candidate`: Yeniden açılma adayı

## Pool State Policy

Policy kayıtları `pool_state_policies` tablosunda tutulur. Çözümleme sırası:

1. Department + year + semester
2. Department + year
3. Faculty + year + semester
4. Faculty + year
5. Department genel
6. Faculty genel
7. Global + year
8. Global default

Varsayılan policy kalıcı iptal ve yeniden müfredata dönüş kararlarını akademik onaya bağlar.

## Course Governance Flags

`course_governance_flags` tablosu ders bazlı koruma ve yönetişim bayraklarını tutar:

- `strategic_flag`
- `accreditation_flag`
- `protected_flag`
- `required_course_flag`
- `service_course_flag`
- `new_course_flag`
- `revised_course_flag`
- `revision_year`
- `first_offered_year`
- `protected_until_year`
- `instructor_changed`
- `content_updated`

Stratejik, akreditasyon kapsamındaki, zorunlu, servis veya korumalı derslerde otomatik sert karar uygulanmaz.

## Yeni Ders ve Revize Ders Grace Period

Yeni derslerde geçmiş trend verisi eksikliği doğrudan cezalandırılmaz. `new_course_grace_period_years` içinde kalıcı iptal önerisi daha hafif bir karara düşürülür.

Revize edilen derslerde `revised_course_grace_period_years` boyunca eski negatif performans temkinli değerlendirilir. İçerik güncellemesi veya öğretim elemanı değişikliği açıklamada belirtilir.

## Veri Güveni ve Trend Entegrasyonu

State machine, varsa veri güveni ve trend servislerinden gelen değerleri kullanır:

- Veri güveni `minimum_data_confidence_for_cancel` altındaysa kalıcı iptal engellenir.
- Veri güveni `minimum_data_confidence_for_rest` altındaysa dinlenme kararı havuzda izlemeye yumuşatılabilir.
- `rising` trend reactivation kararını güçlendirir.
- `falling` trend aşağı yönlü geçiş riskini artırır.
- `volatile` veya `insufficient_data` durumları manuel inceleme gerekçesi olabilir.

## Kalıcı İptal Onay Akışı

Policy `require_approval_for_cancel = true` ise:

1. Algoritma `recommended_status = -2` üretebilir.
2. `final_status` doğrudan `-2` yapılmaz.
3. Ders `cancel_candidate` olarak işaretlenir.
4. `course_state_approvals` tablosunda `pending` onay kaydı oluşturulur.
5. Onay verilirse `final_status = -2` uygulanır.
6. Red verilirse daha hafif mevcut final statü korunur.

## Manual Override

Kurul kararı veya yetkili manuel karar `course_state_overrides` tablosunda tutulur. Override gerekçesi zorunludur. Override uygulandığında:

- Sistem önerisi saklanır.
- Final statü override kararına göre belirlenir.
- Transition log üzerinde `override_applied` ve `override_id` saklanır.

## Transition History

Her değerlendirme `course_state_transitions` tablosuna yazılır:

- Eski statü
- Önerilen statü
- Final statü
- Uygulanan kural
- Skor, trend, veri güveni
- Policy id
- Governance flag snapshot
- Onay/override bilgisi
- İnsan okunabilir açıklama

Hiç final statü değişmese bile öneri/final ayrımı önemliyse transition loglanır.

## Reactivation Kuralları

Havuzda veya dinlenmede olan dersler yüksek skor, olumlu trend ve yeterli veri güveniyle `reactivation_candidate` olabilir.

Kalıcı iptal edilmiş ders otomatik açılmaz. Policy izin verse bile bu dönüş manuel/onaylı süreç gerektirir.

## Tkinter UI

Karar Merkezi içinde `Havuz Yaşam Döngüsü` alt sekmesi bulunur:

- Durum özeti
- Ders yaşam döngüsü tablosu
- Transition açıklaması ve geçmişi
- Onay bekleyen kararlar
- Onayla/reddet işlemleri

UI hesaplama yapmaz; servis katmanını çağırır.

## API Endpointleri

- `GET /api/v1/havuz/state-policies`
- `POST /api/v1/havuz/state-policies`
- `POST /api/v1/havuz/state-policies/{id}/activate`
- `GET /api/v1/havuz/courses/{course_id}/governance`
- `POST /api/v1/havuz/courses/{course_id}/governance`
- `PATCH /api/v1/havuz/courses/{course_id}/governance`
- `GET /api/v1/havuz/state-transitions`
- `GET /api/v1/havuz/courses/{course_id}/state-history`
- `POST /api/v1/havuz/evaluate`
- `GET /api/v1/havuz/approvals`
- `POST /api/v1/havuz/approvals/{id}/approve`
- `POST /api/v1/havuz/approvals/{id}/reject`
- `GET /api/v1/havuz/overrides`
- `POST /api/v1/havuz/overrides`
- `PATCH /api/v1/havuz/overrides/{id}`
- `GET /api/v1/havuz/lifecycle-summary`
- `GET /api/v1/havuz/reactivation-candidates`

## Geriye Dönük Uyum

`calculate_next_status` eski imzasıyla korunur. Yeni `calculate_next_status_governed` adapter fonksiyonu, bağlam ve veritabanı bağlantısı verildiğinde yeni yaşam döngüsü servisine delegasyon yapar; hata durumunda legacy sonucu döndürür.
