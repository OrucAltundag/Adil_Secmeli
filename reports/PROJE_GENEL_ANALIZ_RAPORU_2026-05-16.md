# Proje Genel Analiz Raporu - 2026-05-16

Bu rapor `Adil_Secmeli_Python` projesinin mevcut kod tabanı, çalışma akışı, hedefleri, fonksiyon aileleri, doğrulama sonucu ve açık riskleri üzerinden hazırlanmıştır. Fonksiyon/sınıf düzeyi tam envanter ayrıca `reports/FONKSIYON_ENVANTERI_2026-05-16.md` dosyasına çıkarılmıştır.

## 1. Kısa Sonuç

Proje, fakülte bazlı seçmeli ders kararlarını veriyle destekleyen Tkinter masaüstü uygulaması ve FastAPI REST API yüzeyinden oluşuyor. Ana ürün hattı; veri importu, veri kalitesi, kriter tamlığı, AHP ağırlık yönetimi, TOPSIS sıralama, karar yönetişimi, havuz yaşam döngüsü, dönem planlama, raporlama ve benchmark/ML analizlerinden oluşuyor.

Mevcut test sonuçlarına göre çekirdek karar mantığı çalışıyor: AHP, TOPSIS, trend, state machine, karar yönetişimi, import yönetişimi, veri kalitesi, ML yönetişimi ve dönem planlama testleri başarılı. Ancak üretim hazır olma tarafında güvenlik ayarları, bağımlılık listesi, mimari sınır ihlalleri, bazı UI modüllerinin düşük test kapsamı ve legacy SQLite erişimleri önemli teknik borç olarak duruyor.

## 2. Kod Tabanı Envanteri

Üretim `app/` kodu, `app/tests` hariç:

| Ölçüm | Değer |
|---|---:|
| Python dosyası | 277 |
| Üst seviye fonksiyon | 1.430 |
| Sınıf | 387 |
| Sınıf metodu | 841 |

Tam proje taraması, `main.py`, `app`, `alembic`, `scripts`, `tests` dahil:

| Ölçüm | Değer |
|---|---:|
| Python dosyası | 356 |
| Üst seviye fonksiyon | 1.754 |
| Sınıf | 431 |
| Sınıf metodu | 1.008 |

Tam fonksiyon ve sınıf listesi: `reports/FONKSIYON_ENVANTERI_2026-05-16.md`

## 3. Projenin Hedefi

Sistemin hedefi, üniversitelerde seçmeli ders havuzunu sezgisel kararlarla değil, izlenebilir veri ve akademik kurallarla yönetmek:

- Derslerin performans, popülerlik, anket ve trend verisini toplamak.
- Fakülte/bölüm/yıl/dönem bağlamında kriter tamlığını kontrol etmek.
- AHP profilleriyle kriter ağırlıklarını versiyonlamak ve onaylamak.
- TOPSIS ile dersleri çok kriterli sıralamak.
- Düşük skor, düşük veri güveni, stratejik/akreditasyon koruması gibi kuralları karar merkezinde açıklanabilir hale getirmek.
- Havuzdaki dersleri `müfredatta`, `havuzda`, `dinlenmede`, `kalıcı iptal` yaşam döngüsüyle yönetmek.
- Güz/Bahar dönem planlarını kapasite, ön koşul, kaynak, öğretim üyesi ve tekrar kısıtlarıyla üretmek.
- ML ve alternatif algoritmaları nihai karar yerine benchmark, destekleyici analiz veya uyarı katmanı olarak konumlandırmak.

## 4. Ana Çalışma Akışı

```text
config.json / .env
  -> app.main veya app.api.main
  -> DB bağlantısı ve schema compatibility
  -> veri importu / manuel kriter girişi
  -> veri kalitesi ve kriter tamlığı
  -> AHP profil seçimi ve ağırlık snapshot'ı
  -> TOPSIS skorları ve trend/veri güveni hesapları
  -> karar run kaydı, açıklama, fairness, sensitivity
  -> havuz state machine ve onay/override mekanizması
  -> dönem planlama ve raporlama
  -> UI sekmeleri / REST API / benchmark paneli
```

