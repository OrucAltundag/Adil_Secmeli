# -*- coding: utf-8 -*-
"""Uygulama başlangıç (startup) sağlık kontrolleri."""

from __future__ import annotations

import importlib

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _StartupCheck(BaseHealthCheck):
    category = "Başlangıç"
    score_bucket = "ops"


class AppEntrypointCheck(_StartupCheck):
    name = "Uygulama giriş noktası kontrolü"
    quick = True
    default_severity = HealthSeverity.HIGH

    def run(self, context: HealthContext) -> HealthCheckResult:
        try:
            main_mod = importlib.import_module("app.main")
        except Exception as exc:  # noqa: BLE001
            return self.critical(
                "Uygulama giriş modülü import edilemiyor.",
                detail=f"app.main: {type(exc).__name__}: {exc}",
                suggestion="app/main.py import hatalarını giderin.",
            )
        has_app = hasattr(main_mod, "AdilSecmeliApp")
        has_main = hasattr(main_mod, "main")
        if not (has_app and has_main):
            return self.warning(
                "Beklenen giriş bileşenleri eksik.",
                detail=f"AdilSecmeliApp={has_app}, main()={has_main}",
                suggestion="app/main.py içinde AdilSecmeliApp ve main() bulunmalı.",
            )
        return self.ok(
            "Uygulama giriş noktası sağlıklı.",
            detail="app.main: AdilSecmeliApp + main() mevcut.",
        )


class StartupConfigCheck(_StartupCheck):
    name = "Başlangıç yapılandırması kontrolü"
    quick = True
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        cfg = context.app_config
        if not cfg.database_url:
            return self.critical(
                "Veritabanı bağlantı adresi tanımlı değil.",
                detail="config.database_url boş.",
                suggestion="config.json/.env içinde DATABASE_URL tanımlayın.",
            )
        return self.ok(
            "Başlangıç yapılandırması yüklendi.",
            detail=f"mode={cfg.app_mode}, env={cfg.environment}, "
            f"backend={cfg.db_backend}",
            metadata={"environment": cfg.environment},
        )


class StartupDatabaseInitCheck(_StartupCheck):
    name = "Veritabanı başlatma fonksiyonu kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        try:
            from app.db.session import init_database  # noqa: F401
        except Exception as exc:  # noqa: BLE001
            return self.critical(
                "init_database import edilemedi.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="app/db/session.py modülünü kontrol edin.",
            )
        return self.ok(
            "Veritabanı başlatma fonksiyonu erişilebilir.",
            detail="app.db.session.init_database import edilebiliyor.",
        )
