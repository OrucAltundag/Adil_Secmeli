# -*- coding: utf-8 -*-
"""Algoritma veri uygunluk ve minimum örnek koruma servisi."""

from __future__ import annotations

import math
import sqlite3
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from app.services.algorithm_governance_service import (
    ADVISORY_ML,
    BASELINE,
    BENCHMARK_ONLY,
    PRODUCTION_DECISION,
    get_algorithm_governance,
    normalize_algorithm_key,
)


@dataclass(slots=True)
class DataGuardResult:
    algorithm_key: str
    task_type: str
    sample_count: int
    feature_count: int
    target_available: bool
    class_distribution: dict[str, int] | None
    min_required_samples: int
    min_required_per_class: int | None
    is_allowed_to_run: bool
    allowed_mode: str
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["class_distribution_json"] = self.class_distribution
        return data


def check_data_requirements(
    conn: sqlite3.Connection,
    algorithm_key: str,
    X: Any = None,
    y: Iterable[Any] | None = None,
    task_type: str | None = None,
    *,
    sample_count: int | None = None,
    feature_count: int | None = None,
    n_clusters: int | None = None,
) -> DataGuardResult:
    """Registry kurallarına göre algoritmanın veriyle çalıştırılabilirliğini değerlendir."""

    algo = get_algorithm_governance(conn, normalize_algorithm_key(algorithm_key))
    samples, features = _shape(X)
    if sample_count is not None:
        samples = int(sample_count)
    if feature_count is not None:
        features = int(feature_count)

    effective_task = str(task_type or algo.get("task_type") or "")
    y_values = list(y) if y is not None else []
    target_available = bool(y_values)
    class_distribution = calculate_class_distribution(y_values) if target_available else None
    blocking: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []

    min_samples = int(algo.get("minimum_sample_count") or 1)
    min_per_class = algo.get("minimum_samples_per_class")
    min_per_class = int(min_per_class) if min_per_class is not None else None

    if bool(algo.get("requires_target")) and not target_available:
        blocking.append("Bu algoritma hedef değişken gerektirir; y/target verisi bulunamadı.")

    if samples <= 0:
        blocking.append("Eğitim/benchmark veri setinde örnek bulunamadı.")

    if samples < min_samples:
        warnings.append(
            f"{algo['display_name']} için önerilen minimum örnek sayısı {min_samples}; mevcut veri {samples} kayıttır."
        )
        recommendations.append("Daha fazla ders-yıl kaydı toplayın veya algoritmayı yalnızca deneysel benchmark olarak işaretleyin.")

    if effective_task == "classification":
        if not target_available:
            blocking.append("Sınıflandırma için hedef sınıf etiketi zorunludur.")
        elif len(class_distribution or {}) < 2:
            blocking.append("Sınıflandırma için en az iki sınıf gerekir.")
        elif min_per_class is not None:
            weak_classes = {k: v for k, v in (class_distribution or {}).items() if v < min_per_class}
            if weak_classes:
                warnings.append(f"Bazı sınıflarda minimum {min_per_class} örnek yok: {weak_classes}.")
                recommendations.append("Macro F1 ve balanced accuracy metriklerini öne çıkarın.")
        imbalance = check_class_balance(y_values)
        if imbalance:
            warnings.append(imbalance)

    if effective_task == "clustering":
        if features <= 0:
            blocking.append("Kümeleme için en az bir sayısal feature gerekir.")
        if n_clusters is not None and samples < int(n_clusters):
            blocking.append("KMeans için örnek sayısı küme sayısından düşük olamaz.")
        if bool(algo.get("requires_feature_scaling")):
            warnings.append("Bu kümeleme algoritması için feature scaling zorunlu/önerilidir.")

    if bool(algo.get("requires_feature_scaling")) and effective_task != "clustering":
        warnings.append("Bu algoritma feature scaling ile daha güvenilir çalışır.")

    missing = check_missing_values(X)
    if missing:
        warnings.append(f"Veri setinde {missing} eksik değer tespit edildi.")
        recommendations.append("Eksik değerleri ortak feature pipeline ile imputasyon raporu üreterek tamamlayın.")

    role = str(algo.get("usage_role") or "")
    allowed_mode = _allowed_mode(role, samples, min_samples, blocking, algo["algorithm_key"])
    is_allowed = allowed_mode not in {"blocked"}
    if role == BENCHMARK_ONLY:
        warnings.append("Bu algoritma sadece benchmark/keşifsel analiz rolündedir; nihai kararı etkileyemez.")
    if role == ADVISORY_ML:
        warnings.append("Bu algoritma destekleyici ML rolündedir; nihai kararı tek başına üretmez.")
    if role == PRODUCTION_DECISION and not bool(algo.get("can_affect_final_decision")):
        blocking.append("Registry çelişkisi: production role var ancak final karara etki izni yok.")

    if blocking:
        allowed_mode = "blocked"
        is_allowed = False

    return DataGuardResult(
        algorithm_key=algo["algorithm_key"],
        task_type=effective_task,
        sample_count=samples,
        feature_count=features,
        target_available=target_available,
        class_distribution=class_distribution,
        min_required_samples=min_samples,
        min_required_per_class=min_per_class,
        is_allowed_to_run=is_allowed,
        allowed_mode=allowed_mode,
        blocking_reasons=blocking,
        warnings=warnings,
        recommendations=recommendations,
    )


