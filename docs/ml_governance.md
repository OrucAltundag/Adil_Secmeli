# ML Governance

Bu doküman, Adil Seçmeli projesindeki makine öğrenmesi bileşenlerinin bilimsel ve yönetsel konumunu tanımlar.

## Temel İlke

Mevcut veri miktarı düşük olduğunda ML modelleri nihai karar verici olarak kullanılmaz. Nihai karar AHP/TOPSIS + kural motoru + state machine hattıyla üretilir. ML çıktıları destekleyici ve deneysel analiz olarak sunulur.

Ana karar motoru:

- AHP ağırlıkları
- TOPSIS skorları
- Trend analizi
- Kural motoru
- Havuz state machine

ML tarafı:

- Destekleyici tahmin
- Deneysel analiz
- Benchmark karşılaştırması
- Gelecek veri büyümesi için hazırlık
- Model güvenilirlik raporu

## Algorithm Registry

`ml_algorithm_registry` tablosu her algoritmanın kullanım rolünü ve veri gereksinimini saklar.

Kullanım rolleri:

- `production_decision`: Üretim karar hattında kullanılabilecek algoritmalar. Varsayılan karar hattı AHP/TOPSIS + kurallar + state machine olarak kalır.
- `advisory_ml`: Karara destek verir, nihai kararı tek başına üretmez.
- `benchmark_only`: Gerçek karar hattına dahil değildir; deney ve karşılaştırma amaçlıdır.
- `experimental`: Veri veya doğrulama yetersiz olduğunda deneysel etiket.

Varsayılan minimum örnek eşikleri:

- Linear Regression: 50
- Decision Tree: 100
- Random Forest: 200
- Logistic Regression: 100
- Naive Bayes: 100
- XGBoost / GradientBoosting: 500
- Clustering: 100
- Historical Average Baseline: 10

## Minimum Sample Guard

`ml_readiness_service` model çalışmadan önce veri yeterliliğini kontrol eder.

Kontrol edilenler:

- Eğitim örneği sayısı
- Sınıflandırma için sınıf sayısı
- Sınıf başına minimum örnek
- Sınıf dengesizliği
- Algoritmanın kullanım rolü
- Production-ready uygunluğu

Veri yetersizse model `production_decision` olarak kullanılamaz. Gerektiğinde model run `skipped` durumuna alınır ve kullanıcıya açık uyarı üretilir.

## Feature Pipeline

`ml_feature_pipeline` ders-yıl seviyesinde ortak feature veri seti üretir.

Feature schema version:

- `course_features_v1`

Öne çıkan feature alanları:

- `success_rate`
- `average_grade_normalized`
- `enrollment_rate`
- `capacity`
- `enrolled_students`
- `survey_count`
- `survey_rate`
- `popularity_score`
- `trend_score`
- `previous_topsis_score`
- `years_in_pool`
- `years_in_rest`
- `course_age`
- `faculty_id_encoded`
- `department_id_encoded`
- `course_type_encoded`

Normalize davranışı:

- Başarı oranı 0-1 aralığına çekilir.
- Not ortalaması 0-4 veya 0-100 ölçeğine göre normalize edilir.
- Kontenjan 0 ise doluluk oranı bölme hatası üretmez, 0 kabul edilir.
- Eksik feature bilgileri `missing_features_summary` içinde saklanır.
- Imputation yapıldıysa kullanılan strateji kaydedilir.

Feature snapshot kayıtları `ml_feature_snapshots` tablosunda tutulur.

## Model Run ve Versioning

Her eğitim denemesi `ml_model_runs` tablosuna yazılır.

Saklanan bilgiler:

- Algoritma anahtarı
- Model adı ve tipi
- Kullanım rolü
- Model versiyonu
- Feature schema version
- Eğitim kapsamı
- Eğitim örnek sayısı
- Parametreler
- Sınıf dağılımı
- Train/validation metrikleri
- Cross-validation özeti
- Overfitting raporu
- Readiness seviyesi
- Status: `created`, `trained`, `skipped`, `failed`, `deprecated`

Veri yetersizse model run oluşturulur ama `skipped` olarak işaretlenir; neden `skip_reason` alanında saklanır.

## Training, Validation ve Overfitting

`ml_evaluation_service` regresyon ve sınıflandırma modellerini değerlendirir.

Regresyon metrikleri:

- MAE
- RMSE
- R2

Sınıflandırma metrikleri:

- Accuracy
- Precision
- Recall
- F1
- ROC-AUC mümkünse
- Confusion matrix

Küçük veri durumunda cross-validation güvenli şekilde azaltılır veya yapılmaz. Train metriği ile validation metriği arasında büyük fark varsa overfitting uyarısı üretilir.

## Confidence ve Uncertainty

