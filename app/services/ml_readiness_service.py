# -*- coding: utf-8 -*-
"""ML eğitim ve kullanım hazırlık kontrolleri."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd

from app.services.ml_algorithm_registry_service import (
    ADVISORY_ML,
    BENCHMARK_ONLY,
    PRODUCTION_DECISION,
    get_algorithm_config,
)


@dataclass
class MLReadinessResult:
    algorithm_key: str
    sample_count: int
    required_min_samples: int
    class_count: int | None = None
    samples_per_class: dict[str, int] | None = None
    required_min_samples_per_class: int | None = None
    is_ready: bool = False
    readiness_level: str = "not_ready"
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    can_train: bool = False
    can_use_for_advisory: bool = False
    can_use_for_production_decision: bool = False
    usage_role: str = ADVISORY_ML

    def as_dict(self) -> dict:
        return asdict(self)


def _as_dataframe(dataset: Any) -> pd.DataFrame:
    if dataset is None:
        return pd.DataFrame()
    if isinstance(dataset, pd.DataFrame):
        return dataset.copy()
    if hasattr(dataset, "X"):
        return pd.DataFrame(getattr(dataset, "X"))
    if isinstance(dataset, dict):
        if "data" in dataset:
            return pd.DataFrame(dataset["data"])
        return pd.DataFrame(dataset)
    return pd.DataFrame(dataset)


def calculate_class_distribution(y: Any) -> dict[str, int]:
    if y is None:
        return {}
    series = pd.Series(y).dropna()
    return {str(k): int(v) for k, v in series.value_counts().sort_index().items()}


def get_sample_requirements(conn: sqlite3.Connection, algorithm_key: str) -> dict:
    cfg = get_algorithm_config(conn, algorithm_key)
    return {
        "algorithm_key": cfg.algorithm_key,
        "min_training_samples": cfg.min_training_samples,
        "min_samples_per_class": cfg.min_samples_per_class,
        "usage_role": cfg.usage_role,
    }


def check_model_readiness(
    conn: sqlite3.Connection,
    algorithm_key: str,
    dataset: Any,
    target_column: str | None = None,
) -> MLReadinessResult:
    cfg = get_algorithm_config(conn, algorithm_key)
    df = _as_dataframe(dataset)
    sample_count = int(len(df))
    result = MLReadinessResult(
        algorithm_key=cfg.algorithm_key,
        sample_count=sample_count,
        required_min_samples=int(cfg.min_training_samples),
        required_min_samples_per_class=cfg.min_samples_per_class,
        usage_role=cfg.usage_role,
    )

    y = None
    if hasattr(dataset, "y"):
        y = getattr(dataset, "y")
    elif target_column and target_column in df.columns:
        y = df[target_column]

    if y is not None and cfg.algorithm_type == "classification":
        distribution = calculate_class_distribution(y)
        result.samples_per_class = distribution
        result.class_count = len(distribution)
        if len(distribution) < 2:
            result.blocking_reasons.append("Sınıflandırma için en az iki sınıf gereklidir.")
        if cfg.min_samples_per_class:
            small_classes = {k: v for k, v in distribution.items() if v < cfg.min_samples_per_class}
            if small_classes:
                result.warnings.append(
                    f"Bazı sınıflarda örnek sayısı düşük: {small_classes}. Minimum sınıf başı {cfg.min_samples_per_class} önerilir."
                )
        if distribution:
            total = sum(distribution.values()) or 1
            majority_ratio = max(distribution.values()) / total
            if majority_ratio >= 0.80 and len(distribution) > 1:
                result.warnings.append(f"Sınıf dağılımı dengesiz görünüyor. En büyük sınıf oranı %{majority_ratio * 100:.1f}.")

    if sample_count <= 0:
        result.blocking_reasons.append("Eğitim verisi bulunamadı.")
    elif sample_count < cfg.min_training_samples:
        result.blocking_reasons.append(
            f"{cfg.display_name} için önerilen minimum eğitim örneği {cfg.min_training_samples}; mevcut veri {sample_count} kayıttır."
        )
        missing = cfg.min_training_samples - sample_count
        result.recommendations.append(f"Güvenilir kullanım için en az {missing} ek ders-yıl kaydı önerilir.")
    else:
        result.is_ready = True

    if sample_count == 0:
        result.readiness_level = "not_ready"
    elif sample_count < cfg.min_training_samples:
        ratio = sample_count / max(cfg.min_training_samples, 1)
        result.readiness_level = "not_ready" if ratio < 0.50 else "low"
    elif sample_count < cfg.min_training_samples * 2:
        result.readiness_level = "medium"
    elif cfg.usage_role == PRODUCTION_DECISION and not result.blocking_reasons:
        result.readiness_level = "production_ready"
    else:
        result.readiness_level = "high"

    result.can_train = sample_count >= max(10, min(cfg.min_training_samples, 50)) and not any("en az iki sınıf" in r for r in result.blocking_reasons)
    result.can_use_for_advisory = sample_count > 0 and cfg.usage_role in {PRODUCTION_DECISION, ADVISORY_ML, BENCHMARK_ONLY}
    result.can_use_for_production_decision = (
        cfg.usage_role == PRODUCTION_DECISION
        and result.readiness_level == "production_ready"
        and not result.blocking_reasons
        and not result.warnings
    )

    if cfg.usage_role == BENCHMARK_ONLY:
        result.warnings.append("Bu algoritma sadece benchmark olarak konumlandırılmıştır; gerçek karar hattına dahil edilmez.")
        result.can_use_for_production_decision = False
    elif cfg.usage_role == ADVISORY_ML:
        result.warnings.append("Bu algoritma destekleyici ML rolündedir; nihai kararı tek başına üretmez.")
        result.can_use_for_production_decision = False

    if not result.can_use_for_production_decision:
        result.recommendations.append("Nihai karar AHP/TOPSIS + kurallar + state machine hattıyla verilmelidir.")

    return result


def generate_readiness_report(
    conn: sqlite3.Connection,
    dataset: Any,
    *,
    target_column: str | None = None,
    algorithm_key: str | None = None,
) -> dict:
    from app.services.ml_algorithm_registry_service import list_algorithm_registry

    configs = [get_algorithm_config(conn, algorithm_key).as_dict()] if algorithm_key else list_algorithm_registry(conn)
    rows = []
    for cfg in configs:
        rows.append(check_model_readiness(conn, cfg["algorithm_key"], dataset, target_column=target_column).as_dict())
    sample_count = len(_as_dataframe(dataset))
    return {
        "sample_count": sample_count,
        "algorithm_readiness": rows,
        "summary_text": _summary_text(sample_count, rows),
    }


def _summary_text(sample_count: int, rows: list[dict]) -> str:
    not_ready = [r for r in rows if r.get("readiness_level") in {"not_ready", "low"}]
    production_ready = [r for r in rows if r.get("can_use_for_production_decision")]
    if not_ready:
        return (
            f"Mevcut veri sayısı {sample_count}. {len(not_ready)} algoritma minimum örnek koşulunu karşılamıyor. "
            "ML çıktıları destekleyici/deneysel olarak yorumlanmalıdır; nihai karar AHP/TOPSIS + kurallar + state machine hattıyla verilir."
        )
    if production_ready:
        return f"Mevcut veri sayısı {sample_count}. Üretim kararında kullanılabilecek algoritma sayısı: {len(production_ready)}."
    return (
        f"Mevcut veri sayısı {sample_count}. Algoritmalar çalıştırılabilir görünse de registry rolleri nedeniyle ML çıktıları destekleyici/benchmark amaçlıdır."
    )
