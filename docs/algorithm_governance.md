# Algorithm Governance

Bu dokuman, Adil Secmeli projesindeki cok sayidaki algoritmanin ayni karar seviyesinde gorunmesini engelleyen algoritma yonetisimi katmanini aciklar.

## Ana karar motoru

Projede cok sayida algoritma bulunmasina ragmen bu algoritmalar ayni karar seviyesinde kullanilmaz. Nihai mufredat/havuz karari AHP + TOPSIS + kural motoru + state machine hattiyla verilir. XGBoost, Naive Bayes, Logistic Regression ve clustering algoritmalari benchmark, baseline veya kesifsel analiz amaciyla kullanilir.

Ana karar hattindaki uretim bilesenleri:

- AHP: kriter agirliklandirma ve consistency ratio denetimi.
- TOPSIS: cok kriterli ders skoru ve siralama.
- Trend Analysis: yillar arasi egilim etiketi ve skor etkisi.
- Rule Engine: esik, policy ve akademik kural uygulamasi.
- State Machine: mufredat, havuz, dinlenme ve kalici iptal yasam dongusu.

## Algorithm governance registry

`algorithm_governance_registry` tablosu her algoritma icin su bilgileri tutar:

- algoritma anahtari ve gorunen ad
- algoritma ailesi: `mcdm`, `ml`, `clustering`, `allocation`, `baseline`, `similarity`, `rule_based`
- problem tipi: `ranking`, `classification`, `regression`, `clustering`, `allocation`, `similarity`, `decision_rule`
- kullanim rolu: `production_decision`, `advisory_ml`, `benchmark_only`, `experimental`, `baseline`
- final karara etki izni
- minimum veri gereksinimi
- sinif basi minimum ornek
- feature scaling ve target gereksinimleri
- desteklenen metrik, probability, feature importance ve explainability bilgileri
- kullaniciya gosterilecek uyari

Varsayilan roller:

- `production_decision`: AHP, TOPSIS, Rule Engine, State Machine, Trend Analysis
- `advisory_ml`: Linear Regression, Decision Tree, Random Forest
- `benchmark_only`: VIKOR, PROMETHEE, Logistic Regression, Naive Bayes, XGBoost/GradientBoosting, KMeans, Hierarchical Clustering, DBSCAN, allocation algoritmalari, TF-IDF Cosine
- `baseline`: RandomPredictor, MajorityClassPredictor, PopularityRecommender, DummyClassifier, DummyRegressor, RuleBasedBaseline

Benchmark-only algoritmalar final karara dogrudan etki edemez.

## Problem-algoritma eslestirme matrisi

`algorithm_task_mapping` tablosu algoritmanin hangi problemde hangi rolle calisabilecegini tanimlar.

Ornek eslestirmeler:

- `course_ranking`: AHP, TOPSIS, VIKOR, PROMETHEE
- `course_status_classification`: Decision Tree, Random Forest, Logistic Regression, Naive Bayes, XGBoost
- `success_score_regression`: Linear Regression ve regression baseline'lari
- `preference_clustering`: KMeans, Hierarchical Clustering, DBSCAN
- `student_course_allocation`: Gale-Shapley, Greedy Allocation, Minimum Regret
- `course_similarity`: TF-IDF + Cosine Similarity

Yanlis eslestirme ornegi: DBSCAN ile ders status classification calistirilmak istenirse servis bunu engeller.

## Minimum veri sarti ve data guard

`algorithm_data_guard_service` her algoritma calismadan once veri uygunlugunu kontrol eder:

- ornek sayisi
- feature sayisi
- target varligi
- sinif dagilimi
- sinif basi minimum ornek
- class imbalance
- eksik feature degerleri
- scaling gereksinimi
- algoritmaya ozel kurallar

Baslangic minimum veri esikleri:

- Linear Regression: 50
- Decision Tree: 100
- Random Forest: 200
- Logistic Regression: 100
- Naive Bayes: 100
- XGBoost / GradientBoosting: 500
- KMeans: 100
- Hierarchical Clustering: 50
- DBSCAN: 100
- Baseline: 10

Veri yetersizse sonuc `experimental` veya `blocked` olarak isaretlenir. Bu durumda algoritma production decision olarak kullanilamaz.

## Dogru metrik setleri

`benchmark_metric_router` task type'a gore metrik secer.

Classification:

- accuracy
- precision macro/weighted
- recall macro/weighted
- f1 macro/weighted
- balanced accuracy
- confusion matrix
- ROC-AUC, PR-AUC, log-loss, brier score uygun oldugunda

Regression:

- MAE
- RMSE
- R2
- median absolute error
- safe MAPE
- residual mean/std

Ranking:

- Hit@K
- NDCG@K
- MAP@K
- precision/recall@K
- coverage, diversity

Clustering:

- silhouette
- Davies-Bouldin
- Calinski-Harabasz
- cluster count
- cluster size distribution
- DBSCAN noise ratio

Allocation:

- seat fill rate
- average assigned rank
- top-1/top-3 satisfaction
- envy score
- unassigned rate
- capacity violation
- department fairness

## Cross-validation stratejileri

`validation_strategy_service` veri yapisina gore strateji secer:

- classification icin uygun dagilim varsa `stratified_k_fold`
- yil bilgisi varsa `time_based_split`
- grup bilgisi varsa `group_k_fold_by_course`, `group_k_fold_by_department` veya benzeri
- veri cok kucukse `leave_one_out` veya uyarili `holdout`
- clustering icin stability resampling altyapisi

