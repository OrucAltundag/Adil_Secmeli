# -*- coding: utf-8 -*-
"""Algoritma yönetişimi registry ve problem-algoritma eşleştirme servisi."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
import json
import sqlite3
from typing import Any

from app.core.errors import BusinessRuleAppError
from app.db.schema_compat import ensure_algorithm_governance_schema


PRODUCTION_DECISION = "production_decision"
ADVISORY_ML = "advisory_ml"
BENCHMARK_ONLY = "benchmark_only"
EXPERIMENTAL = "experimental"
BASELINE = "baseline"


@dataclass(frozen=True)
class AlgorithmGovernance:
    algorithm_key: str
    display_name: str
    algorithm_family: str
    task_type: str
    usage_role: str
    can_affect_final_decision: bool
    default_enabled: bool
    minimum_sample_count: int
    minimum_samples_per_class: int | None
    requires_feature_scaling: bool
    requires_target: bool
    supports_probability: bool
    supports_feature_importance: bool
    supports_explainability: bool
    supports_cross_validation: bool
    recommended_validation_strategy: str
    recommended_metrics: list[str]
    risk_notes: str | None = None
    user_facing_warning: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


DEFAULT_ALGORITHMS: list[AlgorithmGovernance] = [
    AlgorithmGovernance("ahp", "AHP", "mcdm", "ranking", PRODUCTION_DECISION, True, True, 2, None, False, False, False, False, True, False, "holdout", ["ahp_consistency_ratio", "rank_stability"], "Tutarlılık oranı izlenmelidir.", "Ana karar motoru bileşenidir."),
    AlgorithmGovernance("topsis", "TOPSIS", "mcdm", "ranking", PRODUCTION_DECISION, True, True, 2, None, False, False, False, False, True, False, "holdout", ["top_k_overlap", "rank_stability", "sensitivity_score"], "Ağırlık duyarlılığı izlenmelidir.", "Ana karar motoru bileşenidir."),
    AlgorithmGovernance("rule_engine", "Rule Engine", "rule_based", "decision_rule", PRODUCTION_DECISION, True, True, 1, None, False, False, False, False, True, False, "policy_check", ["rule_coverage"], None, "Ana karar motoru bileşenidir."),
    AlgorithmGovernance("state_machine", "State Machine", "rule_based", "decision_rule", PRODUCTION_DECISION, True, True, 1, None, False, False, False, False, True, False, "policy_check", ["transition_consistency"], None, "Ana karar motoru bileşenidir."),
    AlgorithmGovernance("trend_analysis", "Trend Analysis", "rule_based", "ranking", PRODUCTION_DECISION, True, True, 2, None, False, False, False, False, True, False, "time_based_split", ["trend_stability"], "Geçmiş veri azsa düşük güvenle yorumlanır.", "Ana karar motoruna destek veren trend bileşenidir."),
    AlgorithmGovernance("vikor", "VIKOR", "mcdm", "ranking", BENCHMARK_ONLY, False, True, 2, None, False, False, False, False, True, False, "holdout", ["spearman_correlation", "kendall_tau", "top_k_overlap"], "MCDM karşılaştırma algoritmasıdır.", "Sadece benchmark; nihai karara doğrudan etki etmez."),
    AlgorithmGovernance("promethee", "PROMETHEE", "mcdm", "ranking", BENCHMARK_ONLY, False, True, 2, None, False, False, False, False, True, False, "holdout", ["spearman_correlation", "kendall_tau", "top_k_overlap"], "MCDM karşılaştırma algoritmasıdır.", "Sadece benchmark; nihai karara doğrudan etki etmez."),
    AlgorithmGovernance("linear_regression", "Linear Regression", "ml", "regression", ADVISORY_ML, False, True, 50, None, True, True, False, False, True, True, "repeated_k_fold", ["mae", "rmse", "r2", "median_absolute_error"], "Küçük veriyle genelleme zayıf olabilir.", "Destekleyici ML; nihai karar değildir."),
    AlgorithmGovernance("decision_tree", "Decision Tree", "ml", "classification", ADVISORY_ML, False, True, 100, 10, False, True, True, True, True, True, "stratified_k_fold", ["balanced_accuracy", "f1_macro", "f1_weighted", "confusion_matrix"], "Overfitting riski yüksektir.", "Destekleyici ML; nihai karar değildir."),
    AlgorithmGovernance("random_forest", "Random Forest", "ml", "classification", ADVISORY_ML, False, True, 200, 10, False, True, True, True, True, True, "stratified_k_fold", ["balanced_accuracy", "f1_macro", "f1_weighted", "roc_auc"], "Veri azsa güvenilir genelleme beklenmez.", "Destekleyici ML; nihai karar değildir."),
    AlgorithmGovernance("logistic_regression", "Logistic Regression", "ml", "classification", BENCHMARK_ONLY, False, True, 100, 10, True, True, True, True, True, True, "stratified_k_fold", ["balanced_accuracy", "f1_macro", "f1_weighted", "roc_auc", "brier_score"], "Feature scaling ve sınıf dengesi önemlidir.", "Açıklanabilir benchmark baseline; nihai karar değildir."),
    AlgorithmGovernance("naive_bayes", "Naive Bayes", "ml", "classification", BENCHMARK_ONLY, False, True, 100, 10, False, True, True, False, False, True, "stratified_k_fold", ["balanced_accuracy", "f1_macro", "f1_weighted", "brier_score"], "Bağımsızlık varsayımı güçlüdür.", "Hızlı olasılıksal baseline; nihai karar değildir."),
    AlgorithmGovernance("xgboost", "XGBoost", "ml", "classification", BENCHMARK_ONLY, False, False, 500, 20, False, True, True, True, True, True, "stratified_k_fold", ["balanced_accuracy", "f1_macro", "f1_weighted", "roc_auc"], "Küçük veride overfitting riski çok yüksektir.", "Sadece benchmark; minimum veri sağlanmadan çalıştırılmaz."),
    AlgorithmGovernance("gradient_boosting", "GradientBoosting Fallback", "ml", "classification", BENCHMARK_ONLY, False, True, 500, 20, False, True, True, True, True, True, "stratified_k_fold", ["balanced_accuracy", "f1_macro", "f1_weighted"], "XGBoost fallback; küçük veride risklidir.", "Sadece benchmark; nihai karar değildir."),
    AlgorithmGovernance("kmeans", "KMeans", "clustering", "clustering", BENCHMARK_ONLY, False, True, 100, None, True, False, False, False, False, True, "stability_resampling", ["silhouette_score", "davies_bouldin_score", "calinski_harabasz_score", "cluster_size_distribution"], "Keşifsel analizdir.", "Clustering nihai karar üretmez."),
    AlgorithmGovernance("hierarchical_clustering", "Hierarchical Clustering", "clustering", "clustering", BENCHMARK_ONLY, False, True, 50, None, True, False, False, False, False, True, "stability_resampling", ["silhouette_score", "davies_bouldin_score", "cluster_size_distribution"], "Keşifsel analizdir.", "Clustering nihai karar üretmez."),
    AlgorithmGovernance("dbscan", "DBSCAN", "clustering", "clustering", BENCHMARK_ONLY, False, True, 100, None, True, False, False, False, False, True, "eps_sensitivity", ["noise_ratio", "cluster_count", "silhouette_score"], "eps/min_samples duyarlıdır; noise oranı raporlanmalıdır.", "Deneysel/benchmark clustering; nihai karar üretmez."),
    AlgorithmGovernance("random_predictor", "RandomPredictor", "baseline", "classification", BASELINE, False, True, 10, None, False, True, True, False, False, True, "holdout", ["accuracy", "f1_macro"], "Rastgele baseline.", "Baseline karşılaştırma içindir."),
    AlgorithmGovernance("majority_class_predictor", "MajorityClassPredictor", "baseline", "classification", BASELINE, False, True, 10, None, False, True, True, False, False, True, "holdout", ["balanced_accuracy", "f1_macro"], "Majority baseline sınıf dengesizliğinde yanıltıcı olabilir.", "Baseline karşılaştırma içindir."),
    AlgorithmGovernance("popularity_recommender", "PopularityRecommender", "baseline", "ranking", BASELINE, False, True, 10, None, False, False, False, False, True, False, "holdout", ["hit_at_k", "ndcg_at_k", "map_at_k"], "Popülerlik baseline.", "Baseline karşılaştırma içindir."),
    AlgorithmGovernance("dummy_classifier", "DummyClassifier", "baseline", "classification", BASELINE, False, True, 10, None, False, True, True, False, False, True, "holdout", ["balanced_accuracy", "f1_macro"], "Dummy baseline.", "Baseline karşılaştırma içindir."),
    AlgorithmGovernance("dummy_regressor", "DummyRegressor", "baseline", "regression", BASELINE, False, True, 10, None, False, True, False, False, False, True, "holdout", ["mae", "rmse", "r2"], "Dummy regression baseline.", "Baseline karşılaştırma içindir."),
    AlgorithmGovernance("rule_based_baseline", "RuleBasedBaseline", "baseline", "decision_rule", BASELINE, False, True, 1, None, False, False, False, False, True, False, "policy_check", ["rule_coverage", "f1_macro"], "Basit eşik tabanlı karşılaştırma.", "Baseline karşılaştırma içindir."),
    AlgorithmGovernance("gale_shapley", "Gale-Shapley", "allocation", "allocation", BENCHMARK_ONLY, False, True, 1, None, False, False, False, False, True, False, "holdout", ["seat_fill_rate", "average_assigned_rank", "top_3_satisfaction", "envy_score"], "Yerleştirme benchmark algoritması.", "Müfredat karar motoru değildir."),
    AlgorithmGovernance("greedy_allocation", "Greedy Allocation", "allocation", "allocation", BENCHMARK_ONLY, False, True, 1, None, False, False, False, False, True, False, "holdout", ["seat_fill_rate", "average_assigned_rank", "top_3_satisfaction"], "Yerleştirme benchmark algoritması.", "Müfredat karar motoru değildir."),
    AlgorithmGovernance("minimum_regret", "Minimum Regret", "allocation", "allocation", BENCHMARK_ONLY, False, True, 1, None, False, False, False, False, True, False, "holdout", ["seat_fill_rate", "average_assigned_rank", "envy_score"], "Yerleştirme benchmark algoritması.", "Müfredat karar motoru değildir."),
    AlgorithmGovernance("tfidf_cosine", "TF-IDF + Cosine Similarity", "similarity", "similarity", BENCHMARK_ONLY, False, True, 2, None, True, False, False, False, True, False, "holdout", ["top_k_overlap", "coverage"], "Benzerlik/arama katmanıdır.", "Keşifsel benzerlik analizi içindir."),
]


DEFAULT_TASK_MAPPINGS: list[tuple[str, str, str, bool, str]] = [
    ("course_ranking", "ahp", PRODUCTION_DECISION, True, "Ana ağırlıklandırma."),
    ("course_ranking", "topsis", PRODUCTION_DECISION, True, "Ana sıralama motoru."),
    ("course_ranking", "vikor", BENCHMARK_ONLY, False, "MCDM benchmark."),
    ("course_ranking", "promethee", BENCHMARK_ONLY, False, "MCDM benchmark."),
    ("course_status_classification", "decision_tree", ADVISORY_ML, True, "Destekleyici sınıflandırma."),
    ("course_status_classification", "random_forest", ADVISORY_ML, True, "Destekleyici sınıflandırma."),
    ("course_status_classification", "logistic_regression", BENCHMARK_ONLY, False, "Benchmark baseline."),
    ("course_status_classification", "naive_bayes", BENCHMARK_ONLY, False, "Hızlı baseline."),
    ("course_status_classification", "xgboost", BENCHMARK_ONLY, False, "Büyük veri benchmark."),
    ("success_score_regression", "linear_regression", ADVISORY_ML, True, "Destekleyici skor tahmini."),
    ("success_score_regression", "dummy_regressor", BASELINE, False, "Regression baseline."),
    ("demand_prediction", "linear_regression", ADVISORY_ML, True, "Talep tahmini."),
    ("preference_clustering", "kmeans", BENCHMARK_ONLY, True, "Keşifsel kümeleme."),
    ("preference_clustering", "hierarchical_clustering", BENCHMARK_ONLY, False, "Keşifsel kümeleme."),
    ("preference_clustering", "dbscan", BENCHMARK_ONLY, False, "Yoğunluk tabanlı keşif."),
    ("student_course_allocation", "gale_shapley", BENCHMARK_ONLY, True, "Stabil eşleşme."),
    ("student_course_allocation", "greedy_allocation", BENCHMARK_ONLY, False, "Greedy baseline."),
    ("student_course_allocation", "minimum_regret", BENCHMARK_ONLY, False, "Regret minimization."),
    ("course_similarity", "tfidf_cosine", BENCHMARK_ONLY, True, "Metin benzerliği."),
    ("benchmark_comparison", "random_forest", ADVISORY_ML, True, "Benchmark dahil."),
    ("benchmark_comparison", "xgboost", BENCHMARK_ONLY, False, "Benchmark dahil."),
    ("benchmark_comparison", "naive_bayes", BENCHMARK_ONLY, False, "Benchmark dahil."),
]


def seed_default_algorithm_registry(conn: sqlite3.Connection) -> list[dict]:
    ensure_algorithm_governance_schema(conn, commit=False)
    for algo in DEFAULT_ALGORITHMS:
        conn.execute(
            """
            INSERT INTO algorithm_governance_registry (
                algorithm_key, display_name, algorithm_family, task_type, usage_role,
                can_affect_final_decision, default_enabled, minimum_sample_count,
                minimum_samples_per_class, requires_feature_scaling, requires_target,
                supports_probability, supports_feature_importance, supports_explainability,
                supports_cross_validation, recommended_validation_strategy,
                recommended_metrics_json, risk_notes, user_facing_warning, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(algorithm_key) DO UPDATE SET
                display_name=excluded.display_name,
                algorithm_family=excluded.algorithm_family,
                task_type=excluded.task_type,
                usage_role=excluded.usage_role,
                can_affect_final_decision=excluded.can_affect_final_decision,
                minimum_sample_count=excluded.minimum_sample_count,
                minimum_samples_per_class=excluded.minimum_samples_per_class,
                recommended_validation_strategy=excluded.recommended_validation_strategy,
                recommended_metrics_json=excluded.recommended_metrics_json,
                risk_notes=excluded.risk_notes,
                user_facing_warning=excluded.user_facing_warning,
                updated_at=excluded.updated_at
            """,
            (
                algo.algorithm_key,
                algo.display_name,
                algo.algorithm_family,
                algo.task_type,
                algo.usage_role,
                int(algo.can_affect_final_decision),
                int(algo.default_enabled),
                algo.minimum_sample_count,
                algo.minimum_samples_per_class,
                int(algo.requires_feature_scaling),
                int(algo.requires_target),
                int(algo.supports_probability),
                int(algo.supports_feature_importance),
                int(algo.supports_explainability),
                int(algo.supports_cross_validation),
                algo.recommended_validation_strategy,
                _json(algo.recommended_metrics),
                algo.risk_notes,
                algo.user_facing_warning,
                _now(),
                _now(),
            ),
        )
    conn.execute("DELETE FROM algorithm_task_mapping")
    for task_key, algorithm_key, role, recommended, notes in DEFAULT_TASK_MAPPINGS:
        conn.execute(
            """
            INSERT INTO algorithm_task_mapping (task_key, algorithm_key, allowed_usage_role, is_recommended, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_key, algorithm_key, role, int(recommended), notes, _now()),
        )
    return list_algorithm_governance(conn)


