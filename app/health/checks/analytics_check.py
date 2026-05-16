# -*- coding: utf-8 -*-
"""Analiz ve grafik altyapısı sağlık kontrolleri."""

from __future__ import annotations

import importlib.util

from app.health.checks.base_check import BaseHealthCheck
from app.health.models import HealthContext, HealthSeverity, HealthStatus
from app.repositories.sqlite_repository import SQLiteRepository


class AnalyticsDependencyCheck(BaseHealthCheck):
    name = "Analiz bağımlılık kontrolü"
    category = "Raporlama / Analiz"
    severity = HealthSeverity.MEDIUM.value
    source = "app.health.checks.analytics_check.AnalyticsDependencyCheck"

    def run(self, context: HealthContext):
        packages = ("pandas", "numpy", "matplotlib", "seaborn")
        missing = [package for package in packages if importlib.util.find_spec(package) is None]
        if missing:
            return self.result(
                HealthStatus.WARNING,
                "Analiz/grafik için bazı bağımlılıklar eksik.",
                severity=HealthSeverity.MEDIUM,
                detail="Eksik paketler: " + ", ".join(missing),
                suggestion="requirements.txt kurulumunu doğrulayın.",
                metadata={"missing": missing},
            )
        return self.result(HealthStatus.OK, "Analiz/grafik bağımlılıkları kullanılabilir.", detail=", ".join(packages))


class ChartGenerationCheck(BaseHealthCheck):
    name = "Grafik üretim kontrolü"
    category = "Raporlama / Analiz"
    source = "app.health.checks.analytics_check.ChartGenerationCheck"

    def run(self, context: HealthContext):
        import matplotlib

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt

        fig = plt.figure()
        try:
            ax = fig.add_subplot(111)
            ax.plot([1, 2, 3], [1, 4, 9])
        finally:
            plt.close(fig)
        return self.result(HealthStatus.OK, "Basit grafik nesnesi üretilebildi.")


class NumericDataAvailabilityCheck(BaseHealthCheck):
    name = "Sayısal veri uygunluğu kontrolü"
    category = "Raporlama / Analiz"
    source = "app.health.checks.analytics_check.NumericDataAvailabilityCheck"

    def run(self, context: HealthContext):
        repo = SQLiteRepository(context.db_path)
        numeric_columns = []
        for table in repo.table_names()[:60]:
            for column in repo.columns(table):
                if any(token in column["type"].upper() for token in ("INT", "REAL", "FLOAT", "NUM", "DOUBLE")):
                    numeric_columns.append({"table": table, "column": column["name"], "type": column["type"]})
        status = HealthStatus.OK if numeric_columns else HealthStatus.WARNING
        return self.result(
            status,
            "Analiz için sayısal kolon varlığı değerlendirildi.",
            detail=f"Sayısal kolon sayısı: {len(numeric_columns)}",
            suggestion="Analiz ekranları için sayısal veri içeren tabloları doğrulayın.",
            metadata={"numeric_columns": numeric_columns[:100]},
        )


class EmptyDatasetHandlingCheck(BaseHealthCheck):
    name = "Boş veri seti davranışı kontrolü"
    category = "Raporlama / Analiz"
    source = "app.health.checks.analytics_check.EmptyDatasetHandlingCheck"

    def run(self, context: HealthContext):
        return self.result(
            HealthStatus.INFO,
            "Boş veri seti davranışı UI smoke testleriyle aşamalı doğrulanacak.",
            suggestion="Grafik ve tablo ekranlarında boş veri mesajlarını standartlaştırın.",
        )
