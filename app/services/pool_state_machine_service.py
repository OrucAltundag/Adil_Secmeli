# -*- coding: utf-8 -*-
"""Akademik havuz yasam dongusu state machine servisi."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_pool_state_governance_schema
from app.services.havuz_karar import (
    STATU_DINLENMEDE,
    STATU_HAVUZDA,
    STATU_IPTAL,
    STATU_MUFREDATTA,
)
from app.services.pool_state_policy_service import normalize_semester, resolve_policy

STATUS_TEXT = {
    STATU_MUFREDATTA: "müfredatta",
    STATU_HAVUZDA: "havuzda",
    STATU_DINLENMEDE: "dinlenmede",
    STATU_IPTAL: "kalıcı iptal",
}

GOVERNANCE_FIELDS = {
    "strategic_flag",
    "accreditation_flag",
    "protected_flag",
    "required_course_flag",
    "service_course_flag",
    "new_course_flag",
    "revised_course_flag",
    "instructor_changed",
    "content_updated",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _load_json(raw: str | None, default: Any = None) -> Any:
    if raw is None:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "evet", "on"}
    return bool(value)


def _int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _score100(value: Any) -> float | None:
    score = _float(value)
    if score is None:
        return None
    if 0.0 <= score <= 1.0:
        return score * 100.0
    return score


def _confidence01(value: Any) -> float | None:
    score = _float(value)
    if score is None:
        return None
    if score > 1.0:
        return max(0.0, min(score / 100.0, 1.0))
    return max(0.0, min(score, 1.0))


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None = None) -> dict[str, Any] | None:
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return {key: row[key] for key in row.keys()}
    if columns:
        return {columns[idx]: row[idx] for idx in range(min(len(columns), len(row)))}
    return None


def _fetch_all_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]:
    columns = [d[0] for d in cur.description] if cur.description else []
    return [_row_to_dict(row, columns) or {} for row in cur.fetchall()]


def _fetch_one_dict(cur: sqlite3.Cursor) -> dict[str, Any] | None:
    columns = [d[0] for d in cur.description] if cur.description else []
    return _row_to_dict(cur.fetchone(), columns)


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return {str(row[1]) for row in cur.fetchall()}


def _status_label(status: int | None) -> str:
    try:
        return STATUS_TEXT.get(int(status or 0), "belirsiz")
    except (TypeError, ValueError):
        return "belirsiz"


def _lifecycle_for_status(status: int, *, protected: bool = False) -> str:
    if protected:
        return "protected"
    if status == STATU_MUFREDATTA:
        return "curriculum"
    if status == STATU_HAVUZDA:
        return "pool"
    if status == STATU_DINLENMEDE:
        return "resting"
    if status == STATU_IPTAL:
        return "permanently_cancelled"
    return "under_review"


def _is_required_course_type(value: str | None) -> bool:
    text = str(value or "").strip().lower()
    return any(token in text for token in ("zorunlu", "required", "core", "mandatory"))


def _is_service_course_type(value: str | None) -> bool:
    text = str(value or "").strip().lower()
    return any(token in text for token in ("servis", "service"))


def get_course_metadata(conn: sqlite3.Connection, course_id: int) -> dict[str, Any]:
    cols = _table_columns(conn, "ders")
    wanted = [c for c in ("ders_id", "kod", "ad", "bolum_id", "fakulte_id", "DersTipi", "tip") if c in cols]
    if not wanted:
        return {"course_id": int(course_id)}
    cur = conn.cursor()
    cur.execute(f"SELECT {', '.join(wanted)} FROM ders WHERE ders_id = ?", (int(course_id),))
    row = _fetch_one_dict(cur)
    if not row:
        return {"course_id": int(course_id)}
    row["course_id"] = int(course_id)
    row["course_type"] = row.get("DersTipi") or row.get("tip") or ""
    return row


def get_governance_flags(conn: sqlite3.Connection, course_id: int) -> dict[str, Any]:
    ensure_pool_state_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM course_governance_flags WHERE course_id = ?", (int(course_id),))
    row = _fetch_one_dict(cur)
    meta = get_course_metadata(conn, int(course_id))
    flags: dict[str, Any] = {
        "course_id": int(course_id),
        "strategic_flag": False,
        "accreditation_flag": False,
        "protected_flag": False,
        "required_course_flag": _is_required_course_type(meta.get("course_type")),
        "service_course_flag": _is_service_course_type(meta.get("course_type")),
        "new_course_flag": False,
        "revised_course_flag": False,
        "revision_year": None,
        "first_offered_year": None,
        "protected_until_year": None,
        "protection_reason": None,
        "instructor_changed": False,
        "content_updated": False,
        "updated_by": None,
        "notes": None,
    }
    if row:
        flags.update(row)
    for field in GOVERNANCE_FIELDS:
        flags[field] = _bool(flags.get(field))
    return flags


def upsert_governance_flags(conn: sqlite3.Connection, course_id: int, **fields: Any) -> dict[str, Any]:
    ensure_pool_state_governance_schema(conn, commit=False)
    allowed = {
        "strategic_flag",
        "accreditation_flag",
        "protected_flag",
        "required_course_flag",
        "service_course_flag",
        "new_course_flag",
        "revised_course_flag",
        "revision_year",
        "first_offered_year",
        "protected_until_year",
        "protection_reason",
        "instructor_changed",
        "content_updated",
        "updated_by",
        "notes",
    }
    payload = {k: v for k, v in fields.items() if k in allowed}
    for key in GOVERNANCE_FIELDS:
        if key in payload:
            payload[key] = 1 if _bool(payload[key]) else 0
    payload["updated_at"] = _now()
    cur = conn.cursor()
    cur.execute("SELECT id FROM course_governance_flags WHERE course_id = ?", (int(course_id),))
    row = cur.fetchone()
    if row:
        assignments = ", ".join(f"{key} = ?" for key in payload)
        cur.execute(
            f"UPDATE course_governance_flags SET {assignments} WHERE course_id = ?",
            tuple(payload.values()) + (int(course_id),),
        )
    else:
        cols = ["course_id"] + list(payload.keys())
        placeholders = ", ".join("?" for _ in cols)
        cur.execute(
            f"INSERT INTO course_governance_flags ({', '.join(cols)}) VALUES ({placeholders})",
            tuple([int(course_id)] + list(payload.values())),
        )
    return get_governance_flags(conn, int(course_id))


def get_active_override(
    conn: sqlite3.Connection,
    course_id: int,
    year: int,
    semester: str | None = None,
) -> dict[str, Any] | None:
    ensure_pool_state_governance_schema(conn, commit=False)
    sem = normalize_semester(semester)
    now = _now()
    where = ["course_id = ?", "year = ?", "is_active = 1", "(expires_at IS NULL OR expires_at >= ?)"]
    params: list[Any] = [int(course_id), int(year), now]
    if sem:
        where.append("(semester IS NULL OR LOWER(SUBSTR(TRIM(semester), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)))")
        params.append(sem)
    else:
        where.append("semester IS NULL")
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM course_state_overrides WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT 1",
        tuple(params),
    )
    row = _fetch_one_dict(cur)
    if not row:
        return None
    row["is_active"] = _bool(row.get("is_active"))
    return row


def create_course_state_override(
    conn: sqlite3.Connection,
    course_id: int,
    year: int,
    overridden_final_status: int,
    reason: str,
    semester: str | None = None,
    recommended_status: int | None = None,
    requested_by: str | None = None,
    approved_by: str | None = None,
    expires_at: str | None = None,
    transition_id: int | None = None,
) -> dict[str, Any]:
    if not str(reason or "").strip():
        raise ValueError("Override gerekçesi zorunludur.")
    ensure_pool_state_governance_schema(conn, commit=False)
    now = _now()
    conn.execute(
        """
        INSERT INTO course_state_overrides (
            course_id, year, semester, transition_id, recommended_status,
            overridden_final_status, reason, requested_by, approved_by,
            approved_at, created_at, expires_at, is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            int(course_id),
            int(year),
            normalize_semester(semester),
            transition_id,
            recommended_status,
            int(overridden_final_status),
            str(reason).strip(),
            requested_by,
            approved_by,
            now if approved_by else None,
            now,
            expires_at,
        ),
    )
    return get_active_override(conn, int(course_id), int(year), semester) or {}


