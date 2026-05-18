# -*- coding: utf-8 -*-
"""Benchmark görev tipine göre doğru metrikleri seçen ve hesaplayan servis."""

from __future__ import annotations

import math
from typing import Any, Sequence


def get_metrics_for_task(task_type: str) -> list[str]:
    mapping = {
        "classification": [
            "accuracy",
            "precision_macro",
            "precision_weighted",
            "recall_macro",
            "recall_weighted",
            "f1_macro",
            "f1_weighted",
            "balanced_accuracy",
            "confusion_matrix",
            "roc_auc",
            "pr_auc",
            "log_loss",
            "brier_score",
        ],
        "regression": ["mae", "rmse", "r2", "median_absolute_error", "mape_safe", "residual_mean", "residual_std"],
        "ranking": ["hit_at_k", "ndcg_at_k", "map_at_k", "recall_at_k", "precision_at_k", "coverage", "diversity", "novelty"],
        "clustering": ["silhouette_score", "davies_bouldin_score", "calinski_harabasz_score", "cluster_count", "cluster_size_distribution", "noise_ratio"],
        "allocation": ["seat_fill_rate", "average_assigned_rank", "top_1_satisfaction", "top_3_satisfaction", "envy_score", "unassigned_rate", "capacity_violation_count", "fairness_by_department"],
        "mcdm": ["spearman_correlation", "kendall_tau", "top_k_overlap", "rank_stability", "sensitivity_score", "ahp_consistency_ratio"],
        "decision_rule": ["rule_coverage", "confusion_matrix", "f1_macro"],
        "similarity": ["top_k_overlap", "coverage", "diversity"],
    }
    return list(mapping.get(str(task_type or "").lower(), []))


def calculate_metrics(
    task_type: str,
    *,
    y_true: Sequence[Any] | None = None,
    y_pred: Sequence[Any] | None = None,
    y_score: Sequence[Any] | None = None,
    rankings: Sequence[Sequence[Any]] | None = None,
    relevant_items: Sequence[set[Any] | list[Any]] | None = None,
    clusters: Sequence[int] | None = None,
    X: Any = None,
    allocations: Sequence[dict[str, Any]] | None = None,
    k: int = 10,
) -> dict[str, Any]:
    task = str(task_type or "").lower()
    warnings: list[str] = []
    metrics: dict[str, Any] = {}
    if task == "classification":
        metrics.update(_classification_metrics(y_true, y_pred, y_score, warnings))
    elif task == "regression":
        metrics.update(_regression_metrics(y_true, y_pred, warnings))
    elif task in {"ranking", "similarity", "mcdm"}:
        metrics.update(_ranking_metrics(rankings or [], relevant_items or [], k=k))
    elif task == "clustering":
        from app.services.clustering_evaluation_service import evaluate_clustering

        metrics.update(evaluate_clustering(X, clusters or [], "clustering").metrics)
    elif task == "allocation":
        metrics.update(_allocation_metrics(allocations or []))
    elif task == "decision_rule":
        metrics.update(_classification_metrics(y_true, y_pred, y_score, warnings))
    else:
        warnings.append(f"{task_type} için metrik yönlendirmesi tanımlı değil.")
    if warnings:
        metrics["warnings"] = warnings
    return metrics


def validate_metric_inputs(task_type: str, data: dict[str, Any]) -> dict[str, Any]:
    task = str(task_type or "").lower()
    warnings: list[str] = []
    ok = True
    if task in {"classification", "regression", "decision_rule"} and (data.get("y_true") is None or data.get("y_pred") is None):
        ok = False
        warnings.append("Bu görev tipi için y_true ve y_pred gereklidir.")
    if task == "clustering" and data.get("clusters") is None:
        ok = False
        warnings.append("Kümeleme metrikleri için cluster label gereklidir.")
    if task == "allocation" and data.get("allocations") is None:
        ok = False
        warnings.append("Yerleştirme metrikleri için allocation kayıtları gereklidir.")
    return {"is_valid": ok, "warnings": warnings}