Fold sayisi sinif orneklerinden fazla secilmez.

## Istatistiksel anlamlilik

`statistical_comparison_service` benchmark sonuclarini sadece ham skor olarak sunmaz:

- bootstrap confidence interval
- paired t-test
- Wilcoxon signed-rank
- McNemar testi
- Friedman testi
- effect size

`scipy` yoksa servis bootstrap CI ve effect size ile graceful fallback yapar.

## Data leakage kontrolu

`data_leakage_detector` su riskleri kontrol eder:

- target degiskenin feature listesinde yer almasi
- TOPSIS/AHP/MCDM ciktilarinin hedef tahminde feature olarak kullanilmasi
- final status veya nihai karar alanlarinin feature'a karismasi
- gelecek yil verisinin egitim setine karismasi
- ayni dersin train/test setinde tekrar etmesi

Kritik leakage varsa benchmark sonucu gecersiz sayilmalidir.

## Overfitting ve class imbalance diagnostics

`model_diagnostics_service` sunlari raporlar:

- train/validation metrik farki
- overfitting warning
- class imbalance warning
- foldlar arasi yuksek varyans

Sinif dengesizliginde balanced accuracy ve macro F1 one cikarilir.

## Clustering ve DBSCAN degerlendirmesi

Clustering algoritmalari nihai mufredat karari uretmez. Bu algoritmalar tercih, ders veya ogrenci davranisi oruntulerini kesifsel analiz etmek icindir.

DBSCAN icin ek kontroller:

- feature scaling uyarisi
- eps/min_samples raporu
- noise ratio
- tek kume veya tum noise uyarisi
- noise ratio %60 ustundeyse dusuk guven uyarisi
- k-distance verisi ve eps onerisi altyapisi

## Ozel algoritma konumlandirmalari

XGBoost / GradientBoosting:

- `benchmark_only`
- minimum 500 ornek
- kucuk veride blocked/experimental
- overfitting diagnostics zorunlu
- final karara etki etmez

Naive Bayes:

- `benchmark_only`
- hizli olasiliksal baseline
- macro F1 ve balanced accuracy ile raporlanir
- final karar motoru degildir

Logistic Regression:

- `benchmark_only`
- aciklanabilir benchmark baseline
- scaling ve class imbalance uyarisi vardir
- final karar motoru degildir

DBSCAN:

- `benchmark_only`
- kesifsel clustering
- noise ratio ve eps duyarliligi raporlanir
- final karar uretmez

## Governed benchmark run

`algorithm_benchmark_runs` yeni governed benchmark yoludur. Mevcut benchmark akisini bozmaz.

Her governed run su adimlari izler:

1. Registry seed ve rol kontrolu
2. Problem-algoritma eslestirme kontrolu
3. Data guard
4. Leakage detector
5. Validation strategy secimi
6. Metrik hesaplama
7. Diagnostics
8. Confidence interval ve istatistiksel karsilastirma
9. Baseline karsilastirmasi
10. Raporlama

Sonuclar su tablolara yazilir:

- `benchmark_metric_results`
- `benchmark_validation_results`
- `benchmark_statistical_comparisons`
- `benchmark_data_leakage_reports`
- `benchmark_model_diagnostics`
- `clustering_evaluation_results`

## UI kullanimi

Benchmark Platformu altinda `Algoritma Yönetişimi` paneli bulunur.

Panelde:

- algoritma rol matrisi
- problem-algoritma eslestirmesi
- veri uygunluk kurallari
- governed benchmark run gecmisi

gosterilir. UI sabit olarak su prensibi belirtir:

“Bu bölümdeki benchmark algoritmaları nihai müfredat kararını doğrudan üretmez. Nihai karar AHP/TOPSIS + kurallar + state machine hattıyla verilir.”

## API endpointleri

Algoritma yonetisimi:

- `GET /api/v1/algorithms/governance`
- `GET /api/v1/algorithms/governance/{algorithm_key}`
- `PATCH /api/v1/algorithms/governance/{algorithm_key}`
- `GET /api/v1/algorithms/governance/report`

Problem eslestirme:

- `GET /api/v1/algorithms/tasks`
- `GET /api/v1/algorithms/tasks/{task_key}/algorithms`

Data guard:

- `POST /api/v1/algorithms/data-guard/check`

Governed benchmark:

- `POST /api/v1/benchmark/governed-runs/execute`
- `GET /api/v1/benchmark/governed-runs`
- `GET /api/v1/benchmark/governed-runs/{run_id}`
- `GET /api/v1/benchmark/governed-runs/{run_id}/metrics`
- `GET /api/v1/benchmark/governed-runs/{run_id}/validation`
- `GET /api/v1/benchmark/governed-runs/{run_id}/statistics`
- `GET /api/v1/benchmark/governed-runs/{run_id}/diagnostics`
- `GET /api/v1/benchmark/governed-runs/{run_id}/leakage`
- `GET /api/v1/benchmark/governed-runs/{run_id}/clustering`
- `GET /api/v1/benchmark/governed-runs/{run_id}/report`

## Yeni kod yazarken

- Yeni algoritma once registry'ye eklenmelidir.
- Hangi task icin calisacagi task mapping'e yazilmalidir.
- Minimum veri, metrik ve validasyon stratejisi belirtilmelidir.
- Benchmark-only algoritma final karar servisinden cagrilmamalidir.
- Veri yetersizliginde sonuc experimental/advisory olarak raporlanmalidir.
