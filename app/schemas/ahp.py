# -*- coding: utf-8 -*-
"""AHP yönetişimi API request modelleri."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AHPCriterionRequest(BaseModel):
    criterion_key: str
    display_name: str
    description: str | None = None
    criterion_type: str = "score"
    is_benefit: bool = True
    default_enabled: bool = True
    min_value: float | None = None
    max_value: float | None = None
    normalization_method: str | None = "minmax"
    source_type: str | None = "manual"
    sort_order: int = 100
    is_active: bool = True


class AHPProfileCreateRequest(BaseModel):
    profile_name: str = Field(default="Yeni AHP Profili")
    profile_code: str | None = None
    scope_type: str = "global"
    faculty_id: int | None = None
    department_id: int | None = None
    year: int | None = None
    semester: str | None = None
    criteria_keys: list[str] | None = None
    pairwise_matrix: list[list[float]] | None = None
    weights: dict[str, float] | None = None
    source: str = "manual"
    status: str = "draft"
    created_by: str | None = None
    notes: str | None = None
    activate: bool = False


class AHPProfileUpdateRequest(BaseModel):
    profile_name: str | None = None
    profile_code: str | None = None
    scope_type: str | None = None
    faculty_id: int | None = None
    department_id: int | None = None
    year: int | None = None
    semester: str | None = None
    criteria_keys: list[str] | None = None
    pairwise_matrix: list[list[float]] | None = None
    weights: dict[str, float] | None = None
    source: str | None = None
    notes: str | None = None
    actor: str | None = None


class AHPRejectRequest(BaseModel):
    reason: str
    rejected_by: str | None = None


class AHPApprovalRequest(BaseModel):
    actor: str | None = None
    approved_by: str | None = None


class AHPCloneRequest(BaseModel):
    new_scope: dict[str, Any] | None = None
    new_year: int | None = None
    actor: str | None = None


class AHPCalculateRequest(BaseModel):
    criteria_keys: list[str]
    pairwise_matrix: list[list[float]]
    method: str = "geometric_mean"


class AHPSensitivityRequest(BaseModel):
    variation_percent: float = 0.05