def summarize_metrics(metrics: dict[str, Any]) -> str:
    if not metrics:
        return "Metrik hesaplanamadı."
    if "f1_macro" in metrics:
        return f"Sınıflandırma özeti: macro F1={metrics.get('f1_macro'):.3f}, balanced accuracy={metrics.get('balanced_accuracy', 0):.3f}."
    if "rmse" in metrics:
        return f"Regresyon özeti: MAE={metrics.get('mae'):.3f}, RMSE={metrics.get('rmse'):.3f}, R2={metrics.get('r2'):.3f}."
    if "silhouette_score" in metrics:
        return f"Kümeleme özeti: küme sayısı={metrics.get('cluster_count')}, silhouette={metrics.get('silhouette_score')}."
    if "seat_fill_rate" in metrics:
        return f"Yerleştirme özeti: doluluk={metrics.get('seat_fill_rate'):.3f}, atanmayan={metrics.get('unassigned_rate'):.3f}."
    return "Metrikler hesaplandı; görev tipine göre raporlanmalıdır."


def _classification_metrics(y_true: Sequence[Any] | None, y_pred: Sequence[Any] | None, y_score: Sequence[Any] | None, warnings: list[str]) -> dict[str, Any]:
    if y_true is None or y_pred is None:
        warnings.append("Classification metrikleri için y_true/y_pred eksik.")
        return {}
    yt = list(y_true)
    yp = list(y_pred)
    if not yt or len(yt) != len(yp):
        warnings.append("Classification metrikleri için hedef ve tahmin uzunlukları uyumsuz.")
        return {}
    try:
        from sklearn.metrics import (
            accuracy_score,
            auc,
            balanced_accuracy_score,
            brier_score_loss,
            confusion_matrix,
            f1_score,
            log_loss,
            precision_recall_curve,
            precision_score,
            recall_score,
            roc_auc_score,
        )

        metrics = {
            "accuracy": float(accuracy_score(yt, yp)),
            "precision_macro": float(precision_score(yt, yp, average="macro", zero_division=0)),
            "precision_weighted": float(precision_score(yt, yp, average="weighted", zero_division=0)),
            "recall_macro": float(recall_score(yt, yp, average="macro", zero_division=0)),
            "recall_weighted": float(recall_score(yt, yp, average="weighted", zero_division=0)),
            "f1_macro": float(f1_score(yt, yp, average="macro", zero_division=0)),
            "f1_weighted": float(f1_score(yt, yp, average="weighted", zero_division=0)),
            "balanced_accuracy": float(balanced_accuracy_score(yt, yp)),
            "confusion_matrix": confusion_matrix(yt, yp).tolist(),
        }
        unique = sorted(set(yt))
        if y_score is not None and len(unique) == 2:
            scores = _binary_scores(y_score)
            if scores and len(scores) == len(yt):
                metrics["roc_auc"] = float(roc_auc_score(yt, scores))
                p, r, _ = precision_recall_curve(yt, scores, pos_label=unique[-1])
                metrics["pr_auc"] = float(auc(r, p))
                metrics["brier_score"] = float(brier_score_loss([1 if v == unique[-1] else 0 for v in yt], scores))
                try:
                    metrics["log_loss"] = float(log_loss(yt, [[1 - s, s] for s in scores], labels=unique))
                except Exception as exc:
                    warnings.append(f"Log-loss hesaplanamadı: {exc}")
        return metrics
    except Exception as exc:
        warnings.append(f"Classification metrikleri hesaplanamadı: {exc}")
        return _basic_classification_metrics(yt, yp)


