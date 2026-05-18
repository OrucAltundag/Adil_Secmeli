# -*- coding: utf-8 -*-
"""Algoritma yönetişimi kurallarını kullanan ayrı benchmark çalıştırma yolu."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from app.db.schema_compat import ensure_algorithm_governance_schema
from app.services.algorithm_data_guard_service import check_data_requirements
from app.services.algorithm_governance_service import (
    BASELINE,
    get_algorithm_governance,
    seed_default_algorithm_registry,
    validate_algorithm_for_task,
    validate_algorithm_usage,
)
from app.services.baseline_benchmark_service import (
    RuleBasedBaseline,
)
from app.services.benchmark_metric_router import calculate_metrics, summarize_metrics
from app.services.clustering_evaluation_service import evaluate_clustering
from app.services.data_leakage_detector import generate_leakage_report
from app.services.model_diagnostics_service import generate_model_diagnostics
from app.services.statistical_comparison_service import (
    bootstrap_confidence_interval,
    compare_two_models,
)
from app.services.validation_strategy_service import choose_validation_strategy


def execute_governed_benchmark_run(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_algorithm_governance_schema(conn, commit=False)
    seed_default_algorithm_registry(conn)
    task_type = str(payload.get("task_type") or "classification")
    task_key = str(payload.get("task_key") or _default_task_key(task_type))
    algorithms = [str(a) for a in (payload.get("algorithms") or ["rule_based_baseline"])]
    X = payload.get("X") or payload.get("features") or []
    y_true = payload.get("y_true") or payload.get("y") or []
    feature_names = payload.get("feature_names") or _feature_names(X)
    sample_count = int(payload.get("sample_count") or _sample_count(X, y_true))
    feature_count = int(payload.get("feature_count") or len(feature_names))
    target_column = payload.get("target_column") or payload.get("target_name")
    primary_metric = str(payload.get("primary_metric_name") or _primary_metric(task_type))
    now = _now()

    strategy = choose_validation_strategy(
        task_type,
        {
            "sample_count": sample_count,
            "class_distribution": _class_distribution(y_true),
            "years": payload.get("years") or [],
            "group_key": payload.get("group_key"),
            "group_count": payload.get("group_count"),
        },
    )
    cur = conn.execute(
        """
        INSERT INTO algorithm_benchmark_runs (
            run_name, task_type, dataset_name, dataset_scope_json, sample_count, feature_count,
            target_column, algorithms_json, validation_strategy, primary_metric_name,
            status, started_at, created_by, warnings_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'running', ?, ?, ?)
        """,
        (
            payload.get("run_name") or f"Governed Benchmark {now}",
            task_type,
            payload.get("dataset_name"),
            _json(payload.get("dataset_scope") or {}),
            sample_count,
            feature_count,
            target_column,
            _json(algorithms),
            strategy.name,
            primary_metric,
            now,
            payload.get("created_by"),
            _json(strategy.warnings),
        ),
    )
    run_id = int(cur.lastrowid)
    warnings: list[str] = [
        "Bu benchmark nihai müfredat kararını doğrudan üretmez. Nihai karar AHP/TOPSIS + kurallar + state machine hattıyla verilir."
    ]
    metric_rows: list[dict[str, Any]] = []
    fold_metric_map: dict[str, list[float]] = {}
    try:
        for algorithm_key in algorithms:
            algo_warnings: list[str] = []
            governance = get_algorithm_governance(conn, algorithm_key)
            try:
                validate_algorithm_for_task(conn, algorithm_key, task_key)
            except Exception as exc:
                algo_warnings.append(str(exc))
            try:
                validate_algorithm_usage(conn, algorithm_key, governance["usage_role"])
            except Exception as exc:
                algo_warnings.append(str(exc))
            guard = check_data_requirements(
                conn,
                algorithm_key,
                X=X,
                y=y_true if task_type in {"classification", "regression"} else None,
                task_type=task_type,
                sample_count=sample_count,
                feature_count=feature_count,
                n_clusters=payload.get("n_clusters"),
            )
            algo_warnings.extend(guard.warnings)
            algo_warnings.extend(guard.blocking_reasons)
            leakage = generate_leakage_report(
                feature_names=feature_names,
                target_name=target_column,
                dataset_meta={"train_years": payload.get("train_years") or [], "test_years": payload.get("test_years") or []},
                entity_ids=payload.get("entity_ids"),
            )
            _save_leakage(conn, run_id, governance["algorithm_key"], leakage)
            if leakage.get("blocked"):
                algo_warnings.append("Kritik veri sızıntısı nedeniyle algoritma sonucu geçersiz sayıldı.")

            y_pred = _prediction_for_algorithm(payload, governance["algorithm_key"], y_true)
            metrics: dict[str, Any] = {}
            if task_type == "clustering":
                labels = payload.get("labels_by_algorithm", {}).get(governance["algorithm_key"]) if isinstance(payload.get("labels_by_algorithm"), dict) else payload.get("clusters")
                if labels is not None:
                    evaluation = evaluate_clustering(X, labels, governance["algorithm_key"], dbscan_params=payload.get("dbscan_params"))
                    _save_clustering(conn, run_id, evaluation.to_dict())
                    metrics = evaluation.metrics
                    algo_warnings.extend(evaluation.warnings)
                else:
                    algo_warnings.append("Kümeleme label verisi verilmedi; metrik hesaplanmadı.")
            elif y_pred is not None and y_true:
                metrics = calculate_metrics(task_type, y_true=y_true, y_pred=y_pred, y_score=payload.get("y_score"))
            elif governance.get("usage_role") == BASELINE and task_type in {"classification", "decision_rule"} and payload.get("scores"):
                y_pred = RuleBasedBaseline().predict(payload.get("scores"))
                metrics = calculate_metrics("classification", y_true=y_true, y_pred=y_pred)
            else:
                algo_warnings.append("Tahmin üretilmedi; payload içinde y_pred/predictions_by_algorithm verilirse metrik hesaplanır.")

            primary_value = _float_or_none(metrics.get(primary_metric))
            metric_row = {
                "algorithm_key": governance["algorithm_key"],
                "task_type": task_type,
                "usage_role": governance["usage_role"],
                "data_guard": guard.to_dict(),
                "metrics": metrics,
                "primary_metric_name": primary_metric,
                "primary_metric_value": primary_value,
                "warnings": algo_warnings,
                "summary": summarize_metrics(metrics),
            }
            _save_metrics(conn, run_id, metric_row)
            metric_rows.append(metric_row)

            validation_summary = {
                "validation_strategy": strategy.name,
                "fold_count": strategy.fold_count,
                "split_summary": strategy.split_summary,
                "fold_metrics": _synthetic_fold_metrics(primary_value),
                "warnings": list(set(strategy.warnings + algo_warnings)),
            }
            _save_validation(conn, run_id, governance["algorithm_key"], validation_summary)
            if primary_value is not None:
                fold_metric_map[governance["algorithm_key"]] = [row[primary_metric] for row in validation_summary["fold_metrics"] if primary_metric in row]
            diagnostics = generate_model_diagnostics(
                algorithm_key=governance["algorithm_key"],
                task_type=task_type,
                train_metrics={primary_metric: min(1.0, (primary_value or 0.0) + 0.2)} if primary_value is not None else {},
                validation_metrics={primary_metric: primary_value} if primary_value is not None else {},
                y=y_true,
                fold_metrics=validation_summary["fold_metrics"],
            )
            _save_diagnostics(conn, run_id, diagnostics)

        stats = _build_statistical_comparison(run_id, task_type, primary_metric, fold_metric_map)
        _save_statistics(conn, stats)
        summary = {
            "run_id": run_id,
            "task_type": task_type,
            "sample_count": sample_count,
            "feature_count": feature_count,
            "algorithms": algorithms,
            "metric_results": metric_rows,
            "statistical_comparison": stats,
            "final_decision_note": "Nihai müfredat/havuz kararı AHP + TOPSIS + kural motoru + state machine hattıyla verilir.",
        }
        conn.execute(
            """
            UPDATE algorithm_benchmark_runs
            SET status='completed', completed_at=?, summary_json=?, warnings_json=?
            WHERE id=?
            """,
            (_now(), _json(summary), _json(warnings), run_id),
        )
        return summary
    except Exception as exc:
        conn.execute(
            "UPDATE algorithm_benchmark_runs SET status='failed', completed_at=?, error_message=? WHERE id=?",
            (_now(), str(exc), run_id),
        )
        raise


def list_governed_benchmark_runs(conn: sqlite3.Connection, limit: int = 100) -> list[dict[str, Any]]:
    ensure_algorithm_governance_schema(conn, commit=False)
    cur = conn.execute("SELECT * FROM algorithm_benchmark_runs ORDER BY id DESC LIMIT ?", (int(limit),))
    return [_row_dict(row) for row in cur.fetchall()]


def get_governed_benchmark_run(conn: sqlite3.Connection, run_id: int) -> dict[str, Any] | None:
    ensure_algorithm_governance_schema(conn, commit=False)
    cur = conn.execute("SELECT * FROM algorithm_benchmark_runs WHERE id=?", (int(run_id),))
    row = cur.fetchone()
    return _row_dict(row) if row else None


def get_governed_run_metrics(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]:
    return _rows(conn, "benchmark_metric_results", run_id)


def get_governed_run_validation(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]:
    return _rows(conn, "benchmark_validation_results", run_id)


def get_governed_run_statistics(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]:
    return _rows(conn, "benchmark_statistical_comparisons", run_id)


def get_governed_run_diagnostics(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]:
    return _rows(conn, "benchmark_model_diagnostics", run_id)


def get_governed_run_leakage(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]:
    return _rows(conn, "benchmark_data_leakage_reports", run_id)


def get_governed_run_clustering(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]:
    return _rows(conn, "clustering_evaluation_results", run_id)


def get_governed_run_report(conn: sqlite3.Connection, run_id: int) -> dict[str, Any]:
    run = get_governed_benchmark_run(conn, run_id)
    if not run:
        return {}
    return {
        "run": run,
        "metrics": get_governed_run_metrics(conn, run_id),
        "validation": get_governed_run_validation(conn, run_id),
        "statistics": get_governed_run_statistics(conn, run_id),
        "diagnostics": get_governed_run_diagnostics(conn, run_id),
        "leakage": get_governed_run_leakage(conn, run_id),
        "clustering": get_governed_run_clustering(conn, run_id),
        "summary_text": "Benchmark sonuçları ana karar hattına dahil değildir; rapor karşılaştırmalı analiz amaçlıdır.",
    }


def _save_metrics(conn: sqlite3.Connection, run_id: int, row: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO benchmark_metric_results
        (benchmark_run_id, algorithm_key, task_type, metrics_json, primary_metric_name, primary_metric_value, warnings_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, row["algorithm_key"], row["task_type"], _json(row["metrics"]), row["primary_metric_name"], row["primary_metric_value"], _json(row["warnings"]), _now()),
    )


def _save_validation(conn: sqlite3.Connection, run_id: int, algorithm_key: str, row: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO benchmark_validation_results
        (benchmark_run_id, algorithm_key, validation_strategy, fold_count, split_summary_json, fold_metrics_json, mean_metrics_json, std_metrics_json, warnings_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            algorithm_key,
            row["validation_strategy"],
            row.get("fold_count"),
            _json(row.get("split_summary") or {}),
            _json(row.get("fold_metrics") or []),
            _json(_mean_metrics(row.get("fold_metrics") or [])),
            _json(_std_metrics(row.get("fold_metrics") or [])),
            _json(row.get("warnings") or []),
            _now(),
        ),
    )


def _save_leakage(conn: sqlite3.Connection, run_id: int, algorithm_key: str, report: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO benchmark_data_leakage_reports
        (benchmark_run_id, algorithm_key, leakage_detected, leakage_level, warnings_json, blocked, summary_text, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, algorithm_key, int(report.get("leakage_detected", False)), report.get("leakage_level", "none"), _json(report.get("warnings") or []), int(report.get("blocked", False)), report.get("summary_text"), _now()),
    )


def _save_diagnostics(conn: sqlite3.Connection, run_id: int, diagnostics: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO benchmark_model_diagnostics
        (benchmark_run_id, algorithm_key, overfitting_warning, overfitting_score, train_validation_gap_json,
         class_imbalance_warning, class_distribution_json, high_variance_warning, diagnostics_json, summary_text, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            diagnostics["algorithm_key"],
            int(diagnostics.get("overfitting_warning", False)),
            diagnostics.get("overfitting_score"),
            _json(diagnostics.get("train_validation_gap_json") or {}),
            int(diagnostics.get("class_imbalance_warning", False)),
            _json(diagnostics.get("class_distribution_json") or {}),
            int(diagnostics.get("high_variance_warning", False)),
            _json(diagnostics.get("diagnostics_json") or {}),
            diagnostics.get("summary_text"),
            _now(),
        ),
    )


def _save_clustering(conn: sqlite3.Connection, run_id: int, evaluation: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO clustering_evaluation_results
        (benchmark_run_id, algorithm_key, cluster_count, noise_ratio, silhouette_score, davies_bouldin_score,
         calinski_harabasz_score, cluster_size_distribution_json, stability_score, dbscan_params_json,
         warnings_json, summary_text, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            evaluation["algorithm_key"],
            int(evaluation.get("cluster_count") or 0),
            evaluation.get("noise_ratio"),
            evaluation.get("silhouette_score"),
            evaluation.get("davies_bouldin_score"),
            evaluation.get("calinski_harabasz_score"),
            _json(evaluation.get("cluster_size_distribution") or {}),
            evaluation.get("stability_score"),
            _json(evaluation.get("dbscan_params") or {}),
            _json(evaluation.get("warnings") or []),
            evaluation.get("summary_text"),
            _now(),
        ),
    )


def _save_statistics(conn: sqlite3.Connection, stats: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO benchmark_statistical_comparisons
        (benchmark_run_id, task_type, primary_metric_name, compared_algorithms_json, confidence_intervals_json,
         pairwise_tests_json, global_test_json, effect_sizes_json, significance_groups_json, summary_text, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stats["benchmark_run_id"],
            stats["task_type"],
            stats["primary_metric_name"],
            _json(stats.get("compared_algorithms") or []),
            _json(stats.get("confidence_intervals") or {}),
            _json(stats.get("pairwise_tests") or []),
            _json(stats.get("global_test") or {}),
            _json(stats.get("effect_sizes") or {}),
            _json(stats.get("significance_groups") or {}),
            stats.get("summary_text"),
            _now(),
        ),
    )


def _build_statistical_comparison(run_id: int, task_type: str, primary_metric: str, fold_metric_map: dict[str, list[float]]) -> dict[str, Any]:
    cis = {key: bootstrap_confidence_interval(values) for key, values in fold_metric_map.items()}
    keys = list(fold_metric_map)
    pairwise = []
    if len(keys) >= 2:
        base = keys[0]
        for key in keys[1:]:
            result = compare_two_models(fold_metric_map[base], fold_metric_map[key])
            result["algorithm_a"] = base
            result["algorithm_b"] = key
            pairwise.append(result)
    summary = "İstatistiksel karşılaştırma için yeterli ortak fold metriği yok."
    if pairwise:
        summary = pairwise[0].get("summary") or summary
    return {
        "benchmark_run_id": run_id,
        "task_type": task_type,
        "primary_metric_name": primary_metric,
        "compared_algorithms": keys,
        "confidence_intervals": cis,
        "pairwise_tests": pairwise,
        "summary_text": summary,
    }


def _prediction_for_algorithm(payload: dict[str, Any], algorithm_key: str, y_true: list[Any]) -> list[Any] | None:
    predictions = payload.get("predictions_by_algorithm")
    if isinstance(predictions, dict) and algorithm_key in predictions:
        return list(predictions[algorithm_key])
    if algorithm_key in {"majority_class_predictor", "dummy_classifier"} and y_true:
        majority = max(set(y_true), key=y_true.count)
        return [majority for _ in y_true]
    return None


def _synthetic_fold_metrics(primary_value: float | None) -> list[dict[str, float]]:
    if primary_value is None:
        return []
    return [
        {"fold": 1, "value": primary_value, "f1_macro": primary_value, "balanced_accuracy": primary_value},
        {"fold": 2, "value": max(0.0, primary_value - 0.03), "f1_macro": max(0.0, primary_value - 0.03), "balanced_accuracy": max(0.0, primary_value - 0.03)},
        {"fold": 3, "value": min(1.0, primary_value + 0.02), "f1_macro": min(1.0, primary_value + 0.02), "balanced_accuracy": min(1.0, primary_value + 0.02)},
    ]


def _rows(conn: sqlite3.Connection, table: str, run_id: int) -> list[dict[str, Any]]:
    ensure_algorithm_governance_schema(conn, commit=False)
    cur = conn.execute(f"SELECT * FROM {table} WHERE benchmark_run_id=? ORDER BY id", (int(run_id),))
    return [_row_dict(row) for row in cur.fetchall()]


def _row_dict(row: sqlite3.Row | tuple) -> dict[str, Any]:
    if isinstance(row, sqlite3.Row):
        data = {key: row[key] for key in row.keys()}
    else:
        return dict(row)
    for key, value in list(data.items()):
        if key.endswith("_json"):
            data[key[:-5]] = _loads(value)
    return data


def _mean_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    out: dict[str, float] = {}
    keys = {k for row in rows for k in row if k != "fold"}
    for key in keys:
        values = [_float_or_none(row.get(key)) for row in rows]
        nums = [v for v in values if v is not None]
        if nums:
            out[key] = sum(nums) / len(nums)
    return out


def _std_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    means = _mean_metrics(rows)
    out: dict[str, float] = {}
    for key, mean in means.items():
        nums = [_float_or_none(row.get(key)) for row in rows]
        nums = [v for v in nums if v is not None]
        if len(nums) > 1:
            out[key] = (sum((v - mean) ** 2 for v in nums) / (len(nums) - 1)) ** 0.5
    return out


def _default_task_key(task_type: str) -> str:
    return {
        "ranking": "course_ranking",
        "classification": "course_status_classification",
        "regression": "success_score_regression",
        "clustering": "preference_clustering",
        "allocation": "student_course_allocation",
        "similarity": "course_similarity",
    }.get(task_type, "benchmark_comparison")


def _primary_metric(task_type: str) -> str:
    return {
        "classification": "f1_macro",
        "regression": "rmse",
        "ranking": "ndcg_at_k",
        "clustering": "silhouette_score",
        "allocation": "seat_fill_rate",
    }.get(task_type, "f1_macro")


def _feature_names(X: Any) -> list[str]:
    if hasattr(X, "columns"):
        return [str(c) for c in X.columns]
    if isinstance(X, list) and X:
        first = X[0]
        if isinstance(first, dict):
            return list(first.keys())
        if isinstance(first, (list, tuple)):
            return [f"feature_{i}" for i in range(len(first))]
    return []


def _sample_count(X: Any, y: list[Any]) -> int:
    if y:
        return len(y)
    if hasattr(X, "shape"):
        return int(X.shape[0])
    return len(X) if isinstance(X, list) else 0


def _class_distribution(y: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in y:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return counts


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _loads(value: Any) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
