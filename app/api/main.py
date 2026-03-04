# =============================================================================
# app/api/main.py — REST API Giriş Noktası (Üniversite Entegrasyonu)
# =============================================================================
# Bu modül FastAPI uygulamasını tanımlar. OBS, kayıt sistemi vb. dış sistemler
# ile entegrasyon için REST endpoint'leri sağlar.
#
# Çalıştırma: python -m uvicorn app.api.main:app --reload --host 0.0.0.0
# =============================================================================

from fastapi import FastAPI
from app.api import routes

app = FastAPI(
    title="Adil Seçmeli API",
    version="1.0.0",
    description="Fakülte bazlı seçmeli ders öneri ve atama sistemi — Üniversite entegrasyonu"
)

app.include_router(routes.router, prefix="/api/v1", tags=["v1"])


@app.get("/")
def root():
    return {"message": "Adil Seçmeli API", "docs": "/docs"}
