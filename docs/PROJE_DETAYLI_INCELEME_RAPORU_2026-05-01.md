# Adil Seçmeli Projesi Detaylı İnceleme Raporu

**İnceleme tarihi:** 1 Mayıs 2026  
**İncelenen kaynaklar:** `README.md`, `docs/`, `app/`, `data/adil_secmeli.db`, test dosyaları ve algoritma/servis katmanları.  
**Not:** Rapor mevcut kod tabanının güncel haline göre hazırlanmıştır. Bazı eski dokümanlarda API veya bağımlılık durumu için daha eski ifadeler bulunuyor; bu raporda kodda görülen güncel durum esas alınmıştır.

---

## 1. Proje Nedir?

**Adil Seçmeli**, üniversitelerde seçmeli ders planlama, öneri, müfredat güncelleme ve ders havuzu yönetimi süreçlerini veriye dayalı hale getiren bir karar destek sistemidir.

Proje iki ana kullanım yüzeyi sunar:

1. **Tkinter masaüstü uygulaması**
   - Veritabanı tablolarını görüntüler.
   - Kriter, müfredat ve anket verisi girer/yükler.
   - AHP, TOPSIS, trend, ML ve karar ağacı analizlerini çalıştırır.
   - Havuz ve müfredat durumlarını raporlar.
   - Benchmark platformu ekranlarını gösterir.

2. **FastAPI REST API**
   - Dış sistemlerle entegrasyon için ders, skor, havuz, müfredat, akademik plan ve import uçları sağlar.
   - Benchmark deneyleri için ayrı API uçları barındırır.

Projenin temel alanı şudur:

> Bir seçmeli ders gelecek yıl/dönem müfredatta kalmalı mı, havuza mı alınmalı, dinlenmeye mi çekilmeli, kalıcı iptal mi edilmeli veya yerine hangi ders önerilmeli?

---

## 2. Projenin Amacı

Projenin ana amacı, seçmeli ders kararlarını kişisel yorumdan çıkarıp **ölçülebilir, açıklanabilir, izlenebilir ve adil** bir karar sürecine dönüştürmektir.

Amaçlar:

1. **Veriye dayalı seçmeli ders kararı üretmek**
   - Başarı oranı, not ortalaması, doluluk, anket tercihi ve geçmiş trend birlikte değerlendirilir.

2. **Müfredat ve havuz yönetimini otomatikleştirmek**
   - Dersin müfredatta kalması, havuza düşmesi, dinlenmesi veya iptal edilmesi yıllar arasında takip edilir.

3. **Fakülte/bölüm kapsamını korumak**
   - Dersler fakülte ve bölüm bağlamında işlenir.
   - Bölüm dışı ders kullanımı sınırlanır ve audit edilir.

4. **Yeni yıl müfredatı üretmek**
   - Kriter girişleri tamamlanan fakülte/yıl için algoritmalar çalıştırılır.
   - Sonraki yılın müfredatı otomatik oluşturulur.

5. **Dönem bazlı denge sağlamak**
   - Güz/Bahar ayrımı yapılır.
   - 4+4 ders dengesi ve iki dönemde aynı dersin tekrar etmemesi kontrol edilir.

6. **Dış veri kaynaklarıyla çalışmak**
   - Müfredat, kriter ve anket Excel dosyaları içe aktarılır.
   - Import kaynağı, kapsamı ve satır sonuçları izlenebilir hale getirilir.

7. **Algoritmaları karşılaştırılabilir hale getirmek**
   - MCDM, ML, clustering ve allocation algoritmaları ortak arayüzle benchmark edilir.

---

## 3. Mevcut Veri Durumu

İncelenen `data/adil_secmeli.db` dosyasındaki özet durum:

| Varlık / Tablo | Kayıt Sayısı |
|---|---:|
| okul | 1 |
| fakülte | 5 |
| bölüm | 9 |
| ders | 557 |
| müfredat | 13 |
| müfredat_ders | 52 |
| havuz | 2329 |
| performans | 16 |
| popülerlik | 16 |
| skor | 22 |
| ders_kriterleri | 24 |
| survey_import | 1 |
| survey_import_rows | 11 |
| criteria_department_status | 28 |
| criteria_faculty_status | 18 |
| curriculum_generation_audit | 4 |