def list_overrides(
    conn: sqlite3.Connection,
    year: int | None = None,
    course_id: int | None = None,
    active_only: bool = False,
) -> list[dict[str, Any]]:
    ensure_pool_state_governance_schema(conn, commit=False)
    where = ["1=1"]
    params: list[Any] = []
    if year is not None:
        where.append("o.year = ?")
        params.append(int(year))
    if course_id is not None:
        where.append("o.course_id = ?")
        params.append(int(course_id))
    if active_only:
        where.append("o.is_active = 1")
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT o.*, d.kod AS course_code, d.ad AS course_name
        FROM course_state_overrides o
        LEFT JOIN ders d ON d.ders_id = o.course_id
        WHERE {' AND '.join(where)}
        ORDER BY o.id DESC
        """,
        tuple(params),
    )
    rows = _fetch_all_dicts(cur)
    for row in rows:
        row["is_active"] = _bool(row.get("is_active"))
    return rows


def _is_protected(flags: dict[str, Any], policy: dict[str, Any], year: int) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if flags.get("protected_flag"):
        reasons.append("ders korumalı olarak işaretlenmiş")
    if flags.get("strategic_flag") and _bool(policy.get("protect_strategic_courses", True)):
        reasons.append("ders stratejik olarak işaretlenmiş")
    if flags.get("accreditation_flag") and _bool(policy.get("protect_accreditation_courses", True)):
        reasons.append("ders akreditasyon kapsamında")
    if flags.get("required_course_flag") and _bool(policy.get("protect_required_courses", True)):
        reasons.append("ders zorunlu/çekirdek ders olarak işaretlenmiş")
    if flags.get("service_course_flag"):
        reasons.append("ders servis dersi olarak işaretlenmiş")
    protected_until = _int(flags.get("protected_until_year"), 0)
    if protected_until and int(year) <= protected_until:
        reasons.append(f"ders {protected_until} yılına kadar korumalı")
    return bool(reasons), reasons


def _in_grace_period(flags: dict[str, Any], policy: dict[str, Any], year: int) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    first_year = _int(flags.get("first_offered_year"), 0)
    new_grace = _int(policy.get("new_course_grace_period_years"), 2)
    if flags.get("new_course_flag"):
        reasons.append("ders yeni ders olarak işaretlenmiş")
    if first_year and int(year) - first_year < new_grace:
        reasons.append(f"ders yeni ders grace period içinde ({first_year}-{year})")

    revision_year = _int(flags.get("revision_year"), 0)
    revised_grace = _int(policy.get("revised_course_grace_period_years"), 1)
    if flags.get("revised_course_flag") and (not revision_year or int(year) - revision_year <= revised_grace):
        reasons.append("ders yakın dönemde revize edilmiş")
    if flags.get("instructor_changed"):
        reasons.append("öğretim elemanı değişmiş")
    if flags.get("content_updated"):
        reasons.append("ders içeriği güncellenmiş")
    return bool(reasons), reasons


def evaluate_course_state_transition(conn: sqlite3.Connection, context: dict[str, Any]) -> dict[str, Any]:
    """Tek ders icin cok faktorlü havuz state transition sonucu üretir."""
    ensure_pool_state_governance_schema(conn, commit=False)
    course_id = int(context["course_id"])
    year = int(context["year"])
    semester = normalize_semester(context.get("semester"))
    faculty_id = context.get("faculty_id")
    department_id = context.get("department_id")
    policy = context.get("policy") or resolve_policy(
        conn,
        year=year,
        faculty_id=int(faculty_id) if faculty_id is not None else None,
        department_id=int(department_id) if department_id is not None else None,
        semester=semester,
    )
    flags = dict(context.get("governance_flags") or get_governance_flags(conn, course_id))
    meta = get_course_metadata(conn, course_id)
    if _is_required_course_type(context.get("course_type") or meta.get("course_type")):
        flags["required_course_flag"] = True
    if _is_service_course_type(context.get("course_type") or meta.get("course_type")):
        flags["service_course_flag"] = True

    old_status = _int(context.get("current_status"), STATU_HAVUZDA)
    counter_before = _int(context.get("counter_before", context.get("years_in_current_status")), _int(context.get("previous_counter"), 0))
    selected = _bool(context.get("in_mufredat_this_year", context.get("is_selected", False)))
    score = _score100(context.get("topsis_score", context.get("score")))
    score_for_rules = score if score is not None else 0.0
    trend_label = str(context.get("trend_label") or "insufficient_data")
    trend_score = _float(context.get("trend_score"))
    data_confidence = _confidence01(context.get("data_confidence_score"))
    data_confidence_level = context.get("data_confidence_level")
    if data_confidence_level is None:
        if data_confidence is None:
            data_confidence_level = "low"
        elif data_confidence >= 0.75:
            data_confidence_level = "high"
        elif data_confidence >= 0.50:
            data_confidence_level = "medium"
        else:
            data_confidence_level = "low"

    years_in_pool = _int(context.get("years_in_pool"), counter_before if old_status == STATU_HAVUZDA else 0)
    years_in_rest = _int(context.get("years_in_rest"), counter_before if old_status == STATU_DINLENMEDE else 0)
    warnings: list[str] = []
    reasons: list[str] = []
    rule = "no_change"
    recommended = old_status
    final = old_status
    lifecycle = _lifecycle_for_status(old_status)

    protected, protection_reasons = _is_protected(flags, policy, year)
    grace, grace_reasons = _in_grace_period(flags, policy, year)
    cancel_confidence_min = _float(policy.get("minimum_data_confidence_for_cancel"), 0.75) or 0.75
    rest_confidence_min = _float(policy.get("minimum_data_confidence_for_rest"), 0.60) or 0.60
    low_confidence_for_cancel = data_confidence is None or data_confidence < cancel_confidence_min
    low_confidence_for_rest = data_confidence is None or data_confidence < rest_confidence_min

    if data_confidence is None:
        warnings.append("Veri güveni hesaplanamadı; sert kararlar temkinli değerlendirildi.")

    if protected:
        recommended = STATU_MUFREDATTA if selected or old_status == STATU_MUFREDATTA else max(old_status, STATU_HAVUZDA)
        final = recommended
        lifecycle = "protected"
        rule = "governance_protection"
        reasons.append("Koruma nedeniyle otomatik havuz/iptal kararı uygulanmadı: " + ", ".join(protection_reasons) + ".")
    elif old_status == STATU_IPTAL:
        if _bool(policy.get("allow_reactivation_from_cancelled", False)) and score_for_rules >= float(policy.get("reactivation_threshold", 75)):
            recommended = STATU_HAVUZDA
            final = STATU_IPTAL
            lifecycle = "reactivation_candidate"
            rule = "cancelled_reactivation_candidate"
            reasons.append("Kalıcı iptal edilmiş ders yeniden açılma adayıdır; otomatik dönüş uygulanmadı.")
        else:
            recommended = STATU_IPTAL
            final = STATU_IPTAL
            lifecycle = "permanently_cancelled"
            rule = "cancelled_locked"
            reasons.append("Kalıcı iptal edilmiş ders otomatik olarak yeniden açılmaz.")
    elif selected:
        recommended = STATU_MUFREDATTA
        final = STATU_MUFREDATTA
        lifecycle = "curriculum"
        rule = "selected_for_curriculum"
        reasons.append("Ders yeni müfredat seçimine girdiği için müfredatta kalır.")
    elif old_status in (STATU_HAVUZDA, STATU_DINLENMEDE) and score_for_rules >= float(policy.get("reactivation_threshold", 75)):
        if old_status == STATU_DINLENMEDE and not _bool(policy.get("allow_reactivation_from_rest", True)):
            recommended = STATU_HAVUZDA
            final = STATU_HAVUZDA
            lifecycle = "pool"
            rule = "rest_reactivation_not_allowed"
            reasons.append("Skor yüksek olsa da policy dinlenmeden otomatik dönüşe izin vermiyor.")
        elif trend_label in {"rising", "stable", "new_course"}:
            recommended = STATU_MUFREDATTA
            final = STATU_MUFREDATTA
            lifecycle = "reactivation_candidate"
            rule = "high_score_reactivation"
            reasons.append("Skor yüksek ve trend olumlu olduğu için yeniden müfredata dönüş adayıdır.")
        else:
            recommended = STATU_HAVUZDA
            final = STATU_HAVUZDA
            lifecycle = "pool"
            rule = "high_score_but_trend_uncertain"
            reasons.append("Skor yüksek ancak trend yeterince güçlü olmadığı için havuzda izleme önerildi.")
    elif old_status == STATU_DINLENMEDE:
        if (
            score_for_rules <= float(policy.get("cancel_candidate_threshold", 35))
            and years_in_rest >= int(policy.get("cancel_after_years_in_rest", 2))
        ):
            recommended = STATU_IPTAL
            final = STATU_DINLENMEDE
            lifecycle = "cancel_candidate"
            rule = "low_score_long_rest_cancel_candidate"
            reasons.append("Ders uzun süredir dinlenmede ve skoru çok düşük olduğu için iptal adayıdır.")
        else:
            recommended = STATU_HAVUZDA
            final = STATU_HAVUZDA
            lifecycle = "pool"
            rule = "rest_to_pool_review"
            reasons.append("Dinlenme süresi sonrası ders yeniden havuzda izlemeye alınır.")
    elif old_status == STATU_HAVUZDA:
        if (
            score_for_rules <= float(policy.get("cancel_candidate_threshold", 35))
            and years_in_pool >= int(policy.get("rest_after_years_in_pool", 2)) + int(policy.get("cancel_after_years_in_rest", 2))
        ):
            recommended = STATU_IPTAL
            final = STATU_HAVUZDA
            lifecycle = "cancel_candidate"
            rule = "low_score_long_pool_cancel_candidate"
            reasons.append("Ders uzun süredir havuzda ve skoru çok düşük olduğu için iptal adayıdır.")
        elif (
            score_for_rules <= float(policy.get("rest_threshold", 45))
            and years_in_pool >= int(policy.get("rest_after_years_in_pool", 2))
        ):
            recommended = STATU_DINLENMEDE
            final = STATU_DINLENMEDE
            lifecycle = "resting"
            rule = "low_score_pool_to_rest"
            reasons.append("Skor düşük ve havuzda bekleme süresi dolduğu için dinlenmeye alma önerildi.")
        else:
            recommended = STATU_HAVUZDA
            final = STATU_HAVUZDA
            lifecycle = "pool"
            rule = "pool_monitor"
            reasons.append("Ders havuzda izlenmeye devam eder.")
    elif old_status == STATU_MUFREDATTA:
        if score_for_rules <= float(policy.get("cancel_candidate_threshold", 35)) and trend_label == "falling":
            recommended = STATU_IPTAL if counter_before + 1 >= int(policy.get("cancel_after_years_in_rest", 2)) else STATU_DINLENMEDE
            final = recommended
            lifecycle = "cancel_candidate" if recommended == STATU_IPTAL else "resting"
            rule = "curriculum_low_score_falling"
            reasons.append("Skor çok düşük ve trend düşüşte olduğu için aşağı yönlü geçiş önerildi.")
        elif score_for_rules <= float(policy.get("rest_threshold", 45)):
            recommended = STATU_DINLENMEDE
            final = STATU_DINLENMEDE
            lifecycle = "resting"
            rule = "curriculum_low_score_rest"
            reasons.append("Skor dinlenme eşiğinin altında kaldığı için ders dinlenmeye alınır.")
        elif score_for_rules < float(policy.get("pool_entry_threshold", 60)):
            recommended = STATU_HAVUZDA
            final = STATU_HAVUZDA
            lifecycle = "pool"
            rule = "curriculum_to_pool"
            reasons.append("Skor havuz eşiğinin altında kaldığı için havuza alma önerildi.")
        else:
            recommended = STATU_HAVUZDA
            final = STATU_HAVUZDA
            lifecycle = "pool"
            rule = "not_selected_but_viable_pool"
            reasons.append("Ders bu yıl seçilmedi; performansı izlenmek üzere havuzda kalır.")

    legacy_recommended = context.get("legacy_recommended_status")
    if not protected and not selected and legacy_recommended is not None:
        legacy_recommended = _int(legacy_recommended, recommended)
        if old_status == STATU_MUFREDATTA and legacy_recommended == STATU_DINLENMEDE and recommended == STATU_HAVUZDA:
            recommended = STATU_DINLENMEDE
            final = STATU_DINLENMEDE
            lifecycle = "resting"
            rule = "legacy_drop_counter_rest"
            reasons.append("Mevcut state machine düşüş sayacı ilk düşüşü dinlenme olarak işaretledi.")
        elif old_status == STATU_MUFREDATTA and legacy_recommended == STATU_IPTAL and recommended != STATU_IPTAL:
            recommended = STATU_IPTAL
            final = STATU_IPTAL
            lifecycle = "cancel_candidate"
            rule = "legacy_drop_counter_cancel_candidate"
            reasons.append("Mevcut state machine düşüş sayacı kalıcı iptal adaylığı üretti.")

    if grace and recommended == STATU_IPTAL:
        recommended = STATU_DINLENMEDE if old_status == STATU_MUFREDATTA else STATU_HAVUZDA
        final = recommended
        lifecycle = _lifecycle_for_status(final)
        rule = "grace_period_blocks_cancel"
        reasons.append("Grace period nedeniyle kalıcı iptal önerisi yumuşatıldı: " + ", ".join(grace_reasons) + ".")

    if recommended == STATU_IPTAL and _bool(policy.get("low_confidence_blocks_cancel", True)) and low_confidence_for_cancel:
        recommended = STATU_DINLENMEDE if old_status in (STATU_MUFREDATTA, STATU_DINLENMEDE) else STATU_HAVUZDA
        final = recommended
        lifecycle = "under_review"
        rule = "low_confidence_blocks_cancel"
        warnings.append("Veri güveni kalıcı iptal için minimum eşiğin altında.")
        reasons.append("Skor düşük olsa da veri güveni düşük olduğu için kalıcı iptal uygulanmadı.")

    if recommended == STATU_DINLENMEDE and _bool(policy.get("low_confidence_blocks_rest", True)) and low_confidence_for_rest:
        recommended = STATU_HAVUZDA
        final = STATU_HAVUZDA
        lifecycle = "under_review"
        rule = "low_confidence_blocks_rest"
        warnings.append("Veri güveni dinlenme kararı için minimum eşiğin altında.")
        reasons.append("Düşük veri güveni nedeniyle dinlenme yerine havuzda izleme önerildi.")

    approval_required = False
    approval_status = "not_required"
    if old_status != STATU_IPTAL and recommended == STATU_IPTAL and _bool(policy.get("require_approval_for_cancel", True)):
        approval_required = True
        approval_status = "pending"
        final = STATU_DINLENMEDE if old_status in (STATU_MUFREDATTA, STATU_DINLENMEDE) else STATU_HAVUZDA
        lifecycle = "cancel_candidate"
        reasons.append("Kalıcı iptal akademik onay gerektirdiği için final statü otomatik -2 yapılmadı.")

    if (
        old_status in (STATU_HAVUZDA, STATU_DINLENMEDE)
        and recommended == STATU_MUFREDATTA
        and (
            _bool(policy.get("require_approval_for_reactivation", True))
            or _bool(policy.get("reactivation_requires_manual_approval", True))
        )
    ):
        approval_required = True
        approval_status = "pending"
        final = STATU_HAVUZDA
        lifecycle = "reactivation_candidate"
        reasons.append("Yeniden müfredata dönüş akademik onay gerektirdiği için final statü havuzda tutuldu.")

    manual_override = context.get("manual_override") or get_active_override(conn, course_id, year, semester)
    override_applied = False
    override_id = None
    if manual_override:
        override_status = _int(manual_override.get("overridden_final_status"), final)
        final = override_status
        lifecycle = _lifecycle_for_status(final)
        approval_required = False
        approval_status = "approved"
        override_applied = True
        override_id = _int(manual_override.get("id"), 0) or None
        rule = f"{rule}+manual_override"
        reasons.append("Kurul/manuel override uygulandı: " + str(manual_override.get("reason") or "").strip())

    if final == STATU_MUFREDATTA:
        counter_after = counter_before
    elif old_status == STATU_MUFREDATTA and final in (STATU_HAVUZDA, STATU_DINLENMEDE, STATU_IPTAL):
        counter_after = counter_before + 1
    else:
        counter_after = counter_before
    if context.get("legacy_counter_after") is not None and not override_applied:
        legacy_counter_after = _int(context.get("legacy_counter_after"), counter_after)
        if recommended in (STATU_DINLENMEDE, STATU_IPTAL) or final in (STATU_DINLENMEDE, STATU_IPTAL):
            counter_after = max(counter_after, legacy_counter_after)

    explanation = " ".join(reason for reason in reasons if reason).strip()
    if not explanation:
        explanation = f"Ders {_status_label(final)} durumunda kalır."
    if score is not None:
        explanation += f" TOPSIS skoru {score:.1f} olarak değerlendirildi."
    if trend_label:
        explanation += f" Trend etiketi: {trend_label}."
    if data_confidence is not None:
        explanation += f" Veri güveni: {data_confidence:.2f}."

    return {
        "course_id": course_id,
        "year": year,
        "semester": semester,
        "faculty_id": faculty_id,
        "department_id": department_id,
        "old_status": old_status,
        "recommended_status": int(recommended),
        "final_status": int(final),
        "lifecycle_label": lifecycle,
        "approval_required": approval_required,
        "approval_status": approval_status,
        "trigger": context.get("trigger") or "algorithm",
        "rule_applied": rule,
        "counter_before": counter_before,
        "counter_after": counter_after,
        "score_used": score,
        "topsis_score": score,
        "trend_used": trend_label,
        "trend_score": trend_score,
        "trend_label": trend_label,
        "data_confidence_used": data_confidence,
        "data_confidence_score": data_confidence,
        "data_confidence_level": data_confidence_level,
        "policy_id": policy.get("id"),
        "governance_flags": flags,
        "governance_flags_snapshot": flags,
        "override_applied": override_applied,
        "override_id": override_id,
        "explanation": explanation,
        "warnings": warnings,
        "metadata": {
            "policy_name": policy.get("name"),
            "protected": protected,
            "protection_reasons": protection_reasons,
            "grace_period": grace,
            "grace_reasons": grace_reasons,
            "selected": selected,
            "course_type": context.get("course_type") or meta.get("course_type"),
        },
    }


def _approval_type_for_result(result: dict[str, Any]) -> str:
    if int(result.get("recommended_status", 0)) == STATU_IPTAL:
        return "cancel"
    if int(result.get("recommended_status", 0)) == STATU_MUFREDATTA:
        return "reactivate"
    return "override"


def ensure_pending_approval(conn: sqlite3.Connection, result: dict[str, Any], transition_id: int | None = None) -> dict[str, Any]:
    ensure_pool_state_governance_schema(conn, commit=False)
    course_id = int(result["course_id"])
    year = int(result["year"])
    semester = normalize_semester(result.get("semester"))
    requested_status = int(result.get("recommended_status") or 0)
    approval_type = _approval_type_for_result(result)
    cur = conn.cursor()
    where = [
        "course_id = ?",
        "year = ?",
        "requested_status = ?",
        "approval_type = ?",
        "approval_status = 'pending'",
    ]
    params: list[Any] = [course_id, year, requested_status, approval_type]
    if semester:
        where.append("LOWER(SUBSTR(TRIM(COALESCE(semester, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))")
        params.append(semester)
    else:
        where.append("semester IS NULL")
    cur.execute(
        f"SELECT * FROM course_state_approvals WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT 1",
        tuple(params),
    )
    row = _fetch_one_dict(cur)
    now = _now()
    if row:
        cur.execute(
            "UPDATE course_state_approvals SET transition_id = COALESCE(transition_id, ?), updated_at = ? WHERE id = ?",
            (transition_id, now, int(row["id"])),
        )
        row["transition_id"] = row.get("transition_id") or transition_id
        return row
    cur.execute(
        """
        INSERT INTO course_state_approvals (
            course_id, year, semester, transition_id, requested_status,
            current_status, approval_type, approval_status, requested_at,
            approval_reason, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
        """,
        (
            course_id,
            year,
            semester,
            transition_id,
            requested_status,
            int(result.get("old_status", STATU_HAVUZDA)),
            approval_type,
            now,
            result.get("explanation"),
            now,
            now,
        ),
    )
    approval_id = int(cur.lastrowid or 0)
    cur.execute("SELECT * FROM course_state_approvals WHERE id = ?", (approval_id,))
    return _fetch_one_dict(cur) or {"id": approval_id}


def save_state_transition(
    conn: sqlite3.Connection,
    result: dict[str, Any],
    *,
    trigger: str | None = None,
    created_by: str | None = None,
    decision_run_id: int | None = None,
) -> int:
    ensure_pool_state_governance_schema(conn, commit=False)
    now = _now()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO course_state_transitions (
            decision_run_id, course_id, year, semester, old_status,
            recommended_status, final_status, lifecycle_label, trigger,
            rule_applied, topsis_score, trend_score, trend_label,
            data_confidence_score, policy_id, governance_flags_snapshot_json,
            counter_before, counter_after, approval_required, approval_status,
            override_applied, override_id, explanation, warnings_json,
            metadata_json, created_by, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            decision_run_id,
            int(result["course_id"]),
            int(result["year"]),
            normalize_semester(result.get("semester")),
            int(result.get("old_status", STATU_HAVUZDA)),
            int(result.get("recommended_status", STATU_HAVUZDA)),
            int(result.get("final_status", STATU_HAVUZDA)),
            result.get("lifecycle_label"),
            trigger or result.get("trigger") or "algorithm",
            result.get("rule_applied"),
            result.get("topsis_score"),
            result.get("trend_score"),
            result.get("trend_label"),
            result.get("data_confidence_score"),
            result.get("policy_id"),
            _json(result.get("governance_flags_snapshot") or result.get("governance_flags") or {}),
            result.get("counter_before"),
            result.get("counter_after"),
            1 if result.get("approval_required") else 0,
            result.get("approval_status"),
            1 if result.get("override_applied") else 0,
            result.get("override_id"),
            result.get("explanation"),
            _json(result.get("warnings") or []),
            _json(result.get("metadata") or {}),
            created_by,
            now,
        ),
    )
    transition_id = int(cur.lastrowid or 0)
    result["transition_id"] = transition_id
    if result.get("approval_required"):
        approval = ensure_pending_approval(conn, result, transition_id=transition_id)
        result["approval_id"] = approval.get("id")
        cur.execute(
            "UPDATE course_state_transitions SET approval_status = 'pending' WHERE id = ?",
            (transition_id,),
        )
    return transition_id


def update_havuz_lifecycle(conn: sqlite3.Connection, result: dict[str, Any], transition_id: int | None = None) -> int:
    ensure_pool_state_governance_schema(conn, commit=False)
    semester = normalize_semester(result.get("semester"))
    where = ["CAST(ders_id AS INTEGER) = ?", "yil = ?"]
    params: list[Any] = [int(result["course_id"]), int(result["year"])]
    if result.get("faculty_id") is not None:
        where.append("fakulte_id = ?")
        params.append(int(result["faculty_id"]))
    if semester:
        where.append("LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))")
        params.append(semester)
    cur = conn.cursor()
    cur.execute(
        f"""
        UPDATE havuz
        SET statu = ?, recommended_status = ?, final_status = ?, lifecycle_label = ?,
            approval_required = ?, approval_status = ?, transition_id = ?,
            explanation = ?, policy_id = ?
        WHERE {' AND '.join(where)}
        """,
        (
            int(result.get("final_status", STATU_HAVUZDA)),
            int(result.get("recommended_status", STATU_HAVUZDA)),
            int(result.get("final_status", STATU_HAVUZDA)),
            result.get("lifecycle_label"),
            1 if result.get("approval_required") else 0,
            result.get("approval_status"),
            transition_id or result.get("transition_id"),
            result.get("explanation"),
            result.get("policy_id"),
            *params,
        ),
    )
    return int(cur.rowcount or 0)


def approve_state_approval(
    conn: sqlite3.Connection,
    approval_id: int,
    reviewed_by: str | None = None,
    review_note: str | None = None,
) -> dict[str, Any]:
    ensure_pool_state_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM course_state_approvals WHERE id = ?", (int(approval_id),))
    approval = _fetch_one_dict(cur)
    if not approval:
        raise ValueError("Onay kaydı bulunamadı.")
    now = _now()
    requested_status = int(approval["requested_status"])
    cur.execute(
        """
        UPDATE course_state_approvals
        SET approval_status = 'approved', reviewed_by = ?, reviewed_at = ?,
            review_note = ?, updated_at = ?
        WHERE id = ?
        """,
        (reviewed_by, now, review_note, now, int(approval_id)),
    )
    transition_id = approval.get("transition_id")
    if transition_id:
        cur.execute(
            """
            UPDATE course_state_transitions
            SET final_status = ?, approval_status = 'approved',
                lifecycle_label = ?, metadata_json = COALESCE(metadata_json, '{}')
            WHERE id = ?
            """,
            (requested_status, _lifecycle_for_status(requested_status), int(transition_id)),
        )
        cur.execute("SELECT * FROM course_state_transitions WHERE id = ?", (int(transition_id),))
        transition = _fetch_one_dict(cur) or {}
        if transition:
            transition["final_status"] = requested_status
            transition["approval_status"] = "approved"
            transition["lifecycle_label"] = _lifecycle_for_status(requested_status)
            update_havuz_lifecycle(conn, transition, transition_id=int(transition_id))
    cur.execute("SELECT * FROM course_state_approvals WHERE id = ?", (int(approval_id),))
    return _fetch_one_dict(cur) or {}


def reject_state_approval(
    conn: sqlite3.Connection,
    approval_id: int,
    reviewed_by: str | None = None,
    review_note: str | None = None,
) -> dict[str, Any]:
    ensure_pool_state_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM course_state_approvals WHERE id = ?", (int(approval_id),))
    approval = _fetch_one_dict(cur)
    if not approval:
        raise ValueError("Onay kaydı bulunamadı.")
    now = _now()
    cur.execute(
        """
        UPDATE course_state_approvals
        SET approval_status = 'rejected', reviewed_by = ?, reviewed_at = ?,
            review_note = ?, updated_at = ?
        WHERE id = ?
        """,
        (reviewed_by, now, review_note, now, int(approval_id)),
    )
    if approval.get("transition_id"):
        cur.execute(
            "UPDATE course_state_transitions SET approval_status = 'rejected' WHERE id = ?",
            (int(approval["transition_id"]),),
        )
    cur.execute("SELECT * FROM course_state_approvals WHERE id = ?", (int(approval_id),))
    return _fetch_one_dict(cur) or {}


def list_state_transitions(
    conn: sqlite3.Connection,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    course_id: int | None = None,
    status: int | None = None,
    approval_status: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    ensure_pool_state_governance_schema(conn, commit=False)
    where = ["1=1"]
    params: list[Any] = []
    if year is not None:
        where.append("t.year = ?")
        params.append(int(year))
    if course_id is not None:
        where.append("t.course_id = ?")
        params.append(int(course_id))
    if status is not None:
        where.append("t.final_status = ?")
        params.append(int(status))
    if approval_status:
        where.append("t.approval_status = ?")
        params.append(str(approval_status))
    if faculty_id is not None:
        where.append("(d.fakulte_id = ? OR h.fakulte_id = ?)")
        params.extend([int(faculty_id), int(faculty_id)])
    if department_id is not None:
        where.append("(d.bolum_id = ? OR h.bolum_id = ?)")
        params.extend([int(department_id), int(department_id)])
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT t.*, d.kod AS course_code, d.ad AS course_name,
               COALESCE(d.fakulte_id, h.fakulte_id) AS faculty_id,
               COALESCE(d.bolum_id, h.bolum_id) AS department_id
        FROM course_state_transitions t
        LEFT JOIN ders d ON d.ders_id = t.course_id
        LEFT JOIN havuz h ON CAST(h.ders_id AS INTEGER) = t.course_id
             AND h.yil = t.year
             AND (t.semester IS NULL OR LOWER(SUBSTR(TRIM(COALESCE(h.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(t.semester), 1, 1)))
        WHERE {' AND '.join(where)}
        ORDER BY t.id DESC
        LIMIT ?
        """,
        tuple(params + [int(limit)]),
    )
    rows = _fetch_all_dicts(cur)
    for row in rows:
        row["approval_required"] = _bool(row.get("approval_required"))
        row["override_applied"] = _bool(row.get("override_applied"))
        row["warnings"] = _load_json(row.get("warnings_json"), [])
        row["metadata"] = _load_json(row.get("metadata_json"), {})
    return rows


