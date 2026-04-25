# Import Governance ve Audit Trail

Bu dokuman Adil Secmeli import hattina eklenen kurumsal veri yonetisimi katmanini aciklar. Sistem mevcut `criteria_import`, `criteria_import_rows`, `survey_import` ve `survey_import_rows` tablolarini korur; ortak izleme icin `import_batches` ust kaydini kullanir.

## Yeni Import Hatti

1. Dosya alinir ve SHA256 hash hesaplanir.
2. `import_batches` kaydi `uploaded` status ile olusturulur.
3. Excel sheet, kolon, satir sayisi ve kolon imzasi kaydedilir.
4. Duplicate kontrolu ayni hash, import tipi ve kapsam uzerinden yapilir.
5. Mevcut criteria/survey/curriculum servisleri dosyayi parse eder.
6. Satir sonuclari mevcut row tablolarina yazilir ve `import_row_issues` ile siniflandirilir.
7. `import_quality_checks` kalite skorunu hesaplar.
8. Kalite yeterliyse import `validated` veya `active`, dusukse `pending_review`, hataliysa `failed` olur.
9. Onay, aktiflestirme, reddetme ve rollback islemleri status yasam dongusu uzerinden izlenir.

## Import Batch Mantigi

`import_batches` tum import tipleri icin ortak master kayittir.

Saklanan temel bilgiler:

- import tipi: `criteria`, `survey`, `curriculum`, `other`
- kaynak tablo ve kaynak import id
- orijinal dosya adi, dosya boyutu, SHA256 hash
- sheet listesi, satir/kolon sayisi, kolon imza hash'i
- fakulte/bolum/yil/donem kapsami
- status, duplicate, supersede, rollback ve onay alanlari
- kalite skoru ve kalite seviyesi

## Dosya Hash ve Duplicate Kontrol

`import_audit_service.calculate_file_hash()` dosya icerigi uzerinden SHA256 uretir. Dosya adi degisse bile icerik ayniysa hash ayni olur.

Duplicate kontrolu `detect_duplicate_import()` ile su alanlarda yapilir:

- `file_hash_sha256`
- `import_type`
- `faculty_id`
- `department_id`
- `year`
- `semester`

Duplicate import engellenmez; `duplicate_of_import_batch_id` ile isaretlenir ve UI/API tarafinda uyarilabilir.

## Import Kalite Skoru

`import_quality_service.evaluate_import_quality()` 0-1 arasi skor uretir.

Skor bilesenleri:

- zorunlu kolonlar tam mi
- basarili satir orani
- ders eslesme orani
- sayisal deger gecerliligi
- duplicate satir cezasi
- kapsam tutarliligi
- eksik veri orani

Kalite seviyeleri:

- `high`: 0.80 ve uzeri
- `medium`: 0.55-0.80 arasi
- `low`: 0.55 alti

Dusuk kalite importlar otomatik `active` yapilmaz; `pending_review` olarak incelenir.

## Satir Bazli Hata Siniflandirmasi

`import_row_issues` satir hatalarini kullanici dostu hale getirir.

Desteklenen ornek tipler:

- `missing_required_column`
- `empty_required_value`
- `invalid_numeric_value`
- `out_of_range`
- `course_not_matched`
- `ambiguous_course_match`
- `duplicate_course`
- `invalid_scope`
- `invalid_year`
- `invalid_semester`
- `invalid_header`
- `unknown_error`

Her issue bir `severity`, insan okunabilir `message` ve duzeltme `suggestion` icerir.

## Status Yasam Dongusu

Desteklenen status degerleri:

- `uploaded`
- `validated`
- `pending_review`
- `approved`
- `active`
- `superseded`
- `rejected`
- `rolled_back`
- `failed`

`activate_import()` ayni kapsamda onceki aktif importu `superseded` yapar ve yeni importu `active` hale getirir.

## Preview, Validation ve Approval

API preview endpointi dosyayi aktif veriye yazmadan metadata ve batch kaydi uretir. Mevcut masaustu import butonlari geriye uyumluluk icin hizli import davranisini korur; yeni batch/quality/status katmani arka planda olusur.

