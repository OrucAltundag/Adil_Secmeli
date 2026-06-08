# -*- coding: utf-8 -*-
"""Kriter tamlık override/istisna servisi.

Override, eksik/hatalı veriyle algoritmanın çalıştırılmasına yetkili gerekçeyle
izin veren kontrollü bir bypass mekanizmasıdır. Bu yüzden servis sadece CRUD
yapmaz; bir **durum makinesini** (state machine) korur:

    request -> pending
    pending -> approved        (yetkili onayı; SoD: talep eden ≠ onaylayan)
    pending -> rejected        (gerekçeli ret / talep sahibinin geri çekmesi)
    approved -> used           (algoritma override ile çalıştırıldı)
    approved -> (expired)      (expires_at geçince get_active_override görmez)

Geçersiz geçişler (rejected -> approved, used -> rejected, approved -> rejected …)
servis katmanında açıkça reddedilir.

Transaction sözleşmesi
----------------------
Yazma yapan fonksiyonlar `commit` parametresi alır. `commit=True` (varsayılan)
fonksiyon kendi işlemini atomik commit/rollback eder; `commit=False` ise
commit/rollback sorumluluğu çağırana aittir (üst katman batch'liyor olabilir).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.db.schema_compat import ensure_criteria_completion_governance_schema
from app.services.criteria_completion_policy_service import resolve_policy

logger = logging.getLogger(__name__)

VALID_SCOPE_TYPES = {"global", "faculty", "department"}
VALID_APPROVAL_STATUSES = {"pending", "approved", "rejected"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_semester(value: str | None) -> str | None:
    """Dönemi 'Güz'/'Bahar' kanonik biçimine indirger; bilinmeyen değeri reddeder.

    (Politika servisiyle aynı kuralları kullanır; 'b' ile başlamayan her şeyi
    sessizce 'Güz' yapan eski hatalı davranış kaldırılmıştır.)
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
    scope_type = str(value or "").strip().lower()
    if scope_type not in VALID_SCOPE_TYPES:
        raise ValueError(
            f"Geçersiz override kapsamı (scope_type): '{value}'. "
            f"Geçerli tipler: {sorted(VALID_SCOPE_TYPES)}"
        )
    return scope_type


def _validate_scope_ids(
    scope_type: str,
    faculty_id: int | None,
    department_id: int | None,
    *,
    strict: bool = True,
) -> tuple[int | None, int | None]:
    """Kapsam tipi ile ID alanlarının tutarlılığını uygular (Kapsam İzolasyonu).

    `strict=True` (talep oluşturma — yazma yolu): fazladan dolu gelen ID `ValueError`
    ile reddedilir; anlamsız/erişilemez override kaydı oluşmaz.

    `strict=False` (aktif override arama — güvenlik kapısı/okuma yolu): kapsama
    ilgisiz ID sessizce NULL'a indirgenir; yalnızca *zorunlu* ID eksikse hata verir.
    Böylece tutarsız bir girdi tüm karar kapısını çökertmez.
    """
    if scope_type == "global":
        if strict and (faculty_id is not None or department_id is not None):
            raise ValueError("Global override için faculty_id ve department_id NULL olmalıdır.")
        return None, None
    if scope_type == "faculty":
        if faculty_id is None:
            raise ValueError("Fakülte kapsamındaki override için faculty_id zorunludur.")
        if strict and department_id is not None:
            raise ValueError("Fakülte kapsamındaki override için department_id NULL olmalıdır.")
        return int(faculty_id), None
    # scope_type == "department"
    if faculty_id is None or department_id is None:
        raise ValueError("Bölüm kapsamındaki override için faculty_id ve department_id zorunludur.")
    return int(faculty_id), int(department_id)


