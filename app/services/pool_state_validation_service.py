# -*- coding: utf-8 -*-
"""Havuz state machine istekleri için ortak validasyon."""

from __future__ import annotations

from app.services.havuz_karar import (
    STATU_DINLENMEDE,
    STATU_HAVUZDA,
    STATU_IPTAL,
    STATU_MUFREDATTA,
)
from app.services.validation import ValidationIssue, ValidationResult


def validate_pool_transition_context(context: dict) -> ValidationResult:
    issues: list[ValidationIssue] = []
    if not context.get("course_id"):
        issues.append(ValidationIssue("course_id", "COURSE_REQUIRED", "Ders ID zorunludur."))
    if not context.get("year"):
        issues.append(ValidationIssue("year", "YEAR_REQUIRED", "Yıl zorunludur."))
    status = context.get("current_status", STATU_HAVUZDA)
    try:
        if int(status) not in {STATU_MUFREDATTA, STATU_HAVUZDA, STATU_DINLENMEDE, STATU_IPTAL}:
            issues.append(ValidationIssue("current_status", "INVALID_STATUS", "Geçersiz havuz statüsü."))
    except (TypeError, ValueError):
        issues.append(ValidationIssue("current_status", "INVALID_STATUS", "Havuz statüsü sayısal olmalıdır."))
    return ValidationResult(is_valid=not issues, issues=issues, normalized_data=dict(context))
