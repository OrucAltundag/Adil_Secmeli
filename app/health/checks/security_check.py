# -*- coding: utf-8 -*-
"""Güvenlik sağlık kontrolleri."""

from __future__ import annotations

import re

from app.core.permissions import can
from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _SecurityCheck(BaseHealthCheck):
    category = "Güvenlik"
    score_bucket = "security"


class SQLConsolePermissionCheck(_SecurityCheck):
    name = "SQL Console yetki kontrolü"
    quick = True
    default_severity = HealthSeverity.CRITICAL

    def run(self, context: HealthContext) -> HealthCheckResult:
        cfg = context.app_config
        enabled = cfg.enable_sql_console
        allowed = can(
            context.user_context, "use_sql_console", config=cfg
        )
        is_prod = cfg.environment == "production"
        if not enabled:
            return self.ok(
                "SQL Console kapalı.",
                detail="enable_sql_console = False",
            )
        if is_prod and enabled:
            return self.critical(
                "SQL Console production ortamında açık.",
                detail=f"environment={cfg.environment}, enabled={enabled}",
                suggestion="Production'da SQL Console'u kapatın.",
                metadata={"enabled": enabled, "environment": cfg.environment},
            )
        if enabled and not allowed:
            return self.warning(
                "SQL Console açık ancak mevcut kullanıcı yetkili değil.",
                detail="Yetki politikası erişimi engelliyor (beklenen davranış).",
                suggestion="Yalnızca geliştirici/yönetici erişimi olmalı.",
            )
        return self.ok(
            "SQL Console yalnızca yetkili (developer/admin) modda açık.",
            detail=f"enabled={enabled}, allowed={allowed}, env={cfg.environment}",
        )


class UnsafeSQLPatternCheck(_SecurityCheck):
    name = "Riskli SQL deseni koruması kontrolü"
    default_severity = HealthSeverity.HIGH

    DANGEROUS = ("DROP ", "DELETE ", "ALTER ", "TRUNCATE", "UPDATE ")

    def run(self, context: HealthContext) -> HealthCheckResult:
        try:
            from app.services import sql_console_service

            source = ""
            module_file = getattr(sql_console_service, "__file__", None)
            if module_file:
                with open(module_file, "r", encoding="utf-8", errors="ignore") as fh:
                    source = fh.read().upper()
        except Exception as exc:  # noqa: BLE001
            return self.info(
                "SQL Console servisi incelenemedi.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="sql_console_service modülünü kontrol edin.",
            )
        guards = [kw for kw in ("DROP", "DELETE", "ALTER", "READ_ONLY", "READONLY") if kw in source]
        if not guards:
            return self.warning(
                "Riskli SQL komutları için koruma görünmüyor.",
                detail="sql_console_service içinde DROP/DELETE/ALTER denetimi tespit edilemedi.",
                suggestion="Kullanıcı sorgularında riskli komutları filtreleyin.",
            )
        return self.ok(
            "Riskli SQL desenleri için koruma mantığı mevcut.",
            detail="Tespit edilen koruma anahtarları: " + ", ".join(sorted(set(guards))),
        )


class PathTraversalCheck(_SecurityCheck):
    name = "Path traversal koruması kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        try:
            from app.services import file_upload_security_service

            module_file = getattr(file_upload_security_service, "__file__", "")
            text = ""
            if module_file:
                with open(module_file, "r", encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
        except Exception as exc:  # noqa: BLE001
            return self.info(
                "Dosya güvenlik servisi incelenemedi.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="file_upload_security_service modülünü kontrol edin.",
            )
        markers = ("..", "basename", "abspath", "realpath", "normpath", "traversal")
        found = [m for m in markers if m in text]
        if not found:
            return self.warning(
                "Path traversal koruması açıkça görünmüyor.",
                detail="Dosya güvenlik servisinde yol normalizasyonu işareti yok.",
                suggestion="Dosya yollarını normalize edip taban dizine kısıtlayın.",
            )
        return self.ok(
            "Dosya yolu doğrulama/normalizasyon mantığı mevcut.",
            detail="Tespit edilen işaretler: " + ", ".join(found),
        )


class SensitiveLogCheck(_SecurityCheck):
    name = "Loglarda hassas veri kontrolü"
    default_severity = HealthSeverity.HIGH

    PATTERNS = re.compile(
        r"(password\s*[=:]\s*\S+|token\s*[=:]\s*\S+|secret\s*[=:]\s*\S+|api[_-]?key\s*[=:]\s*\S+)",
        re.IGNORECASE,
    )

    def run(self, context: HealthContext) -> HealthCheckResult:
        logs_dir = context.health_config.logs_path()
        if not logs_dir.exists():
            return self.info(
                "Log klasörü bulunamadı.",
                detail=str(logs_dir),
                suggestion="Loglama yapılandırmasını kontrol edin.",
            )
        hits: list[str] = []
        for log_file in logs_dir.glob("*.log"):
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as fh:
                    for idx, line in enumerate(fh, 1):
                        if self.PATTERNS.search(line):
                            hits.append(f"{log_file.name}:{idx}")
                            if len(hits) >= 10:
                                break
            except Exception:  # noqa: BLE001
                continue
        if hits:
            return self.warning(
                "Loglarda hassas veri kalıbı tespit edildi.",
                detail="Şüpheli satırlar:\n- " + "\n- ".join(hits),
                suggestion="Loglardan şifre/token/anahtar bilgilerini maskeleyin.",
                metadata={"hits": len(hits)},
            )
        return self.ok(
            "Loglarda belirgin hassas veri kalıbı yok.",
            detail="password/token/secret/api_key kalıbı bulunamadı.",
        )


class DeveloperModeCheck(_SecurityCheck):
    name = "Geliştirici modu kontrolü"
    quick = True
    default_severity = HealthSeverity.HIGH

    def run(self, context: HealthContext) -> HealthCheckResult:
        cfg = context.app_config
        if cfg.environment == "production" and cfg.enable_developer_tools:
            return self.critical(
                "Geliştirici modu production ortamında açık.",
                detail=f"environment={cfg.environment}, enable_developer_tools=True",
                suggestion="Production'da ENABLE_DEVELOPER_TOOLS=false yapın.",
            )
        return self.ok(
            "Geliştirici modu ortamla uyumlu.",
            detail=f"environment={cfg.environment}, "
            f"developer_tools={cfg.enable_developer_tools}",
        )
