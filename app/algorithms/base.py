"""Core algorithm contracts for the benchmarking platform."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Mapping


@dataclass(slots=True)
class AlgorithmOutput:
    """Normalized output schema shared by all algorithms."""

    algorithm_name: str
    task_type: str
    predictions: list[Any] = field(default_factory=list)
    recommendations: list[Any] = field(default_factory=list)
    assignments: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    explanation: str = ""
    runtime_ms: float = 0.0
    parameters: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "algorithm_name": self.algorithm_name,
            "task_type": self.task_type,
            "predictions": self.predictions,
            "recommendations": self.recommendations,
            "assignments": self.assignments,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "runtime_ms": self.runtime_ms,
            "parameters": self.parameters,
            "artifacts": self.artifacts,
        }


class IAlgorithm(ABC):
    """Base contract for all algorithm families."""

    def __init__(self, name: str, task_type: str, parameters: Mapping[str, Any] | None = None) -> None:
        self.name = name
        self.task_type = task_type
        self.parameters = dict(parameters or {})

    @property
    def is_fitted(self) -> bool:
        return bool(getattr(self, "_is_fitted", False))

    @abstractmethod
    def fit(self, X: Any, y: Any | None = None) -> "IAlgorithm":
        """Fit internal state using training data."""

    @abstractmethod
    def predict(self, X: Any) -> AlgorithmOutput:
        """Produce predictions for supervised tasks."""

    @abstractmethod
    def recommend(self, X: Any, top_k: int = 5) -> AlgorithmOutput:
        """Produce ranked recommendations."""

    @abstractmethod
    def score(self, X: Any, y: Any | None = None) -> float:
        """Return a scalar quality score."""

    @abstractmethod
    def explain(self, X: Any | None = None) -> str:
        """Return human-readable explanation metadata."""

    def _start_timer(self) -> float:
        return perf_counter()

    def _build_output(
        self,
        started_at: float,
        *,
        predictions: list[Any] | None = None,
        recommendations: list[Any] | None = None,
        assignments: list[dict[str, Any]] | None = None,
        confidence: float = 0.0,
        explanation: str = "",
        artifacts: Mapping[str, Any] | None = None,
    ) -> AlgorithmOutput:
        return AlgorithmOutput(
            algorithm_name=self.name,
            task_type=self.task_type,
            predictions=list(predictions or []),
            recommendations=list(recommendations or []),
            assignments=list(assignments or []),
            confidence=float(confidence),
            explanation=explanation,
            runtime_ms=(perf_counter() - started_at) * 1000.0,
            parameters=dict(self.parameters),
            artifacts=dict(artifacts or {}),
        )


class IPredictor(IAlgorithm, ABC):
    """Contract for predictive models."""

    @abstractmethod
    def predict_proba(self, X: Any) -> list[list[float]]:
        """Return class probabilities."""


class IRanker(IAlgorithm, ABC):
    """Contract for ranking/recommendation models."""

    @abstractmethod
    def rank(self, X: Any, top_k: int = 5) -> AlgorithmOutput:
        """Return ranked items for each input entity."""


class IAllocator(IAlgorithm, ABC):
    """Contract for allocation/optimization models."""

    @abstractmethod
    def allocate(self, students: Any, courses: Any, preferences: Any) -> AlgorithmOutput:
        """Allocate students to courses under constraints."""


class IClusterer(IAlgorithm, ABC):
    """Contract for clustering models."""

    @abstractmethod
    def cluster(self, X: Any) -> AlgorithmOutput:
        """Return cluster labels and clustering artifacts."""