def check_minimum_sample_count(sample_count: int, required: int) -> bool:
    return int(sample_count) >= int(required)


def check_min_samples_per_class(y: Iterable[Any], required: int) -> dict[str, int]:
    return {k: v for k, v in calculate_class_distribution(y).items() if v < int(required)}


def calculate_class_distribution(y: Iterable[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in y:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return counts


def check_feature_count(X: Any, min_features: int = 1) -> bool:
    return _shape(X)[1] >= int(min_features)


def check_class_balance(y: Iterable[Any], imbalance_ratio: float = 0.2) -> str | None:
    counts = list(calculate_class_distribution(y).values())
    if len(counts) < 2:
        return None
    total = sum(counts)
    if not total:
        return None
    smallest = min(counts) / total
    if smallest < imbalance_ratio:
        return "Sınıf dağılımı dengesiz görünüyor; macro F1 ve balanced accuracy raporlanmalıdır."
    return None


def check_scaling_required(algorithm_key: str) -> bool:
    return normalize_algorithm_key(algorithm_key) in {"linear_regression", "logistic_regression", "kmeans", "dbscan", "hierarchical_clustering"}


def check_target_required(task_type: str) -> bool:
    return task_type in {"classification", "regression"}


def check_missing_values(X: Any) -> int:
    rows = _as_rows(X)
    missing = 0
    for row in rows:
        values = row.values() if isinstance(row, dict) else row
        for value in values:
            if value is None:
                missing += 1
            elif isinstance(value, float) and math.isnan(value):
                missing += 1
            elif isinstance(value, str) and not value.strip():
                missing += 1
    return missing


def check_algorithm_specific_requirements(algorithm_key: str, *, sample_count: int, n_clusters: int | None = None) -> list[str]:
    key = normalize_algorithm_key(algorithm_key)
    warnings: list[str] = []
    if key in {"xgboost", "gradient_boosting"} and sample_count < 500:
        warnings.append("Gradient boosting ailesi bu veri hacminde yüksek overfitting riski taşır.")
    if key == "dbscan":
        warnings.append("DBSCAN için eps/min_samples duyarlılığı ve noise ratio mutlaka raporlanmalıdır.")
    if key == "kmeans" and n_clusters is not None and sample_count < int(n_clusters) * 2:
        warnings.append("KMeans için küme başına çok az örnek var; sonuçlar kararsız olabilir.")
    return warnings


def _allowed_mode(role: str, sample_count: int, required: int, blocking: list[str], algorithm_key: str) -> str:
    if blocking:
        return "blocked"
    if sample_count < required:
        if algorithm_key in {"xgboost", "gradient_boosting"}:
            return "blocked"
        return "experimental"
    if role == PRODUCTION_DECISION:
        return PRODUCTION_DECISION
    if role == BASELINE:
        return "benchmark"
    if role == BENCHMARK_ONLY:
        return "benchmark"
    if role == ADVISORY_ML:
        return "advisory"
    return "experimental"


def _shape(X: Any) -> tuple[int, int]:
    if X is None:
        return 0, 0
    if hasattr(X, "shape"):
        shape = getattr(X, "shape")
        if len(shape) == 1:
            return int(shape[0]), 1
        return int(shape[0]), int(shape[1])
    rows = _as_rows(X)
    if not rows:
        return 0, 0
    first = rows[0]
    if isinstance(first, dict):
        return len(rows), len(first)
    if isinstance(first, (list, tuple)):
        return len(rows), len(first)
    return len(rows), 1


def _as_rows(X: Any) -> list[Any]:
    if X is None:
        return []
    if hasattr(X, "to_dict"):
        try:
            return list(X.to_dict(orient="records"))
        except Exception:
            pass
    if hasattr(X, "tolist"):
        try:
            data = X.tolist()
            return data if isinstance(data, list) else [data]
        except Exception:
            pass
    if isinstance(X, list):
        return X
    if isinstance(X, tuple):
        return list(X)
    return [X]