def _normalize_datetime(value: str | None) -> str | None:
    """`expires_at` gibi tarihleri UTC ISO-8601'e indirger.

    String tarih karşılaştırması ancak format tutarlıysa güvenlidir; bu yüzden
    kayda yazmadan önce kanonik biçime çevrilir.
    """
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(
            f"Geçersiz tarih: '{value}'. expires_at ISO-8601 olmalıdır (örn. 2026-09-01T00:00:00+00:00)."
        ) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat(timespec="seconds")


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return list(default) if isinstance(default, list) else default
    try:
        return json.loads(value)
    except Exception:
        logger.exception("Override JSON alanı ayrıştırılamadı, varsayılana düşülüyor. Ham veri: %r", value)
        return list(default) if isinstance(default, list) else default


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None) -> dict[str, Any] | None:
    if not row:
        return None
    data = {key: row[key] for key in row.keys()} if isinstance(row, sqlite3.Row) else {}
    data["missing_fields"] = _json_loads(data.get("missing_fields_json"), [])
    data["validation_issues"] = _json_loads(data.get("validation_issues_json"), [])
    return data


def _is_expired(expires_at: str | None) -> bool:
    """expires_at geçmişte mi? Tarihler kanonik UTC ISO olduğundan string ile güvenli kıyaslanır."""
    return bool(expires_at) and str(expires_at) < _now()


def request_override(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    reason: str,
    faculty_id: int | None = None,
    department_id: int | None = None,
    course_id: int | None = None,
    semester: str | None = None,
    missing_fields: list[str] | None = None,
    validation_issues: list[dict[str, Any]] | None = None,
    requested_by: str | None = None,
    expires_at: str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Doğrulanmış ve mükerrerlik korumalı yeni bir override talebi oluşturur."""
    ensure_criteria_completion_governance_schema(conn, commit=False)

    # --- Normalizasyon ve giriş doğrulamaları ---
    scope_type = _normalize_scope_type(scope_type)
    faculty_id, department_id = _validate_scope_ids(scope_type, faculty_id, department_id, strict=True)
    semester = _normalize_semester(semester)
    expires_at = _normalize_datetime(expires_at)
    requested_by = str(requested_by or "").strip()
    if not requested_by:
        raise ValueError("Override talebini açan kullanıcı (requested_by) zorunludur; anonim talep kaydedilemez.")
    reason = str(reason or "").strip()

    # --- Kapsam politikası ---
    policy = resolve_policy(conn, scope_type, int(year), faculty_id, department_id, semester)
    if not policy.get("allow_override"):
        raise ValueError(
            f"Aktif politika ('{policy.get('name')}') bu kapsamda override talebine izin vermiyor."
        )
    if policy.get("override_requires_reason") and not reason:
        raise ValueError("Aktif politika gereği override talebi için gerekçe (reason) zorunludur.")

    cur = conn.cursor()

    # --- Mükerrer 'pending' talep koruması ---
    cur.execute(
        """
        SELECT id FROM criteria_completion_overrides
        WHERE scope_type = ?
          AND COALESCE(faculty_id, -1) = COALESCE(?, -1)
          AND COALESCE(department_id, -1) = COALESCE(?, -1)
          AND COALESCE(course_id, -1) = COALESCE(?, -1)
          AND year = ?
          AND COALESCE(semester, '') = COALESCE(?, '')
          AND approval_status = 'pending'
        LIMIT 1
        """,
        (scope_type, faculty_id, department_id, course_id, int(year), semester or ""),
    )
    if cur.fetchone():
        raise ValueError(
            "Bu kapsam/yıl/dönem için zaten onay bekleyen (pending) bir override talebi var; mükerrer talep açılamaz."
        )

    # Politika onay gerektirmiyorsa talep doğrudan 'approved' başlar.
    status = "pending" if policy.get("override_requires_approval") else "approved"
    now = _now()
    try:
        cur.execute(
            """
            INSERT INTO criteria_completion_overrides (
                scope_type, faculty_id, department_id, course_id, year, semester,
                missing_fields_json, validation_issues_json, reason, requested_by,
                requested_at, approval_status, approved_by, approved_at, expires_at, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scope_type,
                faculty_id,
                department_id,
                course_id,
                int(year),
                semester,
                _json_dumps(missing_fields or []),
                _json_dumps(validation_issues or []),
                reason,
                requested_by,
                now,
                status,
                requested_by if status == "approved" else None,
                now if status == "approved" else None,
                expires_at,
                now,
            ),
        )
        last_id = int(cur.lastrowid or 0)
    except Exception:
        if commit:
            conn.rollback()
        raise
    if commit:
        conn.commit()
    return get_override(conn, last_id) or {}


