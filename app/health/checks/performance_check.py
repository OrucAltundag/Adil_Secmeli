# -*- coding: utf-8 -*-
"""Performans sağlık kontrolleri."""

from __future__ import annotations

import importlib.util
from time import perf_counter

from app.health.checks.base_check import BaseHealthCheck
from app.health.health_config import DB_CONNECTION_CRITICAL_MS, DB_CONNECTION_WARNING_MS, QUERY_CRITICAL_MS, QUERY_WARNING_MS
from app.health.models import HealthContext, HealthSeverity, HealthStatus
from app.repositories.sqlite_repository import SQLiteRepository


class DatabaseConnectionTimeCheck(BaseHealthCheck):
    name = "DB bağlantı süresi kontrolü"
    category = "Performans"
    severity = HealthSeverity.MEDIUM.value
    source = "app.health.checks.performance_check.DatabaseConnectionTimeCheck"

    def run(self, context: HealthContext):
        started = perf_counter()
        SQLiteRepository(context.db_path).execute_scalar("SELECT 1")
        elapsed_ms = (perf_counter() - started) * 1000.0
        if elapsed_ms > DB_CONNECTION_CRITICAL_MS:
            status = HealthStatus.CRITICAL
            severity = HealthSeverity.HIGH
        elif elapsed_ms > DB_CONNECTION_WARNING_MS:
            status = HealthStatus.WARNING
            severity = HealthSeverity.MEDIUM
        else:
            status = HealthStatus.OK
            severity = HealthSeverity.LOW
        return self.result(
            status,
            "DB bağlantı süresi ölçüldü.",
            severity=severity,
            detail=f"{elapsed_ms:.2f} ms",
            suggestion="Bağlantı süresi yüksekse DB dosya konumunu, disk erişimini ve antivirüs taramasını kontrol edin.",
            metadata={"elapsed_ms": elapsed_ms},
        )


class QueryPerformanceCheck(BaseHealthCheck):
    name = "Kritik sorgu performans kontrolü"
    category = "Performans"
    severity = HealthSeverity.MEDIUM.value
    source = "app.health.checks.performance_check.QueryPerformanceCheck"

    def run(self, context: HealthContext):
        repo = SQLiteRepository(context.db_path)
        queries = [
            ("table_count", "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"),
            ("ders_count", "SELECT COUNT(*) FROM ders" if "ders" in set(repo.table_names()) else "SELECT 0"),
        ]
        timings = []
        max_ms = 0.0
        for name, sql in queries:
            started = perf_counter()
            value = repo.execute_scalar(sql)
            elapsed_ms = (perf_counter() - started) * 1000.0
            max_ms = max(max_ms, elapsed_ms)
            timings.append({"name": name, "elapsed_ms": elapsed_ms, "value": value})
        if max_ms > QUERY_CRITICAL_MS:
            status = HealthStatus.CRITICAL
            severity = HealthSeverity.HIGH
        elif max_ms > QUERY_WARNING_MS:
            status = HealthStatus.WARNING
            severity = HealthSeverity.MEDIUM
        else:
            status = HealthStatus.OK
            severity = HealthSeverity.LOW
        return self.result(
            status,
            "Kritik sorgu süreleri ölçüldü.",
            severity=severity,
            detail=f"Maksimum sorgu süresi: {max_ms:.2f} ms",
            suggestion="Yavaş sorgular için indeks, LIMIT ve sorgu planı kontrolü yapın.",
            metadata={"timings": timings},
        )


class FunctionExecutionTimeCheck(BaseHealthCheck):
    name = "Fonksiyon çalışma süresi kontrolü"
    category = "Performans"
    source = "app.health.checks.performance_check.FunctionExecutionTimeCheck"

    def run(self, context: HealthContext):
        started = perf_counter()
        len(SQLiteRepository(context.db_path).table_names())
        elapsed_ms = (perf_counter() - started) * 1000.0
        return self.result(HealthStatus.OK, "Temel fonksiyon çalışma süresi ölçüldü.", detail=f"{elapsed_ms:.2f} ms")


class MemoryUsageCheck(BaseHealthCheck):
    name = "Bellek kullanımı kontrolü"
    category = "Performans"
    source = "app.health.checks.performance_check.MemoryUsageCheck"

    def run(self, context: HealthContext):
        if importlib.util.find_spec("psutil") is None:
            return self.result(
                HealthStatus.SKIPPED,
                "psutil bağımlılığı olmadığı için bellek ölçümü atlandı.",
                suggestion="Bellek takibi gerekiyorsa psutil bağımlılığını ekleyin.",
            )
        import os

        import psutil

        process = psutil.Process(os.getpid())
        mb = process.memory_info().rss / (1024 * 1024)
        return self.result(HealthStatus.INFO, "Bellek kullanımı ölçüldü.", detail=f"{mb:.1f} MB", metadata={"rss_mb": mb})


class SlowQueryDetectionCheck(BaseHealthCheck):
    name = "Yavaş sorgu tespit kontrolü"
    category = "Performans"
    source = "app.health.checks.performance_check.SlowQueryDetectionCheck"

    def run(self, context: HealthContext):
        return self.result(
            HealthStatus.INFO,
            "Yavaş sorgu tespiti kritik sorgu süre ölçümüyle temel düzeyde yapılıyor.",
            suggestion="Ayrıntılı sorgu izleme için query wrapper seviyesinde süre logları ekleyin.",
        )
