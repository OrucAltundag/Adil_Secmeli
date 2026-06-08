# -*- coding: utf-8 -*-
"""Gelismis kriter tamlik hesaplama ve algoritma kapisi servisi."""

from __future__ import annotations

import json
import logging
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_criteria_completion_governance_schema
from app.services.course_type import filter_elective_course_ids
from app.services.criteria_completion_policy_service import resolve_policy
from app.services.criteria_override_service import get_active_override
from app.services.criteria_validation_service import validate_criterion_value
from app.services.missing_data_risk_service import (
    calculate_missing_data_risk,
    persist_missing_data_risk,
)
from app.services.yearly_workflow import (
    ALGORITHM_NOT_RUN,
    STATUS_COMPLETED,
    STATUS_NOT_STARTED,
    STATUS_PARTIAL,
    ensure_yearly_workflow_schema,
)

logger = logging.getLogger(__name__)

# Bu serviste kriter tamlığı yalnızca fakülte/bölüm kapsamlarında hesaplanır.
# (faculty_id=None ise "tüm fakülteler" anlamına gelen geniş kapsam korunur.)
VALID_SCOPE_TYPES = {"faculty", "department"}

FIELD_DEFINITIONS: dict[str, dict[str, Any]] = {
    "total_students": {
        "label": "Toplam öğrenci",
        "column": "toplam_ogrenci",
        "source_type_column": "criteria_veri_kaynagi",
        "source_id_column": "criteria_import_id",
    },
    "passed_students": {
        "label": "Geçen öğrenci",
        "column": "gecen_ogrenci",
        "source_type_column": "criteria_veri_kaynagi",
        "source_id_column": "criteria_import_id",
    },
    "average_grade": {
        "label": "Not ortalaması",
        "column": "basari_ortalamasi",
        "source_type_column": "criteria_veri_kaynagi",
        "source_id_column": "criteria_import_id",
    },
    "capacity": {
        "label": "Kontenjan",
        "column": "kontenjan",
        "source_type_column": "criteria_veri_kaynagi",
        "source_id_column": "criteria_import_id",
    },
    "enrolled_students": {
        "label": "Kayıtlı öğrenci",
        "column": "kayitli_ogrenci",
        "source_type_column": "criteria_veri_kaynagi",
        "source_id_column": "criteria_import_id",
    },
    "survey_count": {
        "label": "Anket seçimi",
        "column": "anket_dersi_secen",
        "source_type_column": "anket_veri_kaynagi",
        "source_id_column": "anket_import_id",
    },
    "trend": {
        "label": "Geçmiş trend",
        "computed": True,
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        logger.exception("Kriter tamlık JSON alanı ayrıştırılamadı, varsayılana düşülüyor. Ham veri: %r", value)
        return default


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None = None) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return {key: row[key] for key in row.keys()}
    if columns:
        return {columns[idx]: row[idx] for idx in range(min(len(columns), len(row)))}
    return {}


def _fetchone_dict(cur: sqlite3.Cursor) -> dict[str, Any] | None:
    row = cur.fetchone()
    if row is None:
        return None
    columns = [desc[0] for desc in cur.description] if cur.description else []
    return _row_to_dict(row, columns)


def _fetchall_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description] if cur.description else []
    return [_row_to_dict(row, columns) or {} for row in rows]


def _ensure_schema(conn: sqlite3.Connection) -> None:
    ensure_yearly_workflow_schema(conn, auto_commit=False)
    ensure_criteria_completion_governance_schema(conn, commit=False)


def _normalize_semester(value: str | None) -> str | None:
    """Dönemi 'Güz'/'Bahar' kanonik biçimine indirger; bilinmeyen değeri reddeder.

    Eski davranış 'b ile başlamayan her şeyi Güz say' idi; bu, 'Yaz' gibi geçersiz
    bir girdinin sessizce yanlış dönem verisiyle karar üretmesine yol açıyordu.
    """
    if value is None:
        return None
    raw = str(value).strip().lower()
    if not raw:
        return None
    mapping = {
        "b": "Bahar",
        "bahar": "Bahar",
        "spring": "Bahar",
        "s": "Bahar",
        "g": "Güz",
        "güz": "Güz",
        "guz": "Güz",
        "fall": "Güz",
        "autumn": "Güz",
    }
    if raw in mapping:
        return mapping[raw]
    raise ValueError(
        f"Geçersiz dönem (semester) değeri: '{value}'. Sadece 'Güz' veya 'Bahar' kabul edilir."
    )


def _normalize_scope_type(value: str) -> str:
    """Kapsam türünü doğrular; geçersiz değeri sessizce düzeltmek yerine reddeder.

    (faculty_id/department_id'nin None olması meşru 'tümü' kapsamı sayıldığından
    burada yalnızca scope_type string'i denetlenir, ID zorunluluğu uygulanmaz.)
    """
    scope = str(value or "").strip().lower()
    if scope not in VALID_SCOPE_TYPES:
        raise ValueError(
            f"Geçersiz kapsam türü (scope_type): '{value}'. Beklenen: {sorted(VALID_SCOPE_TYPES)}"
        )
    return scope


def _legacy_status_from_level(level: str, ratio: float) -> str:
    if level in {"completed", "completed_with_warnings", "not_applicable"}:
        return STATUS_COMPLETED
    if ratio <= 0:
        return STATUS_NOT_STARTED
    return STATUS_PARTIAL


