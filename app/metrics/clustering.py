"""Clustering quality metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)


def clustering_metrics(X: pd.DataFrame | np.ndarray, labels: list[int] | np.ndarray) -> dict[str, float]:
    X_arr = X.to_numpy(dtype=float) if isinstance(X, pd.DataFrame) else np.asarray(X, dtype=float)
    labels_arr = np.asarray(labels, dtype=int)
    unique = set(labels_arr.tolist())
    valid_cluster_count = len(unique - {-1})
    if valid_cluster_count < 2:
        return {
            "silhouette": -1.0,
            "davies_bouldin": float("inf"),
            "calinski_harabasz": 0.0,
        }
    # remove outliers for metric stability where relevant
    mask = labels_arr != -1
    X_eff = X_arr[mask]
    labels_eff = labels_arr[mask]
    if len(set(labels_eff.tolist())) < 2:
        return {"silhouette": -1.0, "davies_bouldin": float("inf"), "calinski_harabasz": 0.0}
    return {
        "silhouette": float(silhouette_score(X_eff, labels_eff)),
        "davies_bouldin": float(davies_bouldin_score(X_eff, labels_eff)),
        "calinski_harabasz": float(calinski_harabasz_score(X_eff, labels_eff)),
    }