`app.main` otomatik modda Windows gibi GUI ortamlarında Tkinter arayüzünü, headless ortamlarda API modunu başlatacak şekilde tasarlanmış. `--mode migrate` schema compatibility çalıştırıyor, `--mode schema-check` şema sağlığını raporluyor, `--mode api` FastAPI sunucusunu açıyor.

## 5. Giriş Noktaları

| Dosya | Görev |
|---|---|
| `main.py` | Proje kökünden çalıştırma kısayolu. `app.main.main()` fonksiyonunu çağırır. |
| `app/main.py` | Masaüstü uygulaması, CLI modları, Tkinter sekmeleri, DB bağlantısı, otomatik seed/yenileme. |
| `app/api/main.py` | FastAPI uygulaması, CORS, rate limit middleware, router kayıtları ve hata dönüştürücüler. |
| `scripts/run_tests.py` | Marker bazlı test runner; quick, coverage, kategori bazlı test çalıştırma. |

Önemli fonksiyonlar:

- `is_headless_environment()`: GUI display var mı kontrol eder.
- `load_config()`: legacy config sözlüğünü `config.json` ile birleştirir.
- `run_api_server()`, `run_gui()`, `run_migrate()`, `run_schema_check()`: çalışma modlarını uygular.
- `main(argv)`: CLI argümanlarını okuyup doğru moda yönlendirir.
- `AdilSecmeliApp.__init__()`: ürün akışındaki tüm UI sekmelerini kurar.
- `AdilSecmeliApp.auto_connect()`: DB bağlantısı, havuz seed ve UI yenileme akışını başlatır.

## 6. UI Katmanı

`app/ui` Tkinter arayüzüdür. Ürün sırası şu şekilde kurulmuş:

1. Sistem Sağlığı
2. Güvenlik ve Üretim Hazırlığı
3. Veri Yönetimi
4. Veri Kalitesi
5. Hesaplama ve Test
6. AHP Ağırlık Yönetimi
7. Karar Merkezi
8. Dönem Planlama
9. Rapor ve Yükleme
10. Analiz ve Grafik
11. Benchmark Platformu
12. Tablo Görüntüle

UI tarafı ağırlıklı olarak servisleri çağırıyor, fakat hâlâ doğrudan SQL kullanan legacy alanlar var. Mimari standarda göre yeni UI kodunda iş kuralı ve doğrudan DB erişimi olmamalı.

Riskli/iyileştirilecek UI noktaları:

- `app/ui/tabs/data_quality_page.py` doğrudan SQLite bağlantısı açıyor; architecture audit bunu ihlal olarak görüyor.
- `app/ui/tabs/relations_tab.py` `networkx` kullanıyor, fakat `networkx` requirements içinde yok ve mevcut ortamda kurulu değil. Bu sekmede ilişki grafiği açıldığında uyarı verip çalışmayı durdurur.
- UI test kapsamı düşük; çoğu sekme yalnızca import/smoke düzeyinde test edilmiş.

## 7. API Katmanı

`app/api/main.py` toplam 202 route ile FastAPI yüzeyini ayağa kaldırıyor. Endpoint aileleri:

- Temel veri: dersler, skorlar, havuz, müfredat, fakülteler.
- Sistem: health, schema health, architecture audit, config summary.
- Kriter tamlığı: matrix, issues, policy, override, task, history, can-run.
- Algoritma çalıştırma: yıl/fakülte/dönem bazlı çalışma.
- Import governance: preview, validate, approve, reject, activate, diff, rollback, impact, lineage.
- Decision governance: AHP profile, policy, run, course decisions, explanation, fairness, sensitivity, data confidence.
- Havuz governance: policies, course flags, transitions, approvals, overrides, lifecycle summary.
- AHP governance: criteria, profiles, lifecycle, consistency, impact, stale decisions.
- Semester planning: policies, availability, instructors, resources, prerequisites, generation, reports.
- Algorithm/benchmark governance: registry, tasks, data guard, governed benchmark runs.
- ML: algorithm registry, readiness, features, model runs, predictions, explanations.
- Data quality: coverage, readiness, confidence, missing data, validation issues, collection priorities.
- Security: API clients, SQL console, secure import, audit chain, backup.

