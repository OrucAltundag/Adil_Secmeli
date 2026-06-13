"""Mock data used when the benchmark REST API is not reachable."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime

SCENARIOS = [
    {
        "name": "real_mcdm_recommendation",
        "display_name": "MCDM Ders Önerisi (Gerçek Veri)",
        "description": "Gerçek sistem verisinden açıklanabilir MCDM yöntemleriyle ders sıralaması karşılaştırması.",
        "purpose_tr": "Üniversitenin gerçek ders kriterleri (başarı, trend, popülerlik, anket) üzerinde 4 farklı çok-kriterli karar algoritmasını yarıştırır.",
        "system_impact_tr": "AHP ve TOPSIS üretim hattının ANA karar motorudur; VIKOR ve PROMETHEE_II yalnız benchmark amaçlıdır.",
        "problem_type": "ranking",
        "default_algorithms": ["AHP", "TOPSIS", "VIKOR", "PROMETHEE_II"],
    },
    {
        "name": "real_ml_prediction",
        "display_name": "ML Ders Seçimi Tahmini (Gerçek Veri)",
        "description": "Gerçek veriyle denetimli öğrenme tahmin karşılaştırması.",
        "purpose_tr": "Öğrenci özelliklerinden ders tercihini tahmin eden ML modellerini gerçek veride yarıştırır.",
        "system_impact_tr": "RandomForest 'Destekleyici ML' rolündedir; diğer modeller yalnız benchmark.",
        "problem_type": "prediction",
        "default_algorithms": ["NaiveBayes", "LogisticRegression", "RandomForest", "XGBoostLike"],
    },
    {
        "name": "allocation_fairness",
        "display_name": "Yerleştirme Adaleti Karşılaştırması",
        "description": "Kontenjan kısıtı altında öğrenci-ders yerleştirme algoritmaları.",
        "purpose_tr": "Tercih sırasına göre öğrencileri seçmeli derslere yerleştiren 5 algoritmanın adillik karşılaştırması.",
        "system_impact_tr": "Henüz üretim hattında değil; sonuçlar rapor amaçlıdır.",
        "problem_type": "allocation",
        "default_algorithms": ["GaleShapley", "RandomAllocation", "GreedyAllocation", "FirstComeFirstServed", "MinimumRegretAllocation"],
    },
    {
        "name": "clustering_exploration",
        "display_name": "Öğrenci & Ders Kümelemesi (Keşif)",
        "description": "Denetimsiz kümeleme keşfi.",
        "purpose_tr": "Benzer öğrenci veya ders profillerini gruplayan kümeleme algoritmalarını karşılaştırır.",
        "system_impact_tr": "Üretim kararını değiştirmez; yalnız Analiz & Grafik raporunda yardımcı sinyaldir.",
        "problem_type": "clustering",
        "default_algorithms": ["KMeans", "HierarchicalClustering", "DBSCAN"],
    },
]


ALGORITHMS = [
    {"name": "AHP", "group": "MCDM", "usage_role": "production_decision", "role_label": "Ana karar motoru"},
    {"name": "TOPSIS", "group": "MCDM", "usage_role": "production_decision", "role_label": "Ana karar motoru"},
    {"name": "VIKOR", "group": "MCDM", "usage_role": "benchmark_only", "role_label": "Sadece benchmark"},
    {"name": "PROMETHEE_II", "group": "MCDM", "usage_role": "benchmark_only", "role_label": "Sadece benchmark"},
    {"name": "RandomPredictor", "group": "ML", "usage_role": "benchmark_only", "role_label": "Sadece benchmark"},
    {"name": "MajorityClassPredictor", "group": "ML", "usage_role": "benchmark_only", "role_label": "Sadece benchmark"},
    {"name": "PopularityRecommender", "group": "ML", "usage_role": "benchmark_only", "role_label": "Sadece benchmark"},
    {"name": "NaiveBayes", "group": "ML", "usage_role": "benchmark_only", "role_label": "Sadece benchmark"},
    {"name": "LogisticRegression", "group": "ML", "usage_role": "benchmark_only", "role_label": "Sadece benchmark"},
    {"name": "RandomForest", "group": "ML", "usage_role": "advisory_ml", "role_label": "Destekleyici ML"},
    {"name": "XGBoostLike", "group": "ML", "usage_role": "benchmark_only", "role_label": "Sadece benchmark"},
    {"name": "KMeans", "group": "Clustering", "usage_role": "benchmark_only", "role_label": "Sadece benchmark"},
    {"name": "HierarchicalClustering", "group": "Clustering", "usage_role": "benchmark_only", "role_label": "Sadece benchmark"},
    {"name": "DBSCAN", "group": "Clustering", "usage_role": "benchmark_only", "role_label": "Sadece benchmark"},
    {"name": "GaleShapley", "group": "Allocation", "usage_role": "benchmark_only", "role_label": "Sadece benchmark"},
    {"name": "RandomAllocation", "group": "Allocation", "usage_role": "benchmark_only", "role_label": "Sadece benchmark"},
    {"name": "GreedyAllocation", "group": "Allocation", "usage_role": "benchmark_only", "role_label": "Sadece benchmark"},
    {"name": "FirstComeFirstServed", "group": "Allocation", "usage_role": "benchmark_only", "role_label": "Sadece benchmark"},
    {"name": "MinimumRegretAllocation", "group": "Allocation", "usage_role": "benchmark_only", "role_label": "Sadece benchmark"},
]


ML_READINESS = {
    "success": True,
    "data": [
        {
            "algorithm_key": "random_forest",
            "sample_count": 24,
            "required_min_samples": 200,
            "readiness_level": "not_ready",
            "usage_role": "advisory_ml",
            "can_train": False,
            "can_use_for_production_decision": False,
            "warnings": ["Bu algoritma destekleyici ML rolündedir; nihai kararı tek başına üretmez."],
        },
        {
            "algorithm_key": "xgboost",
            "sample_count": 24,
            "required_min_samples": 500,
            "readiness_level": "not_ready",
            "usage_role": "benchmark_only",
            "can_train": False,
            "can_use_for_production_decision": False,
            "warnings": ["Bu algoritma sadece benchmark olarak konumlandırılmıştır."],
        },
        {
            "algorithm_key": "logistic_regression",
            "sample_count": 24,
            "required_min_samples": 50,
            "readiness_level": "low",
            "usage_role": "benchmark_only",
            "can_train": False,
            "can_use_for_production_decision": False,
            "warnings": ["Örnek sayısı düşük; benchmark baseline olarak kalmalı."],
        },
    ],
    "message": "Mock ML readiness verisi.",
}


ALGORITHM_GOVERNANCE = {
    "success": True,
    "data": [
        {
            "algorithm_key": "ahp",
            "display_name": "AHP",
            "algorithm_family": "mcdm",
            "task_type": "ranking",
            "usage_role": "production_decision",
            "can_affect_final_decision": True,
            "minimum_sample_count": 2,
            "recommended_metrics": ["ahp_consistency_ratio", "rank_stability"],
            "user_facing_warning": "Ana karar motoru bileşenidir.",
        },
        {
            "algorithm_key": "topsis",
            "display_name": "TOPSIS",
            "algorithm_family": "mcdm",
            "task_type": "ranking",
            "usage_role": "production_decision",
            "can_affect_final_decision": True,
            "minimum_sample_count": 2,
            "recommended_metrics": ["top_k_overlap", "rank_stability"],
            "user_facing_warning": "Ana karar motoru bileşenidir.",
        },
        {
            "algorithm_key": "random_forest",
            "display_name": "Random Forest",
            "algorithm_family": "ml",
            "task_type": "classification",
            "usage_role": "advisory_ml",
            "can_affect_final_decision": False,
            "minimum_sample_count": 200,
            "recommended_metrics": ["balanced_accuracy", "f1_macro", "f1_weighted"],
            "user_facing_warning": "Destekleyici ML; nihai karar değildir.",
        },
        {
            "algorithm_key": "logistic_regression",
            "display_name": "Logistic Regression",
            "algorithm_family": "ml",
            "task_type": "classification",
            "usage_role": "benchmark_only",
            "can_affect_final_decision": False,
            "minimum_sample_count": 50,
            "recommended_metrics": ["balanced_accuracy", "f1_macro"],
            "user_facing_warning": "Benchmark baseline; final karar olarak kullanılamaz.",
        },
        {
            "algorithm_key": "xgboost",
            "display_name": "XGBoost",
            "algorithm_family": "ml",
            "task_type": "classification",
            "usage_role": "benchmark_only",
            "can_affect_final_decision": False,
            "minimum_sample_count": 500,
            "recommended_metrics": ["balanced_accuracy", "f1_macro", "roc_auc"],
            "user_facing_warning": "Sadece benchmark; minimum veri sağlanmadan çalıştırılmaz.",
        },
        {
            "algorithm_key": "dbscan",
            "display_name": "DBSCAN",
            "algorithm_family": "clustering",
            "task_type": "clustering",
            "usage_role": "benchmark_only",
            "can_affect_final_decision": False,
            "minimum_sample_count": 100,
            "recommended_metrics": ["noise_ratio", "cluster_count", "silhouette_score"],
            "user_facing_warning": "Keşifsel clustering; nihai karar üretmez.",
        },
    ],
}


ALGORITHM_TASKS = {
    "success": True,
    "data": [
        {"task_key": "course_ranking", "algorithm_key": "ahp", "allowed_usage_role": "production_decision", "is_recommended": True, "notes": "Ana ağırlıklandırma."},
        {"task_key": "course_ranking", "algorithm_key": "topsis", "allowed_usage_role": "production_decision", "is_recommended": True, "notes": "Ana sıralama."},
        {"task_key": "course_status_classification", "algorithm_key": "random_forest", "allowed_usage_role": "advisory_ml", "is_recommended": True, "notes": "Destekleyici ML."},
        {"task_key": "course_status_classification", "algorithm_key": "logistic_regression", "allowed_usage_role": "benchmark_only", "is_recommended": False, "notes": "Benchmark baseline."},
        {"task_key": "preference_clustering", "algorithm_key": "dbscan", "allowed_usage_role": "benchmark_only", "is_recommended": False, "notes": "Keşifsel clustering."},
    ],
}


GOVERNED_RUNS = {
    "success": True,
    "data": [
        {
            "id": 1,
            "task_type": "classification",
            "sample_count": 24,
            "feature_count": 8,
            "status": "completed",
            "primary_metric_name": "f1_macro",
            "started_at": "2026-05-06T10:00:00",
        }
    ],
}


DATASETS = [
    "raw_real",
    "derived",
    "synthetic",
    "real_pref_2024_v2",
    "derived_student_2024",
    "synthetic_100k",
]


DATASET_LAYER_CARDS = [
    {"name": "raw_real", "count": "12.4K", "source": "CSV / SQLite", "updated": "Bugün", "description": "Gerçek akademik ve tercih verisi"},
    {"name": "derived", "count": "8.7K", "source": "Feature pipeline", "updated": "Bugün", "description": "İşlenmiş ve ölçeklendirilmiş özellikler"},
    {"name": "synthetic", "count": "100K", "source": "Bootstrap", "updated": "Bugün", "description": "Ölçek ve stres testi verisi"},
]


MODEL_REFERENCES = [
    ("Student", "Ogrenci demografik ve akademik bilgileri"),
    ("Course", "Ders/program/kontenjan bilgileri"),
    ("Preference", "Ogrenci tercih siralari"),
    ("SurveyResponse", "Anket yanitlari"),
    ("Allocation", "Yerlestirme ciktilari"),
    ("BenchmarkRun", "Deney calistirma kaydi"),
    ("MetricResult", "Algoritma-metrik sonucu"),
]


COMPARISON_ROWS = [
    {"algorithm": "RandomForest", "group": "ML", "accuracy": 0.923, "f1": 0.914, "roc_auc": 0.957, "hit_at_10": 0.873, "ndcg_at_10": 0.865, "silhouette": "", "fairness": "", "latency_ms": 128, "runtime": "00:00:18", "explanation": "Yuksek dogruluk, orta gecikme"},
    {"algorithm": "LogisticRegression", "group": "ML", "accuracy": 0.897, "f1": 0.889, "roc_auc": 0.941, "hit_at_10": 0.832, "ndcg_at_10": 0.819, "silhouette": "", "fairness": "", "latency_ms": 94, "runtime": "00:00:09", "explanation": "Yorumlanabilir hizli model"},
    {"algorithm": "AHP", "group": "MCDM", "accuracy": 0.861, "f1": 0.845, "roc_auc": 0.885, "hit_at_10": 0.792, "ndcg_at_10": 0.768, "silhouette": "", "fairness": "", "latency_ms": 52, "runtime": "00:00:04", "explanation": "Tutarlilik orani ile aciklanabilir"},
    {"algorithm": "TOPSIS", "group": "MCDM", "accuracy": 0.843, "f1": 0.830, "roc_auc": 0.871, "hit_at_10": 0.771, "ndcg_at_10": 0.744, "silhouette": "", "fairness": "", "latency_ms": 47, "runtime": "00:00:03", "explanation": "Ideal cozum uzakligi"},
    {"algorithm": "GaleShapley", "group": "Allocation", "accuracy": "", "f1": "", "roc_auc": "", "hit_at_10": "", "ndcg_at_10": "", "silhouette": "", "fairness": 0.843, "latency_ms": 37, "runtime": "00:00:02", "explanation": "Stabil ve adil yerlestirme"},
    {"algorithm": "KMeans", "group": "Clustering", "accuracy": "", "f1": "", "roc_auc": "", "hit_at_10": "", "ndcg_at_10": "", "silhouette": 0.612, "fairness": "", "latency_ms": 110, "runtime": "00:00:11", "explanation": "Segmentasyon icin olceklenebilir"},
]


SAMPLE_RUN = {
    "run_id": "RUN-2024-05-18-104231",
    "scenario": "real_mcdm_recommendation",
    "dataset": "real_pref_2024_v2",
    "algorithms": ["AHP", "TOPSIS", "VIKOR", "PROMETHEE_II", "LogisticRegression", "RandomForest", "KMeans"],
    "started_by": "Admin",
    "date": "18.05.2024 10:42",
    "status": "completed",
    "duration": "00:12:47",
    "dataset_size": "12.4K",
    "metric_count": 9,
    "metrics": {
        "accuracy": 0.923,
        "f1": 0.914,
        "roc_auc": 0.957,
        "hit_at_10": 0.873,
        "ndcg_at_10": 0.865,
        "silhouette": 0.612,
        "fairness": 0.843,
        "latency_ms": 128,
    },
}


RUNS = [
    {
        "run_id": "RUN-2024-05-18-104231",
        "date": "18.05.2024 10:42",
        "scenario": "real_mcdm_recommendation",
        "dataset": "real_pref_2024_v2",
        "algorithms_count": 7,
        "status": "completed",
        "duration": "00:12:47",
        "accuracy": 0.923,
        "f1": 0.914,
        "roc_auc": 0.957,
        "hit_at_k": 0.873,
        "ndcg_at_k": 0.865,
        "silhouette": 0.612,
        "fairness": 0.843,
        "latency": 128,
    },
    {
        "run_id": "RUN-2024-05-17-183015",
        "date": "17.05.2024 18:30",
        "scenario": "real_ml_prediction",
        "dataset": "derived_student_2024",
        "algorithms_count": 5,
        "status": "completed",
        "duration": "00:06:21",
        "accuracy": 0.897,
        "f1": 0.889,
        "roc_auc": 0.941,
        "hit_at_k": 0.832,
        "ndcg_at_k": 0.819,
        "silhouette": "",
        "fairness": "",
        "latency": 94,
    },
    {
        "run_id": "RUN-2024-05-16-141200",
        "date": "16.05.2024 14:12",
        "scenario": "allocation_fairness",
        "dataset": "real_pref_2024_v2",
        "algorithms_count": 5,
        "status": "completed",
        "duration": "00:04:33",
        "accuracy": "",
        "f1": "",
        "roc_auc": "",
        "hit_at_k": "",
        "ndcg_at_k": "",
        "silhouette": "",
        "fairness": 0.871,
        "latency": 37,
    },
]


DATA_PREVIEW_ROWS = [
    {"student_id": 1001, "age": 20, "gender": "K", "gpa": 3.45, "faculty": "Muhendislik", "pref_count": 8, "avg_rank": 3.12, "score_composite": 0.742},
    {"student_id": 1002, "age": 21, "gender": "E", "gpa": 3.12, "faculty": "Saglik", "pref_count": 10, "avg_rank": 4.50, "score_composite": 0.638},
    {"student_id": 1003, "age": 19, "gender": "K", "gpa": 3.78, "faculty": "Tip", "pref_count": 7, "avg_rank": 2.71, "score_composite": 0.812},
]


ALLOCATION_ROWS = [
    {"student_id": 1001, "student_name": "Anonim-001", "assigned_course": "Data Analytics", "assigned_course_id": 1001, "preference_rank_received": 1, "satisfaction_score": 0.96, "algorithm": "GaleShapley", "capacity_status": "Dolu"},
    {"student_id": 1002, "student_name": "Anonim-002", "assigned_course": "AI Fundamentals", "assigned_course_id": 1002, "preference_rank_received": 2, "satisfaction_score": 0.90, "algorithm": "GaleShapley", "capacity_status": "Dolu"},
    {"student_id": 1003, "student_name": "Anonim-003", "assigned_course": "Cyber Security", "assigned_course_id": 1004, "preference_rank_received": 1, "satisfaction_score": 0.93, "algorithm": "GaleShapley", "capacity_status": "Bos kontenjan var"},
]


FAIRNESS_ROWS = [
    {"algorithm": "GaleShapley", "average_rank": 2.31, "top_k_satisfaction": 0.842, "envy_score": 0.126, "seat_fill_rate": 0.987, "assigned": 11880, "unassigned": 520},
    {"algorithm": "RandomAllocation", "average_rank": 3.85, "top_k_satisfaction": 0.455, "envy_score": 0.412, "seat_fill_rate": 0.921, "assigned": 11420, "unassigned": 980},
    {"algorithm": "GreedyAllocation", "average_rank": 2.91, "top_k_satisfaction": 0.731, "envy_score": 0.208, "seat_fill_rate": 0.945, "assigned": 11680, "unassigned": 720},
    {"algorithm": "MinimumRegretAllocation", "average_rank": 2.67, "top_k_satisfaction": 0.795, "envy_score": 0.164, "seat_fill_rate": 0.972, "assigned": 11910, "unassigned": 490},
]


ALGORITHM_DETAILS = {
    "AHP": {
        "group": "MCDM",
        "description": "Kriter agirliklarini tutarlilik orani ile aciklayan cok kriterli karar verme yontemi.",
        "use_case": "Kucuk veri, yuksek aciklanabilirlik, akademik karar gerekcesi.",
        "parameters": ["criteria_weights", "consistency_check", "pairwise_matrix"],
        "metrics": ["Hit@K", "NDCG@K", "Ranking similarity", "Latency"],
        "pros": "Yorumlanabilir, savunulabilir, kriter bazli.",
        "cons": "Buyuk veri ve otomatik ogrenme icin sinirli.",
    },
    "TOPSIS": {
        "group": "MCDM",
        "description": "Alternatifleri ideal ve negatif ideal cozum uzakliklarina gore siralar.",
        "use_case": "Ders/program siralama ve karar matrisi analizi.",
        "parameters": ["weights", "normalization_method"],
        "metrics": ["Hit@K", "NDCG@K", "Latency"],
        "pros": "Hizli, net skor uretir.",
        "cons": "Agirlik secimine duyarlidir.",
    },
    "RandomForest": {
        "group": "ML",
        "description": "Coklu karar agaci toplulugu ile guclu tahmin modeli.",
        "use_case": "Orta-buyuk veri, dogruluk odakli tahmin.",
        "parameters": ["n_estimators", "max_depth", "min_samples_split", "random_state"],
        "metrics": ["Accuracy", "F1", "ROC-AUC", "Feature importance"],
        "pros": "Guclu performans, feature importance.",
        "cons": "Lineer modellere gore daha az seffaf.",
    },
    "KMeans": {
        "group": "Clustering",
        "description": "Ogrencileri ilgi profillerine gore merkez tabanli kumelendirir.",
        "use_case": "Kesifsel segmentasyon ve pattern reproduction.",
        "parameters": ["n_clusters", "max_iter", "random_state"],
        "metrics": ["Silhouette", "Davies-Bouldin", "Calinski-Harabasz"],
        "pros": "Olceklenebilir ve hizli.",
        "cons": "Kume sayisi onceden gerekir.",
    },
    "GaleShapley": {
        "group": "Allocation",
        "description": "Kontenjanli derslere stabil ve tercih uyumlu yerlestirme yapar.",
        "use_case": "Adil yerlestirme ve kontenjan optimizasyonu.",
        "parameters": ["capacity_aware", "preference_source"],
        "metrics": ["Average rank", "Top-K Satisfaction", "Envy Score", "Seat Fill Rate"],
        "pros": "Stabil eslesme ve dusuk envy.",
        "cons": "Utility maksimumunu garanti etmeyebilir.",
    },
}


def get_mock_scenarios():
    return {"scenarios": deepcopy(SCENARIOS)}


def get_mock_algorithms():
    return {"algorithms": deepcopy(ALGORITHMS)}


def get_mock_ml_readiness():
    return deepcopy(ML_READINESS)


def get_mock_ml_model_runs():
    return {"success": True, "data": [], "message": "Mock model run kaydı yok."}


def get_mock_ml_predictions():
    return {"success": True, "data": [], "message": "Mock ML tahmin kaydı yok."}


def get_mock_ml_feature_summary():
    return {
        "success": True,
        "data": {
            "feature_schema_version": "course_features_v1",
            "sample_count": 24,
            "feature_names": ["success_rate", "popularity_score", "trend_score"],
            "missing_features_summary": {},
            "warnings": ["Mock feature özeti."],
        },
    }


def get_mock_ml_feature_snapshot(payload=None):
    return {"success": True, "data": {"snapshot_id": 999, "sample_count": 24}, "message": "Mock snapshot üretildi."}


def get_mock_ml_train(payload=None):
    payload = payload or {}
    return {
        "success": True,
        "data": {
            "id": 999,
            "algorithm_key": payload.get("algorithm_key", "random_forest"),
            "status": "skipped",
            "skip_reason": "Mock veri veya minimum sample yetersiz.",
            "readiness_level": "not_ready",
        },
    }


def get_mock_ml_readiness_report(payload=None):
    return {"success": True, "data": {"report_id": 999, "summary": "Mock readiness raporu."}}


def get_mock_ml_readiness_reports():
    return {"success": True, "data": []}


def get_mock_algorithm_governance():
    return deepcopy(ALGORITHM_GOVERNANCE)


def get_mock_algorithm_tasks():
    return deepcopy(ALGORITHM_TASKS)


def get_mock_governed_runs():
    return deepcopy(GOVERNED_RUNS)


def get_mock_governed_run_metrics():
    return {
        "success": True,
        "data": [
            {
                "algorithm_key": "majority_class_predictor",
                "task_type": "classification",
                "primary_metric_name": "f1_macro",
                "primary_metric_value": 0.62,
                "warnings": [],
            }
        ],
    }


def get_mock_governed_run_validation():
    return {"success": True, "data": [{"algorithm_key": "majority_class_predictor", "validation_strategy": "stratified_kfold", "fold_count": 3}]}


def get_mock_governed_run_statistics():
    return {"success": True, "data": [{"primary_metric_name": "f1_macro", "summary_text": "Mock istatistiksel karşılaştırma."}]}


def get_mock_governed_run_diagnostics():
    return {"success": True, "data": [{"algorithm_key": "majority_class_predictor", "overfitting_warning": False, "summary_text": "Mock diagnostics."}]}


def get_mock_governed_run_leakage():
    return {"success": True, "data": [{"algorithm_key": "majority_class_predictor", "leakage_detected": False, "blocked": False, "summary_text": "Mock leakage yok."}]}


def get_mock_governed_run_clustering():
    return {"success": True, "data": []}


def get_mock_execute_governed_run(payload=None):
    payload = payload or {}
    return {
        "success": True,
        "data": {
            "run_id": 999,
            "task_type": payload.get("task_type", "classification"),
            "sample_count": len(payload.get("y_true") or []),
            "feature_count": len(payload.get("feature_names") or []),
            "algorithms": payload.get("algorithms") or ["majority_class_predictor"],
            "metric_results": [],
            "final_decision_note": "Mock governed benchmark sonucu final kararı etkilemez.",
        },
    }


def get_mock_dataset_load_result():
    return {
        "dataset_name": "mock_benchmark_dataset",
        "raw_real_tables": ["students", "courses", "preferences", "survey_responses", "allocations"],
        "derived_tables": ["student_course_features", "student_course_features_unencoded"],
        "synthetic_tiers": ["5k", "10k", "50k", "100k", "250k"],
        "layer_counts": {
            "raw_real": {"students": 12400, "courses": 180, "preferences": 108000, "survey_responses": 63800, "allocations": 22900},
            "derived": {"student_course_features": 8700, "student_course_features_unencoded": 8700},
            "synthetic": {"5k": 5000, "10k": 10000, "50k": 50000, "100k": 100000, "250k": 250000},
        },
        "preview": {
            "layer": "derived",
            "table": "student_course_features",
            "columns": ["student_id", "age", "gender", "gpa", "faculty", "pref_count", "avg_rank", "score_composite"],
            "rows": deepcopy(DATA_PREVIEW_ROWS),
        },
        "quality_summary": {
            "row_count": 8700,
            "column_count": 8,
            "missing_ratio": 0.012,
            "target_column": "course_id",
            "target_present": True,
            "class_distribution": {"1001": 1250, "1002": 1180, "1004": 960},
        },
        "metadata": {"source": "mock", "loaded_at": datetime.now().isoformat(timespec="seconds")},
    }


def get_mock_execute_run(payload=None):
    run = deepcopy(SAMPLE_RUN)
    payload = payload or {}
    if payload.get("scenario_name"):
        run["scenario"] = payload["scenario_name"]
    if payload.get("dataset"):
        run["dataset"] = payload["dataset"]
    if payload.get("algorithm_names"):
        run["algorithms"] = payload["algorithm_names"]
    if run["scenario"] == "allocation_fairness":
        allocation_results = {}
        for fairness_row in FAIRNESS_ROWS:
            algorithm = fairness_row["algorithm"]
            assignments = deepcopy(ALLOCATION_ROWS)
            for assignment in assignments:
                assignment["algorithm"] = algorithm
                assignment.setdefault("faculty_id", "Mühendislik")
                assignment.setdefault("department_id", "Bilgisayar Mühendisliği")
                assignment.setdefault("course_capacity", 2)
                assignment["allocated"] = bool(assignment.get("assigned_course_id"))
                assignment["rank_received"] = assignment.get("preference_rank_received")
            allocation_results[algorithm] = {
                "output": {"assignments": assignments, "explanation": "Mock allocation sonucu."},
                "metrics": {
                    "fairness": {
                        "average_rank": fairness_row["average_rank"],
                        "top_k_satisfaction": fairness_row["top_k_satisfaction"],
                        "envy_score": fairness_row["envy_score"],
                        "seat_fill_rate": fairness_row["seat_fill_rate"],
                    },
                    "performance": {"latency_ms": 10.0},
                },
            }
        return {
            "summary": {
                "run_id": run["run_id"],
                "scenario_name": run["scenario"],
                "dataset_name": run["dataset"],
                "status": run["status"],
                "started_at": run["date"],
                "finished_at": run["date"],
                "algorithms": list(allocation_results.keys()),
            },
            "comparison_table": deepcopy(FAIRNESS_ROWS),
            "details": {"run": run, "results": allocation_results, "request_parameters": {"allocation": payload.get("allocation_parameters", {})}},
            "request_parameters": {"allocation": payload.get("allocation_parameters", {})},
        }
    return {
        "summary": {
            "run_id": run["run_id"],
            "scenario_name": run["scenario"],
            "dataset_name": run["dataset"],
            "status": run["status"],
            "started_at": run["date"],
            "finished_at": run["date"],
            "algorithms": run["algorithms"],
        },
        "comparison_table": deepcopy(COMPARISON_ROWS),
        "details": {"run": run, "results": deepcopy(COMPARISON_ROWS)},
    }


def get_mock_recommendation(problem_type: "str | dict" = "prediction"):
    explainability_priority = False
    data_size = 5000
    if isinstance(problem_type, dict):
        payload = problem_type
        explainability_priority = bool(payload.get("explainability_priority"))
        data_size = int(payload.get("data_size") or data_size)
        problem_key: str = str(payload.get("problem_type") or "prediction")
    else:
        problem_key = problem_type
    mapping = {
        "prediction": ("RandomForest", 0.884, "Gecmis benchmarklerde F1 ve ROC-AUC dengesi en guclu."),
        "ranking": ("AHP", 0.780, "Kucuk ve aciklanabilir siralama senaryosu icin kriter agirliklari seffaf."),
        "allocation": ("GaleShapley", 0.850, "Kontenjan ve tercih uyumu icin stabil eslesme en uygun baslangic."),
        "clustering": ("KMeans", 0.800, "Buyuk veri kesif senaryosunda en olceklenebilir kumeleme secenegi."),
    }
    if problem_key == "prediction" and explainability_priority and data_size < 10000:
        mapping["prediction"] = ("LogisticRegression", 0.790, "Küçük ve açıklanabilir tahmin senaryosunda lineer baseline önerilir.")
    algorithm, confidence, reason = mapping.get(problem_key, mapping["prediction"])
    return {
        "algorithm": algorithm,
        "confidence": confidence,
        "reason": reason,
        "source": "rules",
        "candidates": ["RandomForest", "LogisticRegression", "AHP", "GaleShapley", "KMeans"],
        "used_run_count": 0,
        "data_coverage": {
            "source": "rules",
            "used_run_count": 0,
            "coverage_note": "Mock/kural tabanlı öneri; geçmiş benchmark run kullanılmadı.",
        },
    }


def get_mock_runs():
    return {"runs": deepcopy(RUNS)}


def get_mock_run_detail(run_id):
    return {
        "summary": next((deepcopy(r) for r in RUNS if r["run_id"] == run_id), deepcopy(RUNS[0])),
        "comparison_table": deepcopy(COMPARISON_ROWS),
        "details": {
            "run": deepcopy(SAMPLE_RUN),
            "results": deepcopy(COMPARISON_ROWS),
            "metrics": deepcopy(SAMPLE_RUN["metrics"]),
        },
    }
