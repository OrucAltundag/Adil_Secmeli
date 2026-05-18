# -*- coding: utf-8 -*-
"""Benchmark baseline algoritmaları ve baseline farkı hesapları."""

from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Sequence


@dataclass(slots=True)
class RuleBasedBaseline:
    curriculum_threshold: float = 70.0
    pool_threshold: float = 50.0

    def predict(self, scores: Iterable[float]) -> list[int]:
        out = []
        for score in scores:
            value = float(score)
            if value >= self.curriculum_threshold:
                out.append(1)
            elif value >= self.pool_threshold:
                out.append(0)
            else:
                out.append(-1)
        return out


class MajorityClassPredictor:
    def __init__(self) -> None:
        self.majority_class: Any = None

    def fit(self, _X: Any, y: Iterable[Any]):
        counts = Counter(y)
        self.majority_class = counts.most_common(1)[0][0] if counts else None
        return self

    def predict(self, X: Sequence[Any]) -> list[Any]:
        return [self.majority_class for _ in range(len(X))]


class RandomPredictor:
    def __init__(self, random_state: int = 42) -> None:
        self.random_state = random_state
        self.classes: list[Any] = []

    def fit(self, _X: Any, y: Iterable[Any]):
        self.classes = list(dict.fromkeys(y))
        return self

    def predict(self, X: Sequence[Any]) -> list[Any]:
        rng = random.Random(self.random_state)
        if not self.classes:
            return [None for _ in range(len(X))]
        return [rng.choice(self.classes) for _ in range(len(X))]


def build_dummy_classifier(strategy: str = "most_frequent", random_state: int = 42):
    try:
        from sklearn.dummy import DummyClassifier

        return DummyClassifier(strategy=strategy, random_state=random_state)
    except Exception:
        return MajorityClassPredictor()


def build_dummy_regressor(strategy: str = "mean"):
    try:
        from sklearn.dummy import DummyRegressor

        return DummyRegressor(strategy=strategy)
    except Exception:
        return None


def compare_with_baseline(model_metrics: dict[str, Any], baseline_metrics: dict[str, Any], primary_metric: str) -> dict[str, Any]:
    model_value = _num(model_metrics.get(primary_metric))
    baseline_value = _num(baseline_metrics.get(primary_metric))
    if model_value is None or baseline_value is None:
        return {
            "primary_metric": primary_metric,
            "improvement_over_baseline": None,
            "summary_text": "Baseline farkı hesaplanamadı; metrik eksik.",
        }
    improvement = model_value - baseline_value
    return {
        "primary_metric": primary_metric,
        "model_metric": model_value,
        "baseline_metric": baseline_value,
        "improvement_over_baseline": improvement,
        "relative_improvement": improvement / abs(baseline_value) if baseline_value else None,
        "summary_text": (
            f"Model {primary_metric} metriğinde baseline'dan {improvement:.3f} daha iyi."
            if improvement > 0
            else f"Model {primary_metric} metriğinde baseline'ı anlamlı biçimde geçemedi."
        ),
    }


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None
