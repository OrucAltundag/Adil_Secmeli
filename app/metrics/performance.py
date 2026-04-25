"""Performance metrics and runtime profiler utilities."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
import tracemalloc


@dataclass(slots=True)
class PerformanceSnapshot:
    latency_ms: float
    throughput_per_sec: float
    memory_peak_mb: float

    def as_dict(self) -> dict[str, float]:
        return {
            "latency_ms": self.latency_ms,
            "throughput_per_sec": self.throughput_per_sec,
            "memory_peak_mb": self.memory_peak_mb,
        }


class PerformanceTracker:
    """Tracks latency, throughput, and memory usage for benchmarked calls."""

    def __init__(self, workload_size: int = 1) -> None:
        self.workload_size = max(int(workload_size), 1)
        self._start_time = 0.0
        self._stop_time = 0.0
        self._peak_memory_bytes = 0

    def __enter__(self) -> "PerformanceTracker":
        tracemalloc.start()
        self._start_time = perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._stop_time = perf_counter()
        _, peak = tracemalloc.get_traced_memory()
        self._peak_memory_bytes = peak
        tracemalloc.stop()

    def snapshot(self) -> PerformanceSnapshot:
        latency_ms = (self._stop_time - self._start_time) * 1000.0
        throughput = self.workload_size / max((self._stop_time - self._start_time), 1e-9)
        memory_peak_mb = self._peak_memory_bytes / (1024.0 * 1024.0)
        return PerformanceSnapshot(latency_ms=latency_ms, throughput_per_sec=throughput, memory_peak_mb=memory_peak_mb)

