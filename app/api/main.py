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

config = load_app_config()
configure_logging(config)

app = FastAPI(
    title=f"{config.project_name} API",
    version=config.version,
    description="Fakülte bazlı seçmeli ders öneri ve atama sistemi - Üniversite entegrasyonu"
)

app.include_router(routes.router, prefix="/api/v1", tags=["v1"])
app.include_router(benchmark_routes.router, prefix="/api/v1/benchmark", tags=["benchmark"])


@app.get("/")
def root():
    return {"message": "Adil Seçmeli API", "docs": "/docs"}


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content=exc.to_api_response())


@app.exception_handler(Exception)
async def unexpected_error_handler(_request: Request, exc: Exception):
    app_error = app_error_from_exception(exc)
    return JSONResponse(status_code=500, content=app_error.to_api_response())
