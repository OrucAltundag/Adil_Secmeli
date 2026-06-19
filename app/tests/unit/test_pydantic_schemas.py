"""Pydantic schema validation tests for API endpoints.

Bu testler kasitli olarak hem Ingilizce (year) hem Turkce (yil) anahtarlarla
calistirilir; populate_by_name=True nedeniyle ikisi de runtime'da gecerlidir
ama Pylance Pydantic v2 alias'tan otomatik turetilen __init__ imzasini sadece
alias adiyla gorur. Bu durum testlerin aslindaki amaci -- iki ismin de calistigini
dogrulamak -- icin gerekli bir false-positive'dir.
"""
# pyright: reportCallIssue=false, reportArgumentType=false

import pytest
from pydantic import ValidationError

from app.schemas.common import (
    YearValidation,
    YearFacultyValidation,
    StatusValidation,
    ReasonValidation,
)
from app.schemas.criteria import (
    CompletionValidateRequest,
    CompletionTaskCreateRequest,
    CompletionTaskUpdateRequest,
    CompletionOverrideRequest,
    CompletionOverrideApproveRequest,
    CompletionOverrideRejectRequest,
)


class TestYearValidation:
    """Test YearValidation schema."""

    def test_valid_year(self):
        """Should accept valid year."""
        schema = YearValidation(year=2024)
        assert schema.year == 2024

    def test_valid_year_alias_yil(self):
        """Should accept Turkish alias 'yil'."""
        schema = YearValidation.model_validate({"yil": 2024})
        assert schema.year == 2024

    def test_missing_year(self):
        """Should reject missing year."""
        with pytest.raises(ValidationError):
            YearValidation(year=None)

    def test_invalid_year_type(self):
        """Should reject non-integer year."""
        with pytest.raises(ValidationError) as exc_info:
            YearValidation(year="not_a_year")
        assert len(exc_info.value.errors()) > 0


class TestYearFacultyValidation:
    """Test YearFacultyValidation schema."""

    def test_valid_year_and_faculty(self):
        """Should accept valid year and faculty_id."""
        schema = YearFacultyValidation(year=2024, faculty_id=1)
        assert schema.year == 2024
        assert schema.faculty_id == 1

    def test_valid_with_turkish_aliases(self):
        """Should accept Turkish aliases."""
        schema = YearFacultyValidation.model_validate(
            {"yil": 2024, "fakulte_id": 1}
        )
        assert schema.year == 2024
        assert schema.faculty_id == 1

    def test_missing_year(self):
        """Should reject missing year."""
        with pytest.raises(ValidationError):
            YearFacultyValidation(year=None, faculty_id=1)

    def test_missing_faculty_id(self):
        """Should reject missing faculty_id."""
        with pytest.raises(ValidationError):
            YearFacultyValidation(year=2024, faculty_id=None)


class TestStatusValidation:
    """Test StatusValidation schema."""

    def test_valid_status_values(self):
        """Should accept valid status values."""
        for status in ["pending", "in_progress", "done", "rejected"]:
            schema = StatusValidation(status=status)
            assert schema.status == status

    def test_invalid_status(self):
        """Should reject invalid status."""
        with pytest.raises(ValidationError):
            StatusValidation(status="invalid_status")

    def test_missing_status(self):
        """Should reject missing status."""
        with pytest.raises(ValidationError):
            StatusValidation(status=None)


class TestReasonValidation:
    """Test ReasonValidation schema."""

    def test_valid_reason(self):
        """Should accept non-empty reason."""
        schema = ReasonValidation(reason="Course not offered this semester")
        assert schema.reason == "Course not offered this semester"

    def test_empty_reason(self):
        """Should reject empty reason."""
        with pytest.raises(ValidationError):
            ReasonValidation(reason="")

    def test_whitespace_only_reason(self):
        """Should reject whitespace-only reason."""
        with pytest.raises(ValidationError):
            ReasonValidation(reason="   ")

    def test_missing_reason(self):
        """Should reject missing reason."""
        with pytest.raises(ValidationError):
            ReasonValidation(reason=None)


class TestCompletionValidateRequest:
    """Test CompletionValidateRequest schema."""

    def test_valid_minimal_payload(self):
        """Should accept minimal valid payload."""
        payload = CompletionValidateRequest(year=2024)
        assert payload.year == 2024
        assert payload.faculty_id is None

    def test_valid_with_faculty(self):
        """Should accept year and faculty_id."""
        payload = CompletionValidateRequest(year=2024, faculty_id=1)
        assert payload.year == 2024
        assert payload.faculty_id == 1

    def test_valid_with_turkish_aliases(self):
        """Should accept Turkish field aliases."""
        payload = CompletionValidateRequest.model_validate(
            {"yil": 2024, "fakulte_id": 1}
        )
        assert payload.year == 2024
        assert payload.faculty_id == 1

    def test_missing_year(self):
        """Should reject missing year."""
        with pytest.raises(ValidationError):
            CompletionValidateRequest(year=None)

    def test_optional_fields(self):
        """Should accept None for optional fields."""
        payload = CompletionValidateRequest(year=2024, department_id=None)
        assert payload.year == 2024
        assert payload.department_id is None


