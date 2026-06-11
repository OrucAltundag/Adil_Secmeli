# -*- coding: utf-8 -*-
"""Benchmark ve ML için güvenli validation stratejisi seçimi."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable


@dataclass(slots=True)
class ValidationStrategy:
    name: str
    fold_count: int | None = None
    group_key: str | None = None
    split_summary: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def choose_validation_strategy(task_type: str, dataset_meta: dict[str, Any] | None = None) -> ValidationStrategy:
    meta = dataset_meta or {}
    sample_count = int(meta.get("sample_count") or 0)
    class_distribution = meta.get("class_distribution") or {}
    years = meta.get("years") or []
    group_key = meta.get("group_key")
    requested = str(meta.get("preferred_strategy") or "").strip()
    warnings: list[str] = []

    if requested:
        return ValidationStrategy(name=requested, fold_count=_safe_fold_count(sample_count, class_distribution), group_key=group_key, warnings=warnings)

    if years and len(set(years)) >= 2:
        return ValidationStrategy(
            name="time_based_split",
            fold_count=None,
            split_summary={"train_years": sorted(set(years))[:-1], "test_year": sorted(set(years))[-1]},
            warnings=warnings,
        )

    if group_key:
        folds = max(2, min(5, int(meta.get("group_count") or 5), sample_count))
        return ValidationStrategy(name=f"group_k_fold_by_{group_key}", fold_count=folds, group_key=group_key, warnings=warnings)

    task = str(task_type or "").lower()
    if sample_count < 10:
        warnings.append("Veri çok küçük; cross-validation güvenilir değildir, leave-one-out/holdout uyarılı seçildi.")
        return ValidationStrategy(name="leave_one_out" if sample_count > 2 else "holdout", fold_count=sample_count if sample_count > 2 else 1, warnings=warnings)

    if task == "classification":
        min_class = min(class_distribution.values()) if class_distribution else 0
        if class_distribution and min_class >= 2:
            folds = max(2, min(5, min_class, sample_count))
            return ValidationStrategy(name="stratified_k_fold", fold_count=folds, warnings=warnings)
        warnings.append("Sınıf dağılımı StratifiedKFold için yetersiz; k-fold seçildi.")
        return ValidationStrategy(name="k_fold", fold_count=max(2, min(5, sample_count)), warnings=warnings)

    if task in {"regression", "ranking"}:
        return ValidationStrategy(name="repeated_k_fold" if sample_count >= 30 else "k_fold", fold_count=max(2, min(5, sample_count)), warnings=warnings)

    if task == "clustering":
        return ValidationStrategy(name="stability_resampling", fold_count=max(2, min(5, sample_count)), warnings=warnings)

    return ValidationStrategy(name="holdout", fold_count=None, warnings=warnings)


def run_validation_strategy(model: Any, X: Any, y: Iterable[Any] | None, strategy: ValidationStrategy) -> dict[str, Any]:
    """Basit, güvenli validation yürütücüsü. Model sklearn uyumluysa fold metrikleri döner."""

    if y is None:
        return {"strategy": strategy.to_dict(), "warnings": ["Hedef değişken olmadığı için validation çalıştırılmadı."], "fold_metrics": []}
    try:
        import numpy as np
        from sklearn.base import clone
        from sklearn.metrics import accuracy_score, mean_absolute_error
    except Exception as exc:
        return {"strategy": strategy.to_dict(), "warnings": [f"sklearn validation çalıştırılamadı: {exc}"], "fold_metrics": []}

    y_arr = np.asarray(list(y))
    X_arr = np.asarray(X)
    if len(y_arr) < 3:
        return {"strategy": strategy.to_dict(), "warnings": ["Validation için örnek sayısı çok düşük."], "fold_metrics": []}

    splits = _make_splits(strategy, X_arr, y_arr)
    fold_metrics = []
    warnings = list(strategy.warnings)
    for fold_idx, (train_idx, test_idx) in enumerate(splits, start=1):
        try:
            estimator: Any = clone(model)
            estimator.fit(X_arr[train_idx], y_arr[train_idx])
            pred = estimator.predict(X_arr[test_idx])
            if _is_numeric(y_arr):
                metric = {"fold": fold_idx, "mae": float(mean_absolute_error(y_arr[test_idx], pred))}
            else:
                metric = {"fold": fold_idx, "accuracy": float(accuracy_score(y_arr[test_idx], pred))}
            fold_metrics.append(metric)
        except Exception as exc:
            warnings.append(f"{fold_idx}. fold çalıştırılamadı: {exc}")
    return {"strategy": strategy.to_dict(), "fold_metrics": fold_metrics, "warnings": warnings}


def time_based_split(years: Iterable[int]) -> dict[str, Any]:
    unique = sorted(set(int(y) for y in years))
    if len(unique) < 2:
        return {"can_split": False, "reason": "Time-based split için en az iki yıl gerekir."}
    return {"can_split": True, "train_years": unique[:-1], "test_year": unique[-1]}


def group_k_fold_split(groups: Iterable[Any], fold_count: int = 5) -> dict[str, Any]:
    unique = list(dict.fromkeys(groups))
    if len(unique) < 2:
        return {"can_split": False, "reason": "GroupKFold için en az iki grup gerekir."}
    return {"can_split": True, "fold_count": max(2, min(int(fold_count), len(unique))), "group_count": len(unique)}


def stratified_k_fold_split(y: Iterable[Any], fold_count: int = 5) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for value in y:
        counts[str(value)] = counts.get(str(value), 0) + 1
    if len(counts) < 2:
        return {"can_split": False, "reason": "StratifiedKFold için en az iki sınıf gerekir."}
    folds = max(2, min(int(fold_count), min(counts.values())))
    return {"can_split": True, "fold_count": folds, "class_distribution": counts}


def repeated_k_fold_split(sample_count: int, fold_count: int = 5, repeats: int = 3) -> dict[str, Any]:
    return {"can_split": sample_count >= 4, "fold_count": max(2, min(fold_count, sample_count)), "repeats": int(repeats)}


def leave_one_out_if_needed(sample_count: int) -> dict[str, Any]:
    return {"strategy": "leave_one_out" if sample_count <= 20 else "k_fold", "fold_count": sample_count if sample_count <= 20 else min(5, sample_count)}


def _safe_fold_count(sample_count: int, class_distribution: dict[str, int]) -> int:
    if class_distribution:
        return max(2, min(5, min(class_distribution.values()), max(2, sample_count)))
    return max(2, min(5, max(2, sample_count)))


def _make_splits(strategy: ValidationStrategy, X: Any, y: Any):
    from sklearn.model_selection import KFold, LeaveOneOut, StratifiedKFold

    folds = int(strategy.fold_count or 3)
    if strategy.name == "leave_one_out":
        return LeaveOneOut().split(X, y)
    if strategy.name == "stratified_k_fold":
        return StratifiedKFold(n_splits=folds, shuffle=True, random_state=42).split(X, y)
    return KFold(n_splits=folds, shuffle=True, random_state=42).split(X)


def _is_numeric(values: Any) -> bool:
    try:
        [float(v) for v in values]
        return True
    except Exception:
        return False
