# -*- coding: utf-8 -*-
"""ML model değerlendirme, çapraz doğrulama ve overfitting uyarıları."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    KFold,
    StratifiedKFold,
    cross_val_score,
    permutation_test_score,
    train_test_split,
)

try:
    from scipy import stats as _scipy_stats
except Exception:  # pragma: no cover
    _scipy_stats = None


@dataclass
class EvaluationResult:
    train_metrics: dict[str, Any] = field(default_factory=dict)
    validation_metrics: dict[str, Any] = field(default_factory=dict)
    cross_validation: dict[str, Any] = field(default_factory=dict)
    overfitting_report: dict[str, Any] = field(default_factory=dict)
    significance: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def evaluate_regression_model(model, X, y) -> EvaluationResult:
    X_df = pd.DataFrame(X).fillna(0.0)
    y_series = pd.Series(y).astype(float)
    result = EvaluationResult()
    if len(X_df) < 4:
        result.warnings.append("Regresyon validasyonu için veri çok küçük; train/test ayrımı yapılmadı.")
        preds = model.predict(X_df) if hasattr(model, "predict") else np.zeros(len(X_df))
        result.train_metrics = _regression_metrics(y_series, preds)
        result.overfitting_report = {"overfit_warning": True, "reason": "Veri sayısı çok düşük."}
        return result

    X_train, X_val, y_train, y_val = train_test_split(X_df, y_series, test_size=0.25, random_state=42)
    model.fit(X_train, y_train)
    train_pred = model.predict(X_train)
    val_pred = model.predict(X_val)
    result.train_metrics = _regression_metrics(y_train, train_pred)
    result.validation_metrics = _regression_metrics(y_val, val_pred)
    result.cross_validation = run_cross_validation(model, X_df, y_series, task_type="regression")
    result.significance = run_significance_test(model, X_df, y_series, task_type="regression")
    result.overfitting_report = detect_overfitting(result.train_metrics, result.validation_metrics, metric_name="r2")
    result.warnings.extend(result.cross_validation.get("warnings", []))
    if result.significance.get("performed") and not result.significance.get("significant"):
        result.warnings.append(result.significance.get("message", "Model anlamli degil."))
    if result.overfitting_report.get("overfit_warning"):
        result.warnings.append(result.overfitting_report.get("message", "Overfitting riski var."))
    return result


def evaluate_classification_model(model, X, y) -> EvaluationResult:
    X_df = pd.DataFrame(X).fillna(0.0)
    y_series = pd.Series(y)
    result = EvaluationResult()
    if y_series.nunique() < 2:
        result.warnings.append("Sınıflandırma için en az iki sınıf gerekir.")
        result.overfitting_report = {"overfit_warning": True, "reason": "Tek sınıf mevcut."}
        return result
    min_class = int(y_series.value_counts().min())
    if len(X_df) < 8 or min_class < 2:
        result.warnings.append("Sınıflandırma validasyonu için veri çok küçük; sonuçlar deneysel yorumlanmalıdır.")
        model.fit(X_df, y_series)
        preds = model.predict(X_df)
        probas = model.predict_proba(X_df) if hasattr(model, "predict_proba") else None
        result.train_metrics = _classification_metrics(y_series, preds, probas)
        result.overfitting_report = {"overfit_warning": True, "reason": "Veri sayısı çok düşük."}
        return result

    stratify = y_series if min_class >= 2 else None
    X_train, X_val, y_train, y_val = train_test_split(X_df, y_series, test_size=0.25, random_state=42, stratify=stratify)
    model.fit(X_train, y_train)
    train_pred = model.predict(X_train)
    val_pred = model.predict(X_val)
    train_proba = model.predict_proba(X_train) if hasattr(model, "predict_proba") else None
    val_proba = model.predict_proba(X_val) if hasattr(model, "predict_proba") else None
    result.train_metrics = _classification_metrics(y_train, train_pred, train_proba)
    result.validation_metrics = _classification_metrics(y_val, val_pred, val_proba)
    result.cross_validation = run_cross_validation(model, X_df, y_series, task_type="classification")
    result.significance = run_significance_test(model, X_df, y_series, task_type="classification")
    result.overfitting_report = detect_overfitting(result.train_metrics, result.validation_metrics, metric_name="accuracy")
    result.warnings.extend(result.cross_validation.get("warnings", []))
    if result.significance.get("performed") and not result.significance.get("significant"):
        result.warnings.append(result.significance.get("message", "Model anlamli degil."))
    if result.overfitting_report.get("overfit_warning"):
        result.warnings.append(result.overfitting_report.get("message", "Overfitting riski var."))
    return result


def run_cross_validation(model, X, y, *, task_type: str = "classification", max_folds: int = 5) -> dict:
    X_df = pd.DataFrame(X).fillna(0.0)
    y_series = pd.Series(y)
    warnings: list[str] = []
    if len(X_df) < 10:
        return {"performed": False, "warnings": ["Veri sayısı 10'dan az olduğu için cross-validation yapılmadı."]}
    folds = min(max_folds, len(X_df))
    scoring = "accuracy"
    if task_type == "classification":
        if y_series.nunique() < 2:
            return {"performed": False, "warnings": ["Tek sınıf nedeniyle StratifiedKFold yapılamadı."]}
        min_class = int(y_series.value_counts().min())
        folds = min(folds, min_class)
        if folds < 2:
            return {"performed": False, "warnings": ["Sınıf başına örnek sayısı yetersiz olduğu için cross-validation yapılmadı."]}
        cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
        scoring = "accuracy"
    else:
        if folds < 2:
            return {"performed": False, "warnings": ["Cross-validation için en az iki fold gerekli."]}
        cv = KFold(n_splits=folds, shuffle=True, random_state=42)
        scoring = "neg_mean_absolute_error"
    try:
        scores = cross_val_score(model, X_df, y_series, cv=cv, scoring=scoring)
        values = scores.tolist()
        if task_type == "regression":
            values = [float(-v) for v in values]
        return {
            "performed": True,
            "folds": int(folds),
            "scoring": "MAE" if task_type == "regression" else scoring,
            "scores": values,
            "mean": float(np.mean(values)) if values else None,
            "std": float(np.std(values)) if values else None,
            "warnings": warnings,
        }
    except Exception as exc:
        return {"performed": False, "warnings": [f"Cross-validation çalışmadı: {exc}"]}


def run_significance_test(
    model, X, y, *, task_type: str = "classification", n_permutations: int = 100
) -> dict:
    """
    Modelin sansa (rastgele) gore istatistiksel olarak anlamli sekilde
    iyi olup olmadigini test eder.

    - permutation_test_score: etiketler karistirilarak elde edilen skor
      dagilimina gore gercek skorun p-degeri (H0: model sanstan iyi degil).
    - scipy t-test: CV fold skorlari ile sans seviyesi karsilastirmasi.

    p < 0.05  => model anlamli (sansa gore gercekten iyi).
    """
    X_df = pd.DataFrame(X).fillna(0.0)
    y_series = pd.Series(y)
    if len(X_df) < 10:
        return {"performed": False, "reason": "Veri sayisi anlamlilik testi icin yetersiz (<10)."}

    try:
        if task_type == "classification":
            if y_series.nunique() < 2:
                return {"performed": False, "reason": "Tek sinif; anlamlilik testi yapilamaz."}
            min_class = int(y_series.value_counts().min())
            folds = max(2, min(5, min_class))
            cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
            scoring = "accuracy"
            sans_seviyesi = float(y_series.value_counts(normalize=True).max())
        else:
            folds = max(2, min(5, len(X_df)))
            cv = KFold(n_splits=folds, shuffle=True, random_state=42)
            scoring = "r2"
            sans_seviyesi = 0.0  # R2: rastgele ~ 0

        gercek_skor, perm_skorlari, p_degeri = permutation_test_score(
            model, X_df, y_series, scoring=scoring, cv=cv,
            n_permutations=int(n_permutations), random_state=42, n_jobs=1,
        )

        # Ek: CV fold skorlari ile sans seviyesi arasinda tek-orneklem t-testi
        t_p = None
        try:
            fold_scores = cross_val_score(model, X_df, y_series, cv=cv, scoring=scoring)
            if _scipy_stats is not None and len(fold_scores) >= 2:
                _, t_p = _scipy_stats.ttest_1samp(fold_scores, sans_seviyesi)
                t_p = float(t_p)  # type: ignore[arg-type]
        except Exception:
            t_p = None

        anlamli = bool(p_degeri < 0.05)
        return {
            "performed": True,
            "method": "permutation_test_score",
            "scoring": scoring,
            "model_score": float(gercek_skor),
            "chance_level": float(sans_seviyesi),
            "p_value": float(p_degeri),
            "ttest_p_value": t_p,
            "n_permutations": int(n_permutations),
            "significant": anlamli,
            "message": (
                f"Model sansa gore ISTATISTIKSEL OLARAK ANLAMLI (p={p_degeri:.4f} < 0.05). "
                f"Skor {gercek_skor:.3f}, sans seviyesi {sans_seviyesi:.3f}."
                if anlamli else
                f"Model sanstan anlamli sekilde iyi DEGIL (p={p_degeri:.4f} >= 0.05). "
                f"Daha fazla/temiz veri veya farkli ozellikler gerekir."
            ),
        }
    except Exception as exc:
        return {"performed": False, "reason": f"Anlamlilik testi calismadi: {exc}"}


def detect_overfitting(train_metrics: dict, validation_metrics: dict, *, metric_name: str = "accuracy") -> dict:
    if not train_metrics or not validation_metrics:
        return {"overfit_warning": True, "message": "Train/validation ayrımı yapılamadığı için overfitting riski değerlendirilemedi."}
    train_value = _metric(train_metrics, metric_name)
    validation_value = _metric(validation_metrics, metric_name)
    if train_value is None or validation_value is None:
        return {"overfit_warning": False, "message": "Karşılaştırılabilir metrik bulunamadı."}
    gap = train_value - validation_value
    warning = gap > 0.20
    return {
        "overfit_warning": bool(warning),
        "metric": metric_name,
        "train": float(train_value),
        "validation": float(validation_value),
        "gap": float(gap),
        "message": (
            f"Eğitim ve doğrulama metriği farkı {gap:.2f}. Model eğitim verisini ezberliyor olabilir."
            if warning else
            f"Eğitim/doğrulama farkı {gap:.2f}; belirgin overfitting sinyali yok."
        ),
    }


def generate_evaluation_report(result: EvaluationResult) -> dict:
    return result.as_dict()


def _regression_metrics(y_true, y_pred) -> dict:
    y_true = pd.Series(y_true).astype(float)
    y_pred = np.asarray(y_pred, dtype=float)
    rmse = math.sqrt(mean_squared_error(y_true, y_pred)) if len(y_true) else 0.0
    return {
        "sample_count": int(len(y_true)),
        "mae": float(mean_absolute_error(y_true, y_pred)) if len(y_true) else 0.0,
        "rmse": float(rmse),
        "r2": float(r2_score(y_true, y_pred)) if len(y_true) > 1 else 0.0,
    }


def _classification_metrics(y_true, y_pred, y_proba=None) -> dict:
    y_true = pd.Series(y_true)
    labels = sorted(y_true.dropna().unique().tolist())
    out = {
        "sample_count": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)) if len(y_true) else 0.0,
        "precision": float(precision_score(y_true, y_pred, average="weighted", zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average="weighted", zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist() if labels else [],
        "class_distribution": {str(k): int(v) for k, v in y_true.value_counts().sort_index().items()},
    }
    if y_proba is not None and len(labels) == 2:
        try:
            out["roc_auc"] = float(roc_auc_score(y_true, np.asarray(y_proba)[:, 1]))
        except Exception:
            pass
    return out


def _metric(metrics: dict, name: str) -> float | None:
    value = metrics.get(name)
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None
