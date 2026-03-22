# -*- coding: utf-8 -*-
# =============================================================================
# app/core/config.py — Uygulama Yapilandirma Sabitleri
# =============================================================================
# Proje adi, versiyon, varsayilan veritabani yolu ve algoritma agirliklari.
# Settings sinifi tum yapilandirma degerlerini merkezi olarak tutar.
# =============================================================================
import os


class Settings:
    """Uygulama geneli yapilandirma degerleri."""

    PROJECT_NAME: str = "Adil Secmeli Ders Asistani"
    VERSION: str = "1.0.0"
    
    # Veritabani Yolu (Otomatik olarak data klasorunu bulur)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DB_NAME = "adil_secmeli.db"
    DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'data', DB_NAME)}"

    # Algoritma Agirliklari (Varsayilan AHP baslangic degerleri)
    WEIGHTS = {
        "performance": 0.5,
        "popularity": 0.3,
        "survey": 0.2
    }

settings = Settings()
