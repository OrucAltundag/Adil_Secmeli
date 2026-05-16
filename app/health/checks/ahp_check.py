# -*- coding: utf-8 -*-
"""AHP ağırlık ve tutarlılık sağlık kontrolleri."""

from __future__ import annotations

import json

from app.health.checks.base_check import BaseHealthCheck
from app.health.health_config import AHP_CR_CRITICAL, AHP_CR_WARNING, AHP_WEIGHT_TOLERANCE
from app.health.models import HealthContext, HealthSeverity, HealthStatus
from app.repositories.sqlite_repository import SQLiteRepository


class AHPWeightSumCheck(BaseHealthCheck):
    name = "AHP ağırlık toplamı kontrolü"
    category = "AHP / Karar Algoritmaları"
    severity = HealthSeverity.HIGH.value
    source = "app.health.checks.ahp_check.AHPWeightSumCheck"

    def run(self, context: HealthContext):
        repo = SQLiteRepository(context.db_path)
        if "ahp_weight_profiles" not in set(repo.table_names()):
            return self.result(
                HealthStatus.INFO,
                "AHP ağırlık profili tablosu bulunamadı.",
                suggestion="AHP ağırlık yönetimi kullanılacaksa ahp_weight_profiles tablosunu oluşturun.",
            )
        rows = repo.execute_rows("SELECT id, name, weights_json FROM ahp_weight_profiles LIMIT 100")
        if not rows:
            return self.result(
                HealthStatus.INFO,
                "AHP ağırlık profili bulunmuyor.",
                suggestion="Karar algoritmaları için en az bir AHP ağırlık profili oluşturun.",
            )
        issues = []
        for row in rows:
            raw = row["weights_json"]
            if not raw:
                issues.append({"id": row["id"], "name": row["name"], "issue": "weights_json boş"})
                continue
            try:
                weights = json.loads(raw)
                values = weights.values() if isinstance(weights, dict) else weights
                total = sum(float(value) for value in values)
            except Exception as exc:
                issues.append({"id": row["id"], "name": row["name"], "issue": f"parse_error: {exc}"})
                continue
            if abs(total - 1.0) > AHP_WEIGHT_TOLERANCE:
                issues.append({"id": row["id"], "name": row["name"], "sum": total})
        if issues:
            return self.result(
                HealthStatus.WARNING,
                "Bazı AHP ağırlık toplamları 1 değerinden sapıyor.",
                severity=HealthSeverity.HIGH,
                detail=f"Sorunlu profil sayısı: {len(issues)}",
                suggestion="AHP ağırlıklarını yeniden normalize edin veya profili yeniden hesaplayın.",
                metadata={"issues": issues},
            )
        return self.result(
            HealthStatus.OK,
            "AHP ağırlık toplamları tolerans içinde.",
            detail=f"Kontrol edilen profil sayısı: {len(rows)}",
            metadata={"profile_count": len(rows)},
        )


class AHPConsistencyRatioCheck(BaseHealthCheck):
    name = "AHP tutarlılık oranı kontrolü"
    category = "AHP / Karar Algoritmaları"
    severity = HealthSeverity.HIGH.value
    source = "app.health.checks.ahp_check.AHPConsistencyRatioCheck"

    def run(self, context: HealthContext):
        repo = SQLiteRepository(context.db_path)
        if "ahp_weight_profiles" not in set(repo.table_names()):
            return self.result(HealthStatus.INFO, "AHP profil tablosu bulunamadığı için CR kontrolü atlandı.")
        rows = repo.execute_rows(
            "SELECT id, name, consistency_ratio FROM ahp_weight_profiles WHERE consistency_ratio IS NOT NULL LIMIT 100"
        )
        if not rows:
            return self.result(
                HealthStatus.INFO,
                "Hesaplanmış AHP tutarlılık oranı bulunmuyor.",
                suggestion="AHP profil hesaplamasını çalıştırıp consistency_ratio alanını doldurun.",
            )
        max_cr = max(float(row["consistency_ratio"]) for row in rows)
        inconsistent = [
            {"id": row["id"], "name": row["name"], "consistency_ratio": float(row["consistency_ratio"])}
            for row in rows
            if float(row["consistency_ratio"]) > AHP_CR_WARNING
        ]
        if max_cr > AHP_CR_CRITICAL:
            status = HealthStatus.CRITICAL
            severity = HealthSeverity.CRITICAL
        elif max_cr > AHP_CR_WARNING:
            status = HealthStatus.WARNING
            severity = HealthSeverity.HIGH
        else:
            status = HealthStatus.OK
            severity = HealthSeverity.LOW
        return self.result(
            status,
            "AHP tutarlılık oranları değerlendirildi.",
            severity=severity,
            detail=f"Maksimum CR: {max_cr:.4f}",
            suggestion="CR > 0.10 olan profillerde ikili karşılaştırma matrisini yeniden gözden geçirin.",
            metadata={"max_consistency_ratio": max_cr, "inconsistent_profiles": inconsistent},
        )


class AHPMatrixShapeCheck(BaseHealthCheck):
    name = "AHP matris boyut kontrolü"
    category = "AHP / Karar Algoritmaları"
    source = "app.health.checks.ahp_check.AHPMatrixShapeCheck"

    def run(self, context: HealthContext):
        return self.result(HealthStatus.INFO, "AHP matris boyut kontrolü profil veri keşfiyle aşamalı genişletilecek.")


class AHPReciprocalMatrixCheck(AHPMatrixShapeCheck):
    name = "AHP reciprocal matris kontrolü"


class CriteriaCompletenessCheck(AHPMatrixShapeCheck):
    name = "Kriter tamlık kontrolü"


class AlternativeCompletenessCheck(AHPMatrixShapeCheck):
    name = "Alternatif tamlık kontrolü"


class SensitivityReadinessCheck(AHPMatrixShapeCheck):
    name = "Duyarlılık analizi hazırlık kontrolü"