def get_override(conn: sqlite3.Connection, override_id: int) -> dict[str, Any] | None:
    ensure_criteria_completion_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT * FROM criteria_completion_overrides WHERE id = ?", (int(override_id),))
    return _row_to_dict(cur.fetchone())


def approve_override(
    conn: sqlite3.Connection,
    override_id: int,
    approved_by: str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Bekleyen bir override talebini onaylar. [pending -> approved]

    Yalnızca 'pending' talepler onaylanır; onaylayan kullanıcı zorunludur ve
    Roller Ayrılığı (SoD) gereği talep eden kişi kendi talebini onaylayamaz.
    Süresi geçmiş talep onaylanmaz.
    """
    ensure_criteria_completion_governance_schema(conn, commit=False)

    approved_by = str(approved_by or "").strip()
    if not approved_by:
        raise ValueError("Onaylayan kullanıcı (approved_by) zorunludur.")

    override = get_override(conn, override_id)
    if not override:
        raise ValueError(f"Override talebi bulunamadı: id={override_id}.")
    if override.get("approval_status") != "pending":
        raise ValueError(
            f"Sadece 'pending' talepler onaylanabilir. Mevcut durum: '{override.get('approval_status')}'."
        )

    requested_by = str(override.get("requested_by") or "").strip()
    if requested_by and requested_by == approved_by:
        raise ValueError("Roller Ayrılığı: Talebi açan kullanıcı kendi override talebini onaylayamaz.")
    if _is_expired(override.get("expires_at")):
        raise ValueError("Süresi dolmuş override talebi onaylanamaz.")

    now = _now()
    cur = conn.cursor()
    try:
        # WHERE'deki 'pending' koşulu eşzamanlılığa karşı ek güvence sağlar.
        cur.execute(
            """
            UPDATE criteria_completion_overrides
            SET approval_status = 'approved', approved_by = ?, approved_at = ?
            WHERE id = ? AND approval_status = 'pending'
            """,
            (approved_by, now, int(override_id)),
        )
    except Exception:
        if commit:
            conn.rollback()
        raise
    if commit:
        conn.commit()
    return get_override(conn, int(override_id)) or {}


def reject_override(
    conn: sqlite3.Connection,
    override_id: int,
    rejection_reason: str,
    rejected_by: str | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Bekleyen bir override talebini gerekçeli reddeder. [pending -> rejected]

    Reddeden kullanıcı ve gerekçe zorunludur. Onayın aksine, talep sahibinin
    kendi bekleyen talebini reddetmesine (geri çekme) izin verilir: ret erişim
    açmaz ve şu an başka bir iptal yolu yoktur. SoD yalnızca onayda zorunludur.
    """
    ensure_criteria_completion_governance_schema(conn, commit=False)

    rejected_by = str(rejected_by or "").strip()
    if not rejected_by:
        raise ValueError("Reddeden kullanıcı (rejected_by) zorunludur.")
    rejection_reason = str(rejection_reason or "").strip()
    if not rejection_reason:
        raise ValueError("Ret gerekçesi (rejection_reason) zorunludur.")

    override = get_override(conn, override_id)
    if not override:
        raise ValueError(f"Override talebi bulunamadı: id={override_id}.")
    if override.get("approval_status") != "pending":
        raise ValueError(
            f"Sadece 'pending' talepler reddedilebilir. Mevcut durum: '{override.get('approval_status')}'."
        )

    now = _now()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE criteria_completion_overrides
            SET approval_status = 'rejected', rejected_by = ?, rejected_at = ?, rejection_reason = ?
            WHERE id = ? AND approval_status = 'pending'
            """,
            (rejected_by, now, rejection_reason, int(override_id)),
        )
    except Exception:
        if commit:
            conn.rollback()
        raise
    if commit:
        conn.commit()
    return get_override(conn, int(override_id)) or {}


def get_active_override(
    conn: sqlite3.Connection,
    scope_type: str,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    course_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any] | None:
    """Seçili **tam kapsam** için onaylı ve süresi dolmamış en güncel override'ı getirir.

    Kapsam izolasyonu (Seçenek A): Override yalnızca açıldığı kapsamda geçerlidir;
    fakülte override'ı otomatik olarak bölüm/ders kapsamını kapsamaz. Güvenlik
    kapısı (`calculate_completion`) tarafından doğrudan sorgulanır.
    """
    ensure_criteria_completion_governance_schema(conn, commit=False)
    scope_type = _normalize_scope_type(scope_type)
    # Okuma/kapı yolu: ilgisiz ID'ler kapsama göre indirgenir, kapı çökmez.
    faculty_id, department_id = _validate_scope_ids(scope_type, faculty_id, department_id, strict=False)
    semester = _normalize_semester(semester)

    cur = conn.cursor()
    now = _now()
    cur.execute(
        """
        SELECT *
        FROM criteria_completion_overrides
        WHERE scope_type = ?
          AND COALESCE(faculty_id, -1) = COALESCE(?, -1)
          AND COALESCE(department_id, -1) = COALESCE(?, -1)
          AND COALESCE(course_id, -1) = COALESCE(?, -1)
          AND year = ?
          AND COALESCE(semester, '') = COALESCE(?, '')
          AND approval_status = 'approved'
          AND (expires_at IS NULL OR expires_at >= ?)
        ORDER BY id DESC
        LIMIT 1
        """,
        (scope_type, faculty_id, department_id, course_id, int(year), semester or "", now),
    )
    return _row_to_dict(cur.fetchone())


def list_overrides(
    conn: sqlite3.Connection,
    scope_type: str | None = None,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    approval_status: str | None = None,
    course_id: int | None = None,
    semester: str | None = None,
    requested_by: str | None = None,
    active_only: bool = False,
) -> list[dict[str, Any]]:
    """Override kayıtlarını filtreleyerek listeler (Merkezi Override Yönetim Ekranı için).

    `active_only=True`: yalnızca onaylı ve süresi dolmamış (hâlâ etkili) kayıtlar.
    """
    ensure_criteria_completion_governance_schema(conn, commit=False)
    where = ["1=1"]
    params: list[Any] = []

    if scope_type is not None:
        where.append("scope_type = ?")
        params.append(_normalize_scope_type(scope_type))
    if approval_status is not None:
        status = str(approval_status).strip().lower()
        if status not in VALID_APPROVAL_STATUSES:
            raise ValueError(f"Geçersiz approval_status filtresi: '{approval_status}'.")
        where.append("approval_status = ?")
        params.append(status)
    if semester is not None:
        where.append("COALESCE(semester, '') = COALESCE(?, '')")
        params.append(_normalize_semester(semester) or "")
    if requested_by is not None:
        where.append("requested_by = ?")
        params.append(str(requested_by))
    for col, value in (("year", year), ("faculty_id", faculty_id), ("department_id", department_id), ("course_id", course_id)):
        if value is not None:
            where.append(f"{col} = ?")
            params.append(int(value))
    if active_only:
        where.append("approval_status = 'approved'")
        where.append("(expires_at IS NULL OR expires_at >= ?)")
        params.append(_now())

    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM criteria_completion_overrides WHERE {' AND '.join(where)} ORDER BY id DESC",
        tuple(params),
    )
    return [_row_to_dict(row) or {} for row in cur.fetchall()]


def mark_override_used(
    conn: sqlite3.Connection,
    override_id: int,
    run_id: int | None = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Karar algoritması override ile çalıştırıldığında kaydı denetim izi için damgalar.

    Yalnızca 'approved' bir override 'used' olarak işaretlenebilir.
    """
    ensure_criteria_completion_governance_schema(conn, commit=False)
    override = get_override(conn, override_id)
    if not override:
        raise ValueError(f"Override kaydı bulunamadı: id={override_id}.")
    if override.get("approval_status") != "approved":
        raise ValueError(
            f"Sadece 'approved' override kullanıldı olarak işaretlenebilir. Mevcut durum: '{override.get('approval_status')}'."
        )

    now = _now()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            UPDATE criteria_completion_overrides
            SET used_at = ?, allowed_for_run_id = COALESCE(?, allowed_for_run_id)
            WHERE id = ? AND approval_status = 'approved'
            """,
            (now, None if run_id is None else int(run_id), int(override_id)),
        )
    except Exception:
        if commit:
            conn.rollback()
        raise
    if commit:
        conn.commit()
    return get_override(conn, int(override_id)) or {}
