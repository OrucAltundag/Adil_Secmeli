# -*- coding: utf-8 -*-
"""Ortak API response schemaları."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, validator

T = TypeVar("T")


class ServiceWarning(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    suggestion: str | None = None
    severity: str = "error"


class PaginationMeta(BaseModel):
    page: int = 1
    page_size: int = 100
    total: int | None = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    message: str | None = None
    warnings: list[Any] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class ApiErrorResponse(BaseModel):
    success: bool = False
    error: ErrorResponse


# ============================================================================
# Request Validation Schemas
# ============================================================================

from pydantic import ConfigDict

class YearFacultyValidation(BaseModel):
    """Base schema for endpoints requiring year and faculty."""
    model_config = ConfigDict(populate_by_name=True)
    
    year: int = Field(..., alias="yil", description="Akademik yıl (2023, 2024, etc.)")
    faculty_id: int | None = Field(None, alias="fakulte_id", description="Fakülte ID'si")

    @validator("year")
    def validate_year(cls, v):
        if v is None:
            raise ValueError("year/yil zorunludur")
        if v < 2000 or v > 2100:
            raise ValueError("year must be between 2000 and 2100")
        return v

    @validator("faculty_id")
    def validate_faculty_id(cls, v):
        if v is None:
            raise ValueError("faculty_id/fakulte_id zorunludur")
        return v


class YearValidation(BaseModel):
    """Base schema for endpoints requiring year."""
    model_config = ConfigDict(populate_by_name=True)
    
    year: int = Field(..., alias="yil", description="Akademik yıl (2023, 2024, etc.)")

    @validator("year")
    def validate_year(cls, v):
        if v is None:
            raise ValueError("year/yil zorunludur")
        if v < 2000 or v > 2100:
            raise ValueError("year must be between 2000 and 2100")
        return v


class StatusValidation(BaseModel):
    """Schema for status field validation."""
    model_config = ConfigDict(populate_by_name=True)
    
    status: str = Field(..., description="Status değeri")

    @validator("status")
    def validate_status(cls, v):
        if not v or not v.strip():
            raise ValueError("status zorunludur")
        allowed_statuses = ["pending", "in_progress", "done", "blocked", "rejected"]
        if v.strip().lower() not in allowed_statuses:
            raise ValueError(f"status must be one of: {', '.join(allowed_statuses)}")
        return v.strip()


class ReasonValidation(BaseModel):
    """Schema for reason field validation."""
    model_config = ConfigDict(populate_by_name=True)
    
    reason: str = Field(..., description="Gerekçe/reason")
    
    @validator("reason")
    def validate_reason(cls, v):
        if not v or not v.strip():
            raise ValueError("Reddetme gerekçesi zorunludur / reason is required")
        return v.strip()

