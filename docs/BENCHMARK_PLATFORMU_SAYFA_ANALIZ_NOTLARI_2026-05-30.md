# Benchmark Platformu Sayfa Analiz Notları

Tarih: 2026-05-30  
Kapsam: `app/ui/benchmark` altındaki tüm Benchmark Platformu sayfaları, bağlı API client fonksiyonları ve temel FastAPI endpoint kontrolleri.

## 1. Yapılan UI İyileştirmeleri

- Tüm Benchmark Platformu alt sayfalarına "Bu sayfa ne işe yarar?" açıklama kutusu eklendi.
- Sol menü ve sayfa başlıkları daha anlaşılır Türkçe adlara çevrildi.
- Tablo başlıkları için `DataTable` bileşenine Türkçe görünen başlık desteği eklendi.
- Sayfalardaki temel buton, uyarı ve açıklama metinleri Türkçeleştirildi.
- `Decision Engine` sayfası kullanıcıya daha doğru anlam vermesi için "Algoritma Öneri Motoru" olarak yeniden adlandırıldı.
- `Algorithm Explorer` kategori filtresi gerçek API'den `mcdm`, `ml_baseline`, `clustering` gibi küçük harfli grup adları geldiğinde de çalışacak şekilde düzeltildi.
- `Algorithm Governance` sayfasında gerçek API client çağrıları arka plan thread akışına alındı; test/mock client kullanımında tablo dolumu senkron bırakıldı.
- `Algorithm Comparison` sayfasında önceki filtrelemeden kalan birden fazla "best" işaretinin kalmaması için sıralama öncesi işaret temizliği eklendi.

## 2. Çalıştırılan Kontroller

### 2.1 Compile Kontrolü

Çalıştırılan komut:

```text
env\Scripts\python.exe -m py_compile app\ui\benchmark\widgets.py app\ui\benchmark\benchmark_panel.py app\ui\benchmark\pages\dashboard_page.py app\ui\benchmark\pages\comparison_page.py app\ui\benchmark\pages\dataset_lab_page.py app\ui\benchmark\pages\algorithm_explorer_page.py app\ui\benchmark\pages\algorithm_governance_page.py app\ui\benchmark\pages\ml_readiness_page.py app\ui\benchmark\pages\allocation_fairness_page.py app\ui\benchmark\pages\decision_engine_page.py app\ui\benchmark\pages\run_history_page.py
```

Sonuç: Başarılı.

### 2.1.1 İlgili Test Paketi

Çalıştırılan komut:

```text
env\Scripts\python.exe -m pytest app\tests\test_algorithm_governance.py app\tests\test_ml_governance.py app\tests\benchmark -q
```

Sonuç:

```text
33 passed
```

### 2.2 UI Sayfa Oluşturma Kontrolü

Tkinter içinde şu sayfalar tek tek oluşturulup kapatıldı:

- `DashboardPage`
- `ComparisonPage`
- `DatasetLabPage`
- `AlgorithmExplorerPage`
- `AlgorithmGovernancePage`
- `MLReadinessPage`
- `AllocationFairnessPage`
- `DecisionEnginePage`
- `RunHistoryPage`

Sonuç: Tüm sayfalar constructor seviyesinde hata vermeden açıldı.

### 2.3 API Client Fallback Kontrolü

Backend API kapalı kabul edilerek `BenchmarkApiClient(timeout=0.2)` ile client metodları çağrıldı.

Sonuç: Tüm client metodları hata fırlatmadan mock/fallback veri döndürdü.

Kontrol edilenler:

- `get_algorithms`
- `get_scenarios`
- `execute_run`
- `get_runs`
- `load_dataset`
- `get_recommendation`
- `get_run_detail`
- `get_ml_readiness`
- `get_ml_model_runs`
- `get_ml_predictions`
- `get_algorithm_governance`
- `get_algorithm_tasks`
- `get_governed_runs`

### 2.4 FastAPI Endpoint Kontrolü

Yerel server açmadan `TestClient(app, raise_server_exceptions=False)` ile endpointler test edildi.

Başarılı endpointler:

- `GET /api/v1/benchmark/scenarios` -> 200
- `GET /api/v1/benchmark/algorithms` -> 200
- `POST /api/v1/benchmark/recommendation` -> 200
- `GET /api/v1/benchmark/runs` -> 200
- `GET /api/v1/ml/readiness` -> 200
- `GET /api/v1/ml/model-runs` -> 200
- `GET /api/v1/ml/predictions` -> 200
- `GET /api/v1/algorithms/governance` -> 200
- `GET /api/v1/algorithms/tasks` -> 200
- `GET /api/v1/benchmark/governed-runs` -> 200

Hatalı/engellenen endpointler:

- `POST /api/v1/benchmark/datasets/load` -> 500
- `POST /api/v1/benchmark/runs/execute` -> 400