def _regression_metrics(y_true: Sequence[Any] | None, y_pred: Sequence[Any] | None, warnings: list[str]) -> dict[str, Any]:
    if y_true is None or y_pred is None:
        warnings.append("Regression metrikleri için y_true/y_pred eksik.")
        return {}
    yt = [float(v) for v in y_true]
    yp = [float(v) for v in y_pred]
    if not yt or len(yt) != len(yp):
        warnings.append("Regression hedef ve tahmin uzunlukları uyumsuz.")
        return {}
    residuals = [a - b for a, b in zip(yt, yp)]
    try:
        from sklearn.metrics import (
            mean_absolute_error,
            mean_squared_error,
            median_absolute_error,
            r2_score,
        )

        rmse = math.sqrt(float(mean_squared_error(yt, yp)))
        mae = float(mean_absolute_error(yt, yp))
        medae = float(median_absolute_error(yt, yp))
        r2 = float(r2_score(yt, yp)) if len(yt) > 1 else 0.0
    except Exception:
        mae = sum(abs(x) for x in residuals) / len(residuals)
        rmse = math.sqrt(sum(x * x for x in residuals) / len(residuals))
        medae = sorted(abs(x) for x in residuals)[len(residuals) // 2]
        r2 = 0.0
    mape_values = [abs((a - b) / a) for a, b in zip(yt, yp) if a != 0]
    return {
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "median_absolute_error": medae,
        "mape_safe": float(sum(mape_values) / len(mape_values)) if mape_values else None,
        "residual_mean": float(sum(residuals) / len(residuals)),
        "residual_std": _std(residuals),
    }


def _ranking_metrics(rankings: Sequence[Sequence[Any]], relevant_items: Sequence[set[Any] | list[Any]], *, k: int) -> dict[str, Any]:
    if not rankings:
        return {"warnings": ["Ranking metrikleri için sıralama verisi yok."]}
    hit = precision = recall = ndcg = ap = 0.0
    total = len(rankings)
    all_items = set()
    for ranking, relevant in zip(rankings, relevant_items or [set()] * total):
        top = list(ranking)[:k]
        rel = set(relevant)
        all_items.update(top)
        hits = [1 if item in rel else 0 for item in top]
        hit += 1.0 if any(hits) else 0.0
        precision += sum(hits) / max(1, len(top))
        recall += sum(hits) / max(1, len(rel))
        dcg = sum(val / math.log2(idx + 2) for idx, val in enumerate(hits))
        ideal = sum(1 / math.log2(idx + 2) for idx in range(min(len(rel), k)))
        ndcg += dcg / ideal if ideal else 0.0
        running_hits = 0
        precisions = []
        for idx, val in enumerate(hits, start=1):
            if val:
                running_hits += 1
                precisions.append(running_hits / idx)
        ap += sum(precisions) / max(1, min(len(rel), k))
    return {
        "hit_at_k": hit / total,
        "precision_at_k": precision / total,
        "recall_at_k": recall / total,
        "ndcg_at_k": ndcg / total,
        "map_at_k": ap / total,
        "coverage": len(all_items),
        "diversity": len(all_items) / max(1, sum(len(r) for r in rankings)),
    }


def _allocation_metrics(allocations: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not allocations:
        return {"warnings": ["Yerleştirme metrikleri için allocation verisi yok."]}
    assigned = [row for row in allocations if row.get("assigned_course") or row.get("assigned_course_id")]
    ranks = [float(row.get("preference_rank_received") or row.get("rank") or 0) for row in assigned if row.get("preference_rank_received") or row.get("rank")]
    capacity_violations = sum(1 for row in allocations if row.get("capacity_violation"))
    top1 = sum(1 for r in ranks if r <= 1) / max(1, len(ranks))
    top3 = sum(1 for r in ranks if r <= 3) / max(1, len(ranks))
    departments: dict[str, int] = {}
    for row in assigned:
        dept = str(row.get("department_id") or row.get("department") or "unknown")
        departments[dept] = departments.get(dept, 0) + 1
    return {
        "seat_fill_rate": len(assigned) / max(1, len(allocations)),
        "average_assigned_rank": sum(ranks) / max(1, len(ranks)) if ranks else None,
        "top_1_satisfaction": top1,
        "top_3_satisfaction": top3,
        "envy_score": float(sum(abs(r - 1) for r in ranks) / max(1, len(ranks))) if ranks else None,
        "unassigned_rate": (len(allocations) - len(assigned)) / max(1, len(allocations)),
        "capacity_violation_count": capacity_violations,
        "fairness_by_department": departments,
    }


def _basic_classification_metrics(y_true: list[Any], y_pred: list[Any]) -> dict[str, Any]:
    correct = sum(1 for a, b in zip(y_true, y_pred) if a == b)
    return {"accuracy": correct / max(1, len(y_true))}


def _binary_scores(y_score: Sequence[Any]) -> list[float]:
    values = []
    for item in y_score:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            values.append(float(item[-1]))
        else:
            values.append(float(item))
    return values


def _std(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return float(math.sqrt(sum((x - mean) ** 2 for x in values) / len(values)))
