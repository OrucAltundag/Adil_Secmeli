# -*- coding: utf-8 -*-
"""Eksik kriter verisi risk skoru servisi.

Eksik/geçersiz kriter verisinin karar güvenilirliği üzerindeki riskini 0.0–1.0
arasında ölçer. Risk, **ders × kriter satırları** üzerinden ağırlıklı yaygınlık
olarak hesaplanır: aynı alanın 1 derste mi yoksa 100 derste mi eksik olduğunu
ayırt eder (eski sürüm yalnızca benzersiz alan listesine bakıyordu).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_criteria_completion_governance_schema

# Kriter Tamlık Yönetişimi belgesiyle uyumlu varsayılan alan ağırlıkları (toplam ≈ 1.0).
DEFAULT_FIELD_WEIGHTS = {
    "total_students": 0.18,
    "passed_students": 0.18,
    "average_grade": 0.22,
    "capacity": 0.16,
    "enrolled_students": 0.16,
    "survey_count": 0.06,
    "trend": 0.04,
}

# Risk seviyesi eşikleri (governance belgesi §7 ile aynı):
#   < 0.25 low | 0.25–0.54 medium | 0.55–0.79 high | >= 0.80 critical
RISK_THRESHOLDS = {"medium": 0.25, "high": 0.55, "critical": 0.80}

# Opsiyonel alan eksikliğinin risk havuzundaki ağırlık çarpanı (zorunluya göre düşük).
DEFAULT_OPTIONAL_MULTIPLIER = 0.35


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
        return default


def _risk_level(score: float, thresholds: dict[str, float] | None = None) -> str:
    th = thresholds or RISK_THRESHOLDS
    if score >= th.get("critical", 0.80):
        return "critical"
    if score >= th.get("high", 0.55):
        return "high"
    if score >= th.get("medium", 0.25):
        return "medium"
    return "low"


def calculate_missing_data_risk(
    matrix_rows: list[dict[str, Any]],
    policy: dict[str, Any],
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    course_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any]:
    """Eksik/geçersiz kriter verisinin karar riskini satır-bazlı ağırlıklı yaygınlıkla hesaplar.

    `course_id` verilirse matris yalnızca o derse daraltılır (course-level risk).
    """
    policy = policy or {}
    field_weights = policy.get("risk_field_weights") or DEFAULT_FIELD_WEIGHTS
    try:
        optional_multiplier = float(policy.get("optional_risk_multiplier") or DEFAULT_OPTIONAL_MULTIPLIER)
    except (TypeError, ValueError):
        optional_multiplier = DEFAULT_OPTIONAL_MULTIPLIER
    thresholds = policy.get("risk_thresholds") or RISK_THRESHOLDS

    # course_id izolasyonu: parametre verildiyse rapor gerçekten o derse ait olsun.
    if course_id is not None:
        matrix_rows = [
            row for row in matrix_rows
            if row.get("course_id") is not None and int(row["course_id"]) == int(course_id)
        ]

    if not matrix_rows:
        return {
            "scope_type": scope_type,
            "faculty_id": faculty_id,
            "department_id": department_id,
            "course_id": course_id,
            "year": int(year),
            "semester": semester,
            "risk_score": 0.0,
            "risk_level": "low",
            "missing_required_fields": [],
            "missing_optional_fields": [],
            "affected_weight_sum": 0.0,
            "weighted_risk_ratio": 0.0,
            "total_course_count": 0,
            "affected_course_count": 0,
            "missing_required_count": 0,
            "invalid_required_count": 0,
            "missing_optional_count": 0,
            "invalid_optional_count": 0,
            "explanation": "Seçili kapsamda risk hesaplanacak kriter matris satırı bulunamadı.",
            "not_applicable": True,
        }

    total_possible_weight = 0.0
    total_affected_weight = 0.0
    missing_required_fields: set[str] = set()
    missing_optional_fields: set[str] = set()
    all_courses: set[Any] = set()
    required_affected_courses: set[Any] = set()
    optional_affected_courses: set[Any] = set()
    missing_required_count = 0
    invalid_required_count = 0
    missing_optional_count = 0
    invalid_optional_count = 0

    for row in matrix_rows:
        field = str(row.get("criterion_key") or "").strip()
        if not field:
            continue
        cid = row.get("course_id")
        if cid is not None:
            all_courses.add(cid)

        is_required = bool(row.get("is_required"))
        base_weight = field_weights.get(field, 0.10)
        # Her hücrenin teorik ağırlığı; opsiyonel hücreler düşük çarpanla havuza girer.
        cell_weight = base_weight if is_required else base_weight * optional_multiplier
        total_possible_weight += cell_weight

        is_missing = not bool(row.get("is_present"))
        is_invalid = bool(row.get("is_present")) and not bool(row.get("is_valid"))
        if not (is_missing or is_invalid):
            continue

        total_affected_weight += cell_weight
        if is_required:
            missing_required_fields.add(field)
            if cid is not None:
                required_affected_courses.add(cid)
            if is_missing:
                missing_required_count += 1
            else:
                invalid_required_count += 1
        else:
            missing_optional_fields.add(field)
            if cid is not None:
                optional_affected_courses.add(cid)
            if is_missing:
                missing_optional_count += 1
            else:
                invalid_optional_count += 1

    weighted_risk_ratio = total_affected_weight / total_possible_weight if total_possible_weight > 0 else 0.0
    total_course_count = max(1, len(all_courses))
    required_affected_ratio = len(required_affected_courses) / total_course_count
    optional_affected_ratio = len(optional_affected_courses) / total_course_count

    # Dengeli skor: %70 hücresel ağırlık oranı + %25 zorunlu ders yaygınlığı
    # + %5 opsiyonel ders yaygınlığı. Böylece yaygın zorunlu eksikler hak ettiği
    # ağırlığı alır; yalnızca opsiyonel yaygın eksiklik riski aşırı şişirmez.
    score = min(
        1.0,
        round(
            (weighted_risk_ratio * 0.70)
            + (required_affected_ratio * 0.25)
            + (optional_affected_ratio * 0.05),
            4,
        ),
    )
    level = _risk_level(score, thresholds)
    affected_course_count = len(required_affected_courses | optional_affected_courses)

    if missing_required_fields:
        explanation = (
            f"{len(missing_required_fields)} zorunlu kriterde {missing_required_count} eksik, "
            f"{invalid_required_count} geçersiz veri var. Seçmeli ders havuzunun "
            f"%{required_affected_ratio * 100:.1f}'i etkileniyor; risk seviyesi {level}."
        )
    elif missing_optional_fields:
        explanation = (
            f"Zorunlu kriterler tamam; {len(missing_optional_fields)} opsiyonel kriterde "
            f"{missing_optional_count + invalid_optional_count} eksik/geçersiz hücre var. "
            f"Karar riski {level} seviyesinde."
        )
    else:
        explanation = "Eksik/geçersiz kriter verisi tespit edilmedi; risk düşük."

    return {
        "scope_type": scope_type,
        "faculty_id": faculty_id,
        "department_id": department_id,
        "course_id": course_id,
        "year": int(year),
        "semester": semester,
        "risk_score": score,
        "risk_level": level,
        "missing_required_fields": sorted(missing_required_fields),
        "missing_optional_fields": sorted(missing_optional_fields),
        "affected_weight_sum": round(total_affected_weight, 4),
        "weighted_risk_ratio": round(weighted_risk_ratio, 4),
        "total_course_count": total_course_count,
        "affected_course_count": affected_course_count,
        "missing_required_count": missing_required_count,
        "invalid_required_count": invalid_required_count,
        "missing_optional_count": missing_optional_count,
        "invalid_optional_count": invalid_optional_count,
        "explanation": explanation,
    }


def persist_missing_data_risk(conn: sqlite3.Connection, risk: dict[str, Any]) -> dict[str, Any]:
    """Risk snapshot'ını `criteria_missing_data_risks` tablosuna yazar.

    Tek transaction modelini korumak için burada commit YAPILMAZ; commit sorumluluğu
    çağırana aittir (`refresh_completion_status` zincirin sonunda commit eder).
    Tablo yalnızca alan-listesi + ağırlık + açıklama kolonlarını tuttuğundan, ek
    sayaçlar (missing_required_count vb.) yalnızca dönen sözlükte taşınır.
    """
    ensure_criteria_completion_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM criteria_missing_data_risks
        WHERE scope_type = ?
          AND COALESCE(faculty_id, -1) = COALESCE(?, -1)
          AND COALESCE(department_id, -1) = COALESCE(?, -1)
          AND COALESCE(course_id, -1) = COALESCE(?, -1)
          AND year = ?
          AND COALESCE(semester, '') = COALESCE(?, '')
        """,
        (
            risk.get("scope_type"),
            risk.get("faculty_id"),
            risk.get("department_id"),
            risk.get("course_id"),
            int(risk.get("year") or 0),
            risk.get("semester"),
        ),
    )
    cur.execute(
        """
        INSERT INTO criteria_missing_data_risks (
            scope_type, faculty_id, department_id, course_id, year, semester,
            risk_score, risk_level, missing_required_fields_json,
            missing_optional_fields_json, affected_weight_sum, explanation, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            risk.get("scope_type"),
            risk.get("faculty_id"),
            risk.get("department_id"),
            risk.get("course_id"),
            int(risk.get("year") or 0),
            risk.get("semester"),
            float(risk.get("risk_score") or 0.0),
            risk.get("risk_level") or "low",
            _json_dumps(risk.get("missing_required_fields") or []),
            _json_dumps(risk.get("missing_optional_fields") or []),
            risk.get("affected_weight_sum"),
            risk.get("explanation"),
            _now(),
        ),
    )
    risk["id"] = int(cur.lastrowid or 0)
    return risk


def get_missing_data_risk_report(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any] | None:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM criteria_missing_data_risks
        WHERE scope_type = ?
          AND COALESCE(faculty_id, -1) = COALESCE(?, -1)
          AND COALESCE(department_id, -1) = COALESCE(?, -1)
          AND course_id IS NULL
          AND year = ?
          AND COALESCE(semester, '') = COALESCE(?, '')
        ORDER BY id DESC
        LIMIT 1
        """,
        (scope_type, faculty_id, department_id, int(year), semester),
    )
    row = cur.fetchone()
    if not row:
        return None
    # row_factory ayarlı değilse (tuple) de doğru dict üret (dayanıklılık).
    if isinstance(row, sqlite3.Row):
        data = {key: row[key] for key in row.keys()}
    else:
        columns = [desc[0] for desc in cur.description] if cur.description else []
        data = {columns[idx]: row[idx] for idx in range(min(len(columns), len(row)))}
    for key in ("missing_required_fields_json", "missing_optional_fields_json"):
        data[key.replace("_json", "")] = _json_loads(data.get(key), [])
    return data
