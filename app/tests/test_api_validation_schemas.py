import pytest
from pydantic import ValidationError

from app.schemas.workflow_requests import (
    CourseOrYearRequest,
    CriteriaTaskCreateRequest,
    ImportDiffRecalculateRequest,
    ImportImpactRecalculateRequest,
    ReasonRequest,
    TaskStatusUpdateRequest,
    YearFacultyRequest,
    YearReasonRequest,
)


def test_year_faculty_request_accepts_legacy_aliases():
    payload = YearFacultyRequest(yil=2025, fakulte_id=3)

    assert payload.year == 2025
    assert payload.faculty_id == 3


def test_reason_request_accepts_rejection_and_rollback_aliases():
    assert ReasonRequest(rejection_reason="Eksik veri").reason == "Eksik veri"
    assert ReasonRequest(rollback_reason="Geri alma").reason == "Geri alma"


def test_task_status_update_requires_status():
    with pytest.raises(ValidationError):
        TaskStatusUpdateRequest(notes="Eksik durum")

    with pytest.raises(ValidationError):
        TaskStatusUpdateRequest(status="   ")

    assert TaskStatusUpdateRequest(durum="done").status == "done"


def test_criteria_task_create_preserves_scope_and_audit_fields():
    payload = CriteriaTaskCreateRequest(
        yil=2025,
        fakulte_id=3,
        bolum_id=9,
        donem="Bahar",
        assigned_role="coordinator",
        created_by="tester",
    )

    assert payload.year == 2025
    assert payload.faculty_id == 3
    assert payload.department_id == 9
    assert payload.semester == "Bahar"
    assert payload.assigned_role == "coordinator"
    assert payload.created_by == "tester"


def test_course_or_year_request_requires_course_id_or_year():
    with pytest.raises(ValidationError):
        CourseOrYearRequest(fakulte_id=1)

    assert CourseOrYearRequest(ders_id=10).course_id == 10
    assert CourseOrYearRequest(yil=2025, fakulte_id=1).year == 2025


def test_import_recalculation_requests_are_typed():
    diff = ImportDiffRecalculateRequest(compared_to_import_batch_id="12")
    impact = ImportImpactRecalculateRequest(previous_decision_run_id="4", new_decision_run_id="5")

    assert diff.compared_to_import_batch_id == 12
    assert impact.previous_decision_run_id == 4
    assert impact.new_decision_run_id == 5


def test_year_reason_request_preserves_override_scope_aliases():
    payload = YearReasonRequest(
        yil=2025,
        override_reason="Geçici kapsam dışı",
        fakulte_id=2,
        bolum_id=5,
        ders_id=99,
        donem="Guz",
        requested_by="reviewer",
    )

    assert payload.year == 2025
    assert payload.reason == "Geçici kapsam dışı"
    assert payload.faculty_id == 2
    assert payload.department_id == 5
    assert payload.course_id == 99
    assert payload.semester == "Guz"
    assert payload.requested_by == "reviewer"
