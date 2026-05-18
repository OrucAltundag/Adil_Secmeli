# -*- coding: utf-8 -*-
"""ML tahmin güveni ve belirsizlik sinyalleri."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ConfidenceResult:
    confidence_score: float
    confidence_level: str
    uncertainty_reasons: list[str] = field(default_factory=list)
    should_influence_decision: bool = False
    explanation: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def confidence_from_sample_size(sample_count: int, required_min_samples: int) -> tuple[float, list[str]]:
    if required_min_samples <= 0:
        return 0.5, []
    ratio = max(0.0, min(float(sample_count) / float(required_min_samples), 1.5))
    if ratio < 0.50:
        return 0.20, [f"Eğitim verisi çok az: {sample_count}/{required_min_samples}."]
    if ratio < 1.0:
        return 0.45, [f"Eğitim verisi önerilen minimumun altında: {sample_count}/{required_min_samples}."]
    if ratio < 1.5:
        return 0.70, []
    return 0.85, []


def confidence_from_validation_metrics(metrics: dict | None, task_type: str = "classification") -> tuple[float, list[str]]:
    if not metrics:
        return 0.35, ["Doğrulama metriği bulunmuyor."]
    if task_type == "regression":
        r2 = _to_float(metrics.get("r2"), None)
        if r2 is None:
            return 0.40, ["Regresyon için R2 metriği bulunmuyor."]
        return max(0.10, min((r2 + 0.2) / 1.2, 0.90)), [] if r2 >= 0.30 else ["Doğrulama R2 değeri düşük."]
    accuracy = _to_float(metrics.get("accuracy"), None)
    f1 = _to_float(metrics.get("f1"), None)
    score = max([v for v in (accuracy, f1) if v is not None] or [0.35])
    reasons = [] if score >= 0.65 else ["Doğrulama başarımı düşük veya belirsiz."]
    return max(0.10, min(score, 0.90)), reasons


def confidence_from_model_probability(probability: float | None) -> tuple[float, list[str]]:
    if probability is None:
        return 0.50, ["Model olasılık değeri üretmedi."]
    probability = max(0.0, min(float(probability), 1.0))
    if probability < 0.55:
        return probability, ["Model sınıf olasılığı düşük."]
    return probability, []


def combine_confidence_signals(signals: list[tuple[float, list[str]]], *, readiness_level: str | None = None, overfit_warning: bool = False) -> ConfidenceResult:
    if not signals:
        score = 0.20
        reasons = ["Güven sinyali üretilemedi."]
    else:
        weights = [0.35, 0.35, 0.20, 0.10]
        total = 0.0
        denom = 0.0
        reasons: list[str] = []
        for idx, (value, signal_reasons) in enumerate(signals):
            weight = weights[idx] if idx < len(weights) else 0.10
            total += max(0.0, min(float(value), 1.0)) * weight
            denom += weight
            reasons.extend(signal_reasons)
        score = total / max(denom, 1e-9)
    if readiness_level in {"not_ready", "low"}:
        score = min(score, 0.45)
        reasons.append(f"Readiness seviyesi {readiness_level}.")
    if overfit_warning:
        score = min(score, 0.50)
        reasons.append("Overfitting uyarısı bulundu.")
    level = "high" if score >= 0.75 else ("medium" if score >= 0.50 else "low")
    should_influence = level == "high" and readiness_level == "production_ready" and not overfit_warning
    explanation = f"Model güveni {score:.2f} / {level}. " + (" ".join(reasons) if reasons else "Belirgin belirsizlik sinyali yok.")
    return ConfidenceResult(
        confidence_score=round(float(score), 4),
        confidence_level=level,
        uncertainty_reasons=reasons,
        should_influence_decision=should_influence,
        explanation=explanation,
    )


def estimate_prediction_confidence(model, prediction, X_row, context: dict[str, Any]) -> ConfidenceResult:
    sample_signal = confidence_from_sample_size(
        int(context.get("sample_count") or 0),
        int(context.get("required_min_samples") or 1),
    )
    validation_signal = confidence_from_validation_metrics(
        context.get("validation_metrics"),
        task_type=str(context.get("model_type") or "classification"),
    )
    probability = context.get("probability")
    if probability is None and hasattr(model, "predict_proba"):
        try:
            probas = model.predict_proba(X_row)
            probability = float(max(probas[0]))
        except Exception:
            probability = None
    probability_signal = confidence_from_model_probability(probability)
    missing_ratio = float(context.get("missing_feature_ratio") or 0.0)
    missing_signal = (max(0.1, 1.0 - missing_ratio), [f"Eksik/impute edilen feature oranı %{missing_ratio * 100:.1f}."] if missing_ratio > 0.20 else [])
    return combine_confidence_signals(
        [sample_signal, validation_signal, probability_signal, missing_signal],
        readiness_level=context.get("readiness_level"),
        overfit_warning=bool((context.get("overfitting_report") or {}).get("overfit_warning")),
    )


def _to_float(value: Any, default: float | None) -> float | None:
    try:
        return float(value)
    except Exception:
        return default
