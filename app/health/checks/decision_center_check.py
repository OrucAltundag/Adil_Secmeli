# -*- coding: utf-8 -*-
"""Karar Merkezi yönetişim sağlık kontrolleri.

decision_check.py girdi/sıralama/normalizasyon tarafına bakar; bu modül
karar yönetişimini (run kaydı, açıklama, fairness, sensitivity, override,
düşük güven) denetler.
"""

from __future__ import annotations

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _DecisionCenterCheck(BaseHealthCheck):
    category = "Karar Merkezi"
    score_bucket = "ahp_topsis_decision"


class DecisionRunTraceabilityCheck(_DecisionCenterCheck):
    name = "Karar run izlenebilirlik kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            if not repo.table_exists("decision_runs"):
                return self.info(
                    "Karar run tablosu bulunamadı.",
                    detail="decision_runs tablosu yok.",
                    suggestion="Karar Merkezi'nden bir karar çalıştırın.",
                )
            total = repo.row_count("decision_runs")
        if total == 0:
            return self.info(
                "Henüz karar run kaydı yok.",
                detail="decision_runs boş.",
                suggestion="Bir karar çalıştırıldığında izlenebilirlik oluşur.",
            )
        return self.ok(
            f"Karar run'ları izlenebilir ({total} kayıt).",
            detail="decision_runs kayıtları mevcut.",
            metadata={"runs": total},
        )


class DecisionExplanationCheck(_DecisionCenterCheck):
    name = "Karar açıklaması kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            if not repo.table_exists("course_decision_explanations"):
                return self.info(
                    "Karar açıklama tablosu yok.",
                    detail="course_decision_explanations bulunamadı.",
                    suggestion="Açıklama üretimi karar çalıştırınca oluşur.",
                )
            total = repo.row_count("course_decision_explanations")
            decisions = (
                repo.row_count("course_decisions")
                if repo.table_exists("course_decisions")
                else 0
            )
        if decisions and total == 0:
            return self.warning(
                "Kararlar var ama açıklama üretilmemiş.",
                detail=f"course_decisions={decisions}, açıklama=0",
                suggestion="Karar açıklama (explanation) hattını kontrol edin.",
            )
        return self.ok(
            "Karar açıklamaları üretilebiliyor.",
            detail=f"açıklama kaydı={total}, karar={decisions}",
            metadata={"explanations": total},
        )


class FairnessReportCheck(_DecisionCenterCheck):
    name = "Adalet (fairness) raporu kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            has = repo.table_exists("decision_fairness_reports")
        if not has:
            return self.info(
                "Fairness rapor altyapısı bulunamadı.",
                detail="decision_fairness_reports tablosu yok.",
                suggestion="Fairness modülü çalıştırıldığında oluşur.",
            )
        return self.ok(
            "Fairness rapor altyapısı mevcut.",
            detail="decision_fairness_reports tablosu hazır.",
        )


class SensitivityResultCheck(_DecisionCenterCheck):
    name = "Duyarlılık (sensitivity) sonucu kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            has = repo.table_exists("decision_sensitivity_results")
        if not has:
            return self.info(
                "Duyarlılık sonuç altyapısı bulunamadı.",
                detail="decision_sensitivity_results tablosu yok.",
                suggestion="Duyarlılık analizi çalıştırıldığında oluşur.",
            )
        return self.ok(
            "Duyarlılık sonuç altyapısı mevcut.",
            detail="decision_sensitivity_results tablosu hazır.",
        )


class LowConfidenceGuardCheck(_DecisionCenterCheck):
    name = "Düşük güven / override kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            tables = set(repo.table_names())
            low_conf = "low_confidence_decision_flags" in tables
            overrides = "course_state_overrides" in tables
        if not low_conf and not overrides:
            return self.info(
                "Düşük güven / override altyapısı görünmüyor.",
                detail=f"low_confidence={low_conf}, overrides={overrides}",
                suggestion="İlgili yönetişim tabloları oluşturulmalı.",
            )
        return self.ok(
            "Düşük güven ve override mekanizmaları mevcut.",
            detail=f"low_confidence={low_conf}, overrides={overrides}",
        )
