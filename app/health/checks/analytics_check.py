# -*- coding: utf-8 -*-
"""Analiz & grafik sağlık kontrolleri."""

from __future__ import annotations

import importlib.util

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _AnalyticsCheck(BaseHealthCheck):
    category = "Analiz & Grafik"
    score_bucket = "reporting_analytics"


class AnalyticsDependencyCheck(_AnalyticsCheck):
    name = "Analiz bağımlılıkları kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        required = ("pandas", "numpy", "matplotlib")
        missing = [m for m in required if importlib.util.find_spec(m) is None]
        if missing:
            return self.warning(
                "Bazı analiz kütüphaneleri eksik.",
                detail="Eksik: " + ", ".join(missing),
                suggestion="'pip install -r requirements.txt' komutunu çalıştırın.",
                metadata={"missing": missing},
            )
        return self.ok(
            "Analiz/grafik bağımlılıkları mevcut.",
            detail="pandas, numpy, matplotlib bulundu.",
        )


class ChartGenerationCheck(_AnalyticsCheck):
    name = "Grafik üretimi kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        if importlib.util.find_spec("matplotlib") is None:
            return self.skipped(
                "matplotlib yok; grafik testi atlandı.",
                detail="matplotlib modülü bulunamadı.",
                suggestion="Grafik gerekiyorsa matplotlib kurun.",
            )
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots()
            ax.plot([0, 1, 2], [1, 3, 2])
            fig.canvas.draw()
            plt.close(fig)
        except Exception as exc:  # noqa: BLE001
            return self.warning(
                "Basit grafik üretilemedi.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="matplotlib backend (Agg) kurulumunu kontrol edin.",
            )
        return self.ok(
            "Basit grafik üretilebiliyor (Agg backend).",
            detail="Test figürü çizildi ve kapatıldı.",
        )


class NumericDataAvailabilityCheck(_AnalyticsCheck):
    name = "Analiz için sayısal veri kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            if not repo.table_exists("ders_kriterleri"):
                return self.info(
                    "Sayısal analiz verisi bulunamadı.",
                    detail="ders_kriterleri tablosu yok.",
                    suggestion="Kriter verisini import edin.",
                )
            count = repo.scalar(
                "SELECT COUNT(*) FROM ders_kriterleri "
                "WHERE basari_ortalamasi IS NOT NULL"
            )
        if not count:
            return self.info(
                "Analiz için yeterli sayısal veri yok.",
                detail="basari_ortalamasi dolu kayıt bulunamadı.",
                suggestion="Sayısal kriter verisi ekleyin.",
            )
        return self.ok(
            f"Analiz için sayısal veri mevcut ({count} kayıt).",
            detail="basari_ortalamasi dolu kayıtlar bulundu.",
            metadata={"numeric_rows": count},
        )


class EmptyDatasetHandlingCheck(_AnalyticsCheck):
    name = "Boş veri seti dayanıklılık kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        try:
            import pandas as pd

            df = pd.DataFrame({"x": [], "y": []})
            _ = df.describe(include="all")
            _ = df.head(10)
        except Exception as exc:  # noqa: BLE001
            return self.warning(
                "Boş veri setinde analiz hattı hata verdi.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="Boş veri durumunu açıkça ele alın.",
            )
        return self.ok(
            "Boş veri seti çökme olmadan ele alınıyor.",
            detail="Boş DataFrame describe/head çağrıları sorunsuz.",
        )