class TestCompletionTaskCreateRequest:
    """Test CompletionTaskCreateRequest schema."""

    def test_valid_payload(self):
        """Should accept valid payload with required fields."""
        payload = CompletionTaskCreateRequest(year=2024, faculty_id=1)
        assert payload.year == 2024
        assert payload.faculty_id == 1

    def test_missing_faculty_id(self):
        """Should reject missing faculty_id (required)."""
        with pytest.raises(ValidationError):
            CompletionTaskCreateRequest(year=2024, faculty_id=None)

    def test_missing_year(self):
        """Should reject missing year (required)."""
        with pytest.raises(ValidationError):
            CompletionTaskCreateRequest(year=None, faculty_id=1)

    def test_valid_with_optional_department(self):
        """Should accept optional department_id."""
        payload = CompletionTaskCreateRequest(year=2024, faculty_id=1, department_id=5)
        assert payload.year == 2024
        assert payload.faculty_id == 1
        assert payload.department_id == 5


class TestCompletionTaskUpdateRequest:
    """Test CompletionTaskUpdateRequest schema."""

    def test_valid_status_update(self):
        """Should accept valid status."""
        payload = CompletionTaskUpdateRequest(status="done")
        assert payload.status == "done"

    def test_missing_status(self):
        """Should reject missing status (required)."""
        with pytest.raises(ValidationError):
            CompletionTaskUpdateRequest(status=None)

    def test_invalid_status(self):
        """Should reject invalid status value."""
        with pytest.raises(ValidationError):
            CompletionTaskUpdateRequest(status="invalid")

    def test_valid_status_values(self):
        """Should accept all valid status values."""
        for status in ["pending", "in_progress", "done", "rejected"]:
            payload = CompletionTaskUpdateRequest(status=status)
            assert payload.status == status


class TestCompletionOverrideRequest:
    """Test CompletionOverrideRequest schema."""

    def test_valid_override_request(self):
        """Should accept valid override request."""
        payload = CompletionOverrideRequest(
            year=2024, reason="Course not offered this semester"
        )
        assert payload.year == 2024
        assert payload.reason == "Course not offered this semester"

    def test_missing_year(self):
        """Should reject missing year."""
        with pytest.raises(ValidationError):
            CompletionOverrideRequest(year=None, reason="Test reason")

    def test_missing_reason(self):
        """Should reject missing reason."""
        with pytest.raises(ValidationError):
            CompletionOverrideRequest(year=2024, reason=None)

    def test_empty_reason(self):
        """Should reject empty reason."""
        with pytest.raises(ValidationError):
            CompletionOverrideRequest(year=2024, reason="")

    def test_valid_with_turkish_aliases(self):
        """Should accept Turkish field aliases."""
        payload = CompletionOverrideRequest.model_validate(
            {"yil": 2024, "reason": "Test reason"}
        )
        assert payload.year == 2024
        assert payload.reason == "Test reason"


class TestCompletionOverrideApproveRequest:
    """Test CompletionOverrideApproveRequest schema."""

    def test_valid_minimal_payload(self):
        """Should accept minimal payload (all fields optional)."""
        payload = CompletionOverrideApproveRequest()
        assert payload.approved_by is None
        assert payload.notes is None

    def test_valid_with_approved_by(self):
        """Should accept optional approved_by."""
        payload = CompletionOverrideApproveRequest(approved_by="admin@example.com")
        assert payload.approved_by == "admin@example.com"

    def test_valid_with_notes(self):
        """Should accept optional notes."""
        payload = CompletionOverrideApproveRequest(notes="Approved due to special circumstances")
        assert payload.notes == "Approved due to special circumstances"


class TestCompletionOverrideRejectRequest:
    """Test CompletionOverrideRejectRequest schema."""

    def test_valid_reject_request(self):
        """Should accept valid rejection request."""
        payload = CompletionOverrideRejectRequest(reason="Not a valid reason for override")
        assert payload.reason == "Not a valid reason for override"

    def test_missing_reason(self):
        """Should reject missing reason (required)."""
        with pytest.raises(ValidationError):
            CompletionOverrideRejectRequest(reason=None)

    def test_empty_reason(self):
        """Should reject empty reason."""
        with pytest.raises(ValidationError):
            CompletionOverrideRejectRequest(reason="")

    def test_valid_with_optional_rejected_by(self):
        """Should accept optional rejected_by."""
        payload = CompletionOverrideRejectRequest(
            reason="Invalid request", rejected_by="admin@example.com"
        )
        assert payload.reason == "Invalid request"
        assert payload.rejected_by == "admin@example.com"
