# -*- coding: utf-8 -*-
"""Bağımlılık sağlık kontrolleri (paket KURMAZ; yalnızca raporlar)."""

from __future__ import annotations

import importlib.util

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.dependency_scanner import scan_dependencies
from app.health.models import HealthCheckResult, HealthSeverity


class _DependencyCheck(BaseHealthCheck):
    category = "Bağımlılık"
    score_bucket = "ops"


class RequirementsPresenceCheck(_DependencyCheck):
    name = "Bağımlılık listesi kontrolü"
    quick = True
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        scan = scan_dependencies(context.health_config)
        if not scan.requirements_present and not scan.pyproject_present:
            return self.critical(
                "Bağımlılık listesi bulunamadı.",
                detail="requirements.txt ve pyproject.toml yok.",
                suggestion="requirements.txt oluşturup bağımlılıkları listeleyin.",
            )
        return self.ok(
            "Bağımlılık listesi mevcut.",
            detail=f"requirements.txt={scan.requirements_present}, "
            f"pyproject.toml={scan.pyproject_present}, "
            f"tanımlı paket={len(scan.declared)}",
        )


class MissingDependencyCheck(_DependencyCheck):
    name = "Eksik bağımlılık kontrolü"
    default_severity = HealthSeverity.HIGH

    def run(self, context: HealthContext) -> HealthCheckResult:
        scan = scan_dependencies(context.health_config)
        if scan.missing_critical:
            return self.critical(
                "Kritik bağımlılıklar requirements.txt'te eksik.",
                detail="Eksik: " + ", ".join(scan.missing_critical),
                suggestion="Kritik paketleri requirements.txt'e ekleyin (kurmayın, listeleyin).",
                metadata={"missing_critical": scan.missing_critical},
            )
        if scan.used_not_declared:
            return self.warning(
                "Kullanılan bazı paketler bildirilmemiş.",
                detail="Bildirilmemiş: " + ", ".join(scan.used_not_declared[:25]),
                suggestion="İlgili paketleri requirements.txt'e ekleyin.",
                metadata={"used_not_declared": scan.used_not_declared},
            )
        return self.ok(
            "Kritik bağımlılıklar bildirilmiş ve tutarlı.",
            detail=f"Tanımlı paket: {len(scan.declared)}",
        )


class ImportableCriticalPackagesCheck(_DependencyCheck):
    name = "Kritik paket import kontrolü"
    quick = True
    default_severity = HealthSeverity.HIGH

    CRITICAL = ("pandas", "numpy", "sqlalchemy", "fastapi")
    OPTIONAL = ("psutil", "reportlab", "sklearn", "matplotlib", "openpyxl")

    def run(self, context: HealthContext) -> HealthCheckResult:
        missing_critical = [
            m for m in self.CRITICAL if importlib.util.find_spec(m) is None
        ]
        missing_optional = [
            m for m in self.OPTIONAL if importlib.util.find_spec(m) is None
        ]
        if missing_critical:
            return self.critical(
                "Kritik paketler import edilemiyor.",
                detail="Eksik: " + ", ".join(missing_critical),
                suggestion="`pip install -r requirements.txt` çalıştırın.",
                metadata={"missing_critical": missing_critical},
            )
        if missing_optional:
            return self.info(
                "Bazı opsiyonel paketler yok (ilgili kontroller SKIPPED dönecek).",
                detail="Eksik opsiyonel: " + ", ".join(missing_optional),
                suggestion="Gerekirse opsiyonel paketleri kurun.",
                metadata={"missing_optional": missing_optional},
            )
        return self.ok(
            "Kritik ve opsiyonel paketler mevcut.",
            detail="pandas/numpy/sqlalchemy/fastapi import edilebiliyor.",
        )
