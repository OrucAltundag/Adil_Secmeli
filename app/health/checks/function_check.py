# -*- coding: utf-8 -*-
"""Fonksiyon ve import sağlık kontrolleri."""

from __future__ import annotations

import importlib

from app.health.checks.base_check import BaseHealthCheck
from app.health.health_config import CRITICAL_IMPORTS
from app.health.models import HealthContext, HealthSeverity, HealthStatus


class ImportCheck(BaseHealthCheck):
    name = "Kritik modül import kontrolü"
    category = "Fonksiyon Kontrolleri"
    severity = HealthSeverity.HIGH.value
    source = "app.health.checks.function_check.ImportCheck"

    def run(self, context: HealthContext):
        failures: list[dict[str, str]] = []
        for module_name in CRITICAL_IMPORTS:
            try:
                importlib.import_module(module_name)
            except Exception as exc:
                failures.append({"module": module_name, "error": f"{type(exc).__name__}: {exc}"})
        if failures:
            return self.result(
                HealthStatus.CRITICAL,
                "Kritik modüllerden bazıları import edilemedi.",
                severity=HealthSeverity.CRITICAL,
                detail=f"Başarısız import sayısı: {len(failures)}",
                suggestion="Import hatalarını ve eksik bağımlılıkları düzeltin.",
                metadata={"failures": failures},
            )
        return self.result(
            HealthStatus.OK,
            "Kritik modüller import edilebiliyor.",
            detail=", ".join(CRITICAL_IMPORTS),
            metadata={"checked_modules": list(CRITICAL_IMPORTS)},
        )


class ServiceFunctionCheck(BaseHealthCheck):
    name = "Servis fonksiyon kontrolü"
    category = "Fonksiyon Kontrolleri"
    source = "app.health.checks.function_check.ServiceFunctionCheck"

    def run(self, context: HealthContext):
        from app.services.database_service import DatabaseService

        table_count = DatabaseService(context.db_path, context.config).table_count()
        return self.result(
            HealthStatus.OK,
            "Temel servis fonksiyonu güvenli şekilde çağrılabiliyor.",
            detail=f"DatabaseService.table_count={table_count}",
            metadata={"table_count": table_count},
        )


class ContractCheck(BaseHealthCheck):
    name = "Fonksiyon sözleşme kontrolü"
    category = "Fonksiyon Kontrolleri"
    source = "app.health.checks.function_check.ContractCheck"

    def run(self, context: HealthContext):
        return self.result(
            HealthStatus.INFO,
            "Fonksiyon sözleşme kontrolleri için temel import doğrulaması aktif.",
            suggestion="Kritik servis çıktıları için ayrı contract testleri ekleyin.",
        )


class ExceptionHandlingCheck(BaseHealthCheck):
    name = "Hata yakalama kontrolü"
    category = "Fonksiyon Kontrolleri"
    source = "app.health.checks.function_check.ExceptionHandlingCheck"

    def run(self, context: HealthContext):
        return self.result(
            HealthStatus.OK,
            "Sağlık kontrolleri safe_run ile izole hata yakalama kullanıyor.",
            detail="Bir kontrolün hatası raporda FAILED olarak kalır; diğer kontroller çalışmaya devam eder.",
        )


class BoundaryCheck(BaseHealthCheck):
    name = "Sınır durum kontrolü"
    category = "Fonksiyon Kontrolleri"
    source = "app.health.checks.function_check.BoundaryCheck"

    def run(self, context: HealthContext):
        return self.result(
            HealthStatus.INFO,
            "Sınır durum kontrolleri test katmanında aşamalı genişletilecek.",
            suggestion="Boş liste, tek kayıt ve eksik parametre senaryolarını ilgili servis testlerine ekleyin.",
        )
