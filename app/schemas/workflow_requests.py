"""Shared workflow request schemas for validation-heavy API routes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, root_validator


def _first_value(values: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in values and values[key] is not None:
            return values[key]
    return None


class LegacyWorkflowRequest(BaseModel):
    class Config:
        populate_by_name = True
        extra = "ignore"


class YearRequest(LegacyWorkflowRequest):
    year: int

    @root_validator(pre=True)
    def _map_year_aliases(cls, values: dict[str, Any]) -> dict[str, Any]:
        year = _first_value(values, "year", "yil")
        if year is not None:
            values["year"] = year
        return values


class YearFacultyRequest(YearRequest):
    faculty_id: int

    @root_validator(pre=True)
    def _map_faculty_aliases(cls, values: dict[str, Any]) -> dict[str, Any]:
        faculty_id = _first_value(values, "faculty_id", "fakulte_id")
        if faculty_id is not None:
            values["faculty_id"] = faculty_id
        return values


class YearScopeRequest(YearRequest):
    faculty_id: int | None = None
    department_id: int | None = None
    semester: str | None = None

    @root_validator(pre=True)
    def _map_scope_aliases(cls, values: dict[str, Any]) -> dict[str, Any]:
        faculty_id = _first_value(values, "faculty_id", "fakulte_id")
        if faculty_id is not None:
            values["faculty_id"] = faculty_id
        department_id = _first_value(values, "department_id", "bolum_id")
        if department_id is not None:
            values["department_id"] = department_id
        semester = _first_value(values, "semester", "donem")
        if semester is not None:
            values["semester"] = semester
        return values


class YearFacultySemesterRequest(YearFacultyRequest):
    department_id: int | None = None
    semester: str | None = None
    save: bool = False

    @root_validator(pre=True)
    def _map_semester_aliases(cls, values: dict[str, Any]) -> dict[str, Any]:
        department_id = _first_value(values, "department_id", "bolum_id")
        if department_id is not None:
            values["department_id"] = department_id
        semester = _first_value(values, "semester", "donem")
        if semester is not None:
            values["semester"] = semester
        return values


class CriteriaTaskCreateRequest(YearFacultySemesterRequest):
    assigned_role: str | None = None
    created_by: str | None = None


class YearReasonRequest(YearRequest):
    reason: str
    scope_type: str | None = None
    faculty_id: int | None = None
    department_id: int | None = None
    course_id: int | None = None
    semester: str | None = None
    missing_fields: list[str] | None = None
    validation_issues: list[dict[str, Any]] | None = None
    requested_by: str | None = None
    expires_at: str | None = None

    @root_validator(pre=True)
    def _map_reason_aliases(cls, values: dict[str, Any]) -> dict[str, Any]:
        reason = _first_value(values, "reason", "rejection_reason", "rollback_reason", "override_reason")
        if reason is not None:
            values["reason"] = str(reason).strip()
        for canonical, aliases in {
            "faculty_id": ("faculty_id", "fakulte_id"),
            "department_id": ("department_id", "bolum_id"),
            "course_id": ("course_id", "ders_id"),
            "semester": ("semester", "donem"),
        }.items():
            value = _first_value(values, *aliases)
            if value is not None:
                values[canonical] = value
        return values

    @root_validator(skip_on_failure=True)
    def _require_reason(cls, values: dict[str, Any]) -> dict[str, Any]:
        if not values.get("reason"):
            raise ValueError("reason zorunludur")
        return values


class TaskStatusUpdateRequest(LegacyWorkflowRequest):
    status: str
    notes: str | None = None
    approved_by: str | None = None

    @root_validator(pre=True)
    def _map_status_aliases(cls, values: dict[str, Any]) -> dict[str, Any]:
        status = _first_value(values, "status", "task_status", "durum")
        if status is not None:
            values["status"] = str(status).strip()
        return values

    @root_validator(skip_on_failure=True)
    def _require_status(cls, values: dict[str, Any]) -> dict[str, Any]:
        if not values.get("status"):
            raise ValueError("status zorunludur")
        return values


class ReasonRequest(LegacyWorkflowRequest):
    reason: str
    rejected_by: str | None = None
    user: str | None = None

    @root_validator(pre=True)
    def _map_reason_aliases(cls, values: dict[str, Any]) -> dict[str, Any]:
        reason = _first_value(values, "reason", "rejection_reason", "rollback_reason")
        if reason is not None:
            values["reason"] = str(reason).strip()
        return values

    @root_validator(skip_on_failure=True)
    def _require_reason(cls, values: dict[str, Any]) -> dict[str, Any]:
        if not values.get("reason"):
            raise ValueError("reason zorunludur")
        return values


class ApprovalRequest(LegacyWorkflowRequest):
    actor: str | None = None
    approved_by: str | None = None
    reviewed_by: str | None = None
    review_note: str | None = None
    user: str | None = None


class ImportDiffRecalculateRequest(LegacyWorkflowRequest):
    compared_to_import_batch_id: int | None = None


class ImportImpactRecalculateRequest(LegacyWorkflowRequest):
    previous_decision_run_id: int | None = None
    new_decision_run_id: int | None = None


class CourseOrYearRequest(LegacyWorkflowRequest):
    course_id: int | None = None
    year: int | None = None
    faculty_id: int | None = None
    department_id: int | None = None
    semester: str | None = None
    save: bool = False

    @root_validator(pre=True)
    def _map_course_aliases(cls, values: dict[str, Any]) -> dict[str, Any]:
        course_id = _first_value(values, "course_id", "ders_id")
        if course_id is not None:
            values["course_id"] = course_id
        year = _first_value(values, "year", "yil")
        if year is not None:
            values["year"] = year
        faculty_id = _first_value(values, "faculty_id", "fakulte_id")
        if faculty_id is not None:
            values["faculty_id"] = faculty_id
        department_id = _first_value(values, "department_id", "bolum_id")
        if department_id is not None:
            values["department_id"] = department_id
        semester = _first_value(values, "semester", "donem")
        if semester is not None:
            values["semester"] = semester
        return values

    @root_validator(skip_on_failure=True)
    def _require_course_or_year(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values.get("course_id") is None and values.get("year") is None:
            raise ValueError("course_id veya year zorunludur")
        return values


class OverrideCreateRequest(LegacyWorkflowRequest):
    course_id: int
    year: int
    semester: str | None = None
    overridden_final_status: int
    recommended_status: str | None = None
    reason: str
    requested_by: str | None = None
    approved_by: str | None = None
    expires_at: str | None = None
    transition_id: int | None = None

    @root_validator(pre=True)
    def _map_aliases(cls, values: dict[str, Any]) -> dict[str, Any]:
        for canonical, aliases in {
            "course_id": ("course_id", "ders_id"),
            "year": ("year", "yil"),
            "reason": ("reason", "override_reason"),
            "recommended_status": ("recommended_status", "onerilen_status"),
            "semester": ("semester", "donem"),
        }.items():
            value = _first_value(values, *aliases)
            if value is not None:
                values[canonical] = str(value).strip() if canonical == "reason" else value
        return values

    @root_validator(skip_on_failure=True)
    def _require_reason(cls, values: dict[str, Any]) -> dict[str, Any]:
        if not values.get("reason"):
            raise ValueError("Override gerekcesi zorunludur")
        return values


class OverridePatchRequest(LegacyWorkflowRequest):
    reason: str | None = None
    expires_at: str | None = None
    is_active: bool | None = None

    @root_validator(pre=True)
    def _map_reason_aliases(cls, values: dict[str, Any]) -> dict[str, Any]:
        reason = _first_value(values, "reason", "override_reason")
        if reason is not None:
            values["reason"] = reason
        return values

    @root_validator(skip_on_failure=True)
    def _require_any_field(cls, values: dict[str, Any]) -> dict[str, Any]:
        if all(values.get(field) is None for field in ("reason", "expires_at", "is_active")):
            raise ValueError("Güncellenecek alan yok")
        return values
