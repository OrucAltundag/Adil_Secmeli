# -*- coding: utf-8 -*-
"""FastAPI sağlık kontrolleri (uvicorn başlatmaz, yalnızca introspeksiyon)."""

from __future__ import annotations

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _ApiCheck(BaseHealthCheck):
    category = "API"
    score_bucket = "api_ui"

    def _load_app(self):
        from app.api.main import app

        return app


class ApiAppLoadCheck(_ApiCheck):
    name = "FastAPI uygulama yükleme kontrolü"
    default_severity = HealthSeverity.HIGH

    def run(self, context: HealthContext) -> HealthCheckResult:
        try:
            app = self._load_app()
        except Exception as exc:  # noqa: BLE001
            return self.critical(
                "FastAPI uygulaması oluşturulamadı.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="app/api/main.py import hatalarını giderin.",
            )
        title = getattr(app, "title", "")
        return self.ok(
            "FastAPI uygulaması yükleniyor.",
            detail=f"title='{title}'",
            metadata={"title": title},
        )


class ApiRouterCheck(_ApiCheck):
    name = "API router/endpoint kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        try:
            app = self._load_app()
            routes = [getattr(r, "path", "") for r in app.routes]
        except Exception as exc:  # noqa: BLE001
            return self.warning(
                "API route'ları okunamadı.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="Router kayıtlarını kontrol edin.",
            )
        api_routes = [p for p in routes if p.startswith("/api")]
        if not api_routes:
            return self.warning(
                "Kayıtlı API endpoint'i görünmüyor.",
                detail=f"Toplam route: {len(routes)}",
                suggestion="routes.router include edildiğini doğrulayın.",
            )
        return self.ok(
            f"API endpoint'leri kayıtlı ({len(api_routes)} /api yolu).",
            detail=f"Toplam route: {len(routes)}",
            metadata={"api_routes": len(api_routes)},
        )


class ApiMiddlewareCheck(_ApiCheck):
    name = "API middleware/exception handler kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        try:
            app = self._load_app()
            mw = len(getattr(app, "user_middleware", []) or [])
            handlers = len(getattr(app, "exception_handlers", {}) or {})
        except Exception as exc:  # noqa: BLE001
            return self.warning(
                "Middleware bilgisi okunamadı.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="app/api/main.py middleware kurulumunu inceleyin.",
            )
        if mw == 0 or handlers == 0:
            return self.warning(
                "Middleware veya exception handler eksik görünüyor.",
                detail=f"middleware={mw}, exception_handlers={handlers}",
                suggestion="Rate limit/CORS middleware ve hata yakalayıcıyı ekleyin.",
            )
        return self.ok(
            "API middleware ve exception handler mevcut.",
            detail=f"middleware={mw}, exception_handlers={handlers}",
        )


class ApiCorsSecurityCheck(_ApiCheck):
    name = "API CORS güvenlik kontrolü"
    score_bucket = "security"
    default_severity = HealthSeverity.HIGH

    def run(self, context: HealthContext) -> HealthCheckResult:
        cfg = context.app_config
        if cfg.environment == "production":
            origins = (cfg.cors_allowed_origins or "").strip()
            if not origins or origins == "*":
                return self.warning(
                    "Production'da CORS wildcard (*) riski.",
                    detail=f"cors_allowed_origins='{origins or 'boş'}'",
                    suggestion="Production'da CORS_ALLOWED_ORIGINS açıkça tanımlayın.",
                )
        return self.ok(
            "CORS yapılandırması ortamla uyumlu.",
            detail=f"environment={cfg.environment}",
        )