Kök neden:

- Dataset yükleme, sentetik veri üretiminde patlıyor.
- Hata `app/datasets/synthetic_generator.py` içindeki `_bootstrap_sample` fonksiyonunda oluşuyor.
- `class_imbalance_alpha=0` iken `weights = np.ones(n)` olarak kalıyor ve normalize edilmiyor.
- `np.random.choice(..., p=weights)` olasılık toplamı 1 olmadığı için `ValueError: Probabilities do not sum to 1` üretiyor.
- Dataset yüklenemediği için `/runs/execute` doğal olarak `No dataset loaded. Call /datasets/load first.` hatasıyla 400 dönüyor.

## 3. Sayfa Bazlı Analiz

## 3.1 Benchmark Paneli

Ne işe yarar:

- Senaryo, veri seti ve algoritma seçip benchmark çalıştırmak için ana deney ekranıdır.
- Son çalıştırmanın özetini ve temel metriklerini gösterir.

Kontrol edilen fonksiyonlar:

- `get_scenarios`: Client fallback çalışıyor, gerçek API 200.
- `get_algorithms`: Client fallback çalışıyor, gerçek API 200.
- `execute_run`: Client fallback çalışıyor. Gerçek API tarafında dataset yükleme hatası nedeniyle uçtan uca doğrulanamadı.

Çalışmayan/eksik noktalar:

- Gerçek benchmark çalıştırma dataset yükleme bug'ına bağlı olarak çalışmıyor.
- Veri seti combobox'ı statik/mock değerlerle geliyor; gerçek yüklenen dataset durumunu göstermiyor.
- Senaryoya uygun olmayan algoritmalar seçilebiliyor.
- Çalıştırma öncesi "dataset hazır mı?" kontrolü UI'da açık değil.

Önerilen eklemeler:

- "Benchmark readiness" kartı: dataset yüklü, senaryo geçerli, algoritma uyumlu, backend aktif.
- Senaryo seçilince algoritma listesini otomatik uygun algoritmalarla sınırlama.
- Gerçek run sonucundaki `comparison_table` verisini özet kartlara bağlama.
- Run başarısız olursa kök neden ve çözüm önerisini kullanıcıya açık göstermek.

## 3.2 Algoritma Karşılaştırma

Ne işe yarar:

- Algoritmaları aynı senaryo ve veri seti üzerinde metriklere göre karşılaştırır.
- Tablo ve çubuk grafikle seçilen metriğe göre sıralama yapar.

Kontrol edilen fonksiyonlar:

- `get_runs`: Client fallback çalışıyor, gerçek API 200.
- Filtreleme ve sıralama UI içinde çalışıyor.

Çalışmayan/eksik noktalar:

- API'den gelen gerçek run verisi tabloya bağlanmıyor; sayfa halen `mock_data.COMPARISON_ROWS` üzerinden gösterim yapıyor.
- "Görünüm" combobox'ı var ama tablo/çubuk/çizgi görünümü arasında gerçek geçiş yapmıyor.
- `Run History` içindeki "Karşılaştırmaya Ekle" işlemi bu sayfaya gerçek seçim aktarmıyor.
- İstatistiksel anlamlılık, confidence interval ve baseline farkı görünmüyor.

Önerilen eklemeler:

- Seçilen run veya run seti üzerinden gerçek `comparison_table` kullanımı.
- Metrik tipini problem türüne göre sınırlama.
- Baseline'a göre fark, güven aralığı ve istatistiksel anlamlılık sütunları.
- Görünüm seçimine göre tablo, çubuk ve çizgi grafik render akışı.

## 3.3 Veri Seti Laboratuvarı

Ne işe yarar:

- CSV/SQLite kaynaklarından benchmark veri seti yüklemek, veri katmanlarını göstermek ve sentetik veri ayarlarını hazırlamak için kullanılır.

Kontrol edilen fonksiyonlar:

- `load_dataset`: Client fallback çalışıyor.
- Gerçek API `POST /api/v1/benchmark/datasets/load` 500 dönüyor.
- Sayfa UI olarak açılıyor.

Çalışmayan/eksik noktalar:

- Gerçek dataset yükleme sentetik veri üretim bug'ı nedeniyle çalışmıyor.
- "Sentetik Veri Üret" butonu API çağırmıyor; sadece bilgi mesajı gösteriyor.
- "Önizle" gerçek yüklenen dosyayı değil mock preview satırlarını gösteriyor.
- Veri katmanı kartları statik mock sayılar kullanıyor.

Kök neden:

- `SyntheticDataGenerator._bootstrap_sample` default durumda olasılık ağırlıklarını normalize etmiyor.

Önerilen eklemeler:

- Dataset yükleme öncesi dosya/klasör/table preflight kontrolü.
- Sentetik üretim parametrelerini gerçek API payload'ına bağlama.
- Veri önizlemeyi gerçek yüklenen `DatasetBundle` içinden alma.
- Veri kalite özeti: satır sayısı, kolon sayısı, eksik oranı, hedef kolon var mı, sınıf dağılımı.

## 3.4 Algoritma Rehberi

Ne işe yarar:

- Algoritma registry bilgisini, algoritma grubunu, kullanım rolünü, parametreleri ve örnek çıktıyı gösterir.

Kontrol edilen fonksiyonlar:

- `get_algorithms`: Client fallback çalışıyor, gerçek API 200.
- Kategori filtresi gerçek API grup adlarıyla uyumlu hale getirildi.
- Sayfa UI olarak açılıyor.

Çalışmayan/eksik noktalar:

- Algoritma detayları çoğunlukla mock veri sözlüğünden geliyor.
- Registry API yalnızca ad, grup ve rol döndürüyor; minimum veri, önerilen metrik, parametre ve risk bilgileri eksik.
- "Örnek Çıktı Üret" gerçek algoritmayı çalıştırmıyor; statik örnek JSON gösteriyor.

Önerilen eklemeler:

- Backend registry response içine `description`, `parameters`, `recommended_metrics`, `minimum_sample_count`, `limitations` alanları eklenmeli.
- Örnek çıktı, seçilen senaryo/dataset ile dry-run veya fixture üzerinden üretilebilir.
- Algoritmanın final karar etkisi daha belirgin rozetle gösterilmeli.

## 3.5 Algoritma Yönetişimi

Ne işe yarar:

- Algoritmaların kullanım rolünü, görev eşleşmesini, veri uygunluk kurallarını ve governed benchmark kayıtlarını gösterir.

Kontrol edilen fonksiyonlar:

- `get_algorithm_governance`: Client fallback çalışıyor, gerçek API 200.
- `get_algorithm_tasks`: Client fallback çalışıyor, gerçek API 200.
- `get_governed_runs`: Client fallback çalışıyor, gerçek API 200.
- Sayfa UI olarak açılıyor.
- API çağrıları arka plana alındı.

Çalışmayan/eksik noktalar:

- Governed run listesinden metrik, validation, statistics, diagnostics, leakage, clustering detaylarına geçiş yok.
- Governed benchmark çalıştırma UI'ı yok.
- Veri uygunluğu tabı açıklama metni gösteriyor ama seçili algoritmaya özel canlı guard sonucu göstermiyor.

Önerilen eklemeler:

- Run seçilince `metrics`, `validation`, `statistics`, `diagnostics`, `leakage`, `clustering` detaylarını ayrı alt panellerde gösterme.
- Governed benchmark çalıştırma formu.
- Algoritma başına minimum veri ve blocking reason rozetleri.

## 3.6 ML Güvenilirlik & Hazırlık

Ne işe yarar:

- ML modellerinin eğitilebilirlik, minimum veri ihtiyacı, readiness seviyesi, production-ready durumu, model run ve tahmin/fallback kayıtlarını gösterir.

Kontrol edilen fonksiyonlar:

- `get_ml_readiness`: Client fallback çalışıyor, gerçek API 200.
- `get_ml_model_runs`: Client fallback çalışıyor, gerçek API 200.
- `get_ml_predictions`: Client fallback çalışıyor, gerçek API 200.
- Sayfa UI olarak açılıyor.

Çalışmayan/eksik noktalar:

- Model eğitme veya feature snapshot üretme akışı bu sayfada yok.
- Tahmin/fallback paneli boş veri gelirse kullanıcıya açıklayıcı empty-state göstermiyor.
- Readiness report geçmişi görünmüyor.

Önerilen eklemeler:

- Feature summary ve snapshot üretme bağlantısı.
- Model train/run başlatma butonu, ama minimum sample guard zorunlu olmalı.
- Tahmin kayıtlarında `fallback_used`, `advisory_only`, `should_influence_decision` alanlarını okunur rozetlerle gösterme.
- ML readiness raporu export.

## 3.7 Yerleştirme Adaleti

Ne işe yarar:

- Yerleştirme algoritmalarını tercih memnuniyeti, kontenjan doluluğu, envy score ve atanmayan öğrenci sayısıyla karşılaştırır.

Kontrol edilen fonksiyonlar:

- `execute_run` client fallback çalışıyor.
- Sayfa UI olarak açılıyor.
- Gerçek allocation benchmark, dataset yükleme bug'ı nedeniyle doğrulanamadı.

Çalışmayan/eksik noktalar:

- Tablo ve grafik mock allocation verisine bağlı.
- Gerçek atama çıktıları API'den okunmuyor.
- Departman/fakülte bazlı fairness kırılımı yok.
- Kontenjan, öncelik, bölüm kuralı gibi parametreler UI'dan ayarlanamıyor.

