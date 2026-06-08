# Kriter Tamlık Yönetişimi

Bu belge, **Adil Seçmeli** içindeki kriter tamlık kontrolünün yönetişim katmanını açıklar. Amaç yalnızca "tamam/eksik" demek değil; eksik verinin nerede olduğunu, karar riskini, sorumlu aksiyonları ve algoritma çalıştırma iznini **izlenebilir** hale getirmektir.

> **Belge Konvansiyonu**
>
> Aşağıdaki bölümlerde davranışın mevcut kod tabanındaki durumu rozetlerle belirtilir:
>
> - 🟢 **Uygulandı** — Mevcut kodda bu şekilde çalışır.
> - 🟡 **Planlanan** — Tasarımı bu belgede kararlaştırıldı, ancak **henüz kodda uygulanmadı** (yol haritası).
>
> Rozet bulunmayan kısımlar uygulanmış kabul edilir.

---

## 1. Yeni Tamlık Hattı (Pipeline)

Tamlık kontrol hattı sıralı olarak şu adımları işletir:

1. **Kapsam Seçimi:** Kullanıcı tarafından fakülte, bölüm, yıl ve dönem seçilir.
2. **Politika Çözümleme:** Kapsama uyan aktif `criteria_completion_policy` kuralları çözülür (`resolve_policy`).
3. **Ders Filtreleme:** Seçili müfredattaki **seçmeli** dersler bulunur (`filter_elective_course_ids`).
4. **Matris Üretimi:** Ders × Kriter matrisi (`criteria_completion_matrix`) oluşturulur.
5. **Varlık ve Geçerlilik Kontrolü:** Her hücre için verinin varlığı ve iş kurallarına uygunluğu denetlenir (`criteria_validation_service`).
6. **Metrik Hesaplama:** Tamlık oranı, kalite seviyesi ve risk skoru hesaplanır.
7. **Durum Kalıcılığı (Persistence):** Kalıcı durum tabloları (`criteria_faculty_status` / `criteria_department_status`), `criteria_validation_issues`, `criteria_missing_data_risks` ve `criteria_completion_history` kayıtları güncellenir.
8. **Güvenlik Kapısı:** `can_run_algorithm` fonksiyonu nihai kararı vererek algoritma çalıştırmayı engeller veya izin verir.

---

## 2. Kapsam ve Kenar Durum Yönetimi

### 2.1. Fakülte Kapsamında Veri Birleştirme

Kapsam olarak yalnızca "Fakülte" seçildiğinde (Bölüm = "Tümü"), ilgili fakülte altındaki tüm bölümlerin seçmeli dersleri havuza dahil edilir.

- Aynı ders birden fazla bölümde yer alıyorsa; öğrenci grubu, kontenjan ve not ortalaması bölüm bazlı değişebileceği için ders, **ders-bölüm bağlamında** (`course_id` + `department_id`) ayrı satırlar olarak matrise eklenir.

### 2.2. Seçmeli Ders Bulunmaması Durumu (Boş Kapsam)

Seçili kapsamda hiçbir seçmeli ders tanımlanmamışsa:

- Sistem `completion_level = "not_applicable"` döner; tamlık oranı `1.0` (yani %100) kabul edilir.
- **Kapı engellemez** (`can_run_algorithm = True`) — çünkü çalıştırılacak ders yok; yapay bir engel anlamsızdır.
- UI'da `warning_reason` ile uyarı gösterilir: *"Seçili kapsamda müfredatta seçmeli ders bulunmuyor; tamlık kontrolü uygulanmadı."*
- Oran hesabında `total_required_fields == 0` durumunda kod oranı `0.0` olarak kısa devre yaparak sıfıra bölmeye karşı da korunur.

### 2.3. Kapsam İzolasyonu (Scope Isolation)

`scope_type` ve `faculty_id`/`department_id` kombinasyonu için iki ayrı doğrulama davranışı vardır:

- **Yazma yolu (strict)**: Politika/override oluşturulurken kapsamla uyumsuz dolu ID'ler (`scope_type="faculty"` iken `department_id` dolu vb.) `ValueError` ile reddedilir. Erişilemez/anlamsız kayıt oluşmaz.
- **Okuma yolu (toleranslı)**: `resolve_policy`, `get_active_override` gibi sorgu fonksiyonları kapsama göre ilgisiz ID'leri sessizce `NULL`'a indirger. Bu sayede tutarsız bir UI girdisi tüm karar kapısını çökertmez; yalnızca *zorunlu* ID gerçekten eksikse hata verir.

### 2.4. Dönem Normalizasyonu (Katı)

Tüm servislerde dönem değeri ortak ve **katı** bir normalize fonksiyonundan geçer. `"b"` ile başlayan değerler `"Bahar"`, açıkça tanımlı değerler (`"g"`, `"guz"`, `"güz"`, `"fall"`, `"autumn"`) `"Güz"` olarak normalize edilir. **Bilinmeyen değerler** (örn. `"Yaz"`, `"Spring"` istenmeyen mappingsiz, `"abc"`) sessizce `"Güz"`a dönüştürülmez — `ValueError` ile reddedilir.

