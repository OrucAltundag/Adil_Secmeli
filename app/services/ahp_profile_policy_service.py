# -*- coding: utf-8 -*-
"""AHP profil kullanım, tutarlılık ve onay politikası servisi."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from app.db.schema_compat import ensure_ahp_governance_schema


def seed_default_policy(conn: sqlite3.Connection) -> dict[str, Any]:
    ensure_ahp_governance_schema(conn, commit=False)
    cur = conn.execute(
        "SELECT * FROM ahp_profile_policies WHERE scope_type='global' AND is_active=1 ORDER BY id DESC LIMIT 1"
    )
    row = cur.fetchone()
    if row:
        return _row_dict(row)
    now = _now()
    cur = conn.execute(
        """
        INSERT INTO ahp_profile_policies (
            name, scope_type, max_consistency_ratio, require_approval_for_activation,
            allow_inconsistent_profile_for_draft_runs, allow_default_profile_if_missing,
            mark_decisions_stale_on_profile_change, require_notes_for_manual_profile,
            is_active, created_at, updated_at
        )
        VALUES ('Varsayılan AHP Profil Politikası', 'global', 0.10, 1, 0, 1, 1, 1, 1, ?, ?)
        """,
        (now, now),
    )
    cur = conn.execute("SELECT * FROM ahp_profile_policies WHERE id=?", (int(cur.lastrowid),))
    return _row_dict(cur.fetchone())


def resolve_policy(
    conn: sqlite3.Connection,
    *,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any]:
    seed_default_policy(conn)
    candidates = [
        ("department", faculty_id, department_id, year, semester),
        ("department", faculty_id, department_id, year, None),
        ("faculty", faculty_id, None, year, semester),
        ("faculty", faculty_id, None, year, None),
        ("department", faculty_id, department_id, None, None),
        ("faculty", faculty_id, None, None, None),
        ("global", None, None, year, None),
        ("global", None, None, None, None),
    ]
    for scope_type, fac, dep, yy, sem in candidates:
        if scope_type == "department" and dep is None:
            continue
        if scope_type == "faculty" and fac is None:
            continue
        cur = conn.execute(
            """
            SELECT * FROM ahp_profile_policies
            WHERE is_active=1
              AND scope_type=?
              AND COALESCE(faculty_id, -1)=COALESCE(?, -1)
              AND COALESCE(department_id, -1)=COALESCE(?, -1)
              AND COALESCE(year, -1)=COALESCE(?, -1)
              AND COALESCE(semester, '')=COALESCE(?, '')
            ORDER BY id DESC LIMIT 1
            """,
            (scope_type, fac, dep, yy, sem),
        )
        row = cur.fetchone()
        if row:
            return _row_dict(row)
    return seed_default_policy(conn)


def can_activate_profile(profile: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    cr = float(profile.get("consistency_ratio") or 0.0)
    max_cr = float(policy.get("max_consistency_ratio") or 0.10)
    if cr > max_cr:
        reasons.append(f"CR {cr:.3f}, politika sınırı {max_cr:.3f} üzerinde.")
    if policy.get("require_approval_for_activation") and profile.get("status") not in {"approved", "active"} and profile.get("source") != "default":
        reasons.append("Aktivasyon için profil onayı gereklidir.")
    if policy.get("require_notes_for_manual_profile") and profile.get("source") == "manual" and not profile.get("notes"):
        reasons.append("Manuel profil için not/gerekçe gereklidir.")
    return {"can_activate": not reasons, "reasons": reasons}


def can_use_profile_for_decision(profile: dict[str, Any], policy: dict[str, Any], *, draft_run: bool = False) -> dict[str, Any]:
    reasons: list[str] = []
    status = str(profile.get("status") or "active")
    if status in {"draft", "rejected", "archived"}:
        reasons.append(f"{status} durumundaki profil karar çalıştırmada kullanılamaz.")
    cr = float(profile.get("consistency_ratio") or 0.0)
    if cr > float(policy.get("max_consistency_ratio") or 0.10):
        if not (draft_run and policy.get("allow_inconsistent_profile_for_draft_runs")):
            reasons.append("Profil tutarlılık oranı karar için kabul edilebilir sınırın üzerinde.")
    return {"can_use": not reasons, "reasons": reasons}


def should_mark_decisions_stale(policy: dict[str, Any]) -> bool:
    return bool(policy.get("mark_decisions_stale_on_profile_change", True))


def _row_dict(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    if isinstance(row, sqlite3.Row):
        data = {key: row[key] for key in row.keys()}
    else:
        keys = [
            "id",
            "name",
            "scope_type",
            "faculty_id",
            "department_id",
            "year",
            "semester",
            "max_consistency_ratio",
            "require_approval_for_activation",
            "allow_inconsistent_profile_for_draft_runs",
            "allow_default_profile_if_missing",
            "mark_decisions_stale_on_profile_change",
            "require_notes_for_manual_profile",
            "is_active",
            "created_at",
            "updated_at",
        ]
        data = dict(zip(keys, row))
    for key in (
        "require_approval_for_activation",
        "allow_inconsistent_profile_for_draft_runs",
        "allow_default_profile_if_missing",
        "mark_decisions_stale_on_profile_change",
        "require_notes_for_manual_profile",
        "is_active",
    ):
        if key in data:
            data[key] = bool(data[key])
    return data


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