Ek veri özeti:

- Müfredat yılları: **2022-2024** arası, 3 farklı yıl.
- Havuz yılları: **2022-2030** arası, 9 farklı yıl.
- Skor yılları: **2022-2023** arası.
- Ders tipi dağılımı:
  - Zorunlu: 322
  - Seçmeli: 231
  - Entegre: 4
- Havuz statü dağılımı:
  - `1` müfredatta: 52
  - `0` havuzda: 2272
  - `-1` dinlenmede: 5
  - `-2` kalıcı iptal: mevcut veri snapshot'ında yok

---

## 4. Projenin Gerçekleştirdiği Ana İşlevler

1. **Masaüstü uygulama başlatma**
   - `main.py` kök giriş noktasıdır.
   - `app/main.py` GUI/API modunu seçer.
   - Headless ortamda otomatik API moduna düşer.

2. **Veritabanı görüntüleme ve SQL çalıştırma**
   - `app/ui/tabs/view_tab.py`
   - SQLite tablolarını görüntüler, filtreler ve sorgu çalıştırır.

3. **Kriter girişi**
   - `app/ui/tabs/criteria_page.py`
   - Ders bazında toplam öğrenci, geçen öğrenci, not ortalaması, kontenjan, kayıtlı öğrenci ve anket seçimi girilir.
   - Girilen veri `ders_kriterleri`, `performans` ve `populerlik` tablolarına yazılır.

4. **Müfredat Excel import**
   - `app/services/curriculum_import_service.py`
   - Fakülte, bölüm, yıl, dönem ve ders eşleştirmesi yapar.
   - Mevcut müfredatla karşılaştırma üretir.

5. **Kriter Excel import**
   - `app/services/criteria_import_service.py`
   - Fakülte veya bölüm kapsamlı kriter dosyası yükler.
   - Önceki aynı kapsam importlarını supersede eder.
   - Satır bazlı eşleşme ve hata bilgisini saklar.

6. **Anket Excel import**
   - `app/services/survey_import_service.py`
   - Fakülte/yıl bazlı anket sonuçlarını yükler.
   - Anket verisini kriter tablosuna işler.
   - Belge kaynaklı anket alanlarını manuel değişime kapatabilir.

7. **Kriter tamlık takibi**
   - `app/services/yearly_workflow.py`
   - Bölüm ve fakülte seviyesinde kriter durumunu `not_started`, `partial`, `completed` olarak takip eder.
   - Eksik kriterli fakültede yeni yıl müfredatı üretimini engeller.

8. **AHP + TOPSIS skor üretimi**
   - `app/services/calculation.py`
   - Başarı, trend, popülerlik ve anket bileşenlerini birleştirir.
   - Derslere 0-100 bandında kesinleşme puanı üretir.

9. **Havuz durum makinesi**
   - `app/services/havuz_karar.py`
   - Dersin müfredatta, havuzda, dinlenmede veya iptal durumunda olmasını yıllar arasında yönetir.

10. **Sonraki yıl müfredat üretimi**
    - `run_all_algorithms_for_year`
    - `generate_next_year_curricula`
    - `generate_curricula_until_stable`
    - `rebuild_school_curricula`
    - Kriterleri tamamlanmış fakülteler için sonraki yılın müfredatını üretir.

11. **Çift dönem planlama**
    - `app/services/dual_semester.py`
    - Güz/Bahar üretimini ayrı çalıştırır.
    - 4+4 ders blok dengesi ve dönemler arası ders çakışması kontrol edilir.

12. **Tek ders analiz laboratuvarı**
    - `app/services/course_analyzer.py`
    - Bir ders için AHP, TOPSIS, trend/LR, RF, DT ve state machine adımlarını tek pakette açıklar.

13. **Ders benzerlik analizi**
    - `app/services/similarity_engine.py`
    - Ders açıklamalarından TF-IDF + cosine similarity ile benzer dersleri bulur.

14. **Öğrenci ders uygunluk kuralları**
    - `app/services/rules_engine.py`
    - Daha önce kalma engeli, kontenjan ve saat çakışmasını kontrol eder.