Mimari olarak yeni endpointlerin servis katmanına gitmesi hedeflenmiş. `app/api/routes.py` ise hâlâ allowlist'e alınmış legacy/raw SQL adaptörü olarak duruyor.

## 8. Servis Katmanı

Projenin asıl iş kuralları `app/services` altında. Kritik servis aileleri:

### 8.1 Karar ve Skorlama

- `app/services/calculation.py`: AHP, TOPSIS, trend, skor kalıcılığı, sonraki yıl müfredat üretimi.
- `KararMotoru.ahp_matrisi()`: varsayılan Saaty ikili karşılaştırma matrisini döndürür.
- `KararMotoru.ahp_calistir()`: profil ağırlığı varsa onu normalize eder, yoksa özvektör yöntemiyle AHP ağırlığı üretir.
- `KararMotoru.ahp_tutarlilik_kontrolu()`: consistency ratio hesaplar.
- `KararMotoru.gecmis_trend_hesapla()`: son yılların ağırlıklı trend skorunu üretir; eksik yıllarda ağırlığı yeniden ölçekler.
- `KararMotoru.topsis_calistir()`: normalize, ağırlıklı normalize, ideal çözüm ve yakınlık katsayısı adımlarını uygular.
- `get_faculty_year_topsis_results()`: fakülte/yıl/dönem için aday derslerin TOPSIS skorlarını üretir.
- `persist_faculty_year_topsis_scores()`: skorları `havuz` tablosuna yazar.
- `generate_next_year_curricula()`: fakülte/yıl/dönem için sonraki yıl müfredatı üretir.
- `run_all_algorithms_for_year()`: algoritma kontrol merkezi için yıllık manuel çalıştırmadır.
- `rebuild_school_curricula_dual_semester()`: Güz/Bahar blokları için üretim wrapper'ıdır.

### 8.2 Havuz ve Yaşam Döngüsü

- `app/services/havuz_karar.py`: legacy state machine.
- `calculate_next_status()`: önceki statü, sayaç ve bu yıl müfredatta olma durumundan yeni statü/sayaç üretir.
- `calculate_next_status_semester()`: aynı dersin aynı yıl iki dönemde seçilmesini engeller.
- `mufredat_durumunu_esitle()`: yıllar arası statü/sayaç zincirini senkronize eder.
- `app/services/pool_state_machine_service.py`: akademik koruma, grace period, düşük veri güveni, onay ve override destekli yeni state machine.
- `evaluate_course_state_transition()`: tek ders için recommended/final status, onay gereksinimi ve açıklama üretir.
- `save_state_transition()`: geçiş kaydını kalıcılaştırır.
- `approve_state_approval()` / `reject_state_approval()`: akademik onay akışını yürütür.
- `get_pool_lifecycle_summary()`: havuz yaşam döngüsü özetini üretir.

### 8.3 Karar Run Yönetişimi

- `app/services/decision_run_service.py`: karar çalışması kaydı, AHP snapshot, policy, açıklama, fairness, sensitivity ve data confidence entegrasyonu.
- `create_decision_run()`: run üst kaydını açar.
- `record_decision_run_for_faculty_year()`: üretilen kararları run altında kaydeder.
- `execute_decision_run()`: API'den tetiklenen karar çalışması adapter'ıdır.
- `list_decision_runs()`, `get_decision_run()`, `list_course_decisions()`: karar geçmişini okur.

### 8.4 AHP ve Kriter Yönetimi

- `app/services/ahp_profile_service.py`: global/fakülte/bölüm/yıl/dönem kapsamlı AHP profil yaşam döngüsü.
- `seed_default_profile()`: varsayılan AHP profilini idempotent oluşturur.
- `create_profile()`, `update_profile()`, `validate_profile()`, `submit_for_approval()`, `approve_profile()`, `activate_profile()`: profil yönetim hattı.
- `resolve_ahp_profile()`: karar çalışması için en uygun aktif profili bulur.
- `app/services/criteria_completion_service.py`: ders kriterlerinin tamamlanma matrisini, eksik/veri hatalarını ve algoritma çalıştırma kapısını yönetir.
- `calculate_completion()`: kapsam bazlı tamlık oranı, uyarı ve blokaj üretir.
- `can_run_algorithm()`: kriter tamlığı karar hattını çalıştırmaya izin veriyor mu kontrol eder.