def get_course_state_history(conn: sqlite3.Connection, course_id: int) -> list[dict[str, Any]]:
    return list_state_transitions(conn, course_id=int(course_id), limit=1000)


def list_pending_approvals(
    conn: sqlite3.Connection,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    status: str | None = "pending",
) -> list[dict[str, Any]]:
    ensure_pool_state_governance_schema(conn, commit=False)
    where = ["1=1"]
    params: list[Any] = []
    if status:
        where.append("a.approval_status = ?")
        params.append(status)
    if year is not None:
        where.append("a.year = ?")
        params.append(int(year))
    if faculty_id is not None:
        where.append("d.fakulte_id = ?")
        params.append(int(faculty_id))
    if department_id is not None:
        where.append("d.bolum_id = ?")
        params.append(int(department_id))
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT a.*, d.kod AS course_code, d.ad AS course_name, d.fakulte_id, d.bolum_id
        FROM course_state_approvals a
        LEFT JOIN ders d ON d.ders_id = a.course_id
        WHERE {' AND '.join(where)}
        ORDER BY a.id DESC
        """,
        tuple(params),
    )
    return _fetch_all_dicts(cur)


def get_pool_lifecycle_summary(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any]:
    ensure_pool_state_governance_schema(conn, commit=False)
    sem = normalize_semester(semester)
    where = ["h.yil = ?"]
    params: list[Any] = [int(year)]
    if faculty_id is not None:
        where.append("h.fakulte_id = ?")
        params.append(int(faculty_id))
    if department_id is not None:
        where.append("COALESCE(d.bolum_id, h.bolum_id) = ?")
        params.append(int(department_id))
    if sem:
        where.append("LOWER(SUBSTR(TRIM(COALESCE(h.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))")
        params.append(sem)
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT
            SUM(CASE WHEN h.statu = 1 THEN 1 ELSE 0 END) AS curriculum_count,
            SUM(CASE WHEN h.statu = 0 THEN 1 ELSE 0 END) AS pool_count,
            SUM(CASE WHEN h.statu = -1 THEN 1 ELSE 0 END) AS resting_count,
            SUM(CASE WHEN h.statu = -2 THEN 1 ELSE 0 END) AS cancelled_count,
            SUM(CASE WHEN h.lifecycle_label = 'cancel_candidate' THEN 1 ELSE 0 END) AS cancel_candidate_count,
            SUM(CASE WHEN h.lifecycle_label = 'reactivation_candidate' THEN 1 ELSE 0 END) AS reactivation_candidate_count,
            SUM(CASE WHEN h.lifecycle_label = 'protected' THEN 1 ELSE 0 END) AS protected_count,
            COUNT(*) AS total_count
        FROM havuz h
        LEFT JOIN ders d ON d.ders_id = CAST(h.ders_id AS INTEGER)
        WHERE {' AND '.join(where)}
        """,
        tuple(params),
    )
    summary = _fetch_one_dict(cur) or {}
    cur.execute(
        """
        SELECT COUNT(*)
        FROM course_state_approvals a
        LEFT JOIN ders d ON d.ders_id = a.course_id
        WHERE a.approval_status = 'pending'
          AND a.year = ?
          AND (? IS NULL OR d.fakulte_id = ?)
          AND (? IS NULL OR d.bolum_id = ?)
        """,
        (int(year), faculty_id, faculty_id, department_id, department_id),
    )
    row = cur.fetchone()
    summary["pending_approval_count"] = int(row[0] or 0) if row else 0
    for key, value in list(summary.items()):
        if value is None:
            summary[key] = 0
    return summary


