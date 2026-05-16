# -*- coding: utf-8 -*-
"""ML yönetişim sağlık kontrolleri (ML destek katmanı olmalı, nihai karar değil)."""

from __future__ import annotations

import importlib.util

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _MLCheck(BaseHealthCheck):
    category = "ML Yönetişimi"
    score_bucket = "reporting_analytics_benchmark"


class MLDecisionInfluenceCheck(_MLCheck):
    name = "ML karar etkisi yönetişim kontrolü"
    default_severity = HealthSeverity.HIGH

    def run(self, context: HealthContext) -> HealthCheckResult:
        cfg = context.app_config
        influence = getattr(cfg, "enable_ml_decision_influence", False)
        require_high_conf = getattr(
            cfg, "require_high_confidence_for_ml_influence", True
        )
        allow_experimental = getattr(
            cfg, "allow_experimental_ml_in_decision", False
        )
        if influence and not require_high_conf:
            return self.warning(
                "ML karara etki ediyor ama yüksek güven şartı kapalı.",
                detail=f"influence={influence}, require_high_confidence={require_high_conf}",
                suggestion="ML etkisinde yüksek güven şartını açın (destek katmanı kalmalı).",
            )
        if allow_experimental and cfg.environment == "production":
            return self.warning(
                "Deneysel ML production kararında açık.",
                detail="allow_experimental_ml_in_decision=True (production).",
                suggestion="Production'da deneysel ML etkisini kapatın.",
            )
        return self.ok(
            "ML destek katmanı olarak konumlandırılmış.",
            detail=f"influence={influence}, high_conf={require_high_conf}, "
            f"experimental={allow_experimental}",
        )


class MLExplainabilityCheck(_MLCheck):
    name = "ML açıklanabilirlik kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            tables = set(repo.table_names())
            has_expl = "ml_prediction_explanations" in tables
            has_runs = "ml_model_runs" in tables
        if not has_runs:
            return self.info(
                "ML model çalıştırma kaydı yok.",
                detail="ml_model_runs tablosu bulunamadı.",
                suggestion="ML kullanılmıyorsa bilgilendirme amaçlıdır.",
            )
        if has_runs and not has_expl:
            return self.warning(
                "ML çıktıları için açıklanabilirlik altyapısı eksik.",
                detail="ml_model_runs var ama ml_prediction_explanations yok.",
                suggestion="ML tahminleri için açıklama üretimini ekleyin.",
            )
        return self.ok(
            "ML açıklanabilirlik altyapısı mevcut.",
            detail="ml_model_runs + ml_prediction_explanations hazır.",
        )


class MLDependencyCheck(_MLCheck):
    name = "ML bağımlılık kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        if importlib.util.find_spec("sklearn") is None:
            return self.skipped(
                "scikit-learn yok; ML kontrolleri atlandı.",
                detail="sklearn modülü bulunamadı.",
                suggestion="ML gerekiyorsa 'pip install scikit-learn' kurun.",
            )
        return self.ok(
            "ML bağımlılıkları mevcut.",
            detail="scikit-learn import edilebiliyor.",
        )
