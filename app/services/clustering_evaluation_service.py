# -*- coding: utf-8 -*-
"""Kümeleme ve DBSCAN özel değerlendirme servisi."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable


@dataclass(slots=True)
class ClusteringEvaluation:
    algorithm_key: str
    cluster_count: int
    noise_ratio: float | None
    silhouette_score: float | None
    davies_bouldin_score: float | None
    calinski_harabasz_score: float | None
    cluster_size_distribution: dict[str, int]
    stability_score: float | None = None
    dbscan_params: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)
    summary_text: str = ""

    @property
    def metrics(self) -> dict[str, Any]:
        return self.to_dict()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_clustering(X: Any, labels: Iterable[Any], algorithm_key: str, *, dbscan_params: dict[str, Any] | None = None) -> ClusteringEvaluation:
    label_list = list(labels or [])
    distribution = calculate_cluster_size_distribution(label_list)
    non_noise = {label for label in label_list if str(label) != "-1"}
    cluster_count = len(non_noise)
    noise_ratio = calculate_noise_ratio(label_list) if str(algorithm_key).lower() == "dbscan" or "-1" in distribution else None
    warnings: list[str] = []
    if not label_list:
        warnings.append("Küme label verisi yok.")
    if cluster_count <= 1:
        warnings.append("Tek küme veya tüm noise sonucu; silhouette gibi metrikler güvenilir değildir.")
    if noise_ratio is not None and noise_ratio > 0.60:
        warnings.append("DBSCAN noise oranı %60 üzerinde; sonuç güvenilir olmayabilir.")

    sil = db = ch = None
    try:
        from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score
        import numpy as np

        X_arr = np.asarray(X)
        if len(label_list) == len(X_arr) and cluster_count > 1 and cluster_count < len(label_list):
            sil = float(silhouette_score(X_arr, label_list))
            db = float(davies_bouldin_score(X_arr, label_list))
            ch = float(calinski_harabasz_score(X_arr, label_list))
        else:
            warnings.append("Silhouette/Davies/Calinski metrikleri için en az iki geçerli küme gerekir.")
    except Exception as exc:
        warnings.append(f"Kümeleme metrikleri hesaplanamadı: {exc}")

    summary = (
        "Clustering algoritmaları nihai müfredat kararı üretmez; tercih/ders örüntülerini keşifsel analiz için kullanılır. "
        f"Küme sayısı {cluster_count}, noise oranı {noise_ratio if noise_ratio is not None else 'uygulanmadı'}."
    )
    return ClusteringEvaluation(
        algorithm_key=str(algorithm_key),
        cluster_count=cluster_count,
        noise_ratio=noise_ratio,
        silhouette_score=sil,
        davies_bouldin_score=db,
        calinski_harabasz_score=ch,
        cluster_size_distribution=distribution,
        dbscan_params=dbscan_params,
        warnings=warnings,
        summary_text=summary,
    )


def calculate_cluster_size_distribution(labels: Iterable[Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for label in labels:
        key = str(label)
        out[key] = out.get(key, 0) + 1
    return out


def calculate_noise_ratio(labels: Iterable[Any]) -> float:
    values = list(labels)
    if not values:
        return 0.0
    return sum(1 for value in values if str(value) == "-1") / len(values)


def calculate_cluster_stability(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    return {"stability_score": None, "warning": "Cluster stability için tekrar örnekleme altyapısı hazır; mevcut çağrıda çalıştırılmadı."}


def recommend_dbscan_eps(X: Any, min_samples: int = 5) -> dict[str, Any]:
    data = generate_k_distance_data(X, min_samples)
    distances = data.get("k_distances") or []
    if not distances:
        return {"eps": None, "warning": "eps önerisi için veri yetersiz."}
    idx = int(len(distances) * 0.90)
    return {"eps": distances[min(idx, len(distances) - 1)], "method": "90th_percentile_k_distance", "min_samples": min_samples}


def generate_k_distance_data(X: Any, min_samples: int = 5) -> dict[str, Any]:
    try:
        from sklearn.neighbors import NearestNeighbors
        import numpy as np

        X_arr = np.asarray(X)
        if len(X_arr) < min_samples:
            return {"k_distances": [], "warning": "k-distance için örnek sayısı min_samples değerinden düşük."}
        nn = NearestNeighbors(n_neighbors=int(min_samples))
        nn.fit(X_arr)
        distances, _ = nn.kneighbors(X_arr)
        k_dist = sorted(float(row[-1]) for row in distances)
        return {"k_distances": k_dist, "min_samples": min_samples}
    except Exception as exc:
        return {"k_distances": [], "warning": f"k-distance hesaplanamadı: {exc}"}


def dbscan_sensitivity_analysis(X: Any, eps_values: Iterable[float], min_samples_values: Iterable[int]) -> list[dict[str, Any]]:
    results = []
    try:
        from sklearn.cluster import DBSCAN

        for eps in eps_values:
            for min_samples in min_samples_values:
                labels = DBSCAN(eps=float(eps), min_samples=int(min_samples)).fit_predict(X)
                evaluation = evaluate_clustering(X, labels, "dbscan", dbscan_params={"eps": eps, "min_samples": min_samples})
                results.append(evaluation.to_dict())
    except Exception as exc:
        results.append({"warning": f"DBSCAN sensitivity çalıştırılamadı: {exc}"})
    return results
