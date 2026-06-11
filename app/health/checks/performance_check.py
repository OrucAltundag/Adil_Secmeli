# -*- coding: utf-8 -*-
"""Performans sağlık kontrolleri."""

from __future__ import annotations

import importlib.util
import time

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _PerfCheck(BaseHealthCheck):
    category = "Performans"
    score_bucket = "database"


class DatabaseConnectionTimeCheck(_PerfCheck):
    name = "Veritabanı bağlantı süresi kontrolü"
    quick = True
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        database = context.require_database()
        if not database.is_sqlite():
            return self.skipped(
                "SQLite dışı backend; bağlantı süre testi atlandı.",
                detail=f"database_url={context.app_config.database_url}",
            )
        elapsed = database.measure_connection_ms()
        th = context.health_config.thresholds
        meta = {"connect_ms": round(elapsed, 1)}
        if elapsed <= th.connection_ok_ms:
            return self.ok(
                f"Bağlantı süresi iyi ({elapsed:.1f} ms).",
                detail=f"Eşik: {th.connection_ok_ms:.0f} ms",
                metadata=meta,
            )
        if elapsed <= th.connection_warning_ms:
            return self.warning(
                f"Bağlantı süresi yüksek ({elapsed:.1f} ms).",
                detail=f"{th.connection_ok_ms:.0f}–{th.connection_warning_ms:.0f} ms",
                suggestion="Disk/IO veya DB boyutunu inceleyin.",
                metadata=meta,
            )
        return self.critical(
            f"Bağlantı süresi çok yüksek ({elapsed:.1f} ms).",
            detail=f"Eşik aşıldı: > {th.connection_warning_ms:.0f} ms",
            suggestion="Veritabanı dosyasını/diski ve kilitleri inceleyin.",
            metadata=meta,
        )


class QueryPerformanceCheck(_PerfCheck):
    name = "Sorgu performansı kontrolü"
    default_severity = HealthSeverity.MEDIUM

    def run(self, context: HealthContext) -> HealthCheckResult:
        th = context.health_config.thresholds
        timings: dict[str, float] = {}
        with context.repository() as repo:
            set(repo.table_names())
            for label, sql in context.health_config.performance_queries.items():
                start = time.perf_counter()
                try:
                    repo.fetchall(sql)
                except Exception:  # noqa: BLE001 - eksik tablo vb. tolere edilir
                    continue
                timings[label] = (time.perf_counter() - start) * 1000.0
        if not timings:
            return self.info(
                "Ölçülecek kritik sorgu çalıştırılamadı.",
                detail="Tanımlı sorgular için tablolar mevcut olmayabilir.",
                suggestion="Şema/veri durumunu kontrol edin.",
            )
        worst = max(timings.values())
        detail = "\n".join(f"- {k}: {v:.1f} ms" for k, v in timings.items())
        meta = {"timings_ms": {k: round(v, 1) for k, v in timings.items()}}
        if worst > th.critical_ms:
            return self.critical(
                f"Bir sorgu çok yavaş ({worst:.0f} ms).",
                detail=detail,
                suggestion="Yavaş sorgulara indeks ekleyin / sorguyu optimize edin.",
                metadata=meta,
            )
        if worst > th.warning_ms:
            return self.warning(
                f"Bazı sorgular yavaş ({worst:.0f} ms).",
                detail=detail,
                suggestion="İndeks ve sorgu planını gözden geçirin.",
                metadata=meta,
            )
        return self.ok(
            f"Kritik sorgular hızlı (en kötü {worst:.0f} ms).",
            detail=detail,
            metadata=meta,
        )


class FunctionExecutionTimeCheck(_PerfCheck):
    name = "Kritik fonksiyon süre kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        start = time.perf_counter()
        try:
            from app.services.schema_health_service import check_schema_health

            check_schema_health(db_path=context.db_path, config=context.app_config)
        except Exception as exc:  # noqa: BLE001
            return self.info(
                "Fonksiyon süre ölçümü yapılamadı.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="schema_health_service çalışmasını kontrol edin.",
            )
        elapsed = (time.perf_counter() - start) * 1000.0
        if elapsed > context.health_config.thresholds.critical_ms:
            return self.warning(
                f"check_schema_health yavaş ({elapsed:.0f} ms).",
                detail=f"Eşik: {context.health_config.thresholds.critical_ms:.0f} ms",
                suggestion="Şema kontrol fonksiyonunu optimize edin.",
                metadata={"elapsed_ms": round(elapsed, 1)},
            )
        return self.ok(
            f"Kritik fonksiyon süresi kabul edilebilir ({elapsed:.0f} ms).",
            detail="check_schema_health ölçüldü.",
            metadata={"elapsed_ms": round(elapsed, 1)},
        )


class MemoryUsageCheck(_PerfCheck):
    name = "Bellek kullanımı kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        if importlib.util.find_spec("psutil") is None:
            return self.skipped(
                "psutil yüklü değil; bellek ölçümü atlandı.",
                detail="psutil modülü bulunamadı.",
                suggestion="Gerekirse 'pip install psutil' kurun (opsiyonel).",
            )
        try:
            import psutil

            proc = psutil.Process()
            rss_mb = proc.memory_info().rss / (1024 * 1024)
        except Exception as exc:  # noqa: BLE001
            return self.skipped(
                "Bellek ölçümü yapılamadı.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="psutil kurulumunu doğrulayın.",
            )
        return self.info(
            f"Süreç bellek kullanımı: {rss_mb:.0f} MB.",
            detail="psutil RSS ölçümü.",
            metadata={"rss_mb": round(rss_mb, 1)},
        )


class SlowQueryDetectionCheck(_PerfCheck):
    name = "Yavaş sorgu tespiti"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        slow: list[str] = []
        limit = context.health_config.slow_query_ms
        with context.repository() as repo:
            for label, sql in context.health_config.performance_queries.items():
                start = time.perf_counter()
                try:
                    repo.fetchall(sql)
                except Exception:  # noqa: BLE001
                    continue
                ms = (time.perf_counter() - start) * 1000.0
                if ms > limit:
                    slow.append(f"- {label}: {ms:.0f} ms")
        if slow:
            return self.warning(
                f"{len(slow)} yavaş sorgu tespit edildi.",
                detail="\n".join(slow),
                suggestion="İlgili sorgulara indeks ekleyin / optimize edin.",
                metadata={"slow_count": len(slow)},
            )
        return self.ok(
            "Yavaş sorgu tespit edilmedi.",
            detail=f"Eşik: {limit:.0f} ms",
        )
