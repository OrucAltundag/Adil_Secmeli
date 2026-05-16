# -*- coding: utf-8 -*-
"""Sağlık kontrolleri için ortak veri modelleri."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class HealthStatus(str, Enum):
    OK = "OK"
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class HealthSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass(slots=True)
class HealthCheckResult:
    category: str
    name: str
    status: str
    severity: str
    message: str
    detail: str
    suggestion: str
    duration_ms: float
    timestamp: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class HealthReport:
    overall_status: str
    score: int
    total_checks: int
    ok_count: int
    warning_count: int
    critical_count: int
    failed_count: int
    skipped_count: int
    results: list[HealthCheckResult]
    generated_at: str
    summary_message: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["results"] = [item.to_dict() for item in self.results]
        return data


@dataclass(slots=True)
class HealthContext:
    db_path: str
    config: Any
    root_path: Path
    mode: str = "quick"
    developer_mode: bool = False
    user_context: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
