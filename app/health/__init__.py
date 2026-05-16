# -*- coding: utf-8 -*-
"""Uygulama sağlık merkezi (health center) altyapısı.

Bu paket; veritabanı, şema, veri kalitesi, AHP/karar, raporlama, analiz,
güvenlik, performans, mimari, log, yedekleme ve UI sağlık kontrollerini
izole, geriye dönük uyumlu ve uygulamayı çökertmeyecek şekilde çalıştırır.

Kamuya açık giriş noktaları için ``app.services.health_service`` kullanın.
"""

from __future__ import annotations

from app.health.models import (
    HealthCheckResult,
    HealthReport,
    HealthSeverity,
    HealthStatus,
)

__all__ = [
    "HealthCheckResult",
    "HealthReport",
    "HealthSeverity",
    "HealthStatus",
]
