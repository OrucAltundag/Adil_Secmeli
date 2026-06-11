"""Clustering algorithms with standardized output."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, AgglomerativeClustering, KMeans

from app.algorithms.base import AlgorithmOutput, IClusterer


class _ClustererBase(IClusterer):
    def __init__(self, name: str, estimator: Any, parameters: dict[str, Any] | None = None) -> None:
        super().__init__(name=name, task_type="clustering", parameters=parameters)
        self.estimator = estimator
        self.labels_: np.ndarray | None = None
        self.feature_names_: list[str] = []

    def fit(self, X: pd.DataFrame, y: None = None) -> "_ClustererBase":
        X_df = self._as_dataframe(X)
        self.feature_names_ = X_df.columns.tolist()
        self.labels_ = self.estimator.fit_predict(X_df)
        return self

    def cluster(self, X: pd.DataFrame) -> AlgorithmOutput:
        started = self._start_timer()
        X_df = self._as_dataframe(X)
        labels = self.estimator.fit_predict(X_df)
        self.labels_ = np.asarray(labels, dtype=int)
        predictions = self.labels_.tolist()
        cluster_sizes = pd.Series(predictions).value_counts().to_dict()
        n_clusters = len([k for k in cluster_sizes if k != -1])
        confidence = float(1.0 / max(n_clusters, 1))
        return self._build_output(
            started,
            predictions=predictions,
            confidence=confidence,
            explanation=f"{self.name} produced {n_clusters} clusters",
            artifacts={"cluster_sizes": {str(k): int(v) for k, v in cluster_sizes.items()}},
        )

    def predict(self, X: pd.DataFrame) -> AlgorithmOutput:
        return self.cluster(X)

    def recommend(self, X: pd.DataFrame, top_k: int = 5) -> AlgorithmOutput:
        out = self.cluster(X)
        recs = []
        labels = out.predictions
        for i, label in enumerate(labels):
            recs.append({"entity_id": i, "items": [{"cluster": int(label), "score": 1.0}]})
        out.recommendations = recs
        return out

    def score(self, X: pd.DataFrame, y: pd.Series | None = None) -> float:
        if self.labels_ is None:
            self.fit(X)
        assert self.labels_ is not None
        valid = self.labels_[self.labels_ >= 0]
        return float(len(valid) / max(len(self.labels_), 1))

    def explain(self, X: pd.DataFrame | None = None) -> str:
        if self.labels_ is None:
            return f"{self.name} not fitted."
        n_clusters = len(set(self.labels_.tolist())) - (1 if -1 in self.labels_ else 0)
        return f"{self.name}: n_clusters={n_clusters}, labels shape={self.labels_.shape}"

    def _as_dataframe(self, X: Any) -> pd.DataFrame:
        if isinstance(X, pd.DataFrame):
            return X.fillna(0.0).copy()
        return pd.DataFrame(X).fillna(0.0)


class KMeansClusterer(_ClustererBase):
    def __init__(self, n_clusters: int = 5, random_seed: int = 42) -> None:
        super().__init__(
            name="KMeans",
            estimator=KMeans(n_clusters=n_clusters, n_init=10, random_state=random_seed),  # type: ignore[arg-type]
            parameters={"n_clusters": n_clusters, "random_seed": random_seed},
        )


class HierarchicalClusterer(_ClustererBase):
    def __init__(self, n_clusters: int = 5, linkage: str = "ward") -> None:
        super().__init__(
            name="HierarchicalClustering",
            estimator=AgglomerativeClustering(n_clusters=n_clusters, linkage=linkage),
            parameters={"n_clusters": n_clusters, "linkage": linkage},
        )


class DBSCANClusterer(_ClustererBase):
    def __init__(self, eps: float = 0.5, min_samples: int = 5) -> None:
        super().__init__(
            name="DBSCAN",
            estimator=DBSCAN(eps=eps, min_samples=min_samples),
            parameters={"eps": eps, "min_samples": min_samples},
        )
