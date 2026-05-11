"""Baseline ML predictors and recommenders."""

from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np
import pandas as pd

from app.algorithms.base import AlgorithmOutput, IPredictor, IRanker


<<<<<<< HEAD
def baseline_algorithm_metadata() -> dict[str, dict[str, str]]:
    return {
        "RandomPredictor": {"algorithm_key": "random_predictor", "usage_role": "benchmark_only", "label": "Sadece benchmark"},
        "MajorityClassPredictor": {"algorithm_key": "majority_class", "usage_role": "benchmark_only", "label": "Sadece benchmark"},
        "PopularityRecommender": {"algorithm_key": "popularity_recommender", "usage_role": "benchmark_only", "label": "Sadece benchmark"},
    }


class RandomPredictor(IPredictor):
    usage_role = "benchmark_only"

=======
class RandomPredictor(IPredictor):
>>>>>>> b9e88394022006b16fd391988c0080a07e411942
    def __init__(self, classes: list[Any] | None = None, random_seed: int = 42) -> None:
        super().__init__(name="RandomPredictor", task_type="prediction", parameters={"random_seed": random_seed})
        self.classes = classes or []
        self.rng = np.random.default_rng(random_seed)

    def fit(self, X: pd.DataFrame, y: pd.Series | np.ndarray | list[Any] | None = None) -> "RandomPredictor":
        if y is not None:
            values = pd.Series(y).dropna().tolist()
            if values:
                self.classes = sorted(set(values))
        if not self.classes:
            raise ValueError("RandomPredictor requires classes from constructor or fit(y).")
        return self

    def predict_proba(self, X: pd.DataFrame) -> list[list[float]]:
        n = len(X)
        m = len(self.classes)
        if m == 0:
            raise ValueError("Model not fitted.")
        probs = np.full((n, m), 1.0 / m, dtype=float)
        return probs.tolist()

    def predict(self, X: pd.DataFrame) -> AlgorithmOutput:
        started = self._start_timer()
        if not self.classes:
            raise ValueError("Model not fitted.")
        preds = self.rng.choice(self.classes, size=len(X), replace=True).tolist()
        return self._build_output(
            started,
            predictions=preds,
            confidence=1.0 / max(len(self.classes), 1),
            explanation=f"Random uniform sampling across classes={self.classes}",
        )

    def recommend(self, X: pd.DataFrame, top_k: int = 5) -> AlgorithmOutput:
        started = self._start_timer()
        if not self.classes:
            raise ValueError("Model not fitted.")
        recs = []
        for idx in range(len(X)):
            sampled = self.rng.choice(self.classes, size=min(top_k, len(self.classes)), replace=False).tolist()
            recs.append({"entity_id": idx, "items": sampled})
        return self._build_output(
            started,
            recommendations=recs,
            confidence=1.0 / max(len(self.classes), 1),
            explanation="Random recommender baseline.",
        )

    def score(self, X: pd.DataFrame, y: pd.Series | None = None) -> float:
        if y is None or len(y) == 0:
            return 0.0
        if not self.classes:
            self.fit(X, y)
        return 1.0 / max(len(self.classes), 1)

    def explain(self, X: pd.DataFrame | None = None) -> str:
        return "RandomPredictor is a baseline with no learned structure."


class MajorityClassPredictor(IPredictor):
<<<<<<< HEAD
    usage_role = "benchmark_only"