15. **Raporlama ve dışa aktarım**
    - `app/services/reporting_service.py`
    - Havuz/müfredat snapshot'ı, skor kaynağı, import özeti ve istatistikleri üretir.
    - UI üzerinden CSV/Excel export yapılır.

16. **Benchmark platformu**
    - `app/algorithms`, `app/benchmark`, `app/datasets`, `app/metrics`, `app/dashboard`
    - Algoritmaları ortak kontratla çalıştırır.
    - Gerçek/sentetik veri üzerinde karşılaştırmalı deneyler üretir.

---

## 5. Mimari Yapı

Proje katmanlı mimariye yakındır:

1. **Giriş katmanı**
   - `main.py`
   - `app/main.py`

2. **Kullanıcı arayüzü**
   - `app/ui/tabs/*`
   - `app/ui/benchmark/*`

3. **API katmanı**
   - `app/api/main.py`
   - `app/api/routes.py`
   - `app/dashboard/api_routes.py`

4. **Servis/iş kuralı katmanı**
   - `app/services/*`

5. **Algoritma katmanı**
   - `app/algorithms/*`

6. **Benchmark ve deney katmanı**
   - `app/benchmark/*`
   - `app/datasets/*`
   - `app/metrics/*`

7. **Veritabanı katmanı**
   - `app/db/models.py`
   - `app/db/sqlite_db.py`
   - `app/db/schema_compat.py`
   - `alembic/`

8. **Veri ve çıktı klasörleri**
   - `data/`
   - `reports/`
   - `exports/`

Bu ayrım, algoritmaların UI koduna gömülmesini engelliyor ve API, masaüstü uygulama ve benchmark ekranlarının aynı servisleri kullanmasını sağlıyor.

---

## 6. Ana Veri Akışı

1. Kullanıcı müfredat/kriter/anket dosyalarını veya manuel kriterleri sisteme girer.
2. Import servisleri dosyayı okur, kolonları çözer, satırları doğrular.
3. Ders eşleştirme motoru satırları sistemdeki derslerle bağlar.
4. Kriterler `ders_kriterleri`, `performans`, `populerlik` ve import tablolarına işlenir.
5. Workflow servisi bölüm/fakülte kriter tamlığını günceller.
6. Kriterler tamamlandıysa algoritma çalıştırılır.
7. AHP kriter ağırlıklarını üretir.
8. TOPSIS dersleri puanlar.
9. Eşikler ve state machine dersin statüsünü belirler.
10. Müfredat üretim fonksiyonları sonraki yıl/dönem derslerini yazar.
11. Raporlama servisi skor, havuz, müfredat ve import kaynağını tek snapshot olarak sunar.

---

## 7. Kullanılan Algoritmalar ve Amaçları

### 7.1 AHP

- **Kod:** `app/services/calculation.py`, `app/algorithms/mcdm/ahp.py`
- **Amaç:** Kriter ağırlıklarını açıklanabilir şekilde belirlemek.
- **Kriterler:** başarı, trend, popülerlik, anket.
- **Teknik:** Saaty ikili karşılaştırma matrisi, özdeğer/özvektör yöntemi.
- **Kontrol:** Tutarlılık indeksi ve tutarlılık oranı hesaplanır; `CR < 0.10` kabul sınırıdır.
- **Projeye katkısı:** “Başarı mı daha önemli, talep mi?” gibi kararları sayısallaştırır.

### 7.2 TOPSIS

- **Kod:** `app/services/calculation.py`, `app/algorithms/mcdm/topsis.py`
- **Amaç:** Dersleri çok kriterli şekilde sıralamak ve kesinleşme puanı üretmek.
- **Teknik:** Vektör normalizasyonu, ağırlıklı normalize matris, pozitif/negatif ideal çözüm, Öklid uzaklığı, yakınlık katsayısı.
- **Çıktı:** 0-1 TOPSIS skoru ve 0-100 kesinleşme puanı.
- **Projeye katkısı:** Müfredatta kalacak veya havuzdan seçilecek dersleri karşılaştırmalı olarak sıralar.

### 7.3 VIKOR