def _completion_level(
    ratio: float,
    warning_count: int,
    invalid_required_fields: int,
    blocking_issue_count: int,
) -> str:
    if blocking_issue_count > 0:
        return "blocked"
    if invalid_required_fields > 0:
        return "invalid"
    if ratio <= 0:
        return "not_started"
    if ratio < 0.50:
        return "low_partial"
    if ratio < 0.80:
        return "medium_partial"
    if ratio < 1.0:
        return "high_partial"
    if warning_count > 0:
        return "completed_with_warnings"
    return "completed"


def _semester_sql(alias: str) -> str:
    return f"LOWER(SUBSTR(TRIM(COALESCE({alias}.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))"


def _course_scope(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> list[dict[str, Any]]:
    cur = conn.cursor()
    query = """
        SELECT DISTINCT
            md.ders_id AS course_id,
            COALESCE(d.kod, '') AS course_code,
            COALESCE(d.ad, '') AS course_name,
            b.fakulte_id AS faculty_id,
            m.bolum_id AS department_id,
            COALESCE(b.ad, '') AS department_name,
            COALESCE(f.ad, '') AS faculty_name
        FROM mufredat m
        JOIN bolum b ON b.bolum_id = m.bolum_id
        LEFT JOIN fakulte f ON f.fakulte_id = b.fakulte_id
        JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
        LEFT JOIN ders d ON d.ders_id = md.ders_id
        WHERE m.akademik_yil = ?
    """
    params: list[Any] = [int(year)]
    if faculty_id is not None:
        query += " AND b.fakulte_id = ?"
        params.append(int(faculty_id))
    if department_id is not None:
        query += " AND m.bolum_id = ?"
        params.append(int(department_id))
    if semester:
        query += f" AND {_semester_sql('m')}"
        params.append(str(semester))
    query += " ORDER BY b.ad, d.ad"
    cur.execute(query, tuple(params))
    rows = _fetchall_dicts(cur)
    ids = {int(row["course_id"]) for row in rows if row.get("course_id") is not None}
    elective_ids = filter_elective_course_ids(cur, ids)
    if elective_ids:
        return [row for row in rows if row.get("course_id") is not None and int(row["course_id"]) in elective_ids]
    return []


def _latest_criteria_row(
    conn: sqlite3.Connection,
    course_id: int,
    year: int,
    semester: str | None,
    department_id: int | None = None,
) -> dict[str, Any] | None:
    """İlgili ders/yıl/dönem için en uygun kriter kaydını döndürür.

    Dönem filtresi verildiğinde, dönem-spesifik kayıt jenerik (dönemsiz) kayda göre
    önceliklendirilir; aksi halde sonradan girilen dönemsiz bir kayıt yanlışlıkla
    dönem-spesifik veriyi gölgeleyebiliyordu.

    Not: `ders_kriterleri` tablosunda bölüm kolonu bulunmadığından (`department_id`
    yalnızca ileride şema desteklerse kullanılmak üzere imzada tutulur), aynı dersin
    farklı bölümlerde farklı kritere sahip olması durumu bu sürümde ayrıştırılamaz.
    """
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ders_kriterleri' LIMIT 1")
    if not cur.fetchone():
        return None
    query = """
        SELECT *
        FROM ders_kriterleri dk
        WHERE dk.ders_id = ? AND dk.yil = ?
    """
    params: list[Any] = [int(course_id), int(year)]
    if semester:
        query += f" AND ({_semester_sql('dk')} OR dk.donem IS NULL OR TRIM(COALESCE(dk.donem, '')) = '')"
        params.append(str(semester))
        # Önce dönem-spesifik kayıt, sonra dönemsiz jenerik kayıt, sonra en yeni id.
        query += (
            f" ORDER BY CASE WHEN {_semester_sql('dk')} THEN 0"
            " WHEN dk.donem IS NULL OR TRIM(COALESCE(dk.donem, '')) = '' THEN 1"
            " ELSE 2 END, dk.id DESC LIMIT 1"
        )
        params.append(str(semester))
    else:
        query += " ORDER BY dk.id DESC LIMIT 1"
    try:
        cur.execute(query, tuple(params))
        return _fetchone_dict(cur)
    except sqlite3.OperationalError:
        return None


def _history_count(conn: sqlite3.Connection, course_id: int, year: int) -> int:
    cur = conn.cursor()
    total = 0
    for table_name, year_col in (("ders_kriterleri", "yil"), ("performans", "akademik_yil")):
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table_name,))
        if not cur.fetchone():
            continue
        try:
            cur.execute(
                f"SELECT COUNT(DISTINCT {year_col}) FROM {table_name} WHERE ders_id = ? AND {year_col} < ?",
                (int(course_id), int(year)),
            )
            total = max(total, int(cur.fetchone()[0] or 0))
        except sqlite3.OperationalError:
            continue
    return total


