# -*- coding: utf-8 -*-
"""ML governance API request/response modelleri."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MLAlgorithmUpdateRequest(BaseModel):
    usage_role: str | None = None
    default_enabled: bool | None = None
    min_training_samples: int | None = Field(default=None, ge=1)
    min_samples_per_class: int | None = Field(default=None, ge=1)
    notes: str | None = None


class MLTrainRequest(BaseModel):
    algorithm_key: str = "random_forest"
    year: int | None = None
    faculty_id: int | None = None
    department_id: int | None = None
    created_by: str | None = None


class MLPredictCourseRequest(BaseModel):
    algorithm_key: str = "random_forest"
    course_id: int
    year: int
    faculty_id: int | None = None
    department_id: int | None = None
    prediction_type: str = "status"


class MLPredictBatchRequest(BaseModel):
    algorithm_key: str = "random_forest"
    course_ids: list[int]
    year: int
    faculty_id: int | None = None
    department_id: int | None = None


class MLReadinessReportRequest(BaseModel):
    year: int | None = None
    faculty_id: int | None = None
    department_id: int | None = None
    save: bool = True


class MLFeatureSnapshotRequest(BaseModel):
    year: int | None = None
    faculty_id: int | None = None
    department_id: int | None = None
    scope: dict[str, Any] | None = None
    save_snapshot: bool = True
