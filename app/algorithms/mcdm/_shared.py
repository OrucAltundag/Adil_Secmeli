"""Shared helpers for MCDM rankers."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


def get_criteria_columns(X: pd.DataFrame, *, excluded: Iterable[str] = ("item_id",)) -> list[str]:
    excluded_set = set(excluded)
    criteria_cols: list[str] = []
    for column in X.columns:
        if column in excluded_set:
            continue
        numeric_values = pd.to_numeric(X[column], errors="coerce")
        if numeric_values.notna().any():
            criteria_cols.append(column)
    return criteria_cols


def normalize_weights(weights: np.ndarray | list[float] | None, criteria_count: int, *, algorithm_name: str) -> np.ndarray:
    if criteria_count <= 0:
        raise ValueError(f"{algorithm_name} icin sayisal kriter bulunamadi.")
    if weights is None:
        return np.ones(criteria_count, dtype=float) / float(criteria_count)
    resolved = np.asarray(weights, dtype=float).reshape(-1)
    ensure_weight_count(resolved, criteria_count, algorithm_name=algorithm_name)
    if not np.all(np.isfinite(resolved)):
        raise ValueError(f"{algorithm_name} weights must be finite numbers.")
    total = float(np.sum(resolved))
    if abs(total) <= 1e-10:
        raise ValueError(f"{algorithm_name} weights must not sum to zero.")
    return resolved / total


def ensure_weight_count(weights: np.ndarray, criteria_count: int, *, algorithm_name: str) -> None:
    if len(weights) != criteria_count:
        raise ValueError(
            f"Weight length mismatch for {algorithm_name}: expected {criteria_count}, got {len(weights)}"
        )