Önerilen eklemeler:

- Gerçek `allocation_fairness` senaryosu sonucundaki atama ve fairness metriklerini tabloya bağlama.
- Bölüm/fakülte bazlı adalet raporu.
- Kontenjan ihlali ve atanmayan öğrenci nedenleri.
- Dönem planlama ile bağlantılı "bu sonuç planlamaya aktarılabilir mi?" kontrolü.

## 3.8 Algoritma Öneri Motoru

Ne işe yarar:

- Problem tipi, veri boyutu ve açıklanabilirlik önceliğine göre denenebilecek algoritma adayı önerir.

Kontrol edilen fonksiyonlar:

- `get_recommendation`: Client fallback çalışıyor, gerçek API 200.
- Problem tipi UI'da Türkçe gösteriliyor ve API payload'ına doğru teknik değere çevriliyor.
- Sayfa UI olarak açılıyor.

Çalışmayan/eksik noktalar:

- Öneri motoru, governance/readiness uyarılarını aynı ekranda göstermiyor.
- `AlgorithmManager` küçük ve açıklanabilir prediction senaryosunda `LogisticRegression` önerebiliyor; bu algoritma registry tarafında `benchmark_only` rolündeyse kullanıcıya ayrıca uyarı gerekir.
- Önerinin geçmiş benchmark verisinden mi kuraldan mı geldiği gösteriliyor, ancak veri yeterliliğiyle çapraz kontrol edilmiyor.

Önerilen eklemeler:

- Önerilen algoritma için anlık governance/readiness kartı.
- "Bu öneri final karar değildir" uyarısının rozet olarak görünmesi.
- Aday algoritmaları neden elendi/neden önerildi açıklaması.
- Öneri geçmişinde kullanılan run sayısı ve veri kapsamı.

## 3.9 Çalıştırma Geçmişi

Ne işe yarar:

- Geçmiş benchmark run kayıtlarını listeler, detay JSON'unu gösterir ve karşılaştırmaya hazırlık sağlar.

Kontrol edilen fonksiyonlar:

- `get_runs`: Client fallback çalışıyor, gerçek API 200.
- `get_run_detail`: Client fallback çalışıyor.
- Sayfa UI olarak açılıyor.

Çalışmayan/eksik noktalar:

- Tarih aralığı filtresi UI'da var ama gerçek filtreleme yapmıyor.
- "Karşılaştırmaya Ekle" sadece uyarı mesajı gösteriyor; comparison sayfasına state aktarmıyor.
- Run detayları kullanıcı dostu sekmeler yerine ham JSON olarak gösteriliyor.
- Report/export bağlantısı yok.

Önerilen eklemeler:

- Tarih filtresini parse edip gerçek listeye uygulama.
- Seçili run sepeti ve karşılaştırma sayfasına aktarım.
- Detay görünümünü özet, metrikler, validation, diagnostics, leakage ve ham JSON sekmelerine bölme.
- Run raporu export.

## 4. Genel Teknik Eksikler

- Benchmark dataset yükleme gerçek API'de kırık; bu düzelmeden Dashboard ve Allocation gerçek çalıştırma yapamaz.
- UI tarafında mock veri ile gerçek veri ayrımı daha görünür olmalı.
- Klasik benchmark API (`reports/benchmark_runs/*.json`) ile governed benchmark DB tabloları iki ayrı sonuç deposu gibi duruyor; kullanıcı açısından tek geçmiş ekranında birleşmeli.
- Bazı ekranlarda buton var ama gerçek fonksiyon bağlı değil veya yalnızca bilgi mesajı gösteriyor.
- Çok sayıda metrik aynı tabloda gösteriliyor; problem türüne göre sadeleştirilmiş metrik setleri gerekir.
- Benchmark sonuçları için rapor/export yüzeyi eksik.
- Dataset, algoritma, senaryo ve run versiyonlama bilgileri UI'da yeterince görünmüyor.

## 5. Öncelikli Düzeltme Sırası Önerisi

1. `SyntheticDataGenerator._bootstrap_sample` ağırlık normalizasyonu düzeltilsin.
2. Dataset Lab gerçek veri yükleme ve gerçek önizleme ile bağlansın.
3. Dashboard çalıştırma akışı dataset readiness kontrolüyle güvenli hale getirilsin.
4. Run History gerçek run detaylarını kullanıcı dostu sekmelere ayırsın.
5. Algorithm Comparison gerçek run verisiyle beslensin.
6. Algorithm Governance run detay endpointlerini UI'a bağlasın.
7. ML Readiness ekranına feature snapshot ve readiness report bağlantıları eklensin.
8. Allocation Fairness gerçek allocation çıktıları ve bölüm/fakülte kırılımlarıyla genişletilsin.
9. Algorithm Recommendation governance/readiness uyarılarıyla birlikte gösterilsin.
