# Algoritma Kullanım Denetimi

Bu belge, projedeki **tüm algoritmaların** nerede ve nasıl kullanıldığını denetler.
Kaynak: kod taraması (`app/services/calculation.py`, `course_analyzer.py`,
`rules_engine.py`, `pool_state_machine_service.py`, `trend_analysis_service.py`,
`decision_run_service.py`) + `algorithm_governance_registry` tablosu.

Tarih: 2026-06-14

## Özet — Üç katman

| Katman | Anlamı | Nihai karara etkisi |
|--------|--------|---------------------|
| **Üretim / Karar (production_decision)** | Müfredat üretimi ve kesinleşme puanını DOĞRUDAN üretir | **Evet** |
| **Destekleyici (advisory_ml)** | İkincil sinyal/yorum; karar değiştirmez | Dolaylı |
| **Sadece benchmark (benchmark_only / baseline)** | Karşılaştırma/araştırma; üretim hattında çalışmaz | **Hayır** |

---

## 1. Üretim hattında kullanılan algoritmalar (nihai kararı üretir)

| Algoritma | Kullanıldığı yer | Rol |
|-----------|------------------|-----|
| **AHP** | `calculation.py` (`ahp_calistir`, kriter ağırlıkları), `get_faculty_year_topsis_results`, `ahp_*_service` | Ana karar motoru — kriter ağırlıkları |
| **TOPSIS** | `calculation.py` (`topsis_calistir` → kesinleşme puanı), `course_analyzer.py` | Ana karar motoru — ders sıralaması |
| **Kural Motoru (rule_engine)** | `calculation.py` (drop eşikleri: `DROP_SCORE_THRESHOLD`, ortalama not barajı), `decision_run_service.py` | Düşme/kalma kuralları |
| **State Machine** | `pool_state_machine_service.py`, `havuz_karar.py` (`calculate_next_status`) | Havuz statü/sayaç geçişleri |
| **Trend Analizi** | `trend_analysis_service.py` (`weighted_trend_score`, `analyze_trend_values`), TOPSIS kriteri olarak | Ağırlıklı geçmiş yıl sinyali |

Kanıt: bu beş bileşen üretim dosyalarında 4–5 yerde geçer.

---

## 2. Destekleyici (advisory) — karar değiştirmez, yorum verir

| Algoritma | Kullanıldığı yer | Not |
|-----------|------------------|-----|
| **Random Forest** | `course_analyzer.py` (`predict_kesinlesme` — RF tahmin adımı) | Ders Lab'de bilgilendirici kesinleşme tahmini; nihai kararı `is_active`/governance kuralıyla değiştiremez |
| **Decision Tree** | `course_analyzer.py` (karar gerekçesi adımı) | Açıklanabilir gerekçe; ikincildir |
| **TF-IDF / Benzerlik** | `course_matcher.py` → `survey_import_service.py` (ders adı eşleştirme) | Anket dersi eşleştirmede normalize/benzerlik; karar skoruna girmez |

---

## 3. Sadece benchmark / baseline — üretim hattında ÇALIŞMAZ

Aşağıdaki algoritmalar üretim dosyalarında **0 kez** geçer; yalnızca Benchmark
Lab senaryolarında karşılaştırma için çalışır. Sonuçları müfredat/kesinleşme
kararını **değiştirmez**.

| Aile | Algoritmalar |
|------|--------------|
| MCDM | VIKOR, PROMETHEE_II |
| ML | Logistic Regression, Naive Bayes, XGBoost, GradientBoosting |
| Clustering | KMeans, Hierarchical, DBSCAN |
| Allocation | Gale-Shapley, Greedy, Random, FCFS, Minimum Regret |
| Baseline | RandomPredictor, MajorityClass, Popularity, Dummy* |

---

## 4. Yönetim

- Bu roller `algorithm_governance_registry` tablosunda `usage_role` ve
  `can_affect_final_decision` alanlarıyla tutulur.
- **Aktif/Pasif**: Benchmark Lab → Algoritma Yönetimi sayfasından her algoritma
  aktif/pasif yapılabilir (`is_active`). Çekirdek karar algoritmaları (AHP,
  TOPSIS, kural motoru, state machine) **pasife alınamaz** — aksi hâlde nihai
  karar üretilemez.
- **Skorların etkisi**: yalnızca 1. ve 2. katman üretim/Ders Lab çıktısını
  etkiler. 3. katman (benchmark) çıktıları raporlama/araştırma içindir.

## 5. Yeniden üretim

Denetimi güncellemek için:

```bash
# Algoritma registry'sini (governance) kontrol et
python -c "import sqlite3; from app.services.algorithm_governance_service import list_algorithm_governance; \
print(len(list_algorithm_governance(sqlite3.connect('data/adil_secmeli.db'))), 'algoritma kayıtlı')"
```