def list_algorithm_governance(conn: sqlite3.Connection, usage_role: str | None = None) -> list[dict]:
    ensure_algorithm_governance_schema(conn, commit=False)
    cur = conn.execute("SELECT COUNT(*) FROM algorithm_governance_registry")
    if int(cur.fetchone()[0] or 0) == 0:
        seed_default_algorithm_registry(conn)
    sql = "SELECT * FROM algorithm_governance_registry"
    params: list[Any] = []
    if usage_role:
        sql += " WHERE usage_role=?"
        params.append(usage_role)
    sql += " ORDER BY algorithm_family, usage_role, display_name"
    cur = conn.execute(sql, tuple(params))
    keys = [d[0] for d in cur.description]
    return [_row_to_governance_dict(row, keys) for row in cur.fetchall()]


def get_algorithm_governance(conn: sqlite3.Connection, algorithm_key: str) -> dict:
    ensure_algorithm_governance_schema(conn, commit=False)
    if not algorithm_key:
        raise ValueError("algorithm_key zorunludur")
    list_algorithm_governance(conn)
    key = normalize_algorithm_key(algorithm_key)
    cur = conn.execute("SELECT * FROM algorithm_governance_registry WHERE algorithm_key=? LIMIT 1", (key,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Algoritma registry kaydı bulunamadı: {algorithm_key}")
    return _row_to_governance_dict(row, [d[0] for d in cur.description])


def list_algorithms_by_role(conn: sqlite3.Connection, usage_role: str) -> list[dict]:
    return list_algorithm_governance(conn, usage_role=usage_role)


def can_algorithm_affect_final_decision(conn: sqlite3.Connection, algorithm_key: str) -> bool:
    return bool(get_algorithm_governance(conn, algorithm_key).get("can_affect_final_decision"))


def validate_algorithm_usage(conn: sqlite3.Connection, algorithm_key: str, requested_usage_role: str) -> dict:
    algo = get_algorithm_governance(conn, algorithm_key)
    if requested_usage_role == PRODUCTION_DECISION and not algo.get("can_affect_final_decision"):
        raise BusinessRuleAppError(
            code="ALGORITHM_ROLE_BLOCKED",
            message=f"{algo['display_name']} nihai karar hattında kullanılamaz.",
            details={"algorithm_key": algo["algorithm_key"], "usage_role": algo["usage_role"]},
            suggestion="Bu algoritmayı benchmark veya destekleyici analiz rolünde kullanın.",
        )
    if algo["usage_role"] == BENCHMARK_ONLY and requested_usage_role != BENCHMARK_ONLY:
        raise BusinessRuleAppError(
            code="BENCHMARK_ONLY_ALGORITHM",
            message=f"{algo['display_name']} sadece benchmark amaçlıdır.",
            details={"algorithm_key": algo["algorithm_key"]},
            suggestion="Nihai karar için AHP/TOPSIS + kural motoru + state machine hattını kullanın.",
        )
    return {"ok": True, "algorithm": algo, "requested_usage_role": requested_usage_role}


def update_algorithm_role(
    conn: sqlite3.Connection,
    algorithm_key: str,
    *,
    usage_role: str | None = None,
    can_affect_final_decision: bool | None = None,
    minimum_sample_count: int | None = None,
    user_facing_warning: str | None = None,
) -> dict:
    algo = get_algorithm_governance(conn, algorithm_key)
    conn.execute(
        """
        UPDATE algorithm_governance_registry
        SET usage_role=?,
            can_affect_final_decision=?,
            minimum_sample_count=?,
            user_facing_warning=?,
            updated_at=?
        WHERE algorithm_key=?
        """,
        (
            usage_role or algo["usage_role"],
            int(can_affect_final_decision if can_affect_final_decision is not None else algo["can_affect_final_decision"]),
            int(minimum_sample_count if minimum_sample_count is not None else algo["minimum_sample_count"]),
            user_facing_warning if user_facing_warning is not None else algo.get("user_facing_warning"),
            _now(),
            algo["algorithm_key"],
        ),
    )
    return get_algorithm_governance(conn, algo["algorithm_key"])


def get_user_facing_algorithm_label(conn: sqlite3.Connection, algorithm_key: str) -> str:
    role = get_algorithm_governance(conn, algorithm_key)["usage_role"]
    return {
        PRODUCTION_DECISION: "Ana karar motoru",
        ADVISORY_ML: "Destekleyici ML",
        BENCHMARK_ONLY: "Sadece benchmark",
        EXPERIMENTAL: "Deneysel",
        BASELINE: "Baseline",
    }.get(role, role)


def get_allowed_algorithms_for_task(conn: sqlite3.Connection, task_key: str) -> list[dict]:
    list_algorithm_governance(conn)
    cur = conn.execute(
        """
        SELECT atm.*, agr.display_name, agr.algorithm_family, agr.task_type, agr.usage_role,
               agr.can_affect_final_decision, agr.minimum_sample_count, agr.recommended_metrics_json
        FROM algorithm_task_mapping atm
        JOIN algorithm_governance_registry agr ON agr.algorithm_key = atm.algorithm_key
        WHERE atm.task_key=?
        ORDER BY atm.is_recommended DESC, agr.display_name
        """,
        (task_key,),
    )
    keys = [d[0] for d in cur.description]
    rows = []
    for row in cur.fetchall():
        data = dict(zip(keys, row)) if not isinstance(row, sqlite3.Row) else {key: row[key] for key in row.keys()}
        data["is_recommended"] = bool(data.get("is_recommended"))
        data["can_affect_final_decision"] = bool(data.get("can_affect_final_decision"))
        try:
            data["recommended_metrics"] = json.loads(data.get("recommended_metrics_json") or "[]")
        except Exception:
            data["recommended_metrics"] = []
        rows.append(data)
    return rows


def validate_algorithm_for_task(conn: sqlite3.Connection, algorithm_key: str, task_key: str) -> dict:
    key = normalize_algorithm_key(algorithm_key)
    allowed = get_allowed_algorithms_for_task(conn, task_key)
    match = next((row for row in allowed if row["algorithm_key"] == key), None)
    if not match:
        raise BusinessRuleAppError(
            code="ALGORITHM_TASK_MISMATCH",
            message=f"{algorithm_key} algoritması {task_key} görevi için uygun değildir.",
            details={"algorithm_key": key, "task_key": task_key},
            suggestion="Problem tipine uygun algoritma listesinden seçim yapın.",
        )
    return {"ok": True, "mapping": match}


def get_task_description(task_key: str) -> str:
    return {
        "course_ranking": "Dersleri çok kriterli şekilde sıralama.",
        "course_status_classification": "Ders statüsü için destekleyici sınıflandırma.",
        "success_score_regression": "Başarı veya skor tahmini.",
        "demand_prediction": "Talep tahmini.",
        "preference_clustering": "Tercih örüntülerini keşifsel kümeleme.",
        "student_course_allocation": "Öğrenci-ders yerleştirme.",
        "course_similarity": "Ders metni/etiket benzerliği.",
        "benchmark_comparison": "Algoritma karşılaştırma deneyi.",
    }.get(task_key, "Tanımlı görev açıklaması yok.")


def list_task_mappings(conn: sqlite3.Connection) -> list[dict]:
    list_algorithm_governance(conn)
    cur = conn.execute("SELECT * FROM algorithm_task_mapping ORDER BY task_key, is_recommended DESC, algorithm_key")
    keys = [d[0] for d in cur.description]
    return [{key: row[key] for key in row.keys()} if isinstance(row, sqlite3.Row) else dict(zip(keys, row)) for row in cur.fetchall()]


def normalize_algorithm_key(value: str) -> str:
    key = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "ahpranker": "ahp",
        "topsisranker": "topsis",
        "promethee_ii": "promethee",
        "prometheeii": "promethee",
        "xgboostlike": "xgboost",
        "randomforest": "random_forest",
        "logisticregression": "logistic_regression",
        "naivebayes": "naive_bayes",
        "kmeans": "kmeans",
        "hierarchicalclustering": "hierarchical_clustering",
        "dbscan": "dbscan",
        "majorityclasspredictor": "majority_class_predictor",
        "randompredictor": "random_predictor",
        "popularityrecommender": "popularity_recommender",
        "galeshapley": "gale_shapley",
        "greedyallocation": "greedy_allocation",
        "minimumregretallocation": "minimum_regret",
    }
    return aliases.get(key, key)


def _row_to_governance_dict(row: sqlite3.Row | tuple, keys: list[str]) -> dict:
    data = {key: row[key] for key in row.keys()} if isinstance(row, sqlite3.Row) else dict(zip(keys, row))
    for key in (
        "can_affect_final_decision",
        "default_enabled",
        "requires_feature_scaling",
        "requires_target",
        "supports_probability",
        "supports_feature_importance",
        "supports_explainability",
        "supports_cross_validation",
    ):
        data[key] = bool(data.get(key))
    try:
        data["recommended_metrics"] = json.loads(data.get("recommended_metrics_json") or "[]")
    except Exception:
        data["recommended_metrics"] = []
    return data
