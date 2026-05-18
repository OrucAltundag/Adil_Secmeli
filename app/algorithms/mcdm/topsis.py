"""TOPSIS ranker for multi-criteria recommendation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.algorithms.base import AlgorithmOutput, IRanker
from app.algorithms.mcdm._shared import (
    ensure_weight_count,
    get_criteria_columns,
    normalize_weights,
)


class TOPSISRanker(IRanker):
    def __init__(self, weights: list[float] | None = None) -> None:
        super().__init__(name="TOPSIS", task_type="ranking")
        self.weights = np.array(weights, dtype=float) if weights is not None else None
        self._is_fitted = False

    def _validate_weights(self, n_criteria: int) -> None:
        """Validate weights array against criteria count."""
        if self.weights is None:
            return
        if len(self.weights) != n_criteria:
            raise ValueError(
                f"Weight length mismatch: expected {n_criteria} criteria but got {len(self.weights)} weights"
            )
        if np.any(np.isnan(self.weights)) or np.any(np.isinf(self.weights)):
            raise ValueError("Weights contain NaN or infinity values")
        if np.all(self.weights == 0):
            raise ValueError("Weights cannot be all zeros")

    def fit(self, X: pd.DataFrame, y: None = None) -> "TOPSISRanker":
<<<<<<< HEAD
        criteria_cols = get_criteria_columns(X)
        self.weights = normalize_weights(self.weights, len(criteria_cols), algorithm_name="TOPSIS")
=======
        criteria_cols = [c for c in X.columns if c != "item_id"]
        n_criteria = len(criteria_cols)
        
        if self.weights is None:
            self.weights = np.ones(n_criteria, dtype=float) / max(n_criteria, 1)
        else:
            self._validate_weights(n_criteria)
            total = float(np.sum(self.weights)) or 1.0
            self.weights = self.weights / total
        
>>>>>>> f064caebbf2bfd6fac014f86504bd92f9d64e647
        self.parameters["weights"] = self.weights.tolist()
        self._is_fitted = True
        return self

    def _rank(self, X: pd.DataFrame, top_k: int) -> AlgorithmOutput:
        started = self._start_timer()
        if not self._is_fitted or self.weights is None:
            self.fit(X)
        assert self.weights is not None and self._is_fitted

        df = X.copy()
        criteria_cols = get_criteria_columns(df)
        ensure_weight_count(self.weights, len(criteria_cols), algorithm_name="TOPSIS")
        matrix = df[criteria_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).to_numpy(dtype=float)

        norm = np.sqrt(np.sum(np.square(matrix), axis=0))
        norm = np.where(norm <= 1e-10, 1.0, norm)
        normalized = matrix / norm
        weighted = normalized * self.weights

        ideal_best = np.max(weighted, axis=0)
        ideal_worst = np.min(weighted, axis=0)
        dist_best = np.sqrt(np.sum(np.square(weighted - ideal_best), axis=1))
        dist_worst = np.sqrt(np.sum(np.square(weighted - ideal_worst), axis=1))
        closeness = dist_worst / np.where((dist_best + dist_worst) <= 1e-10, 1.0, dist_best + dist_worst)

        df["topsis_score"] = closeness
        ranked = df.sort_values("topsis_score", ascending=False).head(top_k)
        recommendations = [
            {
                "item_id": int(row["item_id"]) if "item_id" in row and pd.notna(row["item_id"]) else str(idx),
                "score": float(row["topsis_score"]),
                "rank": rank + 1,
            }
            for rank, (idx, row) in enumerate(ranked.iterrows())
        ]
        return self._build_output(
            started,
            recommendations=recommendations,
            confidence=float(np.mean(closeness)) if len(closeness) else 0.0,
            explanation=f"TOPSIS with weights={self.weights.round(4).tolist()}",
            artifacts={
                "ideal_best": ideal_best.tolist(),
                "ideal_worst": ideal_worst.tolist(),
                "scores": closeness.tolist(),
            },
        )

    def rank(self, X: pd.DataFrame, top_k: int = 5) -> AlgorithmOutput:
        return self._rank(X, top_k=top_k)

    def predict(self, X: pd.DataFrame) -> AlgorithmOutput:
        return self._rank(X, top_k=len(X))

    def recommend(self, X: pd.DataFrame, top_k: int = 5) -> AlgorithmOutput:
        return self._rank(X, top_k=top_k)

    def score(self, X: pd.DataFrame, y: pd.Series | None = None) -> float:
        output = self._rank(X, top_k=len(X))
        return float(np.mean([r["score"] for r in output.recommendations])) if output.recommendations else 0.0

    def explain(self, X: pd.DataFrame | None = None) -> str:
        return f"TOPSIS ranks alternatives by closeness to ideal best/worst using weights={self.weights}"
