"""Academic-consistency metrics."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def ranking_similarity_with_ground_truth(
    predicted_ranking: list[Any],
    ground_truth_ranking: list[Any],
) -> float:
    """Computes Spearman rank correlation between predicted and known ranking."""
    if not predicted_ranking or not ground_truth_ranking:
        return 0.0
    common_items = [item for item in predicted_ranking if item in set(ground_truth_ranking)]
    if len(common_items) < 2:
        return 0.0
    pred_pos = {item: idx for idx, item in enumerate(predicted_ranking)}
    gt_pos = {item: idx for idx, item in enumerate(ground_truth_ranking)}
    pred_vals = [pred_pos[item] for item in common_items]
    gt_vals = [gt_pos[item] for item in common_items]
    pred_arr = np.asarray(pred_vals, dtype=float)
    gt_arr = np.asarray(gt_vals, dtype=float)
    if pred_arr.size < 2 or np.std(pred_arr) == 0 or np.std(gt_arr) == 0:
        return 0.0
    corr = np.corrcoef(pred_arr, gt_arr)[0, 1]
    if np.isnan(corr):
        return 0.0
    return float(corr)


def pattern_reproduction_score(observed: pd.DataFrame, expected_patterns: dict[str, dict[str, Any]]) -> float:
    """
    Generic pattern-matching metric.
    expected_patterns example:
      {
        "eem_physics_interest": {"group_col": "department", "group_value": "EEM", "metric_col": "physics_interest", "min": 0.6}
      }
    """
    if observed.empty or not expected_patterns:
        return 0.0
    scores = []
    for _, rule in expected_patterns.items():
        group_col = rule["group_col"]
        group_value = rule["group_value"]
        metric_col = rule["metric_col"]
        min_threshold = float(rule.get("min", 0.0))
        max_threshold = float(rule.get("max", 1.0))
        subset = observed[observed[group_col] == group_value]
        if subset.empty or metric_col not in subset.columns:
            scores.append(0.0)
            continue
        mean_val = float(pd.to_numeric(subset[metric_col], errors="coerce").fillna(0.0).mean())
        if mean_val < min_threshold:
            scores.append(max(mean_val / max(min_threshold, 1e-9), 0.0))
        elif mean_val > max_threshold:
            scores.append(max(max_threshold / max(mean_val, 1e-9), 0.0))
        else:
            scores.append(1.0)
    return float(np.mean(scores)) if scores else 0.0
