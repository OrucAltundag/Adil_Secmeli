# -*- coding: utf-8 -*-
"""Karar çalıştırma istekleri için ortak validasyon."""

from __future__ import annotations

from app.services.validation import ValidationIssue, ValidationResult


def validate_decision_run_request(year: int | None, faculty_id: int | None = None) -> ValidationResult:
    issues: list[ValidationIssue] = []
    normalized = {"year": year, "faculty_id": faculty_id}
    if year is None or int(year) < 2000:
        issues.append(ValidationIssue("year", "INVALID_YEAR", "Geçerli bir akademik yıl girilmelidir."))
    if faculty_id is not None and int(faculty_id) <= 0:
        issues.append(ValidationIssue("faculty_id", "INVALID_FACULTY", "Fakülte ID pozitif olmalıdır."))
    return ValidationResult(is_valid=not issues, issues=issues, normalized_data=normalized)
