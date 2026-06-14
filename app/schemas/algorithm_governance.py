# -*- coding: utf-8 -*-
"""Algoritma yönetişimi API şemaları."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AlgorithmGovernanceUpdateRequest(BaseModel):
    usage_role: str | None = None
    can_affect_final_decision: bool | None = None
    minimum_sample_count: int | None = None
    user_facing_warning: str | None = None
    is_active: bool | None = None


class AlgorithmActiveRequest(BaseModel):
    is_active: bool


class DataGuardCheckRequest(BaseModel):
    algorithm_key: str
    task_type: str | None = None
    sample_count: int | None = None
    feature_count: int | None = None
    n_clusters: int | None = None
    X: list[Any] | None = None
    y: list[Any] | None = None


class GovernedBenchmarkRunRequest(BaseModel):
    run_name: str | None = None
    task_type: str = "classification"
    task_key: str | None = None
    dataset_name: str | None = None
    dataset_scope: dict[str, Any] | None = None
    algorithms: list[str] = Field(default_factory=lambda: ["rule_based_baseline"])
    X: list[Any] | None = None
    y_true: list[Any] | None = None
    y: list[Any] | None = None
    y_score: list[Any] | None = None
    predictions_by_algorithm: dict[str, list[Any]] | None = None
    labels_by_algorithm: dict[str, list[Any]] | None = None
    clusters: list[Any] | None = None
    scores: list[float] | None = None
    feature_names: list[str] | None = None
    target_column: str | None = None
    primary_metric_name: str | None = None
    sample_count: int | None = None
    feature_count: int | None = None
    n_clusters: int | None = None
    years: list[int] | None = None
    group_key: str | None = None
    group_count: int | None = None
    train_years: list[int] | None = None
    test_years: list[int] | None = None
    entity_ids: dict[str, list[Any]] | None = None
    created_by: str | None = None

    def to_payload(self) -> dict[str, Any]:
        if hasattr(self, "model_dump"):
            return self.model_dump(exclude_none=True)
        return self.dict(exclude_none=True)
