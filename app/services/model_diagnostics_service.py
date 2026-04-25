# -*- coding: utf-8 -*-
"""Overfitting, class imbalance ve fold varyansı diagnostics servisi."""

from __future__ import annotations

import math
from typing import Any, Iterable


def detect_overfitting(train_metrics: dict[str, float], validation_metrics: dict[str, float], task_type: str) -> dict[str, Any]:
    primary = _primary_metric(task_type, train_metrics, validation_metrics)
    if not primary:
        return {"overfitting_warning": False, "summary": "Overfitting için karşılaştırılabilir metrik yok."}
    train = float(train_metrics.get(primary) or 0.0)
    valid = float(validation_metrics.get(primary) or 0.0)
    gap = train - valid
    warning = gap > (0.15 if task_type != "regression" else 10.0)
    return {
        "overfitting_warning": warning,
        "overfitting_score": max(0.0, gap),
        "train_validation_gap_json": {primary: gap, "train": train, "validation": valid},
        "summary": (
            f"Eğitim ve doğrulama {primary} farkı {gap:.3f}; model eğitim verisini ezberliyor olabilir."
            if warning
            else f"Eğitim/doğrulama {primary} farkı kabul edilebilir düzeydedir."
        ),
    }


def detect_class_imbalance(y: Iterable[Any], threshold: float = 0.2) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for value in y:
        counts[str(value)] = counts.get(str(value), 0) + 1
    if len(counts) < 2:
        return {"class_imbalance_warning": True, "class_distribution": counts, "summary": "Tek sınıf veya yetersiz sınıf çeşitliliği var."}
    total = sum(counts.values())
    min_ratio = min(counts.values()) / max(1, total)
    warning = min_ratio < threshold
    return {
        "class_imbalance_warning": warning,
        "class_distribution": counts,
        "summary": "Sınıf dengesizliği var; macro F1 ve balanced accuracy öne çıkarılmalıdır." if warning else "Sınıf dağılımı kritik dengesiz görünmüyor.",
    }


def detect_high_variance_across_folds(fold_metrics: list[dict[str, Any]], metric_name: str | None = None, threshold: float = 0.10) -> dict[str, Any]:
    if not fold_metrics:
        return {"high_variance_warning": False, "summary": "Fold metriği yok."}
    key = metric_name or next((k for k in fold_metrics[0] if k != "fold"), None)
    if not key:
        return {"high_variance_warning": False, "summary": "Fold metriği seçilemedi."}
    values = [float(row[key]) for row in fold_metrics if row.get(key) is not None]
    if len(values) < 2:
        return {"high_variance_warning": False, "summary": "Fold varyansı için veri yetersiz."}
    std = _std(values)
    warning = std > threshold
    return {
        "high_variance_warning": warning,
        "fold_metric": key,
        "fold_std": std,
        "summary": "Fold sonuçları yüksek varyans gösteriyor; model kararsız olabilir." if warning else "Fold varyansı kabul edilebilir düzeydedir.",
    }


def generate_model_diagnostics(
    *,
    algorithm_key: str,
    task_type: str,
    train_metrics: dict[str, float] | None = None,
    validation_metrics: dict[str, float] | None = None,
    y: Iterable[Any] | None = None,
    fold_metrics: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    overfit = detect_overfitting(train_metrics or {}, validation_metrics or {}, task_type)
    imbalance = detect_class_imbalance(y or []) if task_type == "classification" else {"class_imbalance_warning": False, "class_distribution": None, "summary": "Sınıf dengesi bu görev tipi için uygulanmadı."}
    variance = detect_high_variance_across_folds(fold_metrics or [])
    warnings = []
    if overfit.get("overfitting_warning"):
        warnings.append(overfit["summary"])
    if imbalance.get("class_imbalance_warning"):
        warnings.append(imbalance["summary"])
    if variance.get("high_variance_warning"):
        warnings.append(variance["summary"])
    return {
        "algorithm_key": algorithm_key,
        "overfitting_warning": bool(overfit.get("overfitting_warning")),
        "overfitting_score": overfit.get("overfitting_score"),
        "train_validation_gap_json": overfit.get("train_validation_gap_json"),
        "class_imbalance_warning": bool(imbalance.get("class_imbalance_warning")),
        "class_distribution_json": imbalance.get("class_distribution"),
        "high_variance_warning": bool(variance.get("high_variance_warning")),
        "diagnostics_json": {"overfitting": overfit, "class_imbalance": imbalance, "fold_variance": variance, "warnings": warnings},
        "summary_text": " ".join(warnings) if warnings else "Model diagnostics kritik uyarı üretmedi.",
    }


def _primary_metric(task_type: str, train: dict[str, Any], valid: dict[str, Any]) -> str | None:
    for key in ("f1_macro", "balanced_accuracy", "accuracy", "r2", "mae"):
        if key in train and key in valid:
            return key
    return None


def _std(values: list[float]) -> float:
    mean = sum(values) / len(values)
    return float(math.sqrt(sum((x - mean) ** 2 for x in values) / max(1, len(values) - 1)))