`ml_confidence_service` tahmin güvenini 0-1 arası hesaplar.

Dikkate alınan sinyaller:

- Eğitim örneği sayısı
- Validation metriği
- Model probability değeri
- Eksik/impute edilmiş feature oranı
- Readiness seviyesi
- Overfitting uyarısı

Güven seviyeleri:

- `high`
- `medium`
- `low`

Güven düşükse `should_influence_decision=false` olur. Varsayılan konfigürasyonda ML karar etkisi kapalıdır.

## Prediction Log ve Fallback

Tahminler `ml_predictions` tablosuna yazılır.

Önemli alanlar:

- `fallback_used`
- `fallback_method`
- `fallback_reason`
- `advisory_only`
- `should_influence_decision`
- `confidence_score`
- `confidence_level`
- `uncertainty_reasons_json`

Readiness yetersizse model çalıştırılmaz; fallback üretilir. Fallback örnekleri:

- `rule_based_status_estimator`
- `historical_average`
- `no_prediction`

Fallback sonucu ML sonucu gibi sunulmaz; açıklama içinde açıkça belirtilir.

## Explainability

`ml_explainability_service` desteklenen modeller için açıklama üretir.

Desteklenen açıklama türleri:

- Feature importance
- Linear coefficient yönleri
- Decision Tree path
- Sınırlamalar
- İnsan okunabilir açıklama

Veri azsa açıklama metnine şu uyarı eklenir:

“Bu açıklama sınırlı eğitim verisi nedeniyle dikkatli yorumlanmalıdır.”

## ML Readiness Report

`ml_readiness_report_service` kapsam bazlı ML hazırlık raporu üretir.

Raporda:

- Mevcut eğitim örneği sayısı
- Her algoritmanın minimum örnek ihtiyacı
- Eksik örnek sayısı
- Feature kalite özeti
- Production-ready durumu
- Advisory-only durumu
- Benchmark-only durumu
- Öneriler

Raporlar `ml_readiness_reports` tablosunda saklanır.

## Benchmark ve Gerçek Karar Hattı Ayrımı

Benchmark registry artık algoritmalar için kullanım rolü metadata’sı döndürür.

Örnek:

- AHP: Ana karar motoru
- TOPSIS: Ana karar motoru
- Random Forest: Destekleyici ML
- Logistic Regression: Sadece benchmark
- Naive Bayes: Sadece benchmark
- XGBoostLike: Sadece benchmark
- Clustering modelleri: Sadece benchmark

Benchmark sonuçları karar hattına otomatik bağlanmaz.

## UI

Benchmark Platformu içinde “ML Güvenilirlik & Hazırlık” paneli eklendi.

Panelde:

- Eğitim örneği sayısı
- Algoritma readiness tablosu
- Minimum örnek gereksinimi
- Kullanım rolü
- Production-ready durumu
- Model run listesi
- Tahmin/fallback kayıtları

Karar Merkezi ders detayında “ML Destekleyici Tahmin” bölümü kayıtlı ML tahminlerini gösterir. Bu bölümde karara etkisi açıkça “hayır” olarak belirtilir.

## API Endpointleri

Yeni endpointler `/api/v1/ml` altında yer alır.

- `GET /api/v1/ml/algorithms`
- `PATCH /api/v1/ml/algorithms/{algorithm_key}`
- `GET /api/v1/ml/readiness`
- `POST /api/v1/ml/readiness/report`
- `GET /api/v1/ml/features/summary`
- `POST /api/v1/ml/features/build-snapshot`
- `GET /api/v1/ml/model-runs`
- `GET /api/v1/ml/model-runs/{run_id}`
- `POST /api/v1/ml/model-runs/train`
- `POST /api/v1/ml/model-runs/{run_id}/deprecate`
- `GET /api/v1/ml/predictions`
- `POST /api/v1/ml/predictions/predict-course`
- `POST /api/v1/ml/predictions/predict-batch`
- `GET /api/v1/ml/predictions/{prediction_id}/explanation`
- `GET /api/v1/ml/readiness-reports`
- `GET /api/v1/ml/readiness-reports/{report_id}`

Yeni endpointler standart `ApiResponse` formatını kullanır.

## Yeni Kod Yazarken

- ML sonucu final karar gibi gösterilmemelidir.
- Readiness kontrolü yapılmadan model eğitilmemelidir.
- Veri yetersizse model run `skipped` veya tahmin `fallback_used=true` olmalıdır.
- Benchmark-only modeller karar hattına bağlanmamalıdır.
- Confidence düşükse `should_influence_decision=false` kalmalıdır.
- Nihai karar açıklamalarında ana karar motorunun AHP/TOPSIS + kurallar + state machine olduğu belirtilmelidir.
