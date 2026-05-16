# -*- coding: utf-8 -*-
"""Güvenlik sağlık kontrolleri."""

from __future__ import annotations

from pathlib import Path

from app.health.checks.base_check import BaseHealthCheck
from app.health.models import HealthContext, HealthSeverity, HealthStatus


class SQLConsolePermissionCheck(BaseHealthCheck):
    name = "SQL Console yetki kontrolü"
    category = "Güvenlik"
    severity = HealthSeverity.CRITICAL.value
    source = "app.health.checks.security_check.SQLConsolePermissionCheck"
    quick = True

    def run(self, context: HealthContext):
        enabled = bool(getattr(context.config, "enable_sql_console", False))
        developer_tools = bool(getattr(context.config, "enable_developer_tools", False))
        environment = str(getattr(context.config, "environment", "")).lower()
        if enabled and environment == "production":
            return self.result(
                HealthStatus.CRITICAL,
                "SQL Console production ortamda açık görünüyor.",
                severity=HealthSeverity.CRITICAL,
                suggestion="Production ortamda SQL Console'u kapatın.",
                metadata={"enable_sql_console": enabled, "environment": environment},
            )
        if enabled and not developer_tools:
            return self.result(
                HealthStatus.CRITICAL,
                "SQL Console geliştirici araçları kapalıyken açık.",
                severity=HealthSeverity.CRITICAL,
                suggestion="SQL Console'u sadece geliştirici/yönetici modunda açın.",
                metadata={"enable_sql_console": enabled, "enable_developer_tools": developer_tools},
            )
        status = HealthStatus.INFO if enabled else HealthStatus.OK
        return self.result(
            status,
            "SQL Console yetki ayarları güvenli aralıkta.",
            detail=f"enabled={enabled}, developer_tools={developer_tools}, environment={environment}",
            metadata={"enable_sql_console": enabled, "enable_developer_tools": developer_tools, "environment": environment},
        )


class DeveloperModeCheck(BaseHealthCheck):
    name = "Developer mode kontrolü"
    category = "Güvenlik"
    severity = HealthSeverity.HIGH.value
    source = "app.health.checks.security_check.DeveloperModeCheck"
    quick = True

    def run(self, context: HealthContext):
        enabled = bool(getattr(context.config, "enable_developer_tools", False))
        environment = str(getattr(context.config, "environment", "")).lower()
        if enabled and environment == "production":
            return self.result(
                HealthStatus.CRITICAL,
                "Developer tools production ortamda açık.",
                severity=HealthSeverity.CRITICAL,
                suggestion="Production ortamda developer tools kapatılmalı.",
            )
        status = HealthStatus.INFO if enabled else HealthStatus.OK
        return self.result(
            status,
            "Developer mode ayarı ortamla uyumlu.",
            detail=f"developer_tools={enabled}, environment={environment}",
        )


class UnsafeSQLPatternCheck(BaseHealthCheck):
    name = "Riskli SQL pattern kontrolü"
    category = "Güvenlik"
    source = "app.health.checks.security_check.UnsafeSQLPatternCheck"

    def run(self, context: HealthContext):
        sql_console_path = context.root_path / "app" / "services" / "sql_console_service.py"
        exists = sql_console_path.exists()
        return self.result(
            HealthStatus.INFO if exists else HealthStatus.WARNING,
            "Riskli SQL pattern kontrolü için SQL Console servisi değerlendirildi.",
            detail=str(sql_console_path),
            suggestion="DROP/DELETE/ALTER gibi komutlar için merkezi izin kontrolünü koruyun.",
        )


class PathTraversalCheck(BaseHealthCheck):
    name = "Path traversal kontrolü"
    category = "Güvenlik"
    source = "app.health.checks.security_check.PathTraversalCheck"

    def run(self, context: HealthContext):
        security_file = context.root_path / "app" / "services" / "file_upload_security_service.py"
        status = HealthStatus.OK if security_file.exists() else HealthStatus.INFO
        return self.result(status, "Dosya yolu güvenliği servis varlığı değerlendirildi.", detail=str(security_file))


class SensitiveLogCheck(BaseHealthCheck):
    name = "Hassas log kontrolü"
    category = "Güvenlik"
    source = "app.health.checks.security_check.SensitiveLogCheck"

    def run(self, context: HealthContext):
        patterns = ("password", "token", "api_key", "secret")
        findings: list[str] = []
        for log_file in (context.root_path / "logs").glob("*.log") if (context.root_path / "logs").exists() else []:
            text = Path(log_file).read_text(encoding="utf-8", errors="ignore")[-10000:]
            if any(pattern in text.lower() for pattern in patterns):
                findings.append(str(log_file))
        status = HealthStatus.WARNING if findings else HealthStatus.OK
        return self.result(
            status,
            "Loglarda temel hassas veri pattern taraması yapıldı.",
            detail=f"Bulgu dosyası: {len(findings)}",
            suggestion="Loglarda token/secret/kişisel veri yazılmadığını düzenli kontrol edin.",
            metadata={"findings": findings},
        )
