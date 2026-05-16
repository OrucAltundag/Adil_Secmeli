# -*- coding: utf-8 -*-
"""Çalışma ortamı bilgi kontrolü."""

from __future__ import annotations

import platform
import sys

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class SystemInfoCheck(BaseHealthCheck):
    name = "Sistem ve ortam bilgisi"
    category = "Sistem"
    quick = True
    score_bucket = "architecture"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        cfg = context.app_config
        detail = (
            f"Python: {sys.version.split()[0]}\n"
            f"Platform: {platform.platform()}\n"
            f"Uygulama modu: {cfg.app_mode}\n"
            f"Ortam: {cfg.environment}\n"
            f"Sürüm: {cfg.version}\n"
            f"DB backend: {cfg.db_backend}"
        )
        return self.info(
            f"Ortam: {cfg.environment} • Mod: {cfg.app_mode} • "
            f"Python {sys.version.split()[0]}",
            detail=detail,
            suggestion="Bilgilendirme amaçlıdır; işlem gerekmiyor.",
            metadata={
                "python": sys.version.split()[0],
                "environment": cfg.environment,
                "db_backend": cfg.db_backend,
            },
        )
