# -*- coding: utf-8 -*-
"""Kriter degeri gecerlilik kontrolu."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_criteria_completion_governance_schema


MISSING_STRINGS = {"", "-", "yok", "n/a", "na", "none", "null"}


@dataclass
class ValidationResult:
    field_name: str
    value: Any
    status: str = "valid"
    severity: str = "info"
    issue_type: str | None = None
    message: str | None = None
    suggestion: str | None = None
    normalized_value: float | None = None

    @property
    def is_valid(self) -> bool:
        return self.status in {"valid", "warning"}

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_number(value: Any) -> tuple[bool, float | None]:
    if value is None:
        return False, None
    text = str(value).strip().lower()
    if text in MISSING_STRINGS:
        return False, None
    try:
        return True, float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return False, None


def _missing(field_name: str, value: Any, required: bool) -> ValidationResult:
    if required:
        return ValidationResult(
            field_name=field_name,
            value=value,
            status="critical",
            severity="critical",
            issue_type="missing_required_value",
            message=f"{field_name} alanı zorunludur ancak boş görünüyor.",
            suggestion="Bu alanı ilgili ders için doldurun.",
        )
    return ValidationResult(
        field_name=field_name,
        value=value,
        status="warning",
        severity="warning",
        issue_type="missing_optional_value",
        message=f"{field_name} alanı opsiyonel ve boş.",
        suggestion="Varsa bu alanı tamamlayın; yoksa opsiyonel olarak bırakılabilir.",
    )


def validate_criterion_value(
    field_name: str,
    value: Any,
    context: dict[str, Any] | None = None,
) -> ValidationResult:
    context = context or {}
    required = bool(context.get("required", True))
    exists, number = _normalize_number(value)
    if not exists:
        return _missing(field_name, value, required)

    if field_name in {"total_students", "passed_students", "capacity", "enrolled_students", "survey_count"}:
        if number is None:
            return ValidationResult(field_name, value)
        if number < 0:
            return ValidationResult(
                field_name,
                value,
                status="invalid",
                severity="error",
                issue_type="out_of_range",
                message=f"{field_name} negatif olamaz.",
                suggestion="Bu alanı 0 veya pozitif bir sayı yapın.",
                normalized_value=number,
            )
        if int(number) != number:
            return ValidationResult(
                field_name,
                value,
                status="warning",
                severity="warning",
                issue_type="invalid_numeric_value",
                message=f"{field_name} tam sayı olarak beklenir.",
                suggestion="Öğrenci/kontenjan alanlarını tam sayı girin.",
                normalized_value=number,
            )

    if field_name == "passed_students":
        total = context.get("total_students")
        ok, total_number = _normalize_number(total)
        if ok and total_number is not None and number is not None and number > total_number:
            return ValidationResult(
                field_name,
                value,
                status="invalid",
                severity="error",
                issue_type="inconsistent_values",
                message="Geçen öğrenci sayısı toplam öğrenci sayısından büyük olamaz.",
                suggestion="Toplam ve geçen öğrenci sayılarını birlikte kontrol edin.",
                normalized_value=number,
            )

    if field_name == "average_grade":
        grade_scale = str(context.get("grade_scale") or "100")
        max_grade = 4.0 if grade_scale == "4" else 100.0
        if number is None or number < 0 or number > max_grade:
            return ValidationResult(
                field_name,
                value,
                status="invalid",
                severity="error",
                issue_type="out_of_range",
                message=f"Not ortalaması 0-{max_grade:g} aralığında olmalıdır.",
                suggestion="Not ortalamasını beklenen ölçekte girin.",
                normalized_value=number,
            )

    if field_name == "enrolled_students":
        capacity = context.get("capacity")
        ok, capacity_number = _normalize_number(capacity)
        if ok and capacity_number is not None and capacity_number >= 0 and number is not None and number > capacity_number:
            return ValidationResult(
                field_name,
                value,
                status="warning",
                severity="warning",
                issue_type="inconsistent_values",
                message="Kayıtlı öğrenci sayısı kontenjandan yüksek görünüyor.",
                suggestion="Kontenjan aşımı bilinçli değilse kayıtlı öğrenci veya kontenjan değerini kontrol edin.",
                normalized_value=number,
            )

    if field_name in {"success_rate", "popularity"}:
        if number is None or number < 0 or number > 100:
            return ValidationResult(
                field_name,
                value,
                status="invalid",
                severity="error",
                issue_type="out_of_range",
                message=f"{field_name} 0-100 aralığında olmalıdır.",
                suggestion="Oranı yüzde biçiminde 0 ile 100 arasında girin.",
                normalized_value=number,
            )

    return ValidationResult(field_name=field_name, value=value, normalized_value=number)


def _table_exists(cur: sqlite3.Cursor, table_name: str) -> bool:
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table_name,))
    return bool(cur.fetchone())


def _semester_clause(alias: str = "dk") -> str:
    return f"LOWER(SUBSTR(TRIM(COALESCE({alias}.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))"


def validate_course_criteria(
    conn: sqlite3.Connection,
    course_id: int,
    year: int,
    semester: str | None = None,
    required_fields: list[str] | None = None,
) -> dict[str, Any]:
    required_fields = required_fields or [
        "total_students",
        "passed_students",
        "average_grade",
        "capacity",
        "enrolled_students",
    ]
    cur = conn.cursor()
    if not _table_exists(cur, "ders_kriterleri"):
        return {"course_id": int(course_id), "results": [], "issues": []}
    query = """
        SELECT id, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi,
               kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen,
               criteria_veri_kaynagi, anket_veri_kaynagi, criteria_import_id, anket_import_id
        FROM ders_kriterleri dk
        WHERE ders_id = ? AND yil = ?
    """
    params: list[Any] = [int(course_id), int(year)]
    if semester:
        query += f" AND ({_semester_clause('dk')} OR dk.donem IS NULL OR TRIM(COALESCE(dk.donem, '')) = '')"
        params.append(str(semester))
    query += " ORDER BY id DESC LIMIT 1"
    try:
        cur.execute(query, tuple(params))
        row = cur.fetchone()
    except sqlite3.OperationalError:
        row = None
    values = {
        "total_students": row[1] if row else None,
        "passed_students": row[2] if row else None,
        "average_grade": row[3] if row else None,
        "capacity": row[4] if row else None,
        "enrolled_students": row[5] if row else None,
        "survey_count": row[7] if row else None,
    }
    context = {
        "total_students": values.get("total_students"),
        "capacity": values.get("capacity"),
    }
    results = []
    issues = []
    for field, value in values.items():
        result = validate_criterion_value(
            field,
            value,
            context={**context, "required": field in required_fields},
        )
        results.append(result.as_dict())
        if result.issue_type and result.severity in {"warning", "error", "critical"}:
            issues.append(result.as_dict())
    return {
        "course_id": int(course_id),
        "criteria_row_id": int(row[0]) if row and row[0] is not None else None,
        "source_type": row[8] if row and len(row) > 8 else None,
        "source_id": row[10] if row and len(row) > 10 else None,
        "values": values,
        "results": results,
        "issues": issues,
    }


def record_validation_issues(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    issues: list[dict[str, Any]],
    faculty_id: int | None = None,
    department_id: int | None = None,
    course_id: int | None = None,
    semester: str | None = None,
) -> None:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    cur = conn.cursor()
    for issue in issues:
        cur.execute(
            """
            INSERT INTO criteria_validation_issues (
                scope_type, faculty_id, department_id, course_id, year, semester,
                criterion_key, severity, issue_type, raw_value, message, suggestion, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scope_type,
                faculty_id,
                department_id,
                course_id if course_id is not None else issue.get("course_id"),
                int(year),
                semester,
                issue.get("field_name") or issue.get("criterion_key"),
                issue.get("severity") or "warning",
                issue.get("issue_type") or "unknown_error",
                None if issue.get("value") is None else str(issue.get("value")),
                issue.get("message") or "Kriter değeri geçersiz.",
                issue.get("suggestion"),
                _now(),
            ),
        )


def validate_scope_criteria(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
    required_fields: list[str] | None = None,
) -> dict[str, Any]:
    cur = conn.cursor()
    query = """
        SELECT DISTINCT d.ders_id
        FROM ders d
        LEFT JOIN bolum b ON b.bolum_id = d.bolum_id
        WHERE 1=1
    """
    params: list[Any] = []
    if faculty_id is not None:
        query += " AND COALESCE(d.fakulte_id, b.fakulte_id) = ?"
        params.append(int(faculty_id))
    if department_id is not None:
        query += " AND d.bolum_id = ?"
        params.append(int(department_id))
    cur.execute(query, tuple(params))
    course_ids = [int(row[0]) for row in cur.fetchall() if row and row[0] is not None]
    all_issues = []
    courses = []
    for cid in course_ids:
        result = validate_course_criteria(conn, cid, int(year), semester, required_fields)
        courses.append(result)
        for issue in result["issues"]:
            issue["course_id"] = cid
            all_issues.append(issue)
    return {"courses": courses, "issues": all_issues, "issue_count": len(all_issues)}