### 8.5 Import ve Veri Kalitesi

- `curriculum_import_service.py`: müfredat Excel importu, scope bazlı replace ve karşılaştırma.
- `survey_import_service.py`: anket importu, ders eşleştirme, önceki importu replace etme.
- `criteria_import_service.py`: kriter workbook importu, audit batch ve manuel override etkileşimi.
- `import_audit_service.py`, `import_quality_service.py`, `import_diff_service.py`, `import_rollback_service.py`, `import_impact_service.py`: import onay, kalite, fark, geri alma ve etki analizleri.
- `data_quality_integration_service.py`, `data_confidence_service.py`, `missing_data_risk_service.py`: veri kapsaması, veri güveni ve eksik veri riskleri.

### 8.6 Dönem Planlama

- `semester_planning_engine.py`: aday dersleri Güz/Bahar'a dağıtır.
- `generate_semester_plan()`: politika, kapasite, dönem uygunluğu, ön koşul, kaynak ve öğretim üyesi kısıtlarıyla plan üretir.
- `semester_planning_policy_service.py`: planlama politikalarını oluşturur, aktive eder, scope önceliğiyle çözer.
- `semester_planning_reporting_service.py`: plan özetleri, atamalar, ihlaller ve alternatif senaryoları döndürür.

### 8.7 ML, Benchmark ve Alternatif Algoritmalar

- Nihai karar hattı AHP + TOPSIS + kural motoru + state machine olarak tasarlanmış.
- ML modelleri destekleyici/benchmark rolünde kalıyor; testler bunu doğruluyor.
- `algorithm_governance_service.py`: hangi algoritmanın hangi rol ve görevde kullanılacağını registry üzerinden belirliyor.
- `algorithm_data_guard_service.py`: minimum örnek ve sınıf dengesi gibi koşulları kontrol ediyor.
- `ml_training_service.py`, `ml_prediction_service.py`, `ml_explainability_service.py`, `ml_readiness_report_service.py`: ML run, tahmin, açıklama ve readiness akışını oluşturuyor.
- `app/algorithms`: AHP, TOPSIS, VIKOR, PROMETHEE, sınıflandırıcılar, baseline modeller, allocation ve clustering algoritmalarını soyut arayüzlerle sunuyor.

## 9. Veritabanı ve Veri Durumu

Aktif SQLite dosyası:

`data/adil_secmeli.db`

Şema sağlığı:

- DB mevcut: evet
- Alembic version: `20260512_0012`
- Şema sağlıklı: evet
- Runtime schema mutation: development ortamında açık

Seçili tablo sayıları:

| Tablo | Kayıt |
|---|---:|
| `ders` | 650 |
| `fakulte` | 5 |
| `bolum` | 9 |
| `ogrenci` | 1.500 |
| `kayit` | 20.244 |
| `performans` | 1.608 |
| `populerlik` | 1.608 |
| `ders_kriterleri` | 1.609 |
| `havuz` | 2.448 |
| `mufredat` | 85 |
| `mufredat_ders` | 2.247 |
| `decision_runs` | 30 |
| `course_decisions` | 594 |
| `course_state_transitions` | 594 |
| `course_state_approvals` | 120 |
| `data_coverage_reports` | 16 |
| `schema_compat_logs` | 962 |

Bu veri seti demo/analiz için dolu. Buna karşılık bazı üretim modüllerine ait tablolar boş: API client, secure import, ML model runs, ML predictions, semester plan runs, instructors/resources/prerequisites gibi tablolar henüz aktif kullanım verisi taşımıyor.

## 10. Test ve Doğrulama Sonuçları

Çalıştırılan doğrulamalar:

| Komut | Sonuç |
|---|---|
| `python scripts\run_tests.py --quick` | 340 passed, 2 skipped, 8 deselected |
| `python -m pytest tests -q` | 6 passed |
| `python -m app.main --mode migrate` | başarılı |
| `python -m app.main --mode schema-check` | başarılı |
| API import kontrolü | `Adil Seçmeli API`, 202 route |
| `python scripts\run_tests.py --quick --coverage` | 340 passed, 2 skipped, 8 deselected, coverage %58 |

