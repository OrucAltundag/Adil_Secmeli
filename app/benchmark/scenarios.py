"""Scenario definitions for repeatable benchmark runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BenchmarkScenario:
    name: str
    description: str
    problem_type: str  # prediction | ranking | clustering | allocation | mixed
    dataset_layer: str = "derived"
    table_name: str = "student_course_features"
    target_column: str = "course_id"
    top_k: int = 5
    use_synthetic_tier: str | None = None
    algorithm_names: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    # UI'da gosterilen Turkce baslik ve uzun aciklama (kullanici talebi):
    # "Senaryo adlarini turkce yap, anlamli sekle getir."
    display_name: str | None = None
    purpose_tr: str | None = None
    system_impact_tr: str | None = None


DEFAULT_SCENARIOS: dict[str, BenchmarkScenario] = {
    "real_mcdm_recommendation": BenchmarkScenario(
        name="real_mcdm_recommendation",
        description=(
            "Gerçek sistem verisinden açıklanabilir MCDM yöntemleriyle ders sıralaması "
            "karşılaştırması (AHP, TOPSIS, VIKOR, PROMETHEE_II)."
        ),
        display_name="MCDM Ders Önerisi (Gerçek Veri)",
        purpose_tr=(
            "Üniversitenin gerçek ders kriterleri (başarı, trend, popülerlik, anket) "
            "üzerinde 4 farklı çok-kriterli karar algoritmasının ürettiği sıralamayı "
            "karşılaştırır. Hangi yöntem en güvenilir Top-K önerisini üretiyor?"
        ),
        system_impact_tr=(
            "AHP ve TOPSIS üretim hattının ANA karar motorudur (kesinleşme puanı, "
            "müfredat üretimi). VIKOR ve PROMETHEE_II yalnız karşılaştırma içindir; "
            "sonuçları kararı doğrudan değiştirmez."
        ),
        problem_type="ranking",
        table_name="student_course_features_unencoded",
        target_column="course_id",
        top_k=5,
        algorithm_names=["AHP", "TOPSIS", "VIKOR", "PROMETHEE_II"],
    ),
    "real_ml_prediction": BenchmarkScenario(
        name="real_ml_prediction",
        description=(
            "Gerçek veriyle denetimli öğrenme: hangi öğrencinin hangi dersi seçeceğini "
            "tahmin eden modellerin doğruluk/F1/ROC-AUC karşılaştırması."
        ),
        display_name="ML Ders Seçimi Tahmini (Gerçek Veri)",
        purpose_tr=(
            "Öğrenci özelliklerinden (not ortalaması, dönem vb.) ders tercihini tahmin "
            "eden 6 makine öğrenmesi modelini gerçek veride yarıştırır."
        ),
        system_impact_tr=(
            "RandomForest 'Destekleyici ML' rolündedir: kesinleşme puanı yorumlamasına "
            "ikincil sinyal verir. Diğer modeller yalnız benchmark; üretim kararını "
            "doğrudan değiştirmez."
        ),
        problem_type="prediction",
        table_name="student_course_features",
        target_column="course_id",
        top_k=5,
        algorithm_names=[
            "RandomPredictor",
            "MajorityClassPredictor",
            "NaiveBayes",
            "LogisticRegression",
            "RandomForest",
            "XGBoostLike",
        ],
    ),
    "allocation_fairness": BenchmarkScenario(
        name="allocation_fairness",
        description=(
            "Kontenjan kısıtı altında öğrenci-ders yerleştirme algoritmalarını "
            "adillik (envy, regret) ve kullanım açısından karşılaştırır."
        ),
        display_name="Yerleştirme Adaleti Karşılaştırması",
        purpose_tr=(
            "Tercih sırasına göre öğrencileri seçmeli derslere yerleştiren 5 farklı "
            "algoritmanın (Gale-Shapley, FCFS, Açgözlü, vb.) hem doluluk hem adillik "
            "açısından nasıl davrandığını gösterir."
        ),
        system_impact_tr=(
            "Bu algoritmalar henüz üretim hattında değil; sonuçlar yalnız raporlama/"
            "kıyaslama içindir. Kayıt sistemine geçirilmek istenirse hangi algoritmanın "
            "daha adil olduğu kararını destekler."
        ),
        problem_type="allocation",
        dataset_layer="raw_real",
        table_name="preferences",
        top_k=3,
        algorithm_names=[
            "GaleShapley",
            "RandomAllocation",
            "GreedyAllocation",
            "FirstComeFirstServed",
            "MinimumRegretAllocation",
        ],
    ),
    "clustering_exploration": BenchmarkScenario(
        name="clustering_exploration",
        description=(
            "Denetimsiz kümelemeyle öğrenci/ders segmentlerini keşfeder; "
            "silhouette, Davies-Bouldin metrikleriyle kalite ölçer."
        ),
        display_name="Öğrenci & Ders Kümelemesi (Keşif)",
        purpose_tr=(
            "Benzer öğrenci profillerini veya benzer ders davranışını gruplayan 3 "
            "kümeleme algoritmasını (K-Means, Hiyerarşik, DBSCAN) karşılaştırır. "
            "Hedef: 'Hangi gruplar var?' sorusunu yanıtlamak."
        ),
        system_impact_tr=(
            "Kümeleme sonuçları üretim kararını DEĞİŞTİRMEZ; yalnız 'Analiz & Grafik' "
            "raporunda yardımcı betimsel bir görsel/sinyaldir."
        ),
        problem_type="clustering",
        table_name="student_course_features",
        top_k=5,
        algorithm_names=["KMeans", "HierarchicalClustering", "DBSCAN"],
    ),
}


# Senaryo anahtarini gosterim adina cevirmek icin yardimci.
def display_label(scenario: "BenchmarkScenario") -> str:
    return scenario.display_name or scenario.name
