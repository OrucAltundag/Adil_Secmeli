# -*- coding: utf-8 -*-
"""Benchmark platformu sağlık kontrolleri."""

from __future__ import annotations

import time

from app.health.checks.base_check import BaseHealthCheck, HealthContext
from app.health.models import HealthCheckResult, HealthSeverity


class _BenchmarkCheck(BaseHealthCheck):
    category = "Benchmark"
    score_bucket = "reporting_analytics"


class BenchmarkDatasetCheck(_BenchmarkCheck):
    name = "Benchmark veri seti kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        with context.repository() as repo:
            havuz = repo.row_count("havuz") if repo.table_exists("havuz") else 0
        if havuz < 5:
            return self.info(
                "Benchmark için yeterli veri olmayabilir.",
                detail=f"havuz kayıt sayısı: {havuz} (öneri ≥ 5)",
                suggestion="Daha fazla havuz/karar verisi ekleyin.",
                metadata={"havuz": havuz},
            )
        return self.ok(
            f"Benchmark için yeterli veri var ({havuz} havuz kaydı).",
            detail="Benchmark senaryoları çalıştırılabilir.",
            metadata={"havuz": havuz},
        )


class BenchmarkExecutionCheck(_BenchmarkCheck):
    name = "Benchmark çalıştırma kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        try:
            from app.benchmark.registry import AlgorithmRegistry

            algos = AlgorithmRegistry().list_algorithms()
            ok = bool(algos)
        except Exception as exc:  # noqa: BLE001
            return self.info(
                "Benchmark kayıt defteri okunamadı.",
                detail=f"{type(exc).__name__}: {exc}",
                suggestion="Benchmark modülünü kontrol edin (opsiyonel).",
            )
        if not ok:
            return self.info(
                "Kayıtlı benchmark algoritması bulunamadı.",
                detail="registry.list_algorithms boş döndü.",
                suggestion="Benchmark algoritmalarını kaydedin.",
            )
        return self.ok(
            "Benchmark kayıt defteri çalışıyor.",
            detail=f"Kayıtlı algoritma sayısı: {len(algos)}",
            metadata={"algorithm_count": len(algos)},
        )


class RuntimeThresholdCheck(_BenchmarkCheck):
    name = "Benchmark çalışma süresi eşik kontrolü"
    default_severity = HealthSeverity.LOW

    def run(self, context: HealthContext) -> HealthCheckResult:
        start = time.perf_counter()
        with context.repository() as repo:
            repo.scalar("SELECT COUNT(*) FROM sqlite_master")
        elapsed = (time.perf_counter() - start) * 1000.0
        threshold = context.health_config.slow_query_ms
        if elapsed > threshold:
            return self.warning(
                "Temel sorgu süresi eşiğin üzerinde.",
                detail=f"{elapsed:.1f} ms > {threshold:.0f} ms",
                suggestion="Veritabanı boyutunu/indeksleri inceleyin.",
                metadata={"elapsed_ms": round(elapsed, 1)},
            )
        return self.ok(
            "Çalışma süresi eşik altında.",
            detail=f"{elapsed:.1f} ms ≤ {threshold:.0f} ms",
            metadata={"elapsed_ms": round(elapsed, 1)},
        )
