"""Shannon-entropi tabanli OBJEKTIF kriter agirliklandirma ve siralama.

AHP agirliklari uzmanin OZNEL (subjective) yargisindan gelir. Entropi yontemi
ise agirliklari TAMAMEN VERIDEN, hicbir uzman gorusu olmadan uretir: bir kriter
dersler arasinda ne kadar cok ayrisiyorsa (varyasyon/bilgi icerigi yuksekse) o
kadar cok agirlik alir. Bu sayede AHP'nin urettigi agirliklarin veriyle ne kadar
ortustugunu bagimsiz bir sekilde capraz-kontrol etmek mumkun olur.

Adimlar (Shannon entropi yontemi):
  1. Karar matrisi sutunlari oran haline getirilir:  p_ij = x_ij / sum_i(x_ij)
  2. Her kriterin entropisi:  e_j = -k * sum_i(p_ij * ln(p_ij)),  k = 1 / ln(m)
     (m = alternatif/ders sayisi; k entropiyi [0,1] araligina olceklendirir)
  3. Bilgi cesitliligi:  d_j = 1 - e_j   (entropi dusukse cesitlilik/bilgi yuksek)
  4. Objektif agirlik:  w_j = d_j / sum_j(d_j)
  5. Siralama: vektor-normalize edilmis matris bu agirliklarla agirliklandirilir
     ve toplam skora gore (yuksekten dusuge) siralanir (basit toplamali yaklasim).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.algorithms.base import AlgorithmOutput, IRanker
from app.algorithms.mcdm._shared import get_criteria_columns


class EntropyWeightRanker(IRanker):
    """Veriden objektif agirlik ureten entropi tabanli siralayici."""

    def __init__(self) -> None:
        super().__init__(name="EntropyWeighting", task_type="ranking")
        self.weights: np.ndarray | None = None
        self.criteria_cols: list[str] = []
        self._is_fitted = False

    @staticmethod
    def _entropy_weights(matrix: np.ndarray) -> np.ndarray:
        """Karar matrisinden Shannon-entropi agirliklarini hesaplar."""
        m, n = matrix.shape
        if m <= 1:
            # Tek alternatifte entropi tanimsiz → esit agirlik
            return np.ones(n, dtype=float) / float(n)

        col_min = matrix.min(axis=0)
        col_max = matrix.max(axis=0)
        # Tum derslerde ayni olan (ayirt edici olmayan) kriter: bilgi cesitliligi 0.
        constant = (col_max - col_min) <= 1e-12

        # Entropi negatif olmayan sutun bekler; yalnizca negatif iceren sutunlari kaydir.
        base = matrix.astype(float).copy()
        neg_cols = col_min < 0
        if np.any(neg_cols):
            base[:, neg_cols] = base[:, neg_cols] - col_min[neg_cols]
        col_sums = base.sum(axis=0)
        col_sums = np.where(col_sums <= 1e-12, 1.0, col_sums)
        p = base / col_sums
        # 0*ln(0) = 0 kabul edilir; log icin sifirlari maskele
        with np.errstate(divide="ignore", invalid="ignore"):
            log_p = np.where(p > 0, np.log(p), 0.0)
        k = 1.0 / np.log(m)
        entropy = -k * np.sum(p * log_p, axis=0)
        diversity = 1.0 - entropy
        diversity = np.where(constant, 0.0, diversity)
        diversity = np.clip(diversity, 0.0, None)
        total = float(np.sum(diversity))
        if total <= 1e-12:
            # Tum kriterler ayni bilgi → esit agirlik
            return np.ones(n, dtype=float) / float(n)
        return diversity / total

    def fit(self, X: pd.DataFrame, y: None = None) -> "EntropyWeightRanker":
        self.criteria_cols = get_criteria_columns(X)
        if not self.criteria_cols:
            raise ValueError("Entropi icin sayisal kriter bulunamadi.")
        matrix = (
            X[self.criteria_cols]
            .apply(pd.to_numeric, errors="coerce")
            .fillna(0.0)
            .to_numpy(dtype=float)
        )
        self.weights = self._entropy_weights(matrix)
        self.parameters["weights"] = self.weights.tolist()
        self.parameters["criteria"] = list(self.criteria_cols)
        self._is_fitted = True
        return self

    def _rank(self, X: pd.DataFrame, top_k: int) -> AlgorithmOutput:
        started = self._start_timer()
        if not self._is_fitted or self.weights is None:
            self.fit(X)
        assert self.weights is not None

        df = X.copy()
        criteria_cols = get_criteria_columns(df)
        if len(criteria_cols) != len(self.weights):
            # Egitim ve tahmin kriterleri uyumsuzsa yeniden uyumla
            self.fit(df)
            criteria_cols = self.criteria_cols
        matrix = (
            df[criteria_cols]
            .apply(pd.to_numeric, errors="coerce")
            .fillna(0.0)
            .to_numpy(dtype=float)
        )
        norm = np.sqrt(np.sum(np.square(matrix), axis=0))
        norm = np.where(norm <= 1e-10, 1.0, norm)
        normalized = matrix / norm
        scores = normalized @ self.weights

        df["entropy_score"] = scores
        ranked = df.sort_values("entropy_score", ascending=False).head(top_k)
        recommendations = [
            {
                "item_id": int(row["item_id"]) if "item_id" in row and pd.notna(row["item_id"]) else str(idx),
                "score": float(row["entropy_score"]),
                "rank": rank + 1,
            }
            for rank, (idx, row) in enumerate(ranked.iterrows())
        ]
        return self._build_output(
            started,
            recommendations=recommendations,
            confidence=float(np.mean(scores)) if len(scores) else 0.0,
            explanation=(
                "Entropi objektif agirliklari (veriden): "
                f"{dict(zip(criteria_cols, np.round(self.weights, 4).tolist()))}"
            ),
            artifacts={
                "weights": self.weights.tolist(),
                "criteria": list(criteria_cols),
                "scores": scores.tolist(),
            },
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
        if not self._is_fitted or self.weights is None:
            return "EntropyWeighting not fitted."
        pairs = ", ".join(f"{c}={w:.4f}" for c, w in zip(self.criteria_cols, self.weights))
        return (
            "Entropi yontemi agirliklari yalnizca veriden (objektif) uretir; "
            f"kriter agirliklari: {pairs}. Yuksek agirlik = dersler arasinda daha ayirt edici kriter."
        )
