"""AHP ranking with consistency-ratio validation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.algorithms.base import AlgorithmOutput, IRanker
from app.algorithms.mcdm._shared import ensure_weight_count, get_criteria_columns

RI_TABLE = {
    1: 0.0,
    2: 0.0,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
}


@dataclass(slots=True)
class AHPFitState:
    weights: np.ndarray
    lambda_max: float
    consistency_index: float
    consistency_ratio: float


class AHPRanker(IRanker):
    def __init__(self, pairwise_matrix: np.ndarray | list[list[float]] | None = None) -> None:
        super().__init__(name="AHP", task_type="ranking")
        self.pairwise_matrix = np.array(pairwise_matrix, dtype=float) if pairwise_matrix is not None else None
        self.state: AHPFitState | None = None

    def fit(self, X: pd.DataFrame, y: None = None) -> "AHPRanker":
        columns = get_criteria_columns(X)
        n = len(columns)
        if n == 0:
            raise ValueError("AHP icin sayisal kriter bulunamadi.")
        if self.pairwise_matrix is None:
            self.pairwise_matrix = np.ones((n, n), dtype=float)
        elif self.pairwise_matrix.shape[0] != self.pairwise_matrix.shape[1]:
            raise ValueError(f"AHP pairwise matrix kare olmali, mevcut shape={self.pairwise_matrix.shape}.")
        elif not np.all(np.isfinite(self.pairwise_matrix)):
            raise ValueError("AHP pairwise matrix must contain finite numbers.")
        matrix = self.pairwise_matrix
        eigenvalues, eigenvectors = np.linalg.eig(matrix)
        idx = int(np.argmax(eigenvalues.real))
        principal = np.real_if_close(eigenvectors[:, idx]).astype(float)
        principal = np.abs(principal)
        weights = principal / (principal.sum() or 1.0)

        weighted_sum = matrix @ weights
        lambda_values = weighted_sum / np.where(np.abs(weights) < 1e-10, 1e-10, weights)
        lambda_max = float(np.mean(lambda_values))
        n = matrix.shape[0]
        ci = (lambda_max - n) / (n - 1) if n > 1 else 0.0
        ri = RI_TABLE.get(n, RI_TABLE[10])
        cr = ci / ri if ri else 0.0
        self.state = AHPFitState(weights=weights, lambda_max=lambda_max, consistency_index=ci, consistency_ratio=cr)
        self.parameters.update({"consistency_ratio": cr, "consistency_index": ci, "lambda_max": lambda_max})
        return self

    def _rank(self, X: pd.DataFrame, top_k: int) -> AlgorithmOutput:
        started = self._start_timer()
        if self.state is None:
            self.fit(X)
        assert self.state is not None

        df = X.copy()
        criteria_cols = get_criteria_columns(df)
        try:
            ensure_weight_count(self.state.weights, len(criteria_cols), algorithm_name="AHP")
        except ValueError as exc:
            raise ValueError("Criteria count mismatch between pairwise matrix and input data") from exc
        for col in criteria_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        norm = np.linalg.norm(df[criteria_cols].to_numpy(dtype=float), axis=0)
        norm = np.where(norm <= 1e-10, 1.0, norm)
        normalized = df[criteria_cols] / norm
        scores = normalized.to_numpy() @ self.state.weights
        df["ahp_score"] = scores
        ranked = df.sort_values("ahp_score", ascending=False).head(top_k)
        item_key = "item_id" if "item_id" in ranked.columns else ranked.index.name or "index"
        recommendations = [
            {
                "item_id": int(row[item_key]) if item_key in row and pd.notna(row[item_key]) else str(idx),
                "score": float(row["ahp_score"]),
                "rank": rank + 1,
            }
            for rank, (idx, row) in enumerate(ranked.iterrows())
        ]
        explanation = (
            f"AHP weights={self.state.weights.round(4).tolist()}, "
            f"CR={self.state.consistency_ratio:.4f} (acceptable < 0.10)"
        )
        confidence = max(0.0, min(1.0, 1.0 - self.state.consistency_ratio))
        return self._build_output(
            started,
            recommendations=recommendations,
            confidence=confidence,
            explanation=explanation,
            artifacts={
                "weights": self.state.weights.tolist(),
                "lambda_max": self.state.lambda_max,
                "consistency_index": self.state.consistency_index,
                "consistency_ratio": self.state.consistency_ratio,
            },
        )

    def rank(self, X: pd.DataFrame, top_k: int = 5) -> AlgorithmOutput:
        return self._rank(X, top_k=top_k)

    def predict(self, X: pd.DataFrame) -> AlgorithmOutput:
        return self._rank(X, top_k=len(X))

    def recommend(self, X: pd.DataFrame, top_k: int = 5) -> AlgorithmOutput:
        return self._rank(X, top_k=top_k)

    def score(self, X: pd.DataFrame, y: pd.Series | None = None) -> float:
        if self.state is None:
            self.fit(X)
        assert self.state is not None
        return float(max(0.0, 1.0 - self.state.consistency_ratio))

    def explain(self, X: pd.DataFrame | None = None) -> str:
        if self.state is None:
            return "AHP not fitted."
        return (
            f"AHP uses principal eigenvector weighting. "
            f"CR={self.state.consistency_ratio:.4f}, CI={self.state.consistency_index:.4f}, "
            f"weights={self.state.weights.round(4).tolist()}"
        )