- **Kod:** `app/algorithms/mcdm/vikor.py`
- **Amaç:** Benchmark platformunda uzlaşık sıralama alternatifi sunmak.
- **Teknik:** Grup faydası `S`, bireysel pişmanlık `R`, uzlaşık skor `Q`.
- **Parametre:** `v=0.5`, fayda ve pişmanlık dengesini belirler.
- **Projeye katkısı:** TOPSIS/AHP sonucuna alternatif karar bilimi yaklaşımı sağlar.

### 7.4 PROMETHEE-II

- **Kod:** `app/algorithms/mcdm/promethee.py`
- **Amaç:** Alternatif dersleri ikili üstünlük ilişkilerine göre sıralamak.
- **Teknik:** Pairwise preference, leaving flow, entering flow, net flow.
- **Projeye katkısı:** Benchmark tarafında net akışa dayalı MCDM karşılaştırması sağlar.

### 7.5 Trend Analizi

- **Kod:** `app/services/calculation.py`, `app/services/course_analyzer.py`
- **Amaç:** Tek yıl yerine geçmiş eğilimi hesaba katmak.
- **Teknik:** Son 3 yıl ağırlıklı ortalaması.
- **Varsayılan ağırlık:** en yeni yıl `%50`, önceki yıl `%30`, üçüncü yıl `%20`.
- **Eksik veri davranışı:** Eksik/geçersiz yıllar atılır, kalan ağırlıklar yeniden ölçeklenir.
- **Projeye katkısı:** Geçici iniş/çıkışların karar üzerindeki etkisini dengeler.

### 7.6 Linear Regression

- **Kod:** `app/services/ai_engine.py`, `app/services/course_analyzer.py`
- **Amaç:** Başarı oranı veya gelecek yıl başarı eğilimini tahmin etmek.
- **Teknik:** `sklearn.linear_model.LinearRegression`.
- **Özellikler:** başarı oranı, ortalama not, doluluk oranı, anket oranı, trend, sayaç.
- **Validasyon:** K-Fold ile MAE raporlanır.
- **Projeye katkısı:** Deterministik karar hattına destekleyici tahmin sunar.

### 7.7 Random Forest

- **Kod:** `app/services/ai_engine.py`, `app/algorithms/ml/classifiers.py`
- **Amaç:** Kesinleşme puanı veya sınıf/tercih tahmini yapmak.
- **Teknik:** `RandomForestRegressor`, `RandomForestClassifier`.
- **Ayarlar:** Servis tarafında regressor için `n_estimators=100`, `max_depth=8`; benchmark tarafında classifier için `n_estimators=300`, `class_weight="balanced_subsample"`.
- **Validasyon:** K-Fold MAE veya sınıflandırma metrikleri.
- **Projeye katkısı:** Doğrusal olmayan başarı/talep ilişkilerini yakalar.

### 7.8 Decision Tree

- **Kod:** `app/services/ai_engine.py`, `app/services/course_analyzer.py`
- **Amaç:** Ders statüsü tahmini ve karar açıklaması üretmek.
- **Teknik:** `DecisionTreeClassifier(max_depth=5)`.
- **Çıktı:** müfredatta, havuzda, dinlenmede veya iptal statüsü.
- **Fallback:** Eğitim verisi yetersizse kural tabanlı karar üretir.
- **Projeye katkısı:** “Ders neden bu statüye düştü?” sorusuna açıklanabilir cevap sağlar.

### 7.9 Naive Bayes

- **Kod:** `app/algorithms/ml/classifiers.py`
- **Amaç:** Benchmark prediction senaryolarında temel olasılıksal sınıflandırıcı olarak kullanmak.
- **Teknik:** `GaussianNB`.
- **Projeye katkısı:** Basit ve hızlı karşılaştırma modeli sağlar.

### 7.10 Logistic Regression

- **Kod:** `app/algorithms/ml/classifiers.py`
- **Amaç:** Benchmark prediction senaryolarında açıklanabilir doğrusal sınıflandırma.
- **Teknik:** `LogisticRegression(max_iter=2000)`.
- **Projeye katkısı:** Küçük/veri açıklanabilirliği öncelikli senaryolarda referans modeldir.

### 7.11 XGBoost Benzeri Model

- **Kod:** `app/algorithms/ml/classifiers.py`
- **Amaç:** Büyük veri prediction senaryolarında daha güçlü ağaç topluluğu kullanmak.
- **Teknik:** `xgboost.XGBClassifier` varsa kullanılır; yoksa `GradientBoostingClassifier` fallback edilir.
- **Projeye katkısı:** Opsiyonel ileri seviye ML karşılaştırması sağlar.

