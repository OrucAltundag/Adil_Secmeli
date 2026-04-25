# Kriter Tamlık Yönetişimi

Bu belge, Adil Seçmeli içindeki kriter tamlık kontrolünün yeni yönetişim katmanını açıklar. Amaç yalnızca “tamam/eksik” demek değil; eksik verinin nerede olduğunu, karar riskini, sorumlu aksiyonları ve algoritma çalıştırma iznini izlenebilir hale getirmektir.

## Yeni Tamlık Hattı

1. Kapsam seçilir: fakülte, bölüm, yıl ve dönem.
2. Aktif `criteria_completion_policy` çözülür.
3. Müfredattaki seçmeli dersler bulunur.
4. Ders x kriter matrisi üretilir.
5. Her kriter için varlık ve geçerlilik kontrol edilir.
6. Tamlık oranı, seviye ve risk skoru hesaplanır.
7. Status tabloları, validation issue, risk ve history kayıtları güncellenir.
8. Algoritma kapısı `can_run_algorithm` sonucuna göre çalıştırmayı engeller veya izin verir.

## Tamlık Oranı ve Seviyeler

Tamlık oranı yalnızca zorunlu kriter alanları üzerinden hesaplanır:

`completed_required_fields / total_required_fields`

Seviyeler:

- `not_started`: oran 0.
- `low_partial`: %1-%49 arası.
- `medium_partial`: %50-%79 arası.
- `high_partial`: %80-%99 arası.
- `completed`: zorunlu kriterler tam ve engelleyici issue yok.
- `completed_with_warnings`: zorunlu kriterler tam, uyarı seviyesinde kalite bulgusu var.
- `invalid` / `blocked`: geçersiz veya kritik veri algoritmayı engelliyor.

Legacy `not_started / partial / completed` alanları korunur; yeni alanlar ek bilgi sağlar.

## Ders x Kriter Matrisi

`criteria_completion_matrix` her ders ve kriter için şu bilgileri saklar:

- Kriter zorunlu mu?
- Veri var mı?
- Veri geçerli mi?
- Ham/metinsel ve sayısal değer ne?
- Eksiklik veya geçersizlik nedeni ne?
- Kaynak türü ve kaynak kaydı ne?

Varsayılan zorunlu alanlar:

- `total_students`
- `passed_students`
- `average_grade`
- `capacity`
- `enrolled_students`

Varsayılan opsiyonel alanlar:

- `survey_count`
- `trend`

## Veri Geçerlilik Kontrolü

`criteria_validation_service` dolu alanların da anlamlı olup olmadığını kontrol eder.

Örnek kurallar:

- `passed_students <= total_students`
- `average_grade` 0-100 aralığında olmalı.
- `capacity`, `enrolled_students`, `survey_count` negatif olamaz.
- `enrolled_students > capacity` uyarıdır; bazı kurumlarda kontenjan aşımı olabilir.
- Boş, `-`, `N/A`, `yok` gibi değerler eksik sayılır.

Issue kayıtları `criteria_validation_issues` tablosuna kullanıcı dostu mesaj ve öneriyle yazılır.

## Completion Policy

`criteria_completion_policies` fakülte/bölüm/yıl/dönem bazlı kuralları tutar.

Çözümleme önceliği:

1. Bölüm + yıl + dönem
2. Bölüm + yıl
3. Fakülte + yıl + dönem
4. Fakülte + yıl
5. Bölüm genel
6. Fakülte genel
7. Global + yıl
8. Global varsayılan

Varsayılan politika geriye dönük güvenlik için zorunlu alanlarda %100 tamlık ister, yeni derslerde geçmiş veri istisnasına izin verir ve override için gerekçe/onay ister.

## Yeni Ders İstisnası

`trend` gibi geçmiş veri gerektiren alanlarda yeni dersler için istisna desteklenir. Politika `allow_new_course_missing_history` ve `new_course_grace_period_years` alanlarıyla bunu yönetir.

