# Algoritma Envanteri — Sistemde Kullanılan Tüm Algoritmalar

> Bu doküman iki şeyi birleştirir:
> 1. Sağlık-Kontrol panelindeki ("MEVCUT KONTROLLER / ALGORİTMALAR") maddeler.
> 2. Kodda **fiilen uygulanmış** ama o panelde olmayan ya da "PLANNED" görünen
>    gerçek karar/ML/NLP algoritmaları.
>
> **Önemli ayrım:** O paneldeki maddelerin çoğu aslında **sağlık/doğrulama
> kontrolüdür** (test, validation, güvenlik) — karar-bilimi algoritması değil.
> Asıl karar algoritmaları aşağıda Bölüm 1–3'tedir. Panelde "PLANNED" görünen
> birçok ML algoritması (K-Means, Random Forest, Decision Tree, Linear
> Regression…) **kodda mevcut ve çalışıyor**; yalnızca sağlık paneline
> bağlanması planlanmış (Bölüm 6'daki not).

---

## BÖLÜM 1 — Çok Kriterli Karar (MCDM) Çekirdeği

Bunlar sistemin "ders açılsın mı?" kararını üreten ana hattıdır.

| # | Algoritma | Ne yapar / Teknik | Dosya |
|--:|---|---|---|
| 1 | **AHP (Analitik Hiyerarşi Süreci)** | Kriter ağırlıklarını ikili karşılaştırmadan türetir. **Geometrik ortalama** ile normalizasyon; **özdeğer (λmax)** ile tutarlılık. | `ahp_calculation_service.py` |
| 2 | **Tutarlılık Oranı (CR)** | CI=(λmax−n)/(n−1), CR=CI/RI. Kabul: CR≤0.10. | `ahp_calculation_service.py` |
| 3 | **TOPSIS** | İdeal çözüme yakınlık. C = S⁻/(S⁺+S⁻). Normalize → ağırlıklı matris → ideal/negatif-ideal uzaklık. | `calculation.py`, `topsis_explainability_service.py` |
| 4 | **Min-Max / Vektör Normalizasyon** | Kriterleri 0–1 ortak ölçeğe çeker (TOPSIS öncesi). | `calculation.py` |
| 5 | **Ağırlıklı Trend Skoru** | Yıllık değişimi son yıllar daha ağır (0.50/0.30/0.20) harmanlar → yükselen/düşen/sabit. | `trend_analysis_service.py` |
| 6 | **Veri Güveni Skoru** | Kriter/perf/pop/anket/geçmiş doluluğunun ağırlıklı toplamı (0–1). Düşük güven = tekrar incele. | `data_confidence_service.py` |
| 7 | **Açılabilirlik Skoru** | 0.45·TOPSIS+0.25·talep+0.15·güven+0.10·dönem+0.05·kaynak. O dönem fiilen açılabilirlik. | `acilabilirlik_service.py` |
| 8 | **Eşik Tabanlı Sınıflandırma (Karar Politikası)** | Skoru statüye çevirir: ≥70 müfredat, ≥50 havuz, <40 dinlenme, ≤30 iptal. | `decision_policy_service.py` |
| 9 | **Havuz Durum Makinesi (State Machine)** | Statü geçişleri (müfredat↔havuz↔dinlenme↔iptal) + sayaç kuralları. | `pool_state_machine_service.py`, `havuz_karar.py` |
| 10 | **Duyarlılık Analizi (Sensitivity)** | Ağırlık/eşik değişiminin sıralamaya etkisi; karar stabilitesi. | `sensitivity_analysis_service.py`, `ahp_sensitivity_service.py` |
| 11 | **Adalet (Fairness) Metrikleri** | Bölüm/fakülte/ders türü bazında karar dağılımı dengesizliği. | `fairness_report_service.py` |
| 12 | **Havuzdan Öneri (AHP + Cosine boost)** | AHP skoruna benzerlik (cosine) katkısı ekleyerek havuzdan aday önerir. | `pool_recommendation_service.py` |

---

## BÖLÜM 2 — Dönem Planlama (Kısıt Tabanlı Atama)

| # | Algoritma | Ne yapar / Teknik | Dosya |
|--:|---|---|---|
| 13 | **Açgözlü Kısıtlı Atama (Greedy Constrained Assignment)** | Açılabilirliğe göre sıralı dersleri Güz/Bahar'a kısıtlarla yerleştirir. | `semester_planning_engine.py` |
| 14 | **Senaryo Üretimi (score/demand/balance priority)** | Farklı önceliklerle alternatif planlar. | `semester_planning_engine.py` |
| 15 | **Dönem Denge Metrikleri** | Plan skoru + Güz/Bahar denge ölçümü. | `semester_balance_metrics_service.py` |
| 16 | **Ön Koşul Sıra Kontrolü (DAG)** | Ders ön koşul sırası ihlali tespiti + onarım. | `prerequisite_planning_service.py` |
| 17 | **Öğretim Üyesi Fizibilitesi** | Hoca yükü/uygunluk/çakışma kontrolü. | `instructor_planning_service.py` |
| 18 | **Kaynak Fizibilitesi** | Sınıf/lab kapasitesi kontrolü. | `resource_planning_service.py` |
| 19 | **Zaman Çakışması Tespiti** | Aynı dönemde çakışan ders uyarıları. | `time_conflict_planning_service.py` |
| 20 | **İş Yükü Dengeleme** | Bölüm zorunlu ders yüküne göre hedef ayarı. | `semester_workload_service.py` |

---

## BÖLÜM 3 — NLP / Benzerlik

| # | Algoritma | Ne yapar / Teknik | Dosya |
|--:|---|---|---|
| 21 | **TF-IDF Vektörleştirme** | Ders ad/içeriğini sayısal vektöre çevirir. | `similarity_engine.py` |
| 22 | **Cosine Similarity** | Dersler arası benzerlik matrisi → benzer ders tespiti. | `similarity_engine.py` |

> Panelde **NLP Log Classification** "NOT_APPLICABLE"; ama ders benzerliği için
> TF-IDF + cosine **aktif olarak kullanılıyor** (panelde bu haliyle yok).

---

## BÖLÜM 4 — Makine Öğrenmesi (Benchmark / Destekleyici)

> Bunlar **karar bağlayıcı değil** — destekleyici tahmin + akademik karşılaştırma
> içindir. Panelde çoğu "PLANNED (algoritma mevcut)" diyor; **kodda uygulanmış.**

| # | Algoritma | Ne yapar / Teknik | Dosya |
|--:|---|---|---|
| 23 | **Random Forest** (Classifier/Regressor) | Topluluk ağaç sınıflandırma/tahmin. | `ml_training_service.py`, `ml_prediction_service.py` |
| 24 | **Decision Tree** | Karar ağacı sınıflandırma. | `ml_training_service.py` |
| 25 | **Logistic Regression** | Olasılıksal sınıflandırma. | `ml_training_service.py` |
| 26 | **Linear Regression** | Sayısal tahmin. | `ml_training_service.py` |
| 27 | **Gaussian Naive Bayes** | Olasılıksal sınıflandırma. | `ml_training_service.py` |
| 28 | **MLP (Çok Katmanlı Algılayıcı / derin öğrenme)** | Sinir ağı sınıflandırma. | `ml_analysis_service.py` |
| 29 | **K-Means Kümeleme** | Ders/öğrenci kümeleme. | `ml_*` (kümeleme) |
| 30 | **Adaptif Pruning** | Model budama / öznitelik azaltma. | `ml_analysis_service.py` |

### 4.1 ML Değerlendirme & Veri Hazırlık

| # | Teknik | Ne yapar | Dosya |
|--:|---|---|---|
| 31 | **train_test_split** | Eğitim/test ayrımı. | `ml_training_service.py` |
| 32 | **Cross-Validation** | Çapraz doğrulama. | `ml_evaluation_service.py` |
| 33 | **Silhouette Score** | Kümeleme kalitesi. | `ml_evaluation_service.py` |
| 34 | **StandardScaler / MinMaxScaler** | Öznitelik ölçekleme. | `ml_feature_pipeline.py` |
| 35 | **SimpleImputer** | Eksik değer doldurma. | `ml_feature_pipeline.py` |
| 36 | **Veri Sızıntısı Kontrolü (Data Leakage)** | Eğitim/test sızıntı denetimi. | `ml_*` |

### 4.2 ML Açıklanabilirlik (XAI)

| # | Teknik | Ne yapar | Dosya |
|--:|---|---|---|
| 37 | **SHAP** | Öznitelik katkısı (Shapley değerleri). | `ml_explainability_service.py` |
| 38 | **LIME** | Yerel açıklanabilir tahmin. | `ml_explainability_service.py` |
| 39 | **Permutation Importance** | Öznitelik önemi. | `ml_explainability_service.py` |

---

## BÖLÜM 5 — İstatistik & Aykırı Değer

| # | Teknik | Ne yapar | Durum / Dosya |
|--:|---|---|---|
| 40 | **IQR (Çeyrekler Arası)** | Aykırı değer tespiti. | **Aktif** — Veri Kalitesi |
| 41 | **Z-Score** | Standart skor aykırı tespiti. | Panelde PLANNED |
| 42 | **t-test / ANOVA (f_oneway) / Chi-square / Spearman** | p-değeri ile anlamlılık testleri. | `ml_analysis_service.py` (p-value) |
| 43 | **Isolation Forest** | Yüksek boyutlu aykırı tespiti. | PLANNED (sklearn mevcut) |
| 44 | **Local Outlier Factor** | Yoğunluk tabanlı aykırı tespiti. | PLANNED |

---

## BÖLÜM 6 — Sağlık / Doğrulama / Test / Güvenlik Kontrolleri

> Paneldeki maddelerin **çoğunluğu** burasıdır. Bunlar "algoritma" değil,
> **kontrol/doğrulama** mekanizmalarıdır. Aşağıda kategorize özet (panelde
> ACTIVE olanlar gerçekten çalışıyor).

- **Sistem/DB sağlığı:** Health Check, Heartbeat, SQLite Connection Test,
  PRAGMA integrity_check, PRAGMA foreign_key_check, Transaction Test, Backup
  Validation, Schema Validation, Migration Check.
- **Veri kalitesi kontrolleri:** Duplicate Detection, Missing Value Check,
  Referential Integrity, Validity/Range Check, Outlier (IQR), Rule-Based
  Validation, Data Profiling, Sanity Check.
- **Fonksiyon/test kontrolleri:** Smoke/Self/Unit/Integration/Contract/
  Exception/Boundary/Mock Test, Import Check. (Regression/E2E: pytest paketinde
  **var**, health'e bağlanması planlı.)
- **Güvenlik:** Permission Check, SQL Injection Pattern, Input Sanitization,
  Path Validation, Audit Log, Sensitive Data, RBAC, SQL Console Security.
- **Mimari:** Layer Violation, Import/Circular Dependency, Service/Repository
  Pattern, Dead/Duplicate Code (ipucu seviyesi).
- **Performans:** Execution Time, Slow Query, Threshold Alerting. (Memory/CPU/
  Profiling/Timeout: psutil gerektirir, planlı.)
- **Log analizi:** Error Log Scanner, Warning Counter, Critical Error,
  Pattern Matching, Last Error Snapshot.
- **UI kontrolleri:** Tab Load, Widget Existence, Table Render, Empty State,
  UI Exception. (Event Binding/Navigation: planlı.)
- **Sağlık skorlama:** Weighted Scoring, Rule-Based Scoring, Priority Ranking,
  Threshold Alerting. (Risk Matrix / AHP-Based Health Score / FMEA / SLA: planlı
  ya da gereksiz.)

---

## BÖLÜM 7 — Panelde Olup Kodda Durumu Farklı Olanlar (Boşluk Analizi)

| Panel maddesi | Panel durumu | Gerçek durum (kod) |
|---|---|---|
| K-Means / Decision Tree / Random Forest / Linear Regression | "PLANNED (algoritma mevcut)" | **Kodda uygulanmış**, ML modülünde çalışıyor; yalnızca **health paneline** bağlanmamış |
| Recommendation Algorithms | "PLANNED" | Karar motoru + `pool_recommendation` (AHP+cosine) **çalışıyor** |
| Sensitivity Analysis / Ranking Stability | "PLANNED" | `sensitivity_analysis_service` + `ahp_sensitivity_service` **mevcut** |
| Regression/E2E/Full Regression Test | "PLANNED" | pytest paketinde **var** (`test_end_to_end_pipeline.py` dahil); health entegrasyonu yok |
| Anomaly / Isolation Forest / LOF / Z-Score | "PLANNED" | Henüz aktif kullanımda **değil** (gerçekten planlı) |
| NLP (ders benzerliği) | Panelde yok | TF-IDF + cosine **aktif** (`similarity_engine`) |
| Açılabilirlik Skoru | Panelde yok | **Aktif** (`acilabilirlik_service`) — bu projede yeni |

---

## Çalışma Sırası Önerisi (öğrenmek için)

1. **Önce karar çekirdeği:** AHP → TOPSIS → Trend → Veri Güveni → Karar
   Politikası → Açılabilirlik (Bölüm 1). Sistemin kalbi budur.
2. **Sonra planlama:** Greedy kısıtlı atama + kısıt kontrolleri (Bölüm 2).
3. **Sonra destekleyici ML/NLP:** TF-IDF/cosine, RF/DT/LR, SHAP/LIME (Bölüm 3–4).
4. **En son kontroller:** Sağlık/doğrulama/güvenlik (Bölüm 6) — bunlar "karar"
   değil "kalite güvencesi".

> Her algoritmanın formülünü ve arayüzdeki çıktısını **Genel Bakış** sekmesinde
> (🏠) özet olarak da görebilirsin.
