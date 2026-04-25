# -*- coding: utf-8 -*-
"""Müfredat istekleri için ortak validasyon."""

from __future__ import annotations

from app.services.validation import ValidationIssue, ValidationResult


def validate_curriculum_scope(year: int | None, department_id: int | None = None, semester: str | None = None) -> ValidationResult:
    issues: list[ValidationIssue] = []
    if year is None or int(year) < 2000:
        issues.append(ValidationIssue("year", "INVALID_YEAR", "Müfredat için geçerli yıl zorunludur."))
    if department_id is not None and int(department_id) <= 0:
        issues.append(ValidationIssue("department_id", "INVALID_DEPARTMENT", "Bölüm ID pozitif olmalıdır."))
    if semester and str(semester).strip().lower()[0] not in {"g", "b"}:
        issues.append(ValidationIssue("semester", "INVALID_SEMESTER", "Dönem Güz veya Bahar olmalıdır."))
    return ValidationResult(is_valid=not issues, issues=issues, normalized_data={"year": year, "department_id": department_id, "semester": semester})