Coverage sonucu:

- Toplam kapsam: %58
- Algoritma çekirdeği güçlü: `mcdm/ahp.py` %92, `mcdm/topsis.py` %88.
- Kritik governance servisleri iyi: `criteria_completion_service.py` %89, `pool_state_machine_service.py` %79, `semester_planning_engine.py` %82.
- UI dosyaları düşük: birçok Tkinter sekmesi %0-%20 aralığında.
- API route dosyası büyük ve düşük kapsamlı: `app/api/routes.py` yaklaşık %23.

Test sırasında görülen uyarı:

- Coverage çalışmasının sonunda birkaç `ResourceWarning: unclosed database` uyarısı oluştu. Testleri düşürmüyor, fakat DB connection kapanışlarının bazı yollarında iyileştirme gerektiğini gösteriyor.

## 11. Çalışan Kısımlar

- Şema kontrolü ve migration compatibility başarılı.
- Hızlı test paketi temiz geçiyor.
- AHP ağırlık hesaplama, consistency ratio ve profil yönetişimi çalışıyor.
- TOPSIS skorları deterministik ve uç durum testleri geçiyor.
- Havuz state machine ve akademik onay/override mantığı testli.
- Kriter tamlığı, validation issues, eksik veri ve algorithm gate testli.
- Import governance, rollback, diff ve value source akışları testli.
- ML algoritmaları nihai karara etki etmeyecek şekilde yönetişimle sınırlanmış.
- Dönem planlama 4+4 varsayılan politika, kapasite, kaynak ve ön koşul ihlallerini raporluyor.
- API temel health ve sistem endpointleri çalışıyor.

## 12. Çalışmayan veya Riskli Noktalar

### Kritik

1. Güvenlik üretim hazır değil.
   - Security health skoru: 30/100, seviye: `demo_only`.
   - API auth kapalı.
   - RBAC kapalı.
   - Rate limiting kapalı.
   - Import approval kapalı.
   - CORS origin listesi development ayarında permissive.
   - SQL Console development modunda açık.

2. Requirements dosyası kodla tam uyumlu değil.
   - Kodda kullanılan ama `requirements.txt` içinde açıkça olmayan paketler: `networkx`, `psutil`, `scipy`, `pydantic`, opsiyonel `xgboost`.
   - Mevcut ortamda `networkx`, `psutil`, `xgboost` kurulu değil.
   - `relations_tab.py` network graph özelliği `networkx` yoksa çalışmıyor.
   - `performance_check.py` psutil yoksa health performans kontrolü eksik kalır.

3. Mimari sınır ihlalleri devam ediyor.
   - Architecture audit: 810 bulgu, 658 allowlist dışı ihlal.
   - En büyük kaynak servis katmanındaki doğrudan `sqlite3`/`execute` kullanımı.
   - `app/api/routes.py` legacy raw SQL adaptörü olarak allowlist'te.
   - `app/ui/tabs/data_quality_page.py` UI katmanında doğrudan SQLite erişimi yaptığı için ihlal olarak görünüyor.

### Orta

4. API katmanı çok büyük tek dosyada yoğunlaşmış.
   - `app/api/routes.py` 3.000+ satır ve 180+ endpoint fonksiyonu içeriyor.
   - Bakım için route ailelerine ayrılması gerekir: criteria, decision, import, pool, ahp, semester, ml, data quality.

5. UI test kapsamı düşük.
   - Display gerektiren sekmeler gerçek kullanıcı akışına yakın test edilmiyor.
   - Import smoke var, fakat buton/combobox/treeview davranışı geniş ölçüde doğrulanmıyor.

6. Root `tests/` dizini pytest varsayılanına dahil değil.
   - `pytest.ini` sadece `app/tests` çalıştırıyor.
   - Kök `tests` elle çalıştırıldığında geçiyor, fakat standart test komutundan kaçıyor.

