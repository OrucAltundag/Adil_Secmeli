# =============================================================================
# app/api/main.py — REST API Giriş Noktası (Üniversite Entegrasyonu)
# =============================================================================
# Bu modül FastAPI uygulamasını tanımlar. OBS, kayıt sistemi vb. dış sistemler
# ile entegrasyon için REST endpoint'leri sağlar.
#
# Çalıştırma: python -m uvicorn app.api.main:app --reload --host 0.0.0.0
# =============================================================================

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.api import routes
from app.core.config import load_app_config
from app.core.errors import AppError, app_error_from_exception
from app.core.logging_config import configure_logging
from app.dashboard import api_routes as benchmark_routes
from app.api import security_routes
from app.api.middleware.rate_limit import rate_limit_middleware
from fastapi.middleware.cors import CORSMiddleware

config = load_app_config()
configure_logging(config)

app = FastAPI(
    title=f"{config.project_name} API",
    version=config.version,
    description="Fakülte bazlı seçmeli ders öneri ve atama sistemi - Üniversite entegrasyonu"
)

# CORS configuration
allow_origins = ["*"]
if config.environment == "production":
    if config.cors_allowed_origins:
        allow_origins = [o.strip() for o in config.cors_allowed_origins.split(",") if o.strip()]
    else:
        # Warning, shouldn't use * in production
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("SECURITY WARNING: CORS_ALLOWED_ORIGINS is not set in production!")
        allow_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=config.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

from starlette.middleware.base import BaseHTTPMiddleware
app.add_middleware(BaseHTTPMiddleware, dispatch=rate_limit_middleware)

app.include_router(routes.router, prefix="/api/v1", tags=["v1"])
app.include_router(benchmark_routes.router, prefix="/api/v1/benchmark", tags=["benchmark"])
app.include_router(security_routes.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "Adil Seçmeli API", "docs": "/docs"}


def _health_allowed_full() -> bool:
    """Ağır/teknik health yalnızca developer/admin (production değil) için."""

    return bool(config.enable_developer_tools and config.environment != "production")


def _public_health_payload(report) -> dict:
    """Production'da hassas teknik detay/yol döndürmeyen özet."""

    return {
        "overall_status": report.overall_status,
        "score": round(float(report.score), 1),
        "total_checks": report.total_checks,
        "ok_count": report.ok_count,
        "warning_count": report.warning_count,
        "critical_count": report.critical_count,
        "failed_count": report.failed_count,
        "generated_at": report.generated_at,
    }


@app.get("/health", tags=["health"])
def health():
    """Hafif sağlık özeti (public-safe). Teknik detay döndürmez."""

    from app.services.health_service import run_quick_health_check

    report = run_quick_health_check(config=config)
    return _public_health_payload(report)


@app.get("/health/full", tags=["health"])
def health_full(request: Request):
    """Tam sağlık raporu — yalnızca developer/admin (production dışı)."""

    if not _health_allowed_full():
        return JSONResponse(
            status_code=403,
            content={
                "success": False,
                "message": "Tam sağlık raporu yalnızca geliştirici modunda erişilebilir.",
            },
        )
    from app.services.health_service import run_full_health_check

    return run_full_health_check(config=config).to_dict()


@app.get("/health/algorithms", tags=["health"])
def health_algorithms():
    """Algoritma/kontrol kataloğu (ACTIVE/PLANNED/NOT_APPLICABLE)."""

    from app.services.health_service import list_algorithm_catalog

    return {"algorithms": list_algorithm_catalog()}


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content=exc.to_api_response())


@app.exception_handler(Exception)
async def unexpected_error_handler(_request: Request, exc: Exception):
    app_error = app_error_from_exception(exc)
    return JSONResponse(status_code=500, content=app_error.to_api_response())