### 7.12 TF-IDF + Cosine Similarity

- **Kod:** `app/services/similarity_engine.py`
- **Amaç:** Ders açıklamalarından benzer dersleri bulmak.
- **Teknik:** `TfidfVectorizer`, Türkçe stop-word listesi, `ngram_range=(1,2)`, `max_features=5000`, cosine similarity.
- **Çıktı:** Hedef derse en benzer dersler ve skorları.
- **Projeye katkısı:** İçerik tekrarını, yakın dersleri ve yerine önerilebilecek dersleri bulur.

### 7.13 State Machine

- **Kod:** `app/services/havuz_karar.py`
- **Amaç:** Dersin yıllar arası durum geçişlerini yönetmek.
- **Durumlar:**
  - `1`: müfredatta
  - `0`: havuzda
  - `-1`: dinlenmede
  - `-2`: kalıcı iptal
- **Kural:** Müfredattan düşen ders sayaç artırır; sayaç 2'ye ulaşırsa kalıcı iptal olur.
- **Projeye katkısı:** Bir dersin her yıl yeniden rastgele seçilmesini engeller, akademik hafıza oluşturur.

### 7.14 Çift Dönem Dengeleme

- **Kod:** `app/services/dual_semester.py`
- **Amaç:** Güz ve Bahar dönemlerini dengeli üretmek.
- **Teknik:** Skora göre sıralama, blok doldurma, dönemler arası çakışma temizleme, 4+4 dengeleme.
- **Projeye katkısı:** Yıllık müfredatın dönemlere operasyonel olarak uygulanabilir dağılmasını sağlar.

### 7.15 Allocation Algoritmaları

- **Kod:** `app/algorithms/allocation/allocators.py`
- **Amaç:** Öğrenci tercihleri ve ders kontenjanlarına göre adil/kısıtlı atama yapmak.
- **Algoritmalar:**
  - Random Allocation: rastgele kapasite kısıtlı baseline.
  - First-Come-First-Served: öğrenci sırasına göre ilk uygun tercih.
  - Greedy Allocation: ters tercih sırası faydasını maksimize eder.
  - Minimum Regret: global düşük rank eşleşmelerini önce işler.
  - Gale-Shapley: çoktan-bire stable matching; ders tarafı önceliği için GPA kullanır.
- **Projeye katkısı:** Seçmeli ders tercih-atama adaletini ölçmek ve karşılaştırmak için kullanılır.

### 7.16 Clustering Algoritmaları

- **Kod:** `app/algorithms/clustering/models.py`
- **Amaç:** Öğrenci/ders örüntülerini keşif amaçlı segmentlere ayırmak.
- **Algoritmalar:**
  - KMeans
  - Hierarchical / Agglomerative Clustering
  - DBSCAN
- **Projeye katkısı:** Benzer öğrenci-tercih kümelerini veya ders örüntülerini incelemeye yarar.

### 7.17 Baseline Algoritmalar

- **Kod:** `app/algorithms/ml/baselines.py`
- **Amaç:** Benchmark sonuçlarını kıyaslamak için alt seviye referanslar oluşturmak.
- **Algoritmalar:**
  - RandomPredictor
  - MajorityClassPredictor
  - PopularityRecommender
- **Projeye katkısı:** Gelişmiş algoritmaların gerçekten değer ekleyip eklemediğini ölçmek için taban çizgisi sağlar.

---

## 8. Kullanılan Teknikler ve Amaçları

1. **Katmanlı mimari**
   - UI, API, servis, algoritma ve DB kodları ayrılmıştır.
   - Amaç: bakım kolaylığı ve test edilebilirlik.

2. **SQLite + SQLAlchemy + sqlite3 hibrit kullanımı**
   - ORM modelleri SQLAlchemy'de, UI ve bazı servisler doğrudan sqlite3 ile çalışıyor.
   - Amaç: hem hızlı masaüstü kullanım hem de servis tabanlı modelleme.

