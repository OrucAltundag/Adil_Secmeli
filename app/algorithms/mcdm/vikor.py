"""VIKOR compromise ranking algorithm."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.algorithms.base import AlgorithmOutput, IRanker


class VIKORRanker(IRanker):
    def __init__(self, weights: list[float] | None = None, v: float = 0.5) -> None:
        super().__init__(name="VIKOR", task_type="ranking", parameters={"v": v})
        self.weights = np.array(weights, dtype=float) if weights is not None else None
        self.v = float(v)
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

    def fit(self, X: pd.DataFrame, y: None = None) -> "VIKORRanker":
        criteria_cols = [c for c in X.columns if c != "item_id"]
        n_criteria = len(criteria_cols)
        
        if self.weights is None:
            self.weights = np.ones(n_criteria, dtype=float) / max(n_criteria, 1)
        else:
            self._validate_weights(n_criteria)
            total = float(np.sum(self.weights)) or 1.0
            self.weights = self.weights / total
        
        self.parameters["weights"] = self.weights.tolist()
        self._is_fitted = True
        return self

    def _rank(self, X: pd.DataFrame, top_k: int) -> AlgorithmOutput:
        started = self._start_timer()
        if not self._is_fitted or self.weights is None:
            self.fit(X)
        assert self.weights is not None and self._is_fitted

        df = X.copy()
        criteria_cols = [c for c in df.columns if c != "item_id"]
        matrix = df[criteria_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).to_numpy(dtype=float)
        f_star = np.max(matrix, axis=0)
        f_minus = np.min(matrix, axis=0)
        denom = np.where((f_star - f_minus) <= 1e-10, 1.0, f_star - f_minus)
        normalized_gap = (f_star - matrix) / denom
        weighted_gap = normalized_gap * self.weights

        s_values = np.sum(weighted_gap, axis=1)
        r_values = np.max(weighted_gap, axis=1)
        s_min, s_max = np.min(s_values), np.max(s_values)
        r_min, r_max = np.min(r_values), np.max(r_values)
        s_denom = (s_max - s_min) if (s_max - s_min) > 1e-10 else 1.0
        r_denom = (r_max - r_min) if (r_max - r_min) > 1e-10 else 1.0

        q_values = self.v * ((s_values - s_min) / s_denom) + (1 - self.v) * ((r_values - r_min) / r_denom)

        df["vikor_q"] = q_values
        ranked = df.sort_values("vikor_q", ascending=True).head(top_k)
        recommendations = [
            {
                "item_id": int(row["item_id"]) if "item_id" in row and pd.notna(row["item_id"]) else str(idx),
                "score": float(1.0 - row["vikor_q"]),
                "rank": rank + 1,
            }
            for rank, (idx, row) in enumerate(ranked.iterrows())
        ]
        return self._build_output(
            started,
            recommendations=recommendations,
            confidence=float(np.clip(1.0 - np.mean(q_values), 0.0, 1.0)),
            explanation=f"VIKOR compromise ranking with v={self.v}",
            artifacts={"q_values": q_values.tolist(), "s_values": s_values.tolist(), "r_values": r_values.tolist()},
        )

    def rank(self, X: pd.DataFrame, top_k: int = 5) -> AlgorithmOutput:
        return self._rank(X, top_k)

    def predict(self, X: pd.DataFrame) -> AlgorithmOutput:
        return self._rank(X, len(X))

    def recommend(self, X: pd.DataFrame, top_k: int = 5) -> AlgorithmOutput:
        return self._rank(X, top_k)

    def score(self, X: pd.DataFrame, y: pd.Series | None = None) -> float:
        output = self._rank(X, len(X))
        return float(np.mean([rec["score"] for rec in output.recommendations])) if output.recommendations else 0.0

    def explain(self, X: pd.DataFrame | None = None) -> str:
        return f"VIKOR balances group utility and individual regret with v={self.v}."

