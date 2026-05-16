# -*- coding: utf-8 -*-
"""Tüm sağlık kontrolleri için güvenli temel sınıf."""

from __future__ import annotations

from time import perf_counter
from traceback import format_exc
from typing import Any

from app.health.models import HealthCheckResult, HealthContext, HealthSeverity, HealthStatus, now_iso


class BaseHealthCheck:
    name = "Genel sağlık kontrolü"
    category = "Genel Sistem Sağlığı"
    severity = HealthSeverity.MEDIUM.value
    source = "app.health"
    quick = False

    def run(self, context: HealthContext) -> HealthCheckResult:
        raise NotImplementedError

    def safe_run(self, context: HealthContext) -> HealthCheckResult:
        started = perf_counter()
        try:
            result = self.run(context)
            result.duration_ms = round((perf_counter() - started) * 1000.0, 2)
            if not result.timestamp:
                result.timestamp = now_iso()
            if not result.source:
                result.source = self.source
            return result
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            if context.developer_mode:
                detail = f"{detail}\n{format_exc()}"
            return HealthCheckResult(
                category=self.category,
                name=self.name,
                status=HealthStatus.FAILED.value,
                severity=HealthSeverity.HIGH.value,
                message="Kontrol çalışırken beklenmeyen bir hata oluştu.",
                detail=detail,
                suggestion="Bu kontrolün teknik detayını inceleyin; diğer kontroller etkilenmeden çalışmaya devam eder.",
                duration_ms=round((perf_counter() - started) * 1000.0, 2),
                timestamp=now_iso(),
                source=self.source,
                metadata={"exception_class": type(exc).__name__},
            )

    def result(
        self,
        status: HealthStatus | str,
        message: str,
        *,
        severity: HealthSeverity | str | None = None,
        detail: str = "",
        suggestion: str = "İşlem gerekmiyor.",
        metadata: dict[str, Any] | None = None,
    ) -> HealthCheckResult:
        status_value = status.value if isinstance(status, HealthStatus) else str(status)
        severity_value = severity or self.severity
        if isinstance(severity_value, HealthSeverity):
            severity_value = severity_value.value
        return HealthCheckResult(
            category=self.category,
            name=self.name,
            status=status_value,
            severity=str(severity_value),
            message=message,
            detail=detail,
            suggestion=suggestion,
            duration_ms=0.0,
            timestamp=now_iso(),
            source=self.source,
            metadata=metadata or {},
        )