Onay akisinda:

- `approve_import()` importu `approved` yapar.
- `activate_import()` importu aktif hale getirir.
- `reject_import()` gerekceyle reddeder.

## Diff / Karsilastirma

`import_diff_service.recalculate_import_diff()` ayni kapsamda yeni import ile onceki importu karsilastirir.

Karsilastirma anahtari:

1. `matched_ders_id`
2. `ders_kodu`
3. `ders_adi`
4. satir anahtari

Uretilen degisim tipleri:

- `added`
- `removed`
- `changed`
- `unchanged`

Alan bazli `before_value` ve `after_value` `import_diff_items` tablosunda saklanir.

## Rollback Mantigi

`import_rollback_service.rollback_import()` veri silmek yerine pasifleme ve loglama yapar.

Rollback sirasinda:

- import batch `rolled_back` olur
- `criteria_value_sources` aktif kayitlari pasiflenir
- varsa onceki import batch tekrar `active` yapilir
- `import_rollback_logs` tablosuna etkilenen tablo ve aksiyon yazilir

Rollback oncesi UI/API `get_rollback_plan()` ile etki planini gosterebilir.

## Import Impact Report

`import_impact_service` import ile karar calistirmalari arasinda bag kurar.

`decision_run_import_sources` ileride veya mevcut karar merkezi ile import kaynaklarini baglar. `import_impact_reports` onceki ve yeni decision run varsa karar degisim sayilarini hesaplar; run baglantisi yoksa guvenli sekilde sinirli rapor uretir.

## Alan Bazli Veri Kokeni

`criteria_value_sources` her ders/yil/alan icin verinin kaynagini tutar.

Kaynak tipleri:

- `criteria_import`
- `survey_import`
- `curriculum_import`
- `manual`
- `api`
- `computed`
- `override`

Criteria import basari, kontenjan ve doluluk alanlarini; survey import anket alanlarini kaynak kaydi olarak yazar.

## Manuel Override

`import_lineage_service.apply_manual_override()` aktif kaynak kaydini pasifler, yeni `override` kaydi ekler ve gerekceyi saklar. Override icin gerekce zorunludur.

## Veri Yonetimi UI

Ana Tkinter uygulamasina `Veri Yönetimi` sekmesi eklenmistir.

Alt paneller:

- Import Geçmişi
- Import Detayı
- Satır Sonuçları
- Kalite Kontrol
- Diff / Karşılaştırma
- Rollback & Onay
- Karar Etkisi

UI veriyi servislerden okur; import kalite, diff, rollback ve impact hesaplarini dogrudan UI icinde yapmaz.

## API Endpointleri

Temel endpointler `/api/v1` altindadir.

- `GET /imports`
- `GET /imports/{import_batch_id}`
- `GET /imports/{import_batch_id}/rows`
- `GET /imports/{import_batch_id}/issues`
- `GET /imports/{import_batch_id}/quality`
- `POST /imports/{import_batch_id}/quality/recalculate`
- `POST /imports/preview`
- `POST /imports/{import_batch_id}/validate`
- `POST /imports/{import_batch_id}/approve`
- `POST /imports/{import_batch_id}/reject`
- `POST /imports/{import_batch_id}/activate`
- `GET /imports/{import_batch_id}/diff`
- `POST /imports/{import_batch_id}/diff/recalculate`
- `GET /imports/{import_batch_id}/rollback-plan`
- `POST /imports/{import_batch_id}/rollback`
- `GET /imports/{import_batch_id}/impact`
- `POST /imports/{import_batch_id}/impact/recalculate`
- `GET /imports/value-sources`
- `GET /courses/{course_id}/value-sources`

## Geriye Donuk Uyumluluk

Mevcut import servisleri eski imzalarla calismaya devam eder. Yeni opsiyonel parametreler:

- `auto_activate=True`
- `uploaded_by=None`

Eski servisler veri yazmaya devam ederken, yeni audit trail tablolarina batch, kalite, issue, diff ve lineage kayitlari eklenir.
