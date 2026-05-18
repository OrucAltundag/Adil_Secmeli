from __future__ import annotations

import sqlite3
import tkinter as tk

import pytest

from app.core.errors import BusinessRuleAppError
from app.db.schema_compat import ensure_algorithm_governance_schema
from app.services.algorithm_data_guard_service import check_data_requirements
from app.services.algorithm_governance_service import (
    can_algorithm_affect_final_decision,
    get_algorithm_governance,
    get_allowed_algorithms_for_task,
    seed_default_algorithm_registry,
    validate_algorithm_for_task,
)
from app.services.baseline_benchmark_service import (
    MajorityClassPredictor,
    RuleBasedBaseline,
    compare_with_baseline,
)
from app.services.benchmark_metric_router import calculate_metrics
from app.services.clustering_evaluation_service import evaluate_clustering
from app.services.data_leakage_detector import (
    detect_duplicate_entity_leakage,
    generate_leakage_report,
)
from app.services.governed_benchmark_service import execute_governed_benchmark_run
from app.services.model_diagnostics_service import (
    detect_class_imbalance,
    detect_high_variance_across_folds,
    detect_overfitting,
)
from app.services.statistical_comparison_service import (
    bootstrap_confidence_interval,
    compare_two_models,
)
from app.services.validation_strategy_service import choose_validation_strategy


@pytest.fixture()
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    ensure_algorithm_governance_schema(connection)
    seed_default_algorithm_registry(connection)
    yield connection
    connection.close()


def test_algorithm_governance_registry_roles(conn):
    assert get_algorithm_governance(conn, "ahp")["usage_role"] == "production_decision"
    assert get_algorithm_governance(conn, "topsis")["usage_role"] == "production_decision"
    assert get_algorithm_governance(conn, "xgboost")["usage_role"] == "benchmark_only"
    assert get_algorithm_governance(conn, "naive_bayes")["usage_role"] == "benchmark_only"
    assert get_algorithm_governance(conn, "logistic_regression")["usage_role"] == "benchmark_only"
    assert get_algorithm_governance(conn, "dbscan")["usage_role"] == "benchmark_only"
    assert can_algorithm_affect_final_decision(conn, "xgboost") is False


def test_task_mapping_blocks_wrong_algorithm(conn):
    allowed = get_allowed_algorithms_for_task(conn, "course_ranking")
    assert any(row["algorithm_key"] == "topsis" for row in allowed)
    mapping = validate_algorithm_for_task(conn, "logistic_regression", "course_status_classification")
    assert mapping["mapping"]["allowed_usage_role"] == "benchmark_only"
    with pytest.raises(BusinessRuleAppError):
        validate_algorithm_for_task(conn, "dbscan", "course_status_classification")


def test_data_guard_minimum_samples_and_class_rules(conn):
    X = [[1.0, 2.0] for _ in range(24)]
    y = [0, 1] * 12
    xgb = check_data_requirements(conn, "xgboost", X=X, y=y, task_type="classification")
    assert xgb.allowed_mode in {"blocked", "experimental"}
    assert xgb.allowed_mode != "production_decision"
    rf = check_data_requirements(conn, "random_forest", X=X, y=y, task_type="classification")
    assert rf.allowed_mode != "production_decision"
    one_class = check_data_requirements(conn, "logistic_regression", X=X, y=[1] * 24, task_type="classification")
    assert one_class.allowed_mode == "blocked"
    kmeans = check_data_requirements(conn, "kmeans", X=[[1.0], [2.0]], task_type="clustering", n_clusters=3)
    assert kmeans.allowed_mode == "blocked"


def test_metric_router_classification_regression_clustering_allocation():
    cls = calculate_metrics("classification", y_true=[0, 1, 1, 0], y_pred=[0, 1, 0, 0])
    assert "f1_macro" in cls
    assert "balanced_accuracy" in cls
    reg = calculate_metrics("regression", y_true=[1.0, 2.0, 3.0], y_pred=[1.0, 2.5, 2.0])
    assert {"mae", "rmse", "r2"}.issubset(reg)
    clustering = calculate_metrics("clustering", X=[[0, 0], [0, 1], [5, 5], [5, 6]], clusters=[0, 0, 1, 1])
    assert clustering["cluster_count"] == 2
    allocation = calculate_metrics(
        "allocation",
        allocations=[
            {"assigned_course_id": 1, "preference_rank_received": 1, "department_id": 10},
            {"assigned_course_id": None, "department_id": 20},
        ],
    )
    assert allocation["seat_fill_rate"] == 0.5


def test_validation_strategy_selection():
    strategy = choose_validation_strategy("classification", {"sample_count": 40, "class_distribution": {"0": 20, "1": 20}})
    assert strategy.name == "stratified_k_fold"
    time_strategy = choose_validation_strategy("classification", {"sample_count": 40, "years": [2024, 2025, 2026]})
    assert time_strategy.name == "time_based_split"
    group_strategy = choose_validation_strategy("regression", {"sample_count": 40, "group_key": "course", "group_count": 6})
    assert group_strategy.name == "group_k_fold_by_course"
    small = choose_validation_strategy("classification", {"sample_count": 4, "class_distribution": {"0": 2, "1": 2}})
    assert small.warnings


