# -*- coding: utf-8 -*-
"""Kriter değeri geçerlilik kontrolü ve validasyon servisi.

Bu servis "alan dolu görünüyor ama gerçekten anlamlı mı?" sorusunu yanıtlar.
`criteria_completion_service` matris üretirken buradaki `validate_criterion_value`
çağrısını kullanır; dolayısıyla buradaki severity seçimleri doğrudan tamlık oranını,
seviyeyi ve algoritma kapısını etkiler.

Severity sözleşmesi (Kriter Tamlık Yönetişimi belgesiyle uyumlu):
    - missing_required_value           -> critical  (zorunlu alan boş)
    - passed_students > total_students  -> critical  (karar çekirdeği tutarsızlığı)
    - average_grade ölçek dışı          -> critical  (karar çekirdeği veri hatası)
    - negatif / ondalık öğrenci-kontenjan, oran sınır aşımı -> error
    - kontenjan aşımı (enrolled>capacity) -> warning
    - opsiyonel alan boş                -> info (kapıyı/uyarıyı kirletmez)

Not: critical iş kuralı bulgularında `status` bilinçli olarak "invalid" tutulur
(değer mevcut ama geçersiz). Yalnızca tamamen boş zorunlu alan "critical" status'una
sahiptir. Bu ayrım, tüketici tarafın present/missing sınıflamasını bozmaz.
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_criteria_completion_governance_schema
from app.services.course_type import filter_elective_course_ids

MISSING_STRINGS = {"", "-", "yok", "n/a", "na", "none", "null"}
VALID_SCOPE_TYPES = {"faculty", "department"}

# Kullanıcıya teknik alan adı yerine Türkçe etiket göstermek için.
FIELD_LABELS = {
    "total_students": "Toplam öğrenci",
    "passed_students": "Geçen öğrenci",
    "average_grade": "Not ortalaması",
    "capacity": "Kontenjan",
    "enrolled_students": "Kayıtlı öğrenci",
    "survey_count": "Anket seçimi",
    "trend": "Geçmiş trend",
    "success_rate": "Başarı oranı",
    "popularity": "Popülerlik",
}


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
    is_required: bool = True

    @property
    def is_valid(self) -> bool:
        return self.status in {"valid", "warning"}

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_semester(value: str | None) -> str | None:
    """Dönemi 'Güz'/'Bahar' kanonik biçimine indirger; bilinmeyen değeri reddeder."""
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
    scope = str(value or "").strip().lower()
    if scope not in VALID_SCOPE_TYPES:
        raise ValueError(
            f"Geçersiz kapsam türü (scope_type): '{value}'. Beklenen: {sorted(VALID_SCOPE_TYPES)}"
        )
    return scope


def _validate_scope_ids(
    scope_type: str, faculty_id: int | None, department_id: int | None
) -> tuple[int, int | None]:
    if faculty_id is None:
        raise ValueError(f"'{scope_type}' kapsamındaki validasyon için faculty_id zorunludur.")
    if scope_type == "faculty":
        return int(faculty_id), None
    # scope_type == "department"
    if department_id is None:
        raise ValueError("Bölüm kapsamındaki validasyon için department_id zorunludur.")
    return int(faculty_id), int(department_id)


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
    label = FIELD_LABELS.get(field_name, field_name)
    if required:
        return ValidationResult(
            field_name=field_name,
            value=value,
            status="critical",
            severity="critical",
            issue_type="missing_required_value",
            message=f"'{label}' alanı zorunludur ancak boş görünüyor.",
            suggestion="Bu alanı ilgili ders için doldurun.",
            is_required=True,
        )
    # Opsiyonel eksiklik: info seviyesinde tutulur; sistemi 'completed_with_warnings'
    # durumuna kilitlemez ve algoritma kapısını etkilemez.
    return ValidationResult(
        field_name=field_name,
        value=value,
        status="valid",
        severity="info",
        issue_type="missing_optional_value",
        message=f"'{label}' alanı opsiyonel ve boş.",
        suggestion="Varsa bu alanı tamamlayın; yoksa opsiyonel olarak bırakılabilir.",
        is_required=False,
    )


def validate_criterion_value(
    field_name: str,
    value: Any,
    context: dict[str, Any] | None = None,
) -> ValidationResult:
    """Tek bir kriter alanını iş kurallarına göre doğrular."""
    context = context or {}
    required = bool(context.get("required", True))
    label = FIELD_LABELS.get(field_name, field_name)
    exists, number = _normalize_number(value)
    if not exists:
        return _missing(field_name, value, required)

    if field_name in {"total_students", "passed_students", "capacity", "enrolled_students", "survey_count"}:
        if number is None:
            return ValidationResult(field_name, value, is_required=required)
        if number < 0:
            return ValidationResult(
                field_name,
                value,
                status="invalid",
                severity="error",
                issue_type="out_of_range",
                message=f"'{label}' negatif olamaz.",
                suggestion="Bu alanı 0 veya pozitif bir tam sayı yapın.",
                normalized_value=number,
                is_required=required,
            )
        if int(number) != number:
            # Öğrenci/kontenjan/anket alanları ondalıklı olamaz; veri kullanılmamalı.
            return ValidationResult(
                field_name,
                value,
                status="invalid",
                severity="error",
                issue_type="invalid_numeric_value",
                message=f"'{label}' tam sayı olmalıdır, ondalıklı değer kabul edilmez.",
                suggestion="Öğrenci/kontenjan alanlarını tam sayı girin.",
                normalized_value=number,
                is_required=required,
            )

    if field_name == "passed_students":
        total = context.get("total_students")
        ok, total_number = _normalize_number(total)
        if ok and total_number is not None and number is not None and number > total_number:
            return ValidationResult(
                field_name,
                value,
                status="invalid",
                severity="critical",  # Karar çekirdeği tutarsızlığı: kapıyı engeller.
                issue_type="inconsistent_values",
                message=f"Geçen öğrenci sayısı ({int(number)}), '{FIELD_LABELS['total_students']}' sayısından ({int(total_number)}) büyük olamaz.",
                suggestion="Toplam ve geçen öğrenci sayılarını birlikte kontrol edin.",
                normalized_value=number,
                is_required=required,
            )

    if field_name == "average_grade":
        grade_scale = str(context.get("grade_scale") or "100")
        max_grade = 4.0 if grade_scale == "4" else 100.0
        if number is None or number < 0 or number > max_grade:
            return ValidationResult(
                field_name,
                value,
                status="invalid",
                severity="critical",  # Karar çekirdeği veri hatası: kapıyı engeller.
                issue_type="out_of_range",
                message=f"'{label}' 0-{max_grade:g} aralığında olmalıdır.",
                suggestion="Not ortalamasını beklenen ölçekte girin.",
                normalized_value=number,
                is_required=required,
            )

    if field_name == "enrolled_students":
        capacity = context.get("capacity")
        ok, capacity_number = _normalize_number(capacity)
        if ok and capacity_number is not None and capacity_number >= 0 and number is not None and number > capacity_number:
            return ValidationResult(
                field_name,
                value,
                status="warning",  # Kontenjan aşımı olabilir; engellemez, uyarır.
                severity="warning",
                issue_type="inconsistent_values",
                message=f"Kayıtlı öğrenci sayısı ({int(number)}), '{FIELD_LABELS['capacity']}' değerini ({int(capacity_number)}) aşıyor.",
                suggestion="Kontenjan aşımı bilinçli değilse kayıtlı öğrenci veya kontenjan değerini kontrol edin.",
                normalized_value=number,
                is_required=required,
            )

    if field_name in {"success_rate", "popularity"}:
        if number is None or number < 0 or number > 100:
            return ValidationResult(
                field_name,
                value,
                status="invalid",
                severity="error",
                issue_type="out_of_range",
                message=f"'{label}' 0-100 aralığında olmalıdır.",
                suggestion="Oranı yüzde biçiminde 0 ile 100 arasında girin.",
                normalized_value=number,
                is_required=required,
            )

    return ValidationResult(field_name=field_name, value=value, normalized_value=number, is_required=required)


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
    department_id: int | None = None,
    required_fields: list[str] | None = None,
) -> dict[str, Any]:
    """Bir ders için kriter verisini doğrular.

    Dönem filtresi verildiğinde dönem-spesifik kayıt, jenerik (dönemsiz) kayda göre
    önceliklendirilir. (Not: `ders_kriterleri` tablosunda bölüm kolonu bulunmadığından
    `department_id` yalnızca bağlam/raporlama için tutulur; sorguda kullanılamaz.)
    """
    required_fields = required_fields or [
        "total_students",
        "passed_students",
        "average_grade",
        "capacity",
        "enrolled_students",
    ]
    cur = conn.cursor()
    if not _table_exists(cur, "ders_kriterleri"):
        return {"course_id": int(course_id), "department_id": department_id, "results": [], "issues": []}
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
        # Önce dönem-spesifik kayıt, sonra dönemsiz jenerik, sonra en yeni id.
        query += (
            f" ORDER BY CASE WHEN {_semester_clause('dk')} THEN 0"
            " WHEN dk.donem IS NULL OR TRIM(COALESCE(dk.donem, '')) = '' THEN 1"
            " ELSE 2 END, dk.id DESC LIMIT 1"
        )
        params.append(str(semester))
    else:
        query += " ORDER BY dk.id DESC LIMIT 1"
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
        "department_id": department_id,
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
    replace_existing: bool = True,
    commit: bool = True,
) -> None:
    """Validasyon bulgularını kaydeder.

    `replace_existing=True` ise aynı kapsam/yıl/dönem için önceki bulgular silinerek
    mükerrer kayıt önlenir. Transaction sözleşmesi diğer servislerle aynıdır
    (`commit=False` ile çağrı yapıldığında commit/rollback çağırana aittir).
    """
    ensure_criteria_completion_governance_schema(conn, commit=False)
    scope_type = _normalize_scope_type(scope_type)
    faculty_id, department_id = _validate_scope_ids(scope_type, faculty_id, department_id)
    semester = _normalize_semester(semester)
    cur = conn.cursor()
    try:
        if replace_existing:
            where_del = ["scope_type = ?", "year = ?", "COALESCE(semester, '') = COALESCE(?, '')", "faculty_id = ?"]
            params_del: list[Any] = [scope_type, int(year), semester, int(faculty_id)]
            if department_id is not None:
                where_del.append("department_id = ?")
                params_del.append(int(department_id))
            if course_id is not None:
                where_del.append("course_id = ?")
                params_del.append(int(course_id))
            cur.execute(f"DELETE FROM criteria_validation_issues WHERE {' AND '.join(where_del)}", tuple(params_del))
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
    except Exception:
        if commit:
            conn.rollback()
        raise
    if commit:
        conn.commit()


def _course_scope_for_validation(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> list[dict[str, Any]]:
    """Karar kapısıyla aynı kaynağı kullanır: müfredattaki aktif seçmeli dersler.

    (Eski `validate_scope_criteria` doğrudan `ders` tablosundan ders çekiyordu; bu,
    güvenlik kapısının baktığı ders setiyle tutarsızlık üretebiliyordu.)
    """
    cur = conn.cursor()
    query = """
        SELECT DISTINCT
            md.ders_id AS course_id,
            m.bolum_id AS department_id
        FROM mufredat m
        JOIN bolum b ON b.bolum_id = m.bolum_id
        JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
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
        query += " AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))"
        params.append(str(semester))
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    course_ids = {int(r[0]) for r in rows if r[0] is not None}
    elective_ids = filter_elective_course_ids(cur, course_ids)
    out: list[dict[str, Any]] = []
    if elective_ids:
        for r in rows:
            if r[0] is not None and int(r[0]) in elective_ids:
                out.append({"course_id": int(r[0]), "department_id": int(r[1]) if r[1] is not None else None})
    return out


def validate_scope_criteria(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
    required_fields: list[str] | None = None,
) -> dict[str, Any]:
    """Seçili kapsamdaki müfredat seçmeli derslerini toplu doğrular (kapı ile aynı ders seti)."""
    scope_type = _normalize_scope_type(scope_type)
    faculty_id, department_id = _validate_scope_ids(scope_type, faculty_id, department_id)
    semester = _normalize_semester(semester)

    target_courses = _course_scope_for_validation(conn, scope_type, int(year), faculty_id, department_id, semester)
    all_issues: list[dict[str, Any]] = []
    courses_results: list[dict[str, Any]] = []
    for item in target_courses:
        cid = item["course_id"]
        did = item["department_id"]
        result = validate_course_criteria(conn, cid, int(year), semester, department_id=did, required_fields=required_fields)
        courses_results.append(result)
        for issue in result["issues"]:
            issue["course_id"] = cid
            issue["department_id"] = did
            all_issues.append(issue)
    return {
        "scope_type": scope_type,
        "year": int(year),
        "semester": semester,
        "courses": courses_results,
        "issues": all_issues,
        "issue_count": len(all_issues),
    }