def _first_curriculum_year(conn: sqlite3.Connection, course_id: int) -> int | None:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT MIN(m.akademik_yil)
        FROM mufredat m
        JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
        WHERE md.ders_id = ?
        """,
        (int(course_id),),
    )
    row = cur.fetchone()
    return int(row[0]) if row and row[0] is not None else None


def _matrix_row_for_field(
    conn: sqlite3.Connection,
    course: dict[str, Any],
    criteria_row: dict[str, Any] | None,
    field: str,
    required: bool,
    policy: dict[str, Any],
    year: int,
    semester: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    course_id = int(course["course_id"])
    definition = FIELD_DEFINITIONS.get(field, {"label": field})
    now = _now()
    issues: list[dict[str, Any]] = []

    if definition.get("computed") and field == "trend":
        points = _history_count(conn, course_id, int(year))
        first_year = _first_curriculum_year(conn, course_id)
        grace = int(policy.get("new_course_grace_period_years") or 0)
        is_new_exception = bool(
            policy.get("allow_new_course_missing_history")
            and first_year is not None
            and int(year) - int(first_year) < max(1, grace)
        )
        if points >= 2:
            present = valid = True
            value_text = f"{points} yıl geçmiş veri"
            value_numeric = float(points)
            missing_reason = None
            invalid_reason = None
        elif is_new_exception:
            present = valid = True
            value_text = "Yeni ders istisnası"
            value_numeric = float(points)
            missing_reason = "Yeni ders geçmiş veri istisnası"
            invalid_reason = None
        else:
            present = valid = False
            value_text = None
            value_numeric = float(points)
            missing_reason = "Trend için en az 2 yıl geçmiş veri gerekir."
            invalid_reason = missing_reason if required else None
            if required:
                issues.append(
                    {
                        "course_id": course_id,
                        "field_name": field,
                        "value": points,
                        "severity": "critical",
                        "issue_type": "missing_required_value",
                        "message": missing_reason,
                        "suggestion": "Geçmiş yıl kriter verisini tamamlayın veya yeni ders istisnası için override kullanın.",
                        "is_required": True,
                    }
                )
        return (
            {
                "scope_type": None,
                "faculty_id": course.get("faculty_id"),
                "department_id": course.get("department_id"),
                "course_id": course_id,
                "course_code": course.get("course_code"),
                "course_name": course.get("course_name"),
                "year": int(year),
                "semester": semester,
                "criterion_key": field,
                "criterion_label": definition.get("label", field),
                "is_required": bool(required),
                "is_present": bool(present),
                "is_valid": bool(valid),
                "value_text": value_text,
                "value_numeric": value_numeric,
                "missing_reason": missing_reason,
                "invalid_reason": invalid_reason,
                "source_type": "computed",
                "source_id": None,
                "checked_at": now,
            },
            issues,
        )

    raw_value = criteria_row.get(definition["column"]) if criteria_row else None
    context = {
        "required": bool(required),
        "total_students": criteria_row.get("toplam_ogrenci") if criteria_row else None,
        "capacity": criteria_row.get("kontenjan") if criteria_row else None,
    }
    validation = validate_criterion_value(field, raw_value, context=context)
    if field == "survey_count" and raw_value is not None and policy.get("min_survey_response_count") is not None:
        try:
            if float(raw_value) < float(policy["min_survey_response_count"]):
                validation.status = "warning"
                validation.severity = "warning"
                validation.issue_type = validation.issue_type or "out_of_range"
                validation.message = "Anket seçimi aktif politikanın minimum katılım eşiğinin altında."
                validation.suggestion = "Anket katılımını artırın veya kapsam politikasını gözden geçirin."
        except (TypeError, ValueError):
            pass
    present = validation.status not in {"critical"} and validation.issue_type != "missing_required_value"
    if raw_value is None or str(raw_value).strip().lower() in {"", "-", "yok", "n/a", "na", "none", "null"}:
        present = False
    valid = validation.is_valid and present
    if validation.issue_type and validation.severity in {"warning", "error", "critical"}:
        issues.append(
            {
                "course_id": course_id,
                "field_name": field,
                "value": raw_value,
                "severity": validation.severity,
                "issue_type": validation.issue_type,
                "message": validation.message,
                "suggestion": validation.suggestion,
                "is_required": bool(required),
            }
        )
    source_type_col = definition.get("source_type_column")
    source_id_col = definition.get("source_id_column")
    source_type = criteria_row.get(source_type_col) if (criteria_row and source_type_col) else None
    source_id = criteria_row.get(source_id_col) if (criteria_row and source_id_col) else None
    return (
        {
            "scope_type": None,
            "faculty_id": course.get("faculty_id"),
            "department_id": course.get("department_id"),
            "course_id": course_id,
            "course_code": course.get("course_code"),
            "course_name": course.get("course_name"),
            "year": int(year),
            "semester": semester,
            "criterion_key": field,
            "criterion_label": definition.get("label", field),
            "is_required": bool(required),
            "is_present": bool(present),
            "is_valid": bool(valid),
            "value_text": None if raw_value is None else str(raw_value),
            "value_numeric": validation.normalized_value,
            "missing_reason": validation.message if not present else None,
            "invalid_reason": validation.message if present and not valid else None,
            "source_type": source_type,
            "source_id": source_id,
            "checked_at": now,
        },
        issues,
    )


def _delete_scope_rows(
    conn: sqlite3.Connection,
    table_name: str,
    scope_type: str,
    year: int,
    faculty_id: int | None,
    department_id: int | None,
    semester: str | None,
) -> None:
    where = ["scope_type = ?", "year = ?", "COALESCE(semester, '') = COALESCE(?, '')"]
    params: list[Any] = [scope_type, int(year), semester]
    if faculty_id is None:
        where.append("faculty_id IS NULL")
    else:
        where.append("faculty_id = ?")
        params.append(int(faculty_id))
    if scope_type == "department" or department_id is not None:
        if department_id is None:
            where.append("department_id IS NULL")
        else:
            where.append("department_id = ?")
            params.append(int(department_id))
    conn.execute(f"DELETE FROM {table_name} WHERE {' AND '.join(where)}", tuple(params))


def _persist_matrix_and_issues(
    conn: sqlite3.Connection,
    result: dict[str, Any],
    issues: list[dict[str, Any]],
) -> None:
    _delete_scope_rows(
        conn,
        "criteria_completion_matrix",
        result["scope_type"],
        int(result["year"]),
        result.get("faculty_id"),
        result.get("department_id"),
        result.get("semester"),
    )
    _delete_scope_rows(
        conn,
        "criteria_validation_issues",
        result["scope_type"],
        int(result["year"]),
        result.get("faculty_id"),
        result.get("department_id"),
        result.get("semester"),
    )
    cur = conn.cursor()
    for row in result["matrix"]:
        cur.execute(
            """
            INSERT INTO criteria_completion_matrix (
                scope_type, faculty_id, department_id, course_id, year, semester,
                criterion_key, is_required, is_present, is_valid, value_text,
                value_numeric, missing_reason, invalid_reason, source_type, source_id, checked_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result["scope_type"],
                row.get("faculty_id"),
                row.get("department_id"),
                int(row["course_id"]),
                int(result["year"]),
                result.get("semester"),
                row.get("criterion_key"),
                1 if row.get("is_required") else 0,
                1 if row.get("is_present") else 0,
                1 if row.get("is_valid") else 0,
                row.get("value_text"),
                row.get("value_numeric"),
                row.get("missing_reason"),
                row.get("invalid_reason"),
                row.get("source_type"),
                row.get("source_id"),
                row.get("checked_at") or _now(),
            ),
        )
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
                result["scope_type"],
                result.get("faculty_id"),
                result.get("department_id"),
                issue.get("course_id"),
                int(result["year"]),
                result.get("semester"),
                issue.get("field_name") or issue.get("criterion_key"),
                issue.get("severity") or "warning",
                issue.get("issue_type") or "unknown_error",
                None if issue.get("value") is None else str(issue.get("value")),
                issue.get("message") or "Kriter değeri geçersiz.",
                issue.get("suggestion"),
                _now(),
            ),
        )