## Eksik Veri Risk Skoru

`criteria_missing_data_risks` eksik verinin karar üzerindeki riskini 0-1 arası hesaplar.

Riskte dikkate alınanlar:

- Eksik alan zorunlu mu?
- Eksik alan karar çekirdeğinde yüksek etkiye sahip mi?
- Kaç ders etkileniyor?
- Eksiklik opsiyonel mi?
- Yeni ders istisnası geçerli mi?

Risk seviyeleri: `low`, `medium`, `high`, `critical`.

## Görev Takibi

`criteria_completion_tasks` eksik kriterler için sorumlu kişi/rol, son tarih, durum ve öncelik tutar. Servis aynı eksik için açık duplicate görev üretmemeye çalışır.

Görev durumları:

- `open`
- `in_progress`
- `submitted`
- `needs_revision`
- `approved`
- `blocked`
- `closed`

## Override Akışı

`criteria_completion_overrides` eksik veriyle gerekçeli çalıştırma istisnalarını kaydeder.

Kurallar:

- Politika override’a izin vermiyorsa talep oluşturulamaz.
- Gerekçe zorunluysa boş talep reddedilir.
- Onay gerekiyorsa `pending` override algoritmayı çalıştırmaz.
- `approved` override ilgili kapsam/yıl/dönem için algoritma kapısını açabilir.
- Süresi dolan override geçersiz sayılır.

## Tamlık Geçmişi

`criteria_completion_history` anlamlı durum/oran değişimlerini loglar. Örneğin `not_started -> partial`, `partial -> completed` veya `completed -> partial` geçişleri saklanır.

## UI Kullanımı

Kriter Girişi ekranındaki **Gelişmiş Tamlık Paneli** şunları gösterir:

- Tamlık oranı ve seviye
- Algoritma durumu: hazır, engellendi veya override ile hazır
- Eksik/geçersiz zorunlu alan sayısı
- Risk seviyesi
- Ders x kriter matrisi
- Validation issue listesi
- Eksiklerden görev oluşturma
- Override talep etme
- Tamlık matrisini CSV dışa aktarma

Karar Merkezi içinde **Hazırlık Kontrolü** sekmesi algoritma çalıştırmadan önce aynı kapı sonucunu gösterir.

## API Endpointleri

Temel endpointler:

- `GET /api/v1/kriter/tamlik`
- `GET /api/v1/kriter/tamlik/matrix`
- `GET /api/v1/kriter/tamlik/issues`
- `POST /api/v1/kriter/tamlik/validate`
- `GET /api/v1/kriter/tamlik/policies`
- `POST /api/v1/kriter/tamlik/policies`
- `POST /api/v1/kriter/tamlik/policies/{id}/activate`
- `GET /api/v1/kriter/tamlik/risk`
- `GET /api/v1/kriter/tamlik/tasks`
- `POST /api/v1/kriter/tamlik/tasks`
- `PATCH /api/v1/kriter/tamlik/tasks/{id}`
- `GET /api/v1/kriter/tamlik/overrides`
- `POST /api/v1/kriter/tamlik/overrides/request`
- `POST /api/v1/kriter/tamlik/overrides/{id}/approve`
- `POST /api/v1/kriter/tamlik/overrides/{id}/reject`
- `GET /api/v1/kriter/tamlik/history`
- `GET /api/v1/kriter/tamlik/can-run`

## Algoritma Çalıştırma Güvenlik Kapısı

`run_all_algorithms_for_year` ve `generate_next_year_curricula` artık gelişmiş `can_run_algorithm` sonucunu kullanır.

Engelleyici örnek mesaj:

`Algoritma çalıştırılamaz. Tamlık oranı %84.0, minimum eşik %95.0. 7 zorunlu alan eksik, 2 zorunlu alan geçersiz.`

Override onaylıysa çalışma izinli olur, ancak sonuçta override bilgisi görünür.