3. **Runtime schema compatibility**
   - `app/db/schema_compat.py`
   - Eksik kolon/tablo/index çalışma anında tamamlanıyor.
   - Amaç: eski DB dosyalarının yeni kodla çalışmaya devam etmesi.

4. **Alembic migration**
   - `alembic/`
   - Amaç: şema değişikliklerini versiyonlanabilir hale getirmek.

5. **Excel ETL**
   - `pandas`, `openpyxl`
   - Amaç: kurumların gerçek hayatta verdiği Excel dosyalarıyla çalışmak.

6. **Ders eşleştirme**
   - Kod eşleşmesi, normalize ad eşleşmesi ve gevşek anahtar eşleşmesi.
   - Amaç: Excel dosyalarındaki yazım farklılıklarını yönetmek.

7. **Kapsam bazlı import**
   - Fakülte, bölüm, yıl ve dönem kapsamı tutuluyor.
   - Amaç: hangi verinin hangi akademik kapsama ait olduğunu açık tutmak.

8. **Import audit trail**
   - `criteria_import`, `criteria_import_rows`, `survey_import`, `survey_import_rows`.
   - Amaç: veri kaynağını ve satır bazlı import sonucunu izlemek.

9. **Kriter tamlık kontrolü**
   - Kriterler tamamlanmadan algoritma çalıştırılmıyor.
   - Amaç: eksik veriye dayalı müfredat üretimini engellemek.

10. **Kural tabanlı kararlar**
    - Skor eşiği, not ortalaması eşiği, kontenjan, çakışma, failed_before.
    - Amaç: skorun tek başına yakalayamadığı operasyonel gerçekliği modele katmak.

11. **Fallback davranışları**
    - ML verisi yetersizse kural tabanlı tahmin.
    - Eksik geçmiş veride yeniden ölçeklenen trend.
    - XGBoost yoksa GradientBoosting fallback.
    - Amaç: uygulamanın veri eksikliğinde tamamen durmasını önlemek.

12. **Benchmark standardizasyonu**
    - Ortak `IAlgorithm`, `IPredictor`, `IRanker`, `IAllocator`, `IClusterer` arayüzleri.
    - Amaç: farklı algoritmaları aynı deney koşullarında karşılaştırmak.

13. **Sentetik veri üretimi**
    - Bootstrap sampling, noise injection, class imbalance kontrolü, capacity scaling.
    - Amaç: 5k, 10k, 50k, 100k, 250k ölçeklerinde algoritma davranışını test etmek.

14. **Feature engineering**
    - Min-max normalizasyon, one-hot encoding, bileşik skorlar.
    - Amaç: ham öğrenci/ders/tercih/anket verisini ML ve benchmark için hazır hale getirmek.

15. **Performans ve kalite metrikleri**
    - Classification: accuracy, precision, recall, f1, ROC-AUC.
    - Ranking: hit@k, NDCG@k, MAP@k, coverage, diversity.
    - Allocation fairness: average rank, top-k satisfaction, envy score, seat fill rate.
    - Clustering: silhouette, Davies-Bouldin, Calinski-Harabasz.
    - Amaç: algoritmaların sadece çalışmasını değil, kalitesini ölçmek.

---

## 9. REST API'nin Sağladıkları

Ana API:

- `GET /api/v1/dersler`
- `GET /api/v1/skorlar`
- `GET /api/v1/havuz`
- `GET /api/v1/mufredat`
- `GET /api/v1/akademik-plan`
- `GET /api/v1/fakulteler`
- `GET /api/v1/kriter/durum`
- `GET /api/v1/yillar/aktif`
- `POST /api/v1/algoritma/tumunu-calistir`
- `POST /api/v1/mufredat/yukle`
- `POST /api/v1/anket/yukle`

Benchmark API:

- `GET /api/v1/benchmark/scenarios`
- `GET /api/v1/benchmark/algorithms`
- `POST /api/v1/benchmark/datasets/load`
- `POST /api/v1/benchmark/runs/execute`
- `POST /api/v1/benchmark/runs/compare`
- `POST /api/v1/benchmark/recommendation`
- `GET /api/v1/benchmark/runs`
- `GET /api/v1/benchmark/runs/{run_id}`

API'nin amacı, masaüstü uygulamadaki hesaplama ve veri yönetimi yeteneklerini ileride OBS, öğrenci işleri, anket sistemi veya web panel gibi dış sistemlere açmaktır.