def get_reactivation_candidates(
    conn: sqlite3.Connection,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> list[dict[str, Any]]:
    rows = list_state_transitions(conn, year=year, faculty_id=faculty_id, department_id=department_id, limit=1000)
    return [row for row in rows if row.get("lifecycle_label") == "reactivation_candidate"]


def get_protected_courses(
    conn: sqlite3.Connection,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> list[dict[str, Any]]:
    ensure_pool_state_governance_schema(conn, commit=False)
    where = [
        "(g.strategic_flag = 1 OR g.accreditation_flag = 1 OR g.protected_flag = 1 OR g.required_course_flag = 1 OR g.service_course_flag = 1)"
    ]
    params: list[Any] = []
    if faculty_id is not None:
        where.append("d.fakulte_id = ?")
        params.append(int(faculty_id))
    if department_id is not None:
        where.append("d.bolum_id = ?")
        params.append(int(department_id))
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT g.*, d.kod AS course_code, d.ad AS course_name, d.fakulte_id, d.bolum_id
        FROM course_governance_flags g
        JOIN ders d ON d.ders_id = g.course_id
        WHERE {' AND '.join(where)}
        ORDER BY d.ad
        """,
        tuple(params),
    )
    rows = _fetch_all_dicts(cur)
    for row in rows:
        for field in GOVERNANCE_FIELDS:
            if field in row:
                row[field] = _bool(row[field])
    return rows


def evaluate_scope_transitions(
    conn: sqlite3.Connection,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
    save: bool = False,
) -> list[dict[str, Any]]:
    """Mevcut havuz satırları üzerinden kapsam bazlı güvenli değerlendirme yapar."""
    ensure_pool_state_governance_schema(conn, commit=False)
    sem = normalize_semester(semester)
    where = ["h.yil = ?"]
    params: list[Any] = [int(year)]
    if faculty_id is not None:
        where.append("h.fakulte_id = ?")
        params.append(int(faculty_id))
    if department_id is not None:
        where.append("COALESCE(d.bolum_id, h.bolum_id) = ?")
        params.append(int(department_id))
    if sem:
        where.append("LOWER(SUBSTR(TRIM(COALESCE(h.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))")
        params.append(sem)
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT h.*, d.DersTipi, d.tip, d.bolum_id AS ders_bolum_id, d.fakulte_id AS ders_fakulte_id
        FROM havuz h
        LEFT JOIN ders d ON d.ders_id = CAST(h.ders_id AS INTEGER)
        WHERE {' AND '.join(where)}
        ORDER BY h.id
        """,
        tuple(params),
    )
    rows = _fetch_all_dicts(cur)
    out: list[dict[str, Any]] = []
    for row in rows:
        result = evaluate_course_state_transition(
            conn,
            {
                "course_id": int(row["ders_id"]),
                "year": int(row["yil"]),
                "semester": row.get("donem"),
                "faculty_id": row.get("fakulte_id") or row.get("ders_fakulte_id"),
                "department_id": row.get("bolum_id") or row.get("ders_bolum_id"),
                "current_status": row.get("statu"),
                "counter_before": row.get("sayac"),
                "topsis_score": row.get("skor"),
                "course_type": row.get("DersTipi") or row.get("tip"),
            },
        )
        if save:
            transition_id = save_state_transition(conn, result)
            update_havuz_lifecycle(conn, result, transition_id)
        out.append(result)
    return out