=======
>>>>>>> b9e88394022006b16fd391988c0080a07e411942
    def __init__(self) -> None:
        super().__init__(name="MajorityClassPredictor", task_type="prediction")
        self.majority_class: Any | None = None
        self.class_distribution: dict[Any, int] = {}

    def fit(self, X: pd.DataFrame, y: pd.Series | np.ndarray | list[Any] | None = None) -> "MajorityClassPredictor":
        if y is None:
            raise ValueError("MajorityClassPredictor requires target labels in fit().")
        counts = Counter(pd.Series(y).dropna().tolist())
        if not counts:
            raise ValueError("Empty target labels.")
        self.class_distribution = dict(counts)
        self.majority_class = counts.most_common(1)[0][0]
        return self

    def predict_proba(self, X: pd.DataFrame) -> list[list[float]]:
        classes = list(self.class_distribution.keys())
        total = sum(self.class_distribution.values()) or 1
        p = [self.class_distribution[c] / total for c in classes]
        return [p for _ in range(len(X))]

    def predict(self, X: pd.DataFrame) -> AlgorithmOutput:
        started = self._start_timer()
        if self.majority_class is None:
            raise ValueError("Model not fitted.")
        preds = [self.majority_class for _ in range(len(X))]
        confidence = self.class_distribution[self.majority_class] / max(sum(self.class_distribution.values()), 1)
        return self._build_output(
            started,
            predictions=preds,
            confidence=float(confidence),
            explanation=f"Always predicts majority class={self.majority_class}",
            artifacts={"class_distribution": self.class_distribution},
        )

    def recommend(self, X: pd.DataFrame, top_k: int = 5) -> AlgorithmOutput:
        started = self._start_timer()
        classes_by_freq = [k for k, _ in sorted(self.class_distribution.items(), key=lambda t: t[1], reverse=True)]
        recs = [{"entity_id": i, "items": classes_by_freq[:top_k]} for i in range(len(X))]
        return self._build_output(
            started,
            recommendations=recs,
            confidence=1.0,
            explanation="Ranks by class frequency.",
            artifacts={"class_distribution": self.class_distribution},
        )

    def score(self, X: pd.DataFrame, y: pd.Series | None = None) -> float:
        if y is None or self.majority_class is None:
            return 0.0
        y_series = pd.Series(y)
        return float(np.mean(y_series == self.majority_class))

    def explain(self, X: pd.DataFrame | None = None) -> str:
        return f"MajorityClassPredictor learned majority_class={self.majority_class}"


class PopularityRecommender(IRanker):
<<<<<<< HEAD
    usage_role = "benchmark_only"

=======
>>>>>>> b9e88394022006b16fd391988c0080a07e411942
    def __init__(self) -> None:
        super().__init__(name="PopularityRecommender", task_type="ranking")
        self.popularity: dict[Any, float] = {}

    def fit(self, X: pd.DataFrame, y: pd.Series | None = None) -> "PopularityRecommender":
        if y is not None:
            series = pd.Series(y).dropna()
        elif "course_id" in X.columns:
            series = X["course_id"].dropna()
        else:
            raise ValueError("PopularityRecommender requires y or 'course_id' in X.")
        counts = series.value_counts()
        total = float(counts.sum()) or 1.0
        self.popularity = {k: float(v / total) for k, v in counts.items()}
        return self

    def rank(self, X: pd.DataFrame, top_k: int = 5) -> AlgorithmOutput:
        started = self._start_timer()
        if not self.popularity:
            raise ValueError("Model not fitted.")
        top_items = [k for k, _ in sorted(self.popularity.items(), key=lambda t: t[1], reverse=True)[:top_k]]
        recs = [{"entity_id": i, "items": top_items} for i in range(len(X))]
        return self._build_output(
            started,
            recommendations=recs,
            confidence=float(np.mean(list(self.popularity.values()))) if self.popularity else 0.0,
            explanation="Popularity-based ranking using empirical frequency.",
            artifacts={"popularity": self.popularity},
        )

    def predict(self, X: pd.DataFrame) -> AlgorithmOutput:
        return self.rank(X, top_k=1)

    def recommend(self, X: pd.DataFrame, top_k: int = 5) -> AlgorithmOutput:
        return self.rank(X, top_k=top_k)

    def score(self, X: pd.DataFrame, y: pd.Series | None = None) -> float:
        if y is None or not self.popularity:
            return 0.0
        y_series = pd.Series(y)
        scores = y_series.map(self.popularity).fillna(0.0)
        return float(scores.mean())

    def explain(self, X: pd.DataFrame | None = None) -> str:
        return "PopularityRecommender ranks items by observed interaction frequency."
<<<<<<< HEAD
=======

>>>>>>> b9e88394022006b16fd391988c0080a07e411942
