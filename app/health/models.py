# -*- coding: utf-8 -*-
"""Sağlık kontrolü veri modelleri.

Tüm kontroller aynı :class:`HealthCheckResult` yapısını döndürür ve runner
bunları :class:`HealthReport` içinde toplar. Bu modül uygulamanın geri
kalanına bağımlı değildir; böylece her yerden güvenle import edilebilir.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class HealthStatus(str, Enum):
    """Tek bir kontrolün veya genel raporun durumu."""

    OK = "OK"
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    FIXED = "FIXED"

    @classmethod
    def coerce(cls, value: Any, default: "HealthStatus" = None) -> "HealthStatus":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).upper())
        except ValueError:
            return default or cls.OK


class HealthSeverity(str, Enum):
    """Bir bulgunun önem seviyesi."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def coerce(cls, value: Any, default: "HealthSeverity" = None) -> "HealthSeverity":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).upper())
        except ValueError:
            return default or cls.MEDIUM


# Kullanıcıya gösterilecek Türkçe durum etiketleri.
STATUS_LABELS_TR: dict[str, str] = {
    HealthStatus.OK.value: "Başarılı",
    HealthStatus.INFO.value: "Bilgi",
    HealthStatus.WARNING.value: "Uyarı",
    HealthStatus.CRITICAL.value: "Kritik",
    HealthStatus.FAILED.value: "Başarısız",
    HealthStatus.SKIPPED.value: "Atlandı",
    HealthStatus.FIXED.value: "Düzeltildi",
}

SEVERITY_LABELS_TR: dict[str, str] = {
    HealthSeverity.LOW.value: "Düşük",
    HealthSeverity.MEDIUM.value: "Orta",
    HealthSeverity.HIGH.value: "Yüksek",
    HealthSeverity.CRITICAL.value: "Kritik",
}

# Genel sağlık durumu bantları.
OVERALL_HEALTHY = "SAĞLIKLI"
OVERALL_WARNING = "UYARI"
OVERALL_RISKY = "RİSKLİ"
OVERALL_CRITICAL = "KRİTİK"


@dataclass
class HealthCheckResult:
    """Tek bir sağlık kontrolünün standart sonucu."""

    category: str
    name: str
    status: str = HealthStatus.OK.value
    severity: str = HealthSeverity.LOW.value
    message: str = ""
    detail: str = ""
    suggestion: str = ""
    duration_ms: float = 0.0
    timestamp: str = field(default_factory=_now)
    source: str = ""
    auto_fix_available: bool = False
    auto_fix_applied: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.status = HealthStatus.coerce(self.status).value
        self.severity = HealthSeverity.coerce(self.severity).value
        if not self.timestamp:
            self.timestamp = _now()

    @property
    def is_problem(self) -> bool:
        return self.status in {
            HealthStatus.WARNING.value,
            HealthStatus.CRITICAL.value,
            HealthStatus.FAILED.value,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "name": self.name,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
            "detail": self.detail,
            "suggestion": self.suggestion,
            "duration_ms": round(float(self.duration_ms), 2),
            "timestamp": self.timestamp,
            "source": self.source,
            "auto_fix_available": self.auto_fix_available,
            "auto_fix_applied": self.auto_fix_applied,
            "metadata": self.metadata,
        }


@dataclass
class HealthReport:
    """Tüm kontrollerin toplandığı genel sağlık raporu."""

    overall_status: str
    score: float
    total_checks: int
    ok_count: int
    warning_count: int
    critical_count: int
    failed_count: int
    skipped_count: int
    results: list[HealthCheckResult]
    generated_at: str = field(default_factory=_now)
    summary_message: str = ""
    info_count: int = 0
    fixed_count: int = 0
    mode: str = "full"
    duration_ms: float = 0.0
    category_scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "score": round(float(self.score), 1),
            "mode": self.mode,
            "total_checks": self.total_checks,
            "ok_count": self.ok_count,
            "info_count": self.info_count,
            "warning_count": self.warning_count,
            "critical_count": self.critical_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "fixed_count": self.fixed_count,
            "duration_ms": round(float(self.duration_ms), 2),
            "generated_at": self.generated_at,
            "summary_message": self.summary_message,
            "category_scores": {k: round(float(v), 1) for k, v in self.category_scores.items()},
            "results": [r.to_dict() for r in self.results],
        }

    def results_by_category(self) -> dict[str, list[HealthCheckResult]]:
        grouped: dict[str, list[HealthCheckResult]] = {}
        for result in self.results:
            grouped.setdefault(result.category, []).append(result)
        return grouped
