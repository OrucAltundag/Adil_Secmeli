"""Classification metrics."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def classification_metrics(
    y_true: list[Any] | np.ndarray,
    y_pred: list[Any] | np.ndarray,
    y_proba: np.ndarray | None = None,
    *,
    average: str = "weighted",
) -> dict[str, float]:
    y_true_arr = np.asarray(y_true)
    y_pred_arr = np.asarray(y_pred)
    _zd: Any = 0  # sklearn stub yalnız str kabul ediyor; runtime int destekler
    result = {
        "accuracy": float(accuracy_score(y_true_arr, y_pred_arr)),
        "precision": float(precision_score(y_true_arr, y_pred_arr, average=average, zero_division=_zd)),
        "recall": float(recall_score(y_true_arr, y_pred_arr, average=average, zero_division=_zd)),
        "f1": float(f1_score(y_true_arr, y_pred_arr, average=average, zero_division=_zd)),
    }
    if y_proba is not None:
        try:
            if y_proba.ndim == 1 or y_proba.shape[1] == 1:
                result["roc_auc"] = float(roc_auc_score(y_true_arr, y_proba[:, 0] if y_proba.ndim > 1 else y_proba))
            else:
                result["roc_auc"] = float(roc_auc_score(y_true_arr, y_proba, multi_class="ovr", average=average))
        except Exception:
            result["roc_auc"] = 0.0
    else:
        result["roc_auc"] = 0.0
    return result


def top_k_accuracy(
    y_true: list[Any] | np.ndarray,
    ranked_labels: list[list[Any]],
    k: int = 3,
) -> float:
    hits = 0
    total = 0
    for actual, ranking in zip(y_true, ranked_labels):
        if actual in list(ranking)[:k]:
            hits += 1
        total += 1
    return float(hits / max(total, 1))
