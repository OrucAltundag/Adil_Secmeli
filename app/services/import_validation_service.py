# -*- coding: utf-8 -*-
"""Import dosyaları için ortak iş kuralı validasyonu."""

from __future__ import annotations

from app.services.validation import ValidationIssue, ValidationResult


def validate_import_request(import_type: str | None, filename: str | None = None) -> ValidationResult:
    issues: list[ValidationIssue] = []
    normalized = {"import_type": str(import_type or "").strip().lower(), "filename": filename}
    if normalized["import_type"] not in {"criteria", "survey", "curriculum", "other"}:
        issues.append(
            ValidationIssue(
                "import_type",
                "INVALID_IMPORT_TYPE",
                "Import türü geçerli değil.",
                "criteria, survey, curriculum veya other değerlerinden birini kullanın.",
            )
        )
    if filename and not str(filename).lower().endswith((".xlsx", ".xls", ".csv", ".tsv")):
        issues.append(
            ValidationIssue(
                "filename",
                "UNSUPPORTED_IMPORT_FILE",
                "Dosya uzantısı desteklenmiyor.",
                "Excel veya CSV tabanlı bir dosya yükleyin.",
                severity="warning",
            )
        )
    return ValidationResult(is_valid=not any(i.severity == "error" for i in issues), issues=issues, normalized_data=normalized)
