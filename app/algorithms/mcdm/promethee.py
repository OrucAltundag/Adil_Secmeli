"""PROMETHEE-II outranking ranker (preferred optional MCDM method)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.algorithms.base import AlgorithmOutput, IRanker
from app.algorithms.mcdm._shared import (
    ensure_weight_count,
    get_criteria_columns,
    normalize_weights,
)


class PROMETHEERanker(IRanker):
    def __init__(self, weights: list[float] | None = None) -> None:
        super().__init__(name="PROMETHEE_II", task_type="ranking")
        self.weights = np.array(weights, dtype=float) if weights is not None else None

    def fit(self, X: pd.DataFrame, y: None = None) -> "PROMETHEERanker":
        criteria_cols = get_criteria_columns(X)
        self.weights = normalize_weights(self.weights, len(criteria_cols), algorithm_name="PROMETHEE")
        self.parameters["weights"] = self.weights.tolist()
        return self

    def _rank(self, X: pd.DataFrame, top_k: int) -> AlgorithmOutput:
        started = self._start_timer()
        if self.weights is None:
            self.fit(X)
        assert self.weights is not None

        df = X.copy()
        criteria_cols = get_criteria_columns(df)
        ensure_weight_count(self.weights, len(criteria_cols), algorithm_name="PROMETHEE")
        matrix = df[criteria_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).to_numpy(dtype=float)
        n = matrix.shape[0]
        if n == 0:
            return self._build_output(started, recommendations=[], confidence=0.0, explanation="No alternatives provided")

        pref_matrix = np.zeros((n, n), dtype=float)
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                diff = matrix[i, :] - matrix[j, :]
                preference = np.clip(diff, a_min=0.0, a_max=None)  # usual criterion preference function
                pref_matrix[i, j] = float(np.dot(self.weights, preference))

        leaving_flow = np.mean(pref_matrix, axis=1)
        entering_flow = np.mean(pref_matrix, axis=0)
        net_flow = leaving_flow - entering_flow

        df["promethee_net_flow"] = net_flow
        ranked = df.sort_values("promethee_net_flow", ascending=False).head(top_k)
        recommendations = [
            {
                "item_id": int(row["item_id"]) if "item_id" in row and pd.notna(row["item_id"]) else str(idx),
                "score": float(row["promethee_net_flow"]),
                "rank": rank + 1,
            }
            for rank, (idx, row) in enumerate(ranked.iterrows())
        ]
        confidence = float(np.clip(np.std(net_flow), 0.0, 1.0))
        return self._build_output(
            started,
            recommendations=recommendations,
            confidence=confidence,
            explanation="PROMETHEE-II outranking via net preference flow.",
            artifacts={
                "leaving_flow": leaving_flow.tolist(),
                "entering_flow": entering_flow.tolist(),
                "net_flow": net_flow.tolist(),
            },
        )

    def rank(self, X: pd.DataFrame, top_k: int = 5) -> AlgorithmOutput:
        return self._rank(X, top_k)

    def predict(self, X: pd.DataFrame) -> AlgorithmOutput:
        return self._rank(X, len(X))

    def recommend(self, X: pd.DataFrame, top_k: int = 5) -> AlgorithmOutput:
        return self._rank(X, top_k)

    def score(self, X: pd.DataFrame, y: pd.Series | None = None) -> float:
        out = self._rank(X, len(X))
        return float(np.mean([r["score"] for r in out.recommendations])) if out.recommendations else 0.0

    def explain(self, X: pd.DataFrame | None = None) -> str:
        return "PROMETHEE-II compares pairwise preference flows and ranks by net flow."
