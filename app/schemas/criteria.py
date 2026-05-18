# -*- coding: utf-8 -*-
"""Criteria API schemaları."""

from pydantic import BaseModel, ConfigDict, Field, validator


class CriteriaScopeQuery(BaseModel):
    year: int
    faculty_id: int | None = None
    department_id: int | None = None
    semester: str | None = None


# ============================================================================
# Kriter Tamlık (Completion) Request Schemas
# ============================================================================

class CompletionValidateRequest(BaseModel):
    """Validate criteria completion status."""
    model_config = ConfigDict(populate_by_name=True)
    
    year: int = Field(..., alias="yil", description="Akademik yıl")
    faculty_id: int | None = Field(None, alias="fakulte_id", description="Fakülte ID")
    department_id: int | None = Field(None, alias="bolum_id", description="Bölüm ID")
    semester: str | None = Field(None, alias="donem", description="Dönem (Güz/Bahar)")

    @validator("year")
    def validate_year(cls, v):
        if v is None:
            raise ValueError("year/yil zorunludur")
        if not isinstance(v, int) or v < 2000:
            raise ValueError("year must be a valid year >= 2000")
        return v


class CompletionTaskCreateRequest(BaseModel):
    """Create completion task."""
    model_config = ConfigDict(populate_by_name=True)
    
    year: int = Field(..., alias="yil", description="Akademik yıl")
    faculty_id: int = Field(..., alias="fakulte_id", description="Fakülte ID (required)")
    department_id: int | None = Field(None, alias="bolum_id", description="Bölüm ID")
    semester: str | None = Field(None, alias="donem", description="Dönem")
    assigned_role: str | None = None
    created_by: str | None = None

    @validator("year")
    def validate_year(cls, v):
        if v is None:
            raise ValueError("year/yil zorunludur")
        return v

    @validator("faculty_id")
    def validate_faculty_id(cls, v):
        if v is None:
            raise ValueError("faculty_id/fakulte_id zorunludur")
        return v


class CompletionTaskUpdateRequest(BaseModel):
    """Update completion task status."""
    model_config = ConfigDict(populate_by_name=True)
    
    status: str = Field(..., description="Task status (pending, in_progress, done, etc.)")
    notes: str | None = None
    approved_by: str | None = None

    @validator("status")
    def validate_status(cls, v):
        if not v or not v.strip():
            raise ValueError("status zorunludur")
        allowed_statuses = ["pending", "in_progress", "done", "blocked", "rejected"]
        if v.strip().lower() not in allowed_statuses:
            raise ValueError(f"status must be one of: {', '.join(allowed_statuses)}")
        return v.strip()


class CompletionOverrideRequest(BaseModel):
    """Request criteria completion override."""
    model_config = ConfigDict(populate_by_name=True)
    
    year: int = Field(..., alias="yil", description="Akademik yıl")
    reason: str = Field(..., description="Override gerekçesi")
    notes: str | None = None

    @validator("year")
    def validate_year(cls, v):
        if v is None:
            raise ValueError("year/yil zorunludur")
        return v

    @validator("reason")
    def validate_reason(cls, v):
        if not v or not v.strip():
            raise ValueError("Reddetme gerekçesi zorunludur / reason is required")
        return v.strip()


class CompletionOverrideApproveRequest(BaseModel):
    """Approve completion override."""
    approved_by: str | None = None
    notes: str | None = None


class CompletionOverrideRejectRequest(BaseModel):
    """Reject completion override."""
    model_config = ConfigDict(populate_by_name=True)
    
    reason: str = Field(..., description="Reddetme gerekçesi")
    rejected_by: str | None = None

    @validator("reason")
    def validate_reason(cls, v):
        if not v or not v.strip():
            raise ValueError("Reddetme gerekcesi zorunludur")
        return v.strip()


