"""Canonical data entities used by the benchmark platform."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

import pandas as pd


@dataclass(slots=True)
class Student:
    student_id: int
    faculty_id: int | None = None
    department_id: int | None = None
    gender: str | None = None
    term: str | None = None
    gpa: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Course:
    course_id: int
    code: str | None = None
    name: str | None = None
    faculty_id: int | None = None
    department_id: int | None = None
    capacity: int | None = None
    difficulty_score: float | None = None
    instructor_effect_score: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Preference:
    student_id: int
    course_id: int
    rank: int
    score: float | None = None
    source: str = "real"


@dataclass(slots=True)
class SurveyResponse:
    student_id: int
    course_id: int
    satisfaction: float | None = None
    contribution: float | None = None
    general_sentiment: float | None = None
    factors: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Allocation:
    student_id: int
    course_id: int
    allocated: bool
    rank_received: int | None = None
    algorithm: str | None = None
    confidence: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MetricResult:
    run_id: str
    algorithm_name: str
    metric_group: str
    metric_name: str
    metric_value: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BenchmarkRun:
    run_id: str
    scenario_name: str
    dataset_name: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str = "running"
    algorithms: list[str] = field(default_factory=list)
    metrics: list[MetricResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["started_at"] = self.started_at.isoformat()
        payload["finished_at"] = self.finished_at.isoformat() if self.finished_at else None
        payload["metrics"] = [m.as_dict() for m in self.metrics]
        return payload


@dataclass(slots=True)
class DatasetBundle:
    dataset_name: str
    raw_real: dict[str, pd.DataFrame]
    derived: dict[str, pd.DataFrame] = field(default_factory=dict)
    synthetic: dict[str, pd.DataFrame] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def table(self, layer: str, name: str) -> pd.DataFrame:
        layer_map = {"raw_real": self.raw_real, "derived": self.derived, "synthetic": self.synthetic}
        if layer not in layer_map:
            raise KeyError(f"Unknown layer: {layer}")
        try:
            return layer_map[layer][name]
        except KeyError as exc:
            available = ", ".join(sorted(layer_map[layer].keys()))
            raise KeyError(f"Unknown table '{name}' in layer '{layer}'. Available: {available}") from exc