---

## 3. Tamlık Oranı ve Seviyeler

Tamlık oranı **yalnızca zorunlu kriter alanları** üzerinden hesaplanır:

$$\text{Tamlık Oranı} = \frac{\text{completed\_required\_fields}}{\text{total\_required\_fields}}$$

Burada `completed_required_fields`, **hem dolu (`is_present`) hem de geçerli (`is_valid`)** olan zorunlu alanların sayısıdır.

### 3.1. Tamlık Seviyeleri (`completion_level`)

| Seviye | Koşul |
| --- | --- |
| `not_started` | Oran %0. |
| `low_partial` | Oran %1 – %49 arası. |
| `medium_partial` | Oran %50 – %79 arası. |
| `high_partial` | Oran %80 – %99 arası. |
| `completed` | Zorunlu kriterler tam (%100) ve engelleyici (`error`/`critical`) issue yok. |
| `completed_with_warnings` | Zorunlu kriterler tam (%100), ancak `warning` seviyesinde kalite bulgusu var. |
| `invalid` / `blocked` | Geçersiz zorunlu alan veya kritik veri hatası algoritmayı engelliyor. |
| `not_applicable` | Kapsamda hiç seçmeli ders yok (bkz. §2.2). |

> **Miras (Legacy) Uyumu:** Eski sistemdeki `not_started / partial / completed` durumları (`criteria_status`) geriye dönük uyumluluk için güncellenmeye devam eder; yukarıdaki yeni seviyeler detaylı UI gösterimi için ek bilgi sağlar.

### 3.2. Engelleme Sayımı (Blocking Issue Count)

Kapı yalnızca **gerçekten karar mekanizmasını bozacak** bulgularda kapanır:

- **Sadece zorunlu alan** bulguları sayılır (opsiyonel alandaki kirlilik kapıyı tıkamaz, yalnızca UI uyarısı üretir).
- **`missing_required_value` bulguları engelleme sayımına girmez** — eksiklik zaten tamlık oranına yansır ve seviyeyi `not_started/partial` yapar. Aksi halde "veri henüz girilmemiş" durum yanlışlıkla `blocked` görünürdü.
- Geriye kalan **`error` veya `critical`** severity (yani present-ama-geçersiz veri) `block_on_critical_issues`/`block_on_invalid_numeric` politikasına göre sayılır.

---

## 4. Ders × Kriter Matrisi

`criteria_completion_matrix` her ders ve kriter kesişimi için şu meta-verileri saklar:

- `is_required` — Kriter bu kapsamda zorunlu mu?
- `is_present` — Veri var mı?
- `is_valid` — Veri geçerli mi?
- `value_text` / `value_numeric` — Ham metinsel ve normalize edilmiş sayısal değer.
- `missing_reason` / `invalid_reason` — Eksiklik veya geçersizlik gerekçesi (insan-okur metin).
- `source_type` / `source_id` — Verinin geldiği kaynak türü ve ilgili içe aktarma kaydı.
- `checked_at` — Kontrol zaman damgası.

### 4.1. Varsayılan Alan Konfigürasyonu

- **Zorunlu Alanlar:** `total_students`, `passed_students`, `average_grade`, `capacity`, `enrolled_students`
- **Opsiyonel Alanlar:** `survey_count`, `trend`

Bu liste politika bazlı (`required_fields_json` / `optional_fields_json`) ezilebilir. Bir alan aynı politikada **hem zorunlu hem opsiyonel** olamaz — politika oluştururken bu çakışma `ValueError` ile reddedilir.

### 4.2. Dönem-Spesifik Kayıt Önceliği

`_latest_criteria_row` dönem filtresi verildiğinde **dönem-spesifik kaydı** dönemsiz/jenerik kayda göre önceliklendirir. Eski sürüm yalnızca `ORDER BY id DESC` kullandığından, dönem-spesifik bir kayıttan sonra eklenen jenerik bir kayıt dönem filtresini gölgeleyebiliyordu. Yeni sıralama:

```
ORDER BY
  CASE WHEN dönem eşleşiyor THEN 0
       WHEN dönem boş/jenerik THEN 1
       ELSE 2 END,
  dk.id DESC
```

### 4.3. Kriter Özetinde Opsiyonel Alanlar (`display_ratio`)

`_criterion_summary`, her kriter için **iki ayrı oran** üretir:

- `required_completion_ratio` — yalnızca zorunlu satırların doluluk yüzdesi (opsiyonel alanda her zaman `1.0`).
- `completion_ratio` — tüm satırların gerçek doluluk yüzdesi.

Ek olarak `is_required` bayrağı ve UI'ın doğru oranı seçmesi için **`display_ratio`** alanı döner: zorunlu alanda `required_completion_ratio`, opsiyonelde `completion_ratio`. Bu sayede opsiyonel kriterler artık yanlışlıkla %100 görünmez.

---

## 5. Veri Geçerlilik Kontrolü ve İş Kuralları