7. Bazı repository dosyaları iskelet seviyesinde.
   - `department_repository.py` ve `faculty_repository.py` yalnızca `pass` içeriyor.
   - Bu, hedeflenen repository mimarisinin tam bitmediğini gösteriyor.

8. Development DB üzerinde schema compatibility log sayısı yüksek.
   - `schema_compat_logs` 962 kayıt içeriyor.
   - Geliştirme için kabul edilebilir, fakat production'da runtime schema mutation kapalı tutulmalı ve Alembic ana yol olmalı.

### Düşük

9. Bazı modüllerde sessiz `except/pass` kullanımı var.
   - Çoğu compatibility/fallback amaçlı olsa da gerçek hataları gizleme riski taşıyor.

10. API auth doğrulaması tüm aktif API client kayıtlarını çekip hash karşılaştırıyor.
    - Küçük kurulum için çalışır; büyük kullanımda client id prefix veya indexed lookup gerekir.

## 13. Olması Gereken Hedef Mimari

Hedef mimari doğru tanımlanmış ve dokümante edilmiş:

```text
UI / API
  -> Service Layer
  -> Repository Layer
  -> SQLAlchemy ORM / merkezi DB session
  -> Database
```

Bu hedefe ulaşmak için:

- UI içinde doğrudan SQL bırakılmamalı.
- API route fonksiyonları sadece request/response, permission ve servis çağrısı yapmalı.
- İş kuralları servislerde kalmalı.
- Ham SQL gerekiyorsa repository içinde izole edilmeli.
- Schema değişiklikleri Alembic migration ile yapılmalı.
- `schema_compat.py` yalnızca legacy SQLite dosyasını güvenli açma fallback'i olmalı.
- Production'da API auth, RBAC, rate limit, CORS allowlist, import approval ve SQL Console policy netleştirilmeli.

## 14. Öncelikli Aksiyon Planı

1. `requirements.txt` dosyasını kodla eşitle.
   - En azından `pydantic`, `scipy`, `networkx`, `psutil` eklenmeli.
   - `xgboost` opsiyonel kalacaksa extra/optional olarak belgelenmeli.

2. Security production profilini tamamla.
   - `.env.example` içine `API_AUTH_ENABLED`, `REQUIRE_RBAC`, `RATE_LIMIT_ENABLED`, `CORS_ALLOWED_ORIGINS`, `IMPORT_REQUIRES_APPROVAL`, `ENABLE_SQL_CONSOLE` gibi anahtarları ekle.
   - Production'da auth/RBAC/rate limit açık, SQL Console kapalı olmalı.

3. API dosyasını böl.
   - `routes.py` içindeki endpoint ailelerini ayrı router dosyalarına taşı.
   - Legacy raw SQL endpointleri için açık migration planı çıkar.

4. Repository geçişini tamamla.
   - `data_quality_page.py` gibi UI doğrudan DB erişimlerini servis/repository arkasına al.
   - `department_repository.py` ve `faculty_repository.py` iskeletlerini tamamla veya kaldır.

5. Connection cleanup uyarılarını kapat.
   - ResourceWarning veren test yollarında DB bağlantılarının context manager veya `finally` ile kapandığını doğrula.

6. UI testlerini güçlendir.
   - Display gerektiren testleri ayrı marker ile tut, ama en azından servis çağrısı yapan UI event handler'ları mock ile test et.

7. Root testleri standart test komutuna dahil et.
   - Ya `pytest.ini` testpaths içine `tests` ekle ya da `scripts/run_tests.py` root testleri de çalıştırsın.

## 15. Genel Değerlendirme

Proje akademik karar destek sistemi olarak güçlü bir çekirdeğe sahip: karar algoritmaları, yönetişim, veri kalitesi, açıklanabilirlik ve deterministik testler ciddi şekilde ele alınmış. En büyük sorun algoritma doğruluğu değil, üretim sertleştirme ve mimari temizliktir.

Kısa vadede proje demo ve geliştirme ortamında çalışır durumda. Üretim için ise güvenlik varsayılanları, bağımlılık yönetimi, legacy SQLite erişimleri ve API/UI test kapsamı tamamlanmadan doğrudan canlı sisteme alınmamalıdır.