---

## 10. Test ve Doğrulama Durumu

Projede `app/tests/` altında 21 Python test/yardımcı test dosyası bulunuyor. Test kapsamı şu alanlara yayılmış:

- AI engine
- atama motoru
- hesaplama sekmesi
- ders kodu servisi
- kriter import servisi
- kriter sayfası
- müfredat üretimi
- müfredat import servisi
- DB
- ETL
- havuz kararları
- pool rules
- raporlama
- skor motoru
- dönem desteği
- benzerlik
- tek ders analizi
- anket import servisi
- yıllık kriter workflow'u

Bu rapor hazırlanırken testler çalıştırılmadı; analiz kaynak kodu, dokümanlar ve veritabanı snapshot'ı üzerinden yapıldı.

---

## 11. Güçlü Yönler

1. **Karar hattı açıklanabilir**
   - AHP, TOPSIS, eşikler ve state machine kullanıcıya anlatılabilir yapıdadır.

2. **Veri kaynağı izlenebilir**
   - Kriter ve anket import tabloları veri soy kütüğü oluşturur.

3. **Eksik veri yönetimi düşünülmüş**
   - Eksik kriter, eksik geçmiş yıl, yetersiz ML verisi için fallback davranışları var.

4. **Müfredat üretimi operasyonel kısıtları dikkate alıyor**
   - Fakülte, bölüm, dönem, havuz, sayaç ve bölüm dışı ders kısıtları birlikte ele alınıyor.

5. **Benchmark platformu projeyi genişletiyor**
   - Sistem yalnızca tek bir karar motoru değil, algoritma karşılaştırma altyapısı da içeriyor.

6. **Gerçek kullanıma yakın dosya akışı var**
   - Excel şablonları, import servisleri, raporlama ve export gerçek kurum süreçlerine yakındır.

---

## 12. Dikkat Edilmesi Gereken Noktalar

1. **Dokümanların bir kısmı eski durumları anlatıyor**
   - Örneğin bazı dokümanlarda API yok/stub gibi ifadeler var; güncel kodda API uçları mevcut.

2. **Veri yoğunluğu algoritma güvenilirliğini etkiliyor**
   - Mevcut DB snapshot'ında 557 ders olmasına rağmen `performans`, `populerlik`, `skor` ve `ders_kriterleri` kayıtları sınırlı.
   - ML tarafında veri azlığında fallback devreye girdiği için gerçek ML performansı daha fazla veriyle değerlendirilmelidir.

3. **SQLite üretim için sınırlı kalabilir**
   - Tek kullanıcı/demo için uygun; çok kullanıcılı kurumsal kullanımda PostgreSQL benzeri DB gerekir.

4. **Kimlik doğrulama/rol yönetimi API'de görünür değil**
   - Kodda API endpointleri var, ancak üretim seviyesi rol bazlı güvenlik ayrıca ele alınmalıdır.

5. **Kod tabanı hem eski hem yeni yaklaşımları barındırıyor**
   - SQLAlchemy ORM, sqlite3 wrapper, runtime schema guard ve Alembic birlikte kullanılıyor.
   - Bu pratik olarak işe yarıyor, fakat uzun vadede resmi migration hattı netleştirilmeli.

---

## 13. Kısa Sonuç

Adil Seçmeli projesi, seçmeli ders süreçlerini sadece listeleme veya basit puanlama seviyesinde bırakmıyor. Proje; kriter girişi, belge tabanlı veri yükleme, AHP/TOPSIS karar motoru, yıllık müfredat üretimi, havuz durum makinesi, dönem dengesi, ML destekli analiz, NLP benzerlik ve benchmark karşılaştırma katmanlarını birleştiren kapsamlı bir akademik karar destek sistemidir.

En güçlü teknik omurga şudur:

> Kriter verisi tamamlanır, AHP ile ağırlıklandırılır, TOPSIS ile ders puanı üretilir, eşikler ve state machine ile karar verilir, müfredat/havuz güncellenir ve raporlanır.

Bu yapı sayesinde proje, “hangi ders neden seçildi veya neden elendi?” sorusuna hem sayısal hem de kural tabanlı cevap verebilecek seviyededir.