def test_statistical_comparison_and_ci():
    ci = bootstrap_confidence_interval([0.7, 0.8, 0.75, 0.78], n_bootstrap=100)
    assert ci["lower"] <= ci["mean"] <= ci["upper"]
    comparison = compare_two_models([0.8, 0.82, 0.81], [0.7, 0.72, 0.73])
    assert "summary" in comparison
    assert "effect_size" in comparison


def test_leakage_detector():
    report = generate_leakage_report(feature_names=["topsis_score", "average_grade"], target_name="topsis_score")
    assert report["leakage_detected"] is True
    assert report["leakage_level"] in {"high", "critical"}
    group = detect_duplicate_entity_leakage({"train": [1, 2, 3], "test": [3, 4]})
    assert group["leakage_detected"] is True


def test_model_diagnostics():
    overfit = detect_overfitting({"f1_macro": 0.98}, {"f1_macro": 0.54}, "classification")
    assert overfit["overfitting_warning"] is True
    imbalance = detect_class_imbalance([0] * 95 + [1] * 5)
    assert imbalance["class_imbalance_warning"] is True
    variance = detect_high_variance_across_folds([{"f1_macro": 0.5}, {"f1_macro": 0.9}, {"f1_macro": 0.4}], "f1_macro")
    assert variance["high_variance_warning"] is True


def test_clustering_evaluation_dbscan_noise_and_warnings():
    evaluation = evaluate_clustering([[0, 0], [0, 1], [5, 5], [8, 8]], [0, 0, -1, -1], "dbscan")
    assert evaluation.noise_ratio == 0.5
    one_cluster = evaluate_clustering([[0], [1], [2]], [0, 0, 0], "kmeans")
    assert one_cluster.warnings


def test_baseline_comparison():
    baseline = RuleBasedBaseline()
    assert baseline.predict([80, 55, 20]) == [1, 0, -1]
    predictor = MajorityClassPredictor().fit([[0], [1], [2]], [1, 1, 0])
    assert predictor.predict([[9], [10]]) == [1, 1]
    diff = compare_with_baseline({"f1_macro": 0.7}, {"f1_macro": 0.5}, "f1_macro")
    assert diff["improvement_over_baseline"] > 0


def test_governed_benchmark_run_persists_results(conn):
    result = execute_governed_benchmark_run(
        conn,
        {
            "task_type": "classification",
            "task_key": "course_status_classification",
            "algorithms": ["majority_class_predictor", "logistic_regression"],
            "X": [[1, 2], [2, 3], [3, 4], [4, 5]],
            "y_true": [1, 1, 0, 0],
            "predictions_by_algorithm": {"logistic_regression": [1, 1, 1, 0]},
            "feature_names": ["success_rate", "survey_count"],
            "target_column": "final_status",
        },
    )
    assert result["run_id"] > 0
    metric_count = conn.execute("SELECT COUNT(*) FROM benchmark_metric_results").fetchone()[0]
    assert metric_count >= 2


def test_api_smoke(monkeypatch, tmp_path):
    from app.api import routes
    from app.schemas.algorithm_governance import (
        DataGuardCheckRequest,
        GovernedBenchmarkRunRequest,
    )

    db_path = tmp_path / "api.sqlite"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_algorithm_governance_schema(conn)
    conn.close()
    monkeypatch.setattr(routes, "_get_db_path", lambda: str(db_path))
    governance = routes.algorithms_governance()
    assert governance["success"] is True
    guard = routes.algorithms_data_guard_check(DataGuardCheckRequest(algorithm_key="xgboost", task_type="classification", sample_count=24, feature_count=4, y=[0, 1] * 12))
    assert guard["success"] is True
    run = routes.benchmark_governed_run_execute(
        GovernedBenchmarkRunRequest(
            task_type="classification",
            task_key="course_status_classification",
            algorithms=["majority_class_predictor"],
            X=[[1], [2], [3], [4]],
            y_true=[1, 1, 0, 0],
            feature_names=["success_rate"],
            target_column="status",
        )
    )
    assert run["success"] is True


def test_ui_smoke_import_and_create(monkeypatch):
    from app.ui.benchmark.api_client import ApiResult
    from app.ui.benchmark.pages.algorithm_governance_page import AlgorithmGovernancePage

    class FakeApi:
        def get_algorithm_governance(self):
            return ApiResult(ok=True, data={"success": True, "data": [{"display_name": "AHP", "algorithm_family": "mcdm", "task_type": "ranking", "usage_role": "production_decision", "can_affect_final_decision": True, "minimum_sample_count": 2, "recommended_metrics": ["rank_stability"]}]})

        def get_algorithm_tasks(self):
            return ApiResult(ok=True, data={"success": True, "data": [{"task_key": "course_ranking", "algorithm_key": "topsis", "allowed_usage_role": "production_decision", "is_recommended": True, "notes": "Ana sıralama"}]})

        def get_governed_runs(self):
            return ApiResult(ok=True, data={"success": True, "data": []})

    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk display yok")
    try:
        page = AlgorithmGovernancePage(root, FakeApi())
        assert page.role_tree.get_children()
    finally:
        root.destroy()