def _criterion_summary(matrix: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in matrix:
        grouped[str(row.get("criterion_key"))].append(row)
    out: dict[str, dict[str, Any]] = {}
    for key, rows in grouped.items():
        total = len(rows)
        present = sum(1 for row in rows if row.get("is_present"))
        valid = sum(1 for row in rows if row.get("is_valid"))
        required_total = sum(1 for row in rows if row.get("is_required"))
        required_valid = sum(1 for row in rows if row.get("is_required") and row.get("is_valid"))
        is_required_attr = required_total > 0
        completion_ratio = round(valid / total, 4) if total else 0.0
        out[key] = {
            "total": total,
            "present": present,
            "valid": valid,
            "missing": max(0, total - present),
            "invalid": sum(1 for row in rows if row.get("is_present") and not row.get("is_valid")),
            "is_required": is_required_attr,
            "completion_ratio": completion_ratio,
            "required_completion_ratio": round(required_valid / required_total, 4) if required_total else 1.0,
            # UI'nin doğru oranı seçmesi için: zorunlu alanda zorunlu-oran, opsiyonelde gerçek doluluk.
            # (Opsiyonel alanların hep %100 görünmesi sorununu giderir.)
            "display_ratio": (round(required_valid / required_total, 4) if is_required_attr else completion_ratio),
        }
    return out


def _course_counts(matrix: list[dict[str, Any]]) -> dict[str, int]:
    by_course: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in matrix:
        by_course[int(row["course_id"])].append(row)
    counts = {
        "total_courses": len(by_course),
        "completed_courses": 0,
        "partial_courses": 0,
        "missing_courses": 0,
        "invalid_courses": 0,
    }
    for rows in by_course.values():
        required_rows = [row for row in rows if row.get("is_required")]
        if any(row.get("is_present") and not row.get("is_valid") for row in required_rows):
            counts["invalid_courses"] += 1
        elif required_rows and all(row.get("is_present") and row.get("is_valid") for row in required_rows):
            counts["completed_courses"] += 1
        elif any(row.get("is_present") for row in required_rows):
            counts["partial_courses"] += 1
        else:
            counts["missing_courses"] += 1
    return counts


def _blocking_reason(result: dict[str, Any]) -> str | None:
    if result.get("completion_level") == "not_applicable":
        return None
    if result["total_courses"] <= 0:
        return "Bu kapsamda müfredatta seçmeli ders bulunmuyor."
    if result["completion_ratio"] < result["required_completion_ratio"]:
        return (
            f"Algoritma çalıştırılamaz. Tamlık oranı %{result['completion_ratio'] * 100:.1f}, "
            f"minimum eşik %{result['required_completion_ratio'] * 100:.1f}. "
            f"{result['missing_required_fields']} zorunlu alan eksik, "
            f"{result['invalid_required_fields']} zorunlu alan geçersiz."
        )
    if result["blocking_issue_count"] > 0:
        return (
            f"Algoritma çalıştırılamaz. {result['blocking_issue_count']} kritik/geçersiz kriter sorunu var."
        )
    return None


def _empty_scope_result(
    scope_type: str,
    year: int,
    faculty_id: int | None,
    department_id: int | None,
    semester: str | None,
    policy: dict[str, Any],
    required_fields: list[str],
    optional_fields: list[str],
) -> dict[str, Any]:
    """Kapsamda hiç seçmeli ders yokken üretilen 'not_applicable' sonucu.

    Tamlık oranı %100 kabul edilir, kapı engellemez; UI'ya uyarı metni döner.
    """
    return {
        "scope_type": scope_type,
        "faculty_id": faculty_id,
        "department_id": department_id,
        "year": int(year),
        "semester": semester,
        "policy": policy,
        "policy_id": policy.get("id"),
        "policy_name": policy.get("name"),
        "required_fields": required_fields,
        "optional_fields": optional_fields,
        "required_completion_ratio": float(policy.get("required_completion_ratio") or 1.0),
        "completion_ratio": 1.0,
        "completion_level": "not_applicable",
        "criteria_status": STATUS_COMPLETED,
        "total_required_fields": 0,
        "completed_required_fields": 0,
        "missing_required_fields": 0,
        "invalid_required_fields": 0,
        "warning_count": 0,
        "issue_count": 0,
        "blocking_issue_count": 0,
        "matrix": [],
        "validation_issues": [],
        "criterion_summary": {},
        "missing_data_risk": {
            "scope_type": scope_type,
            "faculty_id": faculty_id,
            "department_id": department_id,
            "course_id": None,
            "year": int(year),
            "semester": semester,
            "risk_score": 0.0,
            "risk_level": "low",
            "missing_required_fields": [],
            "missing_optional_fields": [],
            "affected_weight_sum": 0.0,
            "explanation": "Seçili kapsamda seçmeli ders bulunmadığı için risk hesaplanmadı.",
        },
        "override": None,
        "override_active": False,
        "can_run_algorithm": True,
        "blocking_reason": None,
        "warning_reason": "Seçili kapsamda müfredatta seçmeli ders bulunmuyor; tamlık kontrolü uygulanmadı.",
        "total_courses": 0,
        "completed_courses": 0,
        "partial_courses": 0,
        "missing_courses": 0,
        "invalid_courses": 0,
        "last_checked_at": _now(),
    }


def calculate_completion(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any]:
    """Salt okunur kriter tamlık analizi yapar; veritabanına kalıcı yazma yapmaz.

    (Snapshot yazımı için `refresh_completion_status` kullanılır.)
    """
    _ensure_schema(conn)
    scope_type = _normalize_scope_type(scope_type)
    semester = _normalize_semester(semester)
    policy = resolve_policy(conn, scope_type, int(year), faculty_id, department_id, semester)
    required_fields = [str(item) for item in (policy.get("required_fields") or [])]
    optional_fields = [str(item) for item in (policy.get("optional_fields") or []) if item not in required_fields]
    fields = required_fields + optional_fields
    courses = _course_scope(conn, scope_type, int(year), faculty_id, department_id, semester)

    # Boş kapsam (seçmeli ders yok): tıkanma değil 'not_applicable'. Kapı engellemez.
    if not courses:
        return _empty_scope_result(
            scope_type, int(year), faculty_id, department_id, semester,
            policy, required_fields, optional_fields,
        )

    matrix: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for course in courses:
        criteria_row = _latest_criteria_row(
            conn, int(course["course_id"]), int(year), semester,
            department_id=course.get("department_id"),
        )
        for field in fields:
            row, row_issues = _matrix_row_for_field(
                conn=conn,
                course=course,
                criteria_row=criteria_row,
                field=field,
                required=field in required_fields,
                policy=policy,
                year=int(year),
                semester=semester,
            )
            row["scope_type"] = scope_type
            matrix.append(row)
            issues.extend(row_issues)

    required_rows = [row for row in matrix if row.get("is_required")]
    total_required_fields = len(required_rows)
    completed_required_fields = sum(1 for row in required_rows if row.get("is_present") and row.get("is_valid"))
    missing_required_fields = sum(1 for row in required_rows if not row.get("is_present"))
    invalid_required_fields = sum(1 for row in required_rows if row.get("is_present") and not row.get("is_valid"))
    completion_ratio = round(completed_required_fields / total_required_fields, 4) if total_required_fields else 0.0
    warning_count = sum(1 for issue in issues if str(issue.get("severity")) == "warning")
    # Engelleyici bulgu sayımı yalnızca ZORUNLU alanlardaki *geçersiz/bozuk* (present
    # ama valid değil) veriyi sayar. Eksik (missing_required_value) bulgular buraya
    # dahil edilmez; çünkü eksiklik zaten tamlık oranına yansır ve seviyeyi 'blocked'
    # değil 'not_started/partial' yapar. Opsiyonel alanlardaki kirlilik kapıyı tıkamaz.
    # (Kriter Tamlık Yönetişimi belgesiyle uyumlu.)
    def _is_blocking(issue: dict[str, Any]) -> bool:
        if not issue.get("is_required"):
            return False
        if issue.get("issue_type") == "missing_required_value":
            return False
        sev = str(issue.get("severity"))
        if sev == "critical" and policy.get("block_on_critical_issues"):
            return True
        if sev == "error" and policy.get("block_on_invalid_numeric"):
            return True
        return False

    blocking_issue_count = sum(1 for issue in issues if _is_blocking(issue))
    level = _completion_level(
        completion_ratio,
        warning_count=warning_count,
        invalid_required_fields=invalid_required_fields,
        blocking_issue_count=blocking_issue_count,
    )
    counts = _course_counts(matrix)
    risk = calculate_missing_data_risk(
        matrix,
        policy,
        scope_type,
        int(year),
        faculty_id=faculty_id,
        department_id=department_id,
        semester=semester,
    )
    override = get_active_override(
        conn,
        scope_type=scope_type,
        year=int(year),
        faculty_id=faculty_id,
        department_id=department_id,
        course_id=None,
        semester=semester,
    )
    result: dict[str, Any] = {
        "scope_type": scope_type,
        "faculty_id": faculty_id,
        "department_id": department_id,
        "year": int(year),
        "semester": semester,
        "policy": policy,
        "policy_id": policy.get("id"),
        "policy_name": policy.get("name"),
        "required_fields": required_fields,
        "optional_fields": optional_fields,
        "required_completion_ratio": float(policy.get("required_completion_ratio") or 1.0),
        "completion_ratio": completion_ratio,
        "completion_level": level,
        "criteria_status": _legacy_status_from_level(level, completion_ratio),
        "total_required_fields": total_required_fields,
        "completed_required_fields": completed_required_fields,
        "missing_required_fields": missing_required_fields,
        "invalid_required_fields": invalid_required_fields,
        "warning_count": warning_count,
        "issue_count": len(issues),
        "blocking_issue_count": blocking_issue_count,
        "matrix": matrix,
        "validation_issues": issues,
        "criterion_summary": _criterion_summary(matrix),
        "missing_data_risk": risk,
        "override": override,
        "override_active": bool(override),
        "last_checked_at": _now(),
        **counts,
    }
    reason = _blocking_reason(result)
    can_run = reason is None
    if not can_run and override and policy.get("allow_override"):
        can_run = True
        reason = "Onaylı kriter tamlık istisnası ile algoritma çalıştırılabilir."
    result["can_run_algorithm"] = bool(can_run)
    result["blocking_reason"] = None if can_run else reason
    if can_run and level == "completed_with_warnings" and not result["blocking_reason"]:
        result["warning_reason"] = "Kriterler tamam, ancak uyarı seviyesinde veri kalite bulguları var."
    return result


def evaluate_algorithm_readiness(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any]:
    """[Salt okunur] Veritabanına hiçbir yan etki üretmeden tamlık/kapı durumunu döndürür.

    `can_run_algorithm(..., refresh=False)` ve hızlı UI kontrolleri için tercih edilir;
    kalıcı snapshot gerekiyorsa `refresh_completion_status` kullanılmalıdır.
    """
    return calculate_completion(conn, scope_type, int(year), faculty_id, department_id, semester)


def _status_previous(
    conn: sqlite3.Connection,
    table_name: str,
    faculty_id: int | None,
    department_id: int | None,
    year: int,
) -> dict[str, Any] | None:
    cur = conn.cursor()
    if table_name == "criteria_department_status":
        cur.execute(
            """
            SELECT criteria_status, completion_ratio, completion_level
            FROM criteria_department_status
            WHERE fakulte_id = ? AND bolum_id = ? AND yil = ?
            LIMIT 1
            """,
            (int(faculty_id or 0), int(department_id or 0), int(year)),
        )
    else:
        cur.execute(
            """
            SELECT criteria_status, completion_ratio, completion_level
            FROM criteria_faculty_status
            WHERE fakulte_id = ? AND yil = ?
            LIMIT 1
            """,
            (int(faculty_id or 0), int(year)),
        )
    return _fetchone_dict(cur)


def log_completion_change(
    conn: sqlite3.Connection,
    result: dict[str, Any],
    old_status: str | None = None,
    old_ratio: float | None = None,
    old_level: str | None = None,
    changed_by: str | None = None,
    change_reason: str | None = None,
) -> bool:
    _ensure_schema(conn)
    new_status = str(result.get("criteria_status") or STATUS_NOT_STARTED)
    new_ratio = float(result.get("completion_ratio") or 0.0)
    new_level = str(result.get("completion_level") or "not_started")
    ratio_changed = old_ratio is None or abs(float(old_ratio or 0.0) - new_ratio) >= 0.01
    if old_status == new_status and old_level == new_level and not ratio_changed:
        return False
    conn.execute(
        """
        INSERT INTO criteria_completion_history (
            scope_type, faculty_id, department_id, year, semester,
            old_status, new_status, old_completion_ratio, new_completion_ratio,
            old_completion_level, new_completion_level, changed_by, change_reason,
            created_at, summary_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result.get("scope_type"),
            result.get("faculty_id"),
            result.get("department_id"),
            int(result.get("year") or 0),
            result.get("semester"),
            old_status,
            new_status,
            old_ratio,
            new_ratio,
            old_level,
            new_level,
            changed_by,
            change_reason,
            _now(),
            _json_dumps(
                {
                    "total_courses": result.get("total_courses"),
                    "completed_courses": result.get("completed_courses"),
                    "missing_required_fields": result.get("missing_required_fields"),
                    "invalid_required_fields": result.get("invalid_required_fields"),
                    "blocking_reason": result.get("blocking_reason"),
                    "risk_level": (result.get("missing_data_risk") or {}).get("risk_level"),
                    "override_active": result.get("override_active"),
                    "can_run_algorithm": result.get("can_run_algorithm"),
                }
            ),
        ),
    )
    return True


def _upsert_department_status(conn: sqlite3.Connection, result: dict[str, Any], old: dict[str, Any] | None) -> None:
    conn.execute(
        """
        INSERT INTO criteria_department_status (
            fakulte_id, bolum_id, yil, criteria_status,
            required_course_count, completed_course_count, missing_course_count,
            updated_at, semester, completion_ratio, completion_level,
            required_completion_ratio, total_courses, completed_courses,
            partial_courses, missing_courses, invalid_courses,
            total_required_fields, completed_required_fields, missing_required_fields,
            invalid_required_fields, last_checked_at, blocking_reason,
            can_run_algorithm, override_active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(fakulte_id, bolum_id, yil) DO UPDATE SET
            criteria_status = excluded.criteria_status,
            required_course_count = excluded.required_course_count,
            completed_course_count = excluded.completed_course_count,
            missing_course_count = excluded.missing_course_count,
            updated_at = excluded.updated_at,
            semester = excluded.semester,
            completion_ratio = excluded.completion_ratio,
            completion_level = excluded.completion_level,
            required_completion_ratio = excluded.required_completion_ratio,
            total_courses = excluded.total_courses,
            completed_courses = excluded.completed_courses,
            partial_courses = excluded.partial_courses,
            missing_courses = excluded.missing_courses,
            invalid_courses = excluded.invalid_courses,
            total_required_fields = excluded.total_required_fields,
            completed_required_fields = excluded.completed_required_fields,
            missing_required_fields = excluded.missing_required_fields,
            invalid_required_fields = excluded.invalid_required_fields,
            last_checked_at = excluded.last_checked_at,
            blocking_reason = excluded.blocking_reason,
            can_run_algorithm = excluded.can_run_algorithm,
            override_active = excluded.override_active
        """,
        (
            int(result["faculty_id"]),
            int(result["department_id"]),
            int(result["year"]),
            result["criteria_status"],
            int(result["total_courses"]),
            int(result["completed_courses"]),
            int(result["missing_courses"] + result["partial_courses"] + result["invalid_courses"]),
            _now(),
            result.get("semester"),
            float(result["completion_ratio"]),
            result["completion_level"],
            float(result["required_completion_ratio"]),
            int(result["total_courses"]),
            int(result["completed_courses"]),
            int(result["partial_courses"]),
            int(result["missing_courses"]),
            int(result["invalid_courses"]),
            int(result["total_required_fields"]),
            int(result["completed_required_fields"]),
            int(result["missing_required_fields"]),
            int(result["invalid_required_fields"]),
            result["last_checked_at"],
            result.get("blocking_reason"),
            1 if result.get("can_run_algorithm") else 0,
            1 if result.get("override_active") else 0,
        ),
    )
    log_completion_change(
        conn,
        result,
        old_status=old.get("criteria_status") if old else None,
        old_ratio=float(old.get("completion_ratio") or 0.0) if old and old.get("completion_ratio") is not None else None,
        old_level=old.get("completion_level") if old else None,
    )


def _upsert_faculty_status(conn: sqlite3.Connection, result: dict[str, Any], old: dict[str, Any] | None) -> None:
    conn.execute(
        """
        INSERT INTO criteria_faculty_status (
            fakulte_id, yil, criteria_status, total_department_count,
            completed_department_count, algorithm_run_status, algorithm_run_at,
            generated_year, year_active, updated_at, semester, completion_ratio,
            completion_level, required_completion_ratio, total_courses,
            completed_courses, partial_courses, missing_courses, invalid_courses,
            total_required_fields, completed_required_fields, missing_required_fields,
            invalid_required_fields, last_checked_at, blocking_reason,
            can_run_algorithm, override_active
        )
        VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(fakulte_id, yil) DO UPDATE SET
            criteria_status = excluded.criteria_status,
            total_department_count = excluded.total_department_count,
            completed_department_count = excluded.completed_department_count,
            algorithm_run_status = COALESCE(criteria_faculty_status.algorithm_run_status, excluded.algorithm_run_status),
            year_active = 1,
            updated_at = excluded.updated_at,
            semester = excluded.semester,
            completion_ratio = excluded.completion_ratio,
            completion_level = excluded.completion_level,
            required_completion_ratio = excluded.required_completion_ratio,
            total_courses = excluded.total_courses,
            completed_courses = excluded.completed_courses,
            partial_courses = excluded.partial_courses,
            missing_courses = excluded.missing_courses,
            invalid_courses = excluded.invalid_courses,
            total_required_fields = excluded.total_required_fields,
            completed_required_fields = excluded.completed_required_fields,
            missing_required_fields = excluded.missing_required_fields,
            invalid_required_fields = excluded.invalid_required_fields,
            last_checked_at = excluded.last_checked_at,
            blocking_reason = excluded.blocking_reason,
            can_run_algorithm = excluded.can_run_algorithm,
            override_active = excluded.override_active
        """,
        (
            int(result["faculty_id"]),
            int(result["year"]),
            result["criteria_status"],
            int(result.get("total_department_count") or 0),
            int(result.get("completed_department_count") or 0),
            ALGORITHM_NOT_RUN,
            _now(),
            result.get("semester"),
            float(result["completion_ratio"]),
            result["completion_level"],
            float(result["required_completion_ratio"]),
            int(result["total_courses"]),
            int(result["completed_courses"]),
            int(result["partial_courses"]),
            int(result["missing_courses"]),
            int(result["invalid_courses"]),
            int(result["total_required_fields"]),
            int(result["completed_required_fields"]),
            int(result["missing_required_fields"]),
            int(result["invalid_required_fields"]),
            result["last_checked_at"],
            result.get("blocking_reason"),
            1 if result.get("can_run_algorithm") else 0,
            1 if result.get("override_active") else 0,
        ),
    )
    log_completion_change(
        conn,
        result,
        old_status=old.get("criteria_status") if old else None,
        old_ratio=float(old.get("completion_ratio") or 0.0) if old and old.get("completion_ratio") is not None else None,
        old_level=old.get("completion_level") if old else None,
    )


def refresh_completion_status(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    result = calculate_completion(conn, scope_type, int(year), faculty_id, department_id, semester)
    _persist_matrix_and_issues(conn, result, result.get("validation_issues") or [])
    result["missing_data_risk"] = persist_missing_data_risk(conn, result["missing_data_risk"])

    if result["scope_type"] == "department" and result.get("faculty_id") is not None and result.get("department_id") is not None:
        old = _status_previous(
            conn,
            "criteria_department_status",
            result.get("faculty_id"),
            result.get("department_id"),
            int(result["year"]),
        )
        _upsert_department_status(conn, result, old)

    if result["scope_type"] == "faculty" and result.get("faculty_id") is not None:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(DISTINCT m.bolum_id)
            FROM mufredat m
            JOIN bolum b ON b.bolum_id = m.bolum_id
            WHERE b.fakulte_id = ? AND m.akademik_yil = ?
            """,
            (int(result["faculty_id"]), int(result["year"])),
        )
        total_departments = int(cur.fetchone()[0] or 0)
        cur.execute(
            """
            SELECT COUNT(*)
            FROM criteria_department_status
            WHERE fakulte_id = ? AND yil = ? AND criteria_status = ?
            """,
            (int(result["faculty_id"]), int(result["year"]), STATUS_COMPLETED),
        )
        completed_departments = int(cur.fetchone()[0] or 0)
        result["total_department_count"] = total_departments
        result["completed_department_count"] = completed_departments
        old = _status_previous(
            conn,
            "criteria_faculty_status",
            result.get("faculty_id"),
            None,
            int(result["year"]),
        )
        _upsert_faculty_status(conn, result, old)

    if commit:
        conn.commit()
    return result


def get_completion_summary(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
    refresh: bool = True,
) -> dict[str, Any]:
    if refresh:
        return refresh_completion_status(conn, scope_type, int(year), faculty_id, department_id, semester)
    return calculate_completion(conn, scope_type, int(year), faculty_id, department_id, semester)


def get_blocking_reason(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> str | None:
    # Salt sorgu: engel nedenini öğrenmek için kalıcı snapshot yazmaya gerek yok.
    summary = get_completion_summary(conn, scope_type, int(year), faculty_id, department_id, semester, refresh=False)
    return summary.get("blocking_reason")


def can_run_algorithm(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
    scope_type: str | None = None,
    refresh: bool = True,
) -> dict[str, Any]:
    """Güvenlik kapısı sonucunu döndürür.

    `refresh=True` (varsayılan, geriye dönük uyum): durum tablolarına snapshot yazar.
    `refresh=False`: salt okunur — hızlı UI kontrolleri için yazma yan etkisi olmadan
    değerlendirir (bkz. `evaluate_algorithm_readiness`).
    """
    resolved_scope = scope_type or ("department" if department_id is not None else "faculty")
    summary = get_completion_summary(
        conn,
        resolved_scope,
        int(year),
        faculty_id=faculty_id,
        department_id=department_id,
        semester=semester,
        refresh=refresh,
    )
    return {
        "can_run": bool(summary.get("can_run_algorithm")),
        "blocking_reason": summary.get("blocking_reason"),
        "completion_ratio": summary.get("completion_ratio"),
        "completion_level": summary.get("completion_level"),
        "required_completion_ratio": summary.get("required_completion_ratio"),
        "missing_required_fields": summary.get("missing_required_fields"),
        "invalid_required_fields": summary.get("invalid_required_fields"),
        "blocking_issue_count": summary.get("blocking_issue_count"),
        "override_active": summary.get("override_active"),
        "override": summary.get("override"),
        "risk": summary.get("missing_data_risk"),
        "policy": summary.get("policy"),
        "summary": summary,
    }


def get_completion_matrix(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
    refresh: bool = True,
) -> list[dict[str, Any]]:
    summary = get_completion_summary(conn, scope_type, int(year), faculty_id, department_id, semester, refresh=refresh)
    return summary.get("matrix") or []


def get_validation_issues(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
    refresh: bool = True,
) -> list[dict[str, Any]]:
    summary = get_completion_summary(conn, scope_type, int(year), faculty_id, department_id, semester, refresh=refresh)
    return summary.get("validation_issues") or []


def get_completion_history(
    conn: sqlite3.Connection,
    scope_type: str | None = None,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    _ensure_schema(conn)
    where = ["1=1"]
    params: list[Any] = []
    for col, value in (
        ("scope_type", scope_type),
        ("year", year),
        ("faculty_id", faculty_id),
        ("department_id", department_id),
        ("semester", _normalize_semester(semester)),
    ):
        if value is not None:
            where.append(f"{col} = ?")
            params.append(value)
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT *
        FROM criteria_completion_history
        WHERE {' AND '.join(where)}
        ORDER BY id DESC
        LIMIT ?
        """,
        tuple(params + [int(limit)]),
    )
    rows = _fetchall_dicts(cur)
    for row in rows:
        row["summary"] = _json_loads(row.get("summary_json"), {})
    return rows