`criteria_validation_service` dolu alanların mantıksal tutarlılığını denetler. Her bulgunun bir **önem seviyesi (severity)** vardır. Varsayılan politikada `block_on_critical_issues = 1` ve `block_on_invalid_numeric = 1` olduğundan, **yalnızca ZORUNLU alanlardaki `error`/`critical` bulgular** kapıyı engeller; opsiyonel alanlardaki bulgular ve `warning`/`info` engellemez. (Engel sayımı, `missing_required_value` bulgularını hariç tutar — bkz. §3.2.)

> **Severity / status ayrımı:** Karar çekirdeği iş kuralları (`passed_students > total_students`, `average_grade` ölçek dışı) **`critical`** severity üretir; ancak `status` bilinçli olarak `"invalid"` tutulur (değer mevcut ama geçersiz). `status = "critical"` yalnızca tamamen **boş zorunlu alan** içindir. Bu ayrım, tüketici tarafın "var/eksik" sınıflamasını bozmadan kritik veri hatalarını ayrı işaretler.

| İş Kuralı | Koşul | `issue_type` | Severity | Status | Kapıya Etkisi |
| --- | --- | --- | --- | --- | --- |
| **Zorunlu alan boş** | Değer boş / `-` / `N/A` / `yok` ve alan zorunlu | `missing_required_value` | `critical` | `critical` | Oranı düşürür (engel sayımına girmez) |
| **Öğrenci tutarlılığı** | `passed_students > total_students` | `inconsistent_values` | `critical` | `invalid` | Zorunlu alanda engeller |
| **Not skalası** | `average_grade`, 0–100 (veya 4'lük ölçekte 0–4) dışında | `out_of_range` | `critical` | `invalid` | Zorunlu alanda engeller |
| **Negatif değer** | `total_students`, `passed_students`, `capacity`, `enrolled_students`, `survey_count` < 0 | `out_of_range` | `error` | `invalid` | Zorunlu alanda engeller |
| **Ondalık değer** | Öğrenci/kontenjan/anket alanı tam sayı değil | `invalid_numeric_value` | `error` | `invalid` | Zorunlu alanda engeller |
| **Kontenjan aşımı** | `enrolled_students > capacity` | `inconsistent_values` | `warning` | `warning` | Engellemez |
| **Opsiyonel alan boş** | Değer boş ve alan opsiyonel | `missing_optional_value` | `info` | `valid` | Engellemez (uyarı kirliliği yapmaz) |

> Boş/`-`/`N/A`/`yok` gibi metinler her zaman **"eksik"** sayılır (`is_present = false`); zorunlu alansa `critical`, opsiyonel alansa `info` üretir. Her bulgu `is_required` bayrağı taşır; kapı yalnızca zorunlu alan bulgularını dikkate alır.

Üretilen tüm bulgular, kullanıcı dostu mesaj + öneri ile birlikte `criteria_validation_issues` tablosuna yazılır. Mesajlarda teknik alan adı yerine `FIELD_LABELS` üzerinden insan-okur etiket kullanılır (örn. *"'Geçen öğrenci' alanı zorunludur..."*).

### 5.1. Kapsam-Uyumlu Toplu Doğrulama

`validate_scope_criteria`, karar kapısının baktığı **aynı ders setini** kullanır: `mufredat + mufredat_ders + filter_elective_course_ids` üzerinden müfredattaki seçmeli dersler. Bu sayede "Validation ekranı sorun var der, Hazırlık Kontrolü sorun yok der" tipi tutarsızlıklar elimine edilmiştir.

`record_validation_issues` çağrısı `replace_existing=True` ile aynı kapsam/yıl/dönem için önceki bulguları temizleyip yeniden yazar — mükerrer kayıt birikmez.

---

## 6. Tamlık Politikası (Completion Policy)

`criteria_completion_policies`; minimum tamlık eşiği, zorunlu/opsiyonel alan listesi, engelleme bayrakları ve override izinleri gibi kuralları fakülte/bölüm/yıl/dönem bazlı tutar.

### 6.1. Çözümleme Önceliği (Hierarchical Resolution)

Sistem en spesifik kuraldan genele doğru şu sırayla arama yapar (`resolve_policy`):

1. Bölüm + Yıl + Dönem
2. Bölüm + Yıl
3. Fakülte + Yıl + Dönem
4. Fakülte + Yıl
5. Bölüm Genel
6. Fakülte Genel
7. Global + Yıl
8. Global Varsayılan

Hiçbiri yoksa otomatik olarak **Varsayılan Kriter Tamlık Politikası** (`global`, %100 eşik) üretilir. Kapsam izolasyonu (§2.3) gereği `scope_type="faculty"` çözümlemesi sırasında bölüm politikaları **aday listesine bile alınmaz**; yanlışlıkla dolu gelmiş bir `department_id` üst kapsam çözümlemesini bozmaz.

### 6.2. Yeni Ders İstisnası

`trend` gibi geçmiş veri gerektiren alan **varsayılan politikada opsiyoneldir**. Ancak kurumsal bir politika ile `trend` **zorunlu hale getirilirse**, yeni açılan derslerin kapıyı tıkamaması için istisna devreye girer:

- `allow_new_course_missing_history` aktifse ve dersin ilk müfredat yılı `new_course_grace_period_years` (örn. 2 yıl) sınırı içindeyse, `trend` o ders için geçerli kabul edilir ("Yeni ders istisnası") ve tamlık oranını düşürmez.

### 6.3. Politika Doğrulamaları

Politika oluşturulurken sessiz kabul yoktur:

- `scope_type` `{global, faculty, department}` dışında bir değer ise `ValueError`.
- Kapsama uymayan ID'ler (örn. `scope_type="global"` + `faculty_id=5`) `ValueError`.
- `required_completion_ratio` `[0.0, 1.0]` dışında ise `ValueError`.
- `new_course_grace_period_years < 0` veya `min_survey_response_count < 0` ise `ValueError`.
- Zorunlu ve opsiyonel alan listesinde **çakışan alan** varsa `ValueError`.
- Geçersiz alan adları (whitelist dışı) `ValueError`.
- Bozuk JSON alanları (`required_fields_json` vb.) sessizce yutulmaz, en azından `logger.exception` ile loglanır.

---

## 7. Eksik Veri Risk Skoru

`criteria_missing_data_risks`, eksik/hatalı verilerin karar mekanizması üzerindeki etkisini `0.0`–`1.0` arası puanlar (`missing_data_risk_service`).

### 7.1. Hesaplama (Satır-Bazlı Yaygınlık)

Risk, benzersiz eksik alan listesine değil, **ders × kriter satırları** üzerinden hesaplanır. Aynı alanın 1 derste mi yoksa 100 derste mi eksik olduğu ayırt edilir:

```
skor = 0.70 × (etkilenen hücre ağırlığı / toplam hücre ağırlığı)
     + 0.25 × (zorunlu-etkilenen ders oranı)
     + 0.05 × (opsiyonel-etkilenen ders oranı)
```

- Alan ağırlıkları `DEFAULT_FIELD_WEIGHTS` (örn. `average_grade` = 0.22 > `trend` = 0.04).
- Opsiyonel hücreler `optional_risk_multiplier` (varsayılan 0.35) ile düşük tutulur. Böylece yaygın **zorunlu** eksikler hak ettiği ağırlığı alır; yalnızca opsiyonel yaygın eksiklik (örn. her derste `survey_count` boş) riski aşırı şişirmez.
- Hem ağırlıklar hem çarpan hem eşikler politikadan ezilebilir (`risk_field_weights`, `optional_risk_multiplier`, `risk_thresholds`).

### 7.2. Risk Seviyeleri ve Eşikler

| Seviye | Aralık |
| --- | --- |
| `low` | skor < 0.25 |
| `medium` | 0.25 ≤ skor < 0.55 |
| `high` | 0.55 ≤ skor < 0.80 |
| `critical` | skor ≥ 0.80 |

### 7.3. Dönen Detay

`calculate_missing_data_risk` aşağıdaki alanları içeren bir sözlük döner:

- `missing_required_fields`, `missing_optional_fields` — etkilenen alan listeleri.
- `missing_required_count`, `invalid_required_count`, `missing_optional_count`, `invalid_optional_count` — eksik ile geçersiz veriyi ayıran sayaçlar.
- `affected_course_count`, `total_course_count` — yaygınlık göstergeleri.
- `affected_weight_sum`, `weighted_risk_ratio` — formül bileşenleri.
- `explanation` — insan-okur açıklama.
- `course_id` parametresi verildiyse matris **o derse daraltılır**; boş matris `not_applicable=True` döner.

### 7.4. Tamlık ↔ Risk Ayrımı

Tamlık oranı yalnızca matematiksel doluluğu ölçer; risk skoru ise eksik verinin kararın **adilliğini** ne kadar tehlikeye attığını gösterir. Yüksek tamlık + yüksek risk aynı anda mümkündür.

---

## 8. Görev Takibi (Task Tracking)

Eksik/hatalı girişlerin tamamlanması için `criteria_completion_tasks` üzerinden iş ataması yapılır.

- **Mükerrerlik Koruması:** Servis, aynı eksik için açık (`open`/`in_progress`) bir görev varken yeni duplicate görev üretmemeye çalışır.
- **Görev Durumları:** `open`, `in_progress`, `submitted`, `needs_revision`, `approved`, `blocked`, `closed`.

---

## 9. Override (Yönetici İzniyle Esnetme) Akışı

Eksik/hatalı veriyle algoritmayı çalıştırmak zorunda kalan kurumlar için **kontrollü bypass** mekanizmasıdır. Mekanizma artık tam bir **durum makinesi** (state machine) olarak işler.

### 9.1. Durum Makinesi (State Machine)

```
request_override → pending

pending → approved        (yetkili onayı; SoD: talep eden ≠ onaylayan)
pending → rejected        (gerekçeli ret / talep sahibinin geri çekmesi)

approved → used           (algoritma override ile çalıştırıldı)
approved → (expired)      (expires_at geçince get_active_override görmez)

rejected → final
used     → final
```

Geçersiz geçişler (`rejected → approved`, `used → rejected`, `approved → rejected`, `expired → approved` …) servis katmanında açıkça `ValueError` ile reddedilir. `approve_override`/`reject_override` yalnızca `pending` talepte çalışır; UPDATE sorgusu da `WHERE id=? AND approval_status='pending'` koşulu taşır (eşzamanlılık güvencesi).

### 9.2. Güvenlik Kuralları

1. **Politika Kilidi** — Aktif politika `allow_override = false` ise talep oluşturulamaz (`ValueError`).
2. **Gerekçe Zorunluluğu** — `override_requires_reason` açıkken boş gerekçeli talep reddedilir.
3. **Onay Durum Kısıtı** — `override_requires_approval` açıkken talep `pending` doğar ve **`pending` talepler kapıyı açmaz**; yalnızca `approved` ve süresi geçmemiş override kapıyı açar (`get_active_override`).
4. **Zaman Aşımı** — `expires_at` dolmuş override geçersiz sayılır, kapı yeniden kapanır. `expires_at` kayda yazılmadan önce UTC ISO-8601 kanonik biçimine indirgenir (`_normalize_datetime`) — string tarih kıyaslaması güvenli kalır.
5. **Süresi geçmiş talep onaylanamaz** — `approve_override` zaman aşımını kontrol eder; süresi geçmiş `pending` talep onaylanmaya çalışıldığında `ValueError`.
6. **Roller Ayrılığı (SoD)** — Talebi oluşturan kullanıcı kendi talebini **onaylayamaz**; `requested_by == approved_by` olduğunda servis `ValueError` döner. *(Reddetmede SoD uygulanmaz: talep sahibinin kendi bekleyen talebini gerekçeli geri çekebilmesi pratik bir kaçış kapısıdır; reddetme erişim açmaz.)*
7. **Zorunlu Aktör** — `approved_by`, `rejected_by`, `requested_by` boş bırakılamaz; denetim izi anonim olamaz.

### 9.3. Mükerrer Pending Engeli

Aynı kapsam/yıl/dönem/course için zaten `pending` bir override talebi varken yeni talep açılamaz — `request_override` bu durumu önceden kontrol edip `ValueError` döner. Kullanıcı UI'da defalarca "talep et"e bassa bile tek bekleyen kayıt olur.

### 9.4. Talep Sahibinin Kendi Talebini Geri Çekmesi

Bekleyen (`pending`) bir override talebini, talep eden kullanıcı `reject_override` ile gerekçeli geri çekebilir. Bu açıkça desteklenir — çünkü ret erişim açmaz ve şu an başka bir iptal yolu yoktur.

---

## 10. Tamlık Geçmişi (Audit Trail)

Veritabanı şişmesini engellemek ve anlamlı bir denetim izi bırakmak için `criteria_completion_history` tablosuna **her yenilemede değil, yalnızca anlamlı değişimde** kayıt atılır.

- **Tetikleyiciler** (`log_completion_change`): tamlık **durumu** (`criteria_status`) değişti, **seviye** (`completion_level`) değişti veya **oran** ≥ %1 oynadı.
- **Özet alanları** (`summary_json`): her tarihçe kaydı toplam/tamamlanan ders sayıları, eksik/geçersiz zorunlu alan sayıları, blocking_reason, `risk_level`, `override_active` ve `can_run_algorithm` bilgilerini taşır.
- 🟡 **Planlanan ek tetikleyiciler:** risk seviyesi değişimi ve onaylanan/reddedilen override hareketlerinin de ayrıca tarihçeye işlenmesi (şu an yalnızca özet alanına yansıyor, kayıt tetikleyicisi değil).

---

## 11. Mimari Tasarım Notu: Fonksiyon Yan Etkileri (Side-Effects)

Tamlık hesaplaması artık **iki katmanda** açıkça ayrılmıştır:

- `calculate_completion(...)` — Matrisi hesaplar, anlık durumu bellekte döner. **Kalıcı yazma yapmaz** (salt okunur analiz).
- `refresh_completion_status(...)` — Hesaplanan sonucu DB'ye (`matrix`, `issues`, `risk`, `status`, `history`) **kalıcı yazar**.
- `evaluate_algorithm_readiness(...)` — `calculate_completion`'ın insan-okur takma adı: UI hızlı kontrolleri için salt okunur değerlendirme.
- `can_run_algorithm(..., refresh=...)` — `refresh=True` (varsayılan, geriye dönük uyum) snapshot yazar; `refresh=False` salt okunur değerlendirir.

UI tarafında izleme amaçlı çağrılarda (`_load_readiness` filtre değişimleri vb.) `refresh=False` kullanılır; kalıcı snapshot yazımı yalnızca kullanıcı **"Yeni Karar Çalıştır"** veya **"Hazırlığı Yenile"** dediğinde tetiklenir.

### 11.1. Transaction Sözleşmesi

Tüm yazma yapan servis fonksiyonları (`create_default_policy`, `create_completion_policy`, `activate_completion_policy`, `request_override`, `approve_override`, `reject_override`, `mark_override_used`, `record_validation_issues`, …) **`commit: bool = True` parametresi** alır:

- `commit=True` (varsayılan): Fonksiyon atomik olarak commit eder; hata durumunda `rollback` çağırır.
- `commit=False`: Değişiklik açık transaction'da bırakılır, commit/rollback sorumluluğu çağırana aittir. `refresh_completion_status` gibi zinciri batch'leyen üst katman bu modu kullanır.

> **Önemli:** `with conn:` bloğu çıkışta her zaman commit ettiği için `commit=False` sözleşmesini yok sayar. Bu yüzden tüm servislerde açık `try/except: rollback` deseni kullanılır.

---

## 12. UI / UX Kullanımı ve Ekran Tasarımları

### 12.1. Kriter Girişi Sayfası — Gelişmiş Tamlık Paneli

`criteria_page.py`'deki tamlık paneli:

- **Özet Metrikler:** Tamlık oranı, kalite seviyesi, risk seviyesi, kapı durumu (*Hazır* / *Engellendi* / *Override ile hazır* / *Override onayı bekliyor*).
- **Bekleyen Override Bilgisi:** `override_active` yalnızca approved'u yansıttığından, panel ayrıca `list_overrides(approval_status="pending")` ile pending sorgulayıp "Override onayı bekliyor" durumunu doğru gösterir.
- **Ders × Kriter Matrisi:** Hücre bazında görsel doluluk + insan-okur etiket (`FIELD_LABELS`).
- **Opsiyonel Kriter Gösterimi:** `display_ratio` (§4.3) kullanılır; opsiyonel alanların yanına "(opsiyonel)" etiketi konur ve **gerçek doluluk yüzdesi** gösterilir.
- **Validation Issue Listesi:** Mesaj + severity + çözüm önerisi.
- **Eylem Butonları:** Eksiklerden görev oluşturma, override talep etme, matrisi CSV dışa aktarma.

#### 12.1.1. Veri Tutarlılığı Güvenceleri

- **`save_data` her durumda `performans` + `populerlik` yazar** — eski sürümde bu yazımlar yalnızca INSERT (yeni kayıt) dalındaydı; mevcut bir kaydı güncellerken algoritmanın okuduğu tablolar eski kalıyordu. Düzeltildi.
- **Kayıt öncesi validation:** `geçen ≤ toplam`, `ortalama 0-100`, negatif kontrol — hatalı veri baştan engellenir.
- **Excel İçe Aktar butonu eklendi:** `import_kriterler_excel` fonksiyonu vardı ama UI'da butona bağlanmamıştı → erişilemiyordu. Şimdi filtre bar'ında "📥 Kriter Excel İçe Aktar" butonu var.
- **`import_kriterler_excel` `department_id` tanımsız hatası giderildi** — fonksiyon her çağrıldığında `NameError` ile çöküyordu, artık seçili bölüm doğru iletiliyor.
- **Otomatik kriter üretiminde yıl artık kullanıcı seçimine bağlı:** Hard-coded `year=2022` kaldırıldı; "🎓 Otomatik Üretim" seçili akademik yıla yazar.

### 12.2. Karar Merkezi — Hazırlık Kontrolü Sekmesi

Algoritma çalıştırılmadan önceki son kontrol noktasıdır. Salt metin değil, kapının **neden** kapalı olduğunu gösteren durum özeti sunar.

Olası UI durumları:

- `Hazır` — Algoritma çalışmaya hazır, engel yok.
- `Engellendi` — Minimum eşik sağlanamadı veya kritik veri hatası var.
- `Override onayı bekliyor` — Süreç engellenmiş, yetkili onayı bekleniyor (pending override mevcut).
- `Override ile hazır` — Eksik veriye rağmen yetkili onayıyla çalıştırma izni verildi.

Sekme aynı zamanda **bekleyen override talepleri panelini** içerir (bkz. §12.4).

### 12.3. Karar Merkezi — Filtre Bar (Yeniden Tasarım)

Filtre bar artık iki satır:

- **1. satır:** Yıl · Fakülte · Bölüm · Dönem · [Yenile]
- **2. satır:** Karar Çalıştırması: [kapsama göre filtrelenmiş combobox] · [⚡ Yeni Çalıştır] · ● kapsam durumu

Davranış:

- **Kapsama göre filtreli liste:** `cb_run` artık yalnızca seçili yıl/fakülte/bölüm/dönem ile eşleşen `decision_runs` kayıtlarını gösterir. (Eski sürüm tüm sistemdeki run'ları listeliyordu → başka yıl/fakülte çalıştırmaları görünüyor ya da boş kalıyordu.)
- **Boş durumda placeholder + yönlendirme:** Kapsamda hiç çalıştırma yoksa combobox `"(Bu kapsamda henüz karar çalıştırması yok)"` gösterir ve yanında "● Bu kapsamda çalıştırma yok — sağdaki '⚡ Yeni Çalıştır' ile başlatın" yazar.
- **Dolu durumda özet:** "● 3 çalıştırma · son: 2026-06-08 14:32".
- **İnsan-okur etiket:** Eski `#5 | 2022 | completed` → yeni `#5 · 2022 Guz · [run_name] · completed`.
- **⚡ Yeni Çalıştır** butonu Çalıştırmalar alt sekmesine geçer; kullanıcı hızlıca yeni run açabilir.
- **Otomatik tazeleme:** Filtre değişince hem hazırlık görünümü hem run listesi hem ilişkili raporlar otomatik güncellenir.

### 12.4. Override Yönetim Paneli (Karar Merkezi & Kriter Girişi)

§9'daki onay akışını masaüstünde tamamlayan UI katmanı:

- **Bekleyen Override Tablosu:** ID · Kapsam · Talep Eden · Eksik Alanlar · Gerekçe · Durum · Tarih kolonlarıyla `pending` talepler listelenir.
- **Karar Butonları:** Her satırın altında **Onayla** / **Reddet** butonları.
- **Gerekçe Girişi:** Reddetme için ret gerekçesi zorunlu (dialog ile alınır).
- **Roller Ayrılığı UI Tarafı:** Backend SoD ihlali yakaladığında (`requested_by == approved_by`) UI net `messagebox` ile gösterir, sessiz başarısızlık yok.
- **Audit:** `requested_by` / `approved_by` / `rejected_by` artık `app.current_user.username` üzerinden alınır (anonim "ui" sabit string değil).
- **Durum-Duyarlı Mesaj:** Talep sonrası mesaj artık dönüş `approval_status`'a göre değişir:
  - `pending` → "Override talebi kaydedildi; ancak algoritma hâlâ çalıştırılamaz. Yetkili onayı bekleniyor."
  - `approved` → "Override aktif edildi (politika onay gerektirmiyor). Algoritma override ile çalıştırılabilir."
- **Gereksiz Talep Guard'ı:** Hazırlık zaten uygunsa veya eksik alan yoksa kullanıcı override butonuna bastığında bilgilendirici uyarı çıkar; gereksiz `pending` kayıt oluşmaz.

---

## 13. API Endpointleri

| Endpoint | Açıklama |
| --- | --- |
| `GET /api/v1/kriter/tamlik` | Genel durum, oran ve seviye özeti. |
| `GET /api/v1/kriter/tamlik/matrix` | Ders × Kriter matris verisi. |
| `GET /api/v1/kriter/tamlik/issues` | Aktif validasyon bulguları. |
| `POST /api/v1/kriter/tamlik/validate` | Manuel validasyon (salt okunur analiz). |
| `GET /api/v1/kriter/tamlik/policies` | Politikaları listeler. |
| `POST /api/v1/kriter/tamlik/policies` | Yeni politika oluşturur. |
| `POST /api/v1/kriter/tamlik/policies/{id}/activate` | Politikayı aktif yapar. |
| `GET /api/v1/kriter/tamlik/risk` | Eksik veri risk skoru. |
| `GET /api/v1/kriter/tamlik/tasks` · `POST` · `PATCH /{id}` | Görev listeleme/oluşturma/güncelleme. |
| `GET /api/v1/kriter/tamlik/overrides` | Override taleplerini listeler. |
| `POST /api/v1/kriter/tamlik/overrides/request` | Sahadan override talebi açar. |
| `POST /api/v1/kriter/tamlik/overrides/{id}/approve` | **[Yönetici]** Talebi onaylar (SoD denetimine tabi). |
| `POST /api/v1/kriter/tamlik/overrides/{id}/reject` | **[Yönetici]** Talebi reddeder. |
| `GET /api/v1/kriter/tamlik/history` | Tamlık değişim geçmişi. |
| `GET /api/v1/kriter/tamlik/can-run` | Kapının nihai durumu ve engel mesajı. |

---

## 14. Algoritma Çalıştırma Güvenlik Kapısı — Örnek Mesajlar

`run_all_algorithms_for_year` ve `generate_next_year_curricula`, çalıştırma öncesi `can_run_algorithm` sonucunu kullanır.

### Engelleyici Mesaj (`blocked`)

> ❌ **Algoritma çalıştırılamaz.**
> - **Mevcut Tamlık Oranı:** %84.0 | **Gereken Minimum Eşik:** %95.0
> - **Bulgular:** 7 zorunlu alan eksik, 2 zorunlu alan geçersiz (`passed_students > total_students`).
> - **Aksiyon:** Eksik verileri tamamlayın veya yetkili bir kullanıcıdan override onayı talep edin.

### Pending Override (`pending_override`)

> ⏳ **Override talebi kaydedildi; ancak algoritma hâlâ çalıştırılamaz.**
> - Bu kapsam için yetkili onayı gerekiyor.
> - Onay, Karar Merkezi'ndeki "Bekleyen Override Talepleri" panelinden verilebilir.

### İzin Verilen Mesaj (`ready_with_approved_override`)

> ✅ **Algoritma çalıştırılabilir (Override Aktif).**
> - Tamlık oranı %89.0. Normalde kilitli olan bu süreç, Dekanlık makamının onaylı override izniyle (Gerekçe: *"Yaz dönemi staj verileri muafiyeti"*) açılmıştır.
> - *Not: Üretilecek raporlarda override bilgisi dipnot olarak görünür.*

### Boş Kapsam (`not_applicable`)

> ⚪ **Bu kapsamda müfredatta seçmeli ders bulunmuyor.**
> - Tamlık kontrolü uygulanmadı.

---

## 15. Geliştirici İpuçları

- **Boş kapsam koruması:** Kapı kodunda önce seçmeli ders listesinin `count == 0` durumunu kontrol edin → akışı `not_applicable`'a yönlendirin (§2.2). Oran hesabında `total_required_fields == 0` durumunda sıfıra bölmeye karşı oranı `0.0` olarak kısa devre yapın.
- **Opsiyonel alan etiketi:** UI'da alanları çekerken `criterion_summary[*].is_required` veya `display_ratio` kullanın; opsiyonellerin yanına gri fontla `(opsiyonel)` ekleyin. Bu, "veri tam mı?" kaynaklı destek taleplerini belirgin biçimde azaltır.
- **Yan etki farkındalığı:** Sadece okuma amaçlı kontrol için `calculate_completion(..., refresh=False)` veya `can_run_algorithm(..., refresh=False)` kullanın; kalıcı snapshot gerektiğinde `refresh_completion_status` veya `can_run_algorithm(refresh=True)` (§11).
- **Override talebi açarken:** `requested_by` boş bırakılamaz — `app.current_user.username` veya en azından bir dialog ile alın. SoD ihlalleri (`requested_by == approved_by`) backend'de `ValueError` ile dönülür; UI tarafında `try/except ValueError` ile `messagebox.showwarning` gösterilir.
- **Pending durumu doğru göster:** `override_active` yalnızca **approved** override'ı yansıtır. Pending durumu için `list_overrides(approval_status="pending")` ile ayrıca sorgulayın ve "Override onayı bekliyor" durumunu UI'da gösterin.
- **Run combobox kapsama göre filtreli:** Karar Merkezi'nin `cb_run`'una `decision_runs` doldururken `year/faculty_id/department_id/semester` ile filtreleyin; boş durumda placeholder + yönlendirme metni gösterin.

---

## 16. Değişiklik Günlüğü (Bu Sürüm)

Bu sürümde uygulanan başlıca yönetişim güçlendirmeleri:

**Servis katmanı:**
- Override **durum makinesi** ve SoD/zorunlu aktör/mükerrer pending koruması (`criteria_override_service`).
- Boş kapsam için `not_applicable` (`criteria_completion_service`).
- Severity tablosu (`passed>total` ve `average` ölçek dışı → `critical` severity, `status="invalid"`).
- Risk **satır-bazlı yaygınlık formülü** ve ayrı sayaçlar (`missing_data_risk_service`).
- Katı `_normalize_semester`/`_normalize_scope_type`, kapsam-ID doğrulaması (yazma=katı, okuma=toleranslı).
- Politika değer doğrulamaları (ratio, grace, alan çakışması).
- `evaluate_algorithm_readiness` salt okunur ve `can_run_algorithm(refresh=...)` parametresi.
- Dönem-spesifik kayıt önceliği (`_latest_criteria_row`).
- `validate_scope_criteria` artık müfredat+seçmeli ders kapsamını kullanır.
- Atomik transaction sözleşmesi (`commit` parametresi + açık `try/rollback`).

**UI katmanı:**
- Hazırlık Kontrolü ve Kriter Girişi sekmelerine **Bekleyen Override Onay/Red paneli**.
- Override talep mesajı `pending/approved`'a göre durum-duyarlı; gereksiz talep guard'ı.
- Opsiyonel kriterler için `display_ratio` ve "(opsiyonel)" etiketi.
- `criteria_page.save_data` artık `performans`/`populerlik` tablolarını **her durumda** senkronize eder.
- `import_kriterler_excel` `NameError` düzeltildi; UI butonu eklendi.
- `auto_generate_from_dataset` artık seçili yıla yazar.
- Karar Merkezi filtre bar yeniden tasarımı (Run combobox kapsama göre filtreli, ⚡ Yeni Çalıştır kısayolu, boş-durum yönlendirmesi).
- `_safe_load` ile dayanıklı refresh; `logger.exception` ile sessiz hata yutmama.
- `current_user` üzerinden audit; anonim "ui" sabit string değil.

**Tip ve statik kalite:**
- 40 Pylance hatası (`reportArgumentType`, `reportAttributeAccessIssue`) güvenli `or 0` / `or ""` korumaları ve `dict[str, int | None]` anotasyonuyla giderildi.

**Test sonucu:** Tam regresyon set yeşil — **487 / 487 test geçer**, statik analiz temiz.
