# -*- coding: utf-8 -*-
"""AHP profil yönetişimi, versiyonlama ve aktif profil çözümleme servisi."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from app.db.schema_compat import ensure_ahp_governance_schema
from app.services.ahp_calculation_service import (
    build_pairwise_matrix_from_weights,
    calculate_weights_from_pairwise_matrix,
    normalize_weights,
)
from app.services.ahp_profile_policy_service import (
    can_activate_profile,
    can_use_profile_for_decision,
    resolve_policy,
    seed_default_policy,
    should_mark_decisions_stale,
)
from app.services.criteria_definition_service import seed_default_decision_criteria

DEFAULT_CRITERIA_KEYS = ["basari", "trend", "populerlik", "anket"]
DEFAULT_WEIGHTS = {
    "basari": 0.35,
    "trend": 0.25,
    "populerlik": 0.20,
    "anket": 0.20,
}


def seed_default_profile(conn: sqlite3.Connection) -> dict[str, Any]:
    """Global varsayılan AHP profilini idempotent oluşturur."""
    ensure_ahp_governance_schema(conn, commit=False)
    seed_default_decision_criteria(conn)
    seed_default_policy(conn)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM ahp_weight_profiles
        WHERE scope_type='global'
          AND year IS NULL
          AND COALESCE(semester, '')=''
          AND source='default'
          AND is_active=1
          AND status='active'
        ORDER BY id DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if row:
        return _row_to_profile(row)

    matrix = build_pairwise_matrix_from_weights(DEFAULT_WEIGHTS, DEFAULT_CRITERIA_KEYS)
    result = calculate_weights_from_pairwise_matrix(DEFAULT_CRITERIA_KEYS, matrix)
    now = _now()
    cur.execute(
        """
        INSERT INTO ahp_weight_profiles (
            name, profile_name, profile_code, scope_type, faculty_id, department_id,
            year, semester, version, criteria_keys_json, pairwise_matrix_json,
            weights_json, consistency_index, consistency_ratio, is_consistent,
            consistency_warning, source, status, created_by, notes, is_active,
            created_at, updated_at, approved_by, approved_at
        )
        VALUES (?, ?, ?, 'global', NULL, NULL, NULL, NULL, 1, ?, ?, ?, ?, ?, ?, ?, 'default',
                'active', 'system', ?, 1, ?, ?, 'system', ?)
        """,
        (
            "Varsayılan Global AHP Profili",
            "Varsayılan Global AHP Profili",
            "global-default-ahp",
            _json(DEFAULT_CRITERIA_KEYS),
            _json(matrix),
            _json(result.weights),
            result.consistency_index,
            result.consistency_ratio,
            1 if result.is_consistent else 0,
            "; ".join(result.warnings) if result.warnings else None,
            "Sistem tarafından oluşturulan varsayılan AHP profili.",
            now,
            now,
            now,
        ),
    )
    profile_id = int(cur.lastrowid)
    _log_profile_action(cur, profile_id, "created", None, "active", "system", "Varsayılan profil oluşturuldu.")
    conn.commit()
    return get_profile(conn, profile_id) or {}


ensure_default_ahp_profile = seed_default_profile


def create_profile(
    conn: sqlite3.Connection,
    *,
    profile_name: str | None = None,
    name: str | None = None,
    profile_code: str | None = None,
    scope_type: str = "global",
    faculty_id: int | None = None,
    department_id: int | None = None,
    year: int | None = None,
    semester: str | None = None,
    criteria_keys: list[str] | None = None,
    pairwise_matrix: list[list[float]] | None = None,
    weights: dict[str, float] | None = None,
    source: str = "manual",
    status: str = "draft",
    created_by: str | None = None,
    notes: str | None = None,
    parent_profile_id: int | None = None,
    activate: bool = False,
    bypass_activation_policy: bool = False,
) -> dict[str, Any]:
    ensure_ahp_governance_schema(conn, commit=False)
    seed_default_decision_criteria(conn)
    seed_default_policy(conn)

    keys = list(criteria_keys or DEFAULT_CRITERIA_KEYS)
    if weights is not None:
        normalized_weights = normalize_weights(weights, keys)
        matrix = pairwise_matrix or build_pairwise_matrix_from_weights(normalized_weights, keys)
    else:
        matrix = pairwise_matrix or build_pairwise_matrix_from_weights(DEFAULT_WEIGHTS, keys)
        result = calculate_weights_from_pairwise_matrix(keys, matrix)
        normalized_weights = result.weights

    result = calculate_weights_from_pairwise_matrix(keys, matrix)
    normalized_weights = result.weights
    policy = resolve_policy(conn, year=year, faculty_id=faculty_id, department_id=department_id, semester=semester)
    max_cr = float(policy.get("max_consistency_ratio") or 0.10)
    final_status = str(status or "draft")
    if result.consistency_ratio > max_cr and final_status in {"validated", "pending_approval", "approved", "active"}:
        final_status = "draft"
    if final_status == "active" and not activate:
        activate = True
        final_status = "approved"
    version = _next_profile_version(conn, scope_type, faculty_id, department_id, year, semester)
    display_name = str(profile_name or name or "Yeni AHP Profili")
    now = _now()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ahp_weight_profiles (
            name, profile_name, profile_code, scope_type, faculty_id, department_id,
            year, semester, version, criteria_keys_json, pairwise_matrix_json,
            weights_json, consistency_index, consistency_ratio, is_consistent,
            consistency_warning, source, status, created_by, notes, is_active,
            created_at, updated_at, parent_profile_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
        """,
        (
            display_name,
            display_name,
            profile_code,
            str(scope_type or "global"),
            faculty_id,
            department_id,
            year,
            semester,
            int(version),
            _json(keys),
            _json(matrix),
            _json(normalized_weights),
            result.consistency_index,
            result.consistency_ratio,
            1 if result.is_consistent else 0,
            "; ".join(result.warnings) if result.warnings else None,
            str(source or "manual"),
            final_status,
            created_by,
            notes,
            now,
            now,
            parent_profile_id,
        ),
    )
    profile_id = int(cur.lastrowid)
    _log_profile_action(cur, profile_id, "created", None, final_status, created_by, "AHP profili oluşturuldu.")
    conn.commit()
    if activate:
        return activate_profile(conn, profile_id, actor=created_by, bypass_policy=bypass_activation_policy)
    return get_profile(conn, profile_id) or {}


def create_ahp_profile(
    conn: sqlite3.Connection,
    name: str,
    scope_type: str = "global",
    faculty_id: int | None = None,
    department_id: int | None = None,
    year: int | None = None,
    criteria_keys: list[str] | None = None,
    pairwise_matrix: list[list[float]] | None = None,
    weights: dict[str, float] | None = None,
    source: str = "manual",
    created_by: str | None = None,
    notes: str | None = None,
    activate: bool = True,
) -> dict[str, Any]:
    """Eski Decision Center/API çağrıları için geriye dönük uyumlu wrapper."""
    return create_profile(
        conn,
        profile_name=name,
        scope_type=scope_type,
        faculty_id=faculty_id,
        department_id=department_id,
        year=year,
        criteria_keys=criteria_keys,
        pairwise_matrix=pairwise_matrix,
        weights=weights,
        source=source,
        status="approved" if activate else "draft",
        created_by=created_by,
        notes=notes,
        activate=activate,
        bypass_activation_policy=True,
    )


def update_profile(conn: sqlite3.Connection, profile_id: int, **updates: Any) -> dict[str, Any]:
    ensure_ahp_governance_schema(conn, commit=False)
    profile = get_profile(conn, profile_id)
    if not profile:
        raise ValueError(f"AHP profili bulunamadı: {profile_id}")
    allowed = {
        "profile_name",
        "name",
        "profile_code",
        "scope_type",
        "faculty_id",
        "department_id",
        "year",
        "semester",
        "source",
        "notes",
    }
    assignments: list[str] = []
    params: list[Any] = []
    for key, value in updates.items():
        if key not in allowed:
            continue
        column = "profile_name" if key == "name" else key
        assignments.append(f"{column}=?")
        params.append(value)
        if key in {"name", "profile_name"}:
            assignments.append("name=?")
            params.append(value)
    keys = updates.get("criteria_keys")
    matrix = updates.get("pairwise_matrix")
    weights = updates.get("weights")
    if keys is not None or matrix is not None or weights is not None:
        criteria_keys = list(keys or profile["criteria_keys"])
        if weights is not None and matrix is None:
            matrix = build_pairwise_matrix_from_weights(normalize_weights(weights, criteria_keys), criteria_keys)
        else:
            matrix = matrix or profile["pairwise_matrix"]
        result = calculate_weights_from_pairwise_matrix(criteria_keys, matrix)
        assignments.extend(
            [
                "criteria_keys_json=?",
                "pairwise_matrix_json=?",
                "weights_json=?",
                "consistency_index=?",
                "consistency_ratio=?",
                "is_consistent=?",
                "consistency_warning=?",
                "status=?",
            ]
        )
        params.extend(
            [
                _json(criteria_keys),
                _json(matrix),
                _json(result.weights),
                result.consistency_index,
                result.consistency_ratio,
                1 if result.is_consistent else 0,
                "; ".join(result.warnings) if result.warnings else None,
                "validated" if result.is_consistent else "draft",
            ]
        )
    if not assignments:
        return profile
    assignments.append("updated_at=?")
    params.append(_now())
    params.append(int(profile_id))
    conn.execute(f"UPDATE ahp_weight_profiles SET {', '.join(assignments)} WHERE id=?", tuple(params))
    _log_profile_action(conn.cursor(), profile_id, "updated", profile.get("status"), get_profile(conn, profile_id).get("status") if get_profile(conn, profile_id) else None, updates.get("actor"), "AHP profili güncellendi.")
    conn.commit()
    return get_profile(conn, profile_id) or {}


def validate_profile(conn: sqlite3.Connection, profile_id: int) -> dict[str, Any]:
    profile = get_profile(conn, profile_id)
    if not profile:
        raise ValueError(f"AHP profili bulunamadı: {profile_id}")
    result = calculate_weights_from_pairwise_matrix(profile["criteria_keys"], profile["pairwise_matrix"])
    policy = resolve_policy(
        conn,
        year=profile.get("year"),
        faculty_id=profile.get("faculty_id"),
        department_id=profile.get("department_id"),
        semester=profile.get("semester"),
    )
    status = "validated" if result.consistency_ratio <= float(policy.get("max_consistency_ratio") or 0.10) else "draft"
    conn.execute(
        """
        UPDATE ahp_weight_profiles
        SET weights_json=?, consistency_index=?, consistency_ratio=?, is_consistent=?,
            consistency_warning=?, status=?, updated_at=?
        WHERE id=?
        """,
        (
            _json(result.weights),
            result.consistency_index,
            result.consistency_ratio,
            1 if status == "validated" else 0,
            "; ".join(result.warnings) if result.warnings else None,
            status,
            _now(),
            int(profile_id),
        ),
    )
    _log_profile_action(conn.cursor(), profile_id, "validated", profile.get("status"), status, None, "AHP matrisi ve CR doğrulandı.")
    conn.commit()
    return get_profile(conn, profile_id) or {}


def submit_for_approval(conn: sqlite3.Connection, profile_id: int, actor: str | None = None) -> dict[str, Any]:
    profile = validate_profile(conn, profile_id)
    if not profile.get("is_consistent"):
        raise ValueError("Tutarsız AHP profili onaya gönderilemez.")
    _set_status(conn, profile_id, "pending_approval", "submitted", actor, "AHP profili onaya gönderildi.")
    return get_profile(conn, profile_id) or {}


def approve_profile(conn: sqlite3.Connection, profile_id: int, approved_by: str | None = None) -> dict[str, Any]:
    profile = get_profile(conn, profile_id)
    if not profile:
        raise ValueError(f"AHP profili bulunamadı: {profile_id}")
    now = _now()
    conn.execute(
        """
        UPDATE ahp_weight_profiles
        SET status='approved', approved_by=?, approved_at=?, updated_at=?
        WHERE id=?
        """,
        (approved_by, now, now, int(profile_id)),
    )
    _log_profile_action(conn.cursor(), profile_id, "approved", profile.get("status"), "approved", approved_by, "AHP profili onaylandı.")
    conn.commit()
    return get_profile(conn, profile_id) or {}


def reject_profile(
    conn: sqlite3.Connection,
    profile_id: int,
    reason: str,
    rejected_by: str | None = None,
) -> dict[str, Any]:
    if not str(reason or "").strip():
        raise ValueError("Red gerekçesi zorunludur.")
    profile = get_profile(conn, profile_id)
    if not profile:
        raise ValueError(f"AHP profili bulunamadı: {profile_id}")
    now = _now()
    conn.execute(
        """
        UPDATE ahp_weight_profiles
        SET status='rejected', rejected_by=?, rejected_at=?, rejection_reason=?,
            is_active=0, updated_at=?
        WHERE id=?
        """,
        (rejected_by, now, str(reason), now, int(profile_id)),
    )
    _log_profile_action(conn.cursor(), profile_id, "rejected", profile.get("status"), "rejected", rejected_by, str(reason))
    conn.commit()
    return get_profile(conn, profile_id) or {}


def activate_profile(
    conn: sqlite3.Connection,
    profile_id: int,
    actor: str | None = None,
    *,
    bypass_policy: bool = False,
) -> dict[str, Any]:
    ensure_ahp_governance_schema(conn, commit=False)
    profile = get_profile(conn, profile_id)
    if not profile:
        raise ValueError(f"AHP profili bulunamadı: {profile_id}")
    policy = resolve_policy(
        conn,
        year=profile.get("year"),
        faculty_id=profile.get("faculty_id"),
        department_id=profile.get("department_id"),
        semester=profile.get("semester"),
    )
    allowed = can_activate_profile(profile, policy)
    if not bypass_policy and not allowed["can_activate"]:
        raise ValueError("AHP profili aktif yapılamaz: " + " ".join(allowed["reasons"]))

    cur = conn.cursor()
    cur.execute(
        """
        SELECT id
        FROM ahp_weight_profiles
        WHERE is_active=1
          AND scope_type=?
          AND COALESCE(faculty_id, -1)=COALESCE(?, -1)
          AND COALESCE(department_id, -1)=COALESCE(?, -1)
          AND COALESCE(year, -1)=COALESCE(?, -1)
          AND COALESCE(semester, '')=COALESCE(?, '')
          AND id<>?
        """,
        (
            profile["scope_type"],
            profile.get("faculty_id"),
            profile.get("department_id"),
            profile.get("year"),
            profile.get("semester"),
            int(profile_id),
        ),
    )
    old_ids = [int(row[0]) for row in cur.fetchall()]
    now = _now()
    if old_ids:
        cur.execute(
            f"""
            UPDATE ahp_weight_profiles
            SET is_active=0, status='archived', superseded_by_profile_id=?, updated_at=?
            WHERE id IN ({','.join('?' for _ in old_ids)})
            """,
            (int(profile_id), now, *old_ids),
        )
    cur.execute(
        """
        UPDATE ahp_weight_profiles
        SET is_active=1, status='active', updated_at=?
        WHERE id=?
        """,
        (now, int(profile_id)),
    )
    _log_profile_action(cur, profile_id, "activated", profile.get("status"), "active", actor, "AHP profili aktif yapıldı.")
    if old_ids and should_mark_decisions_stale(policy):
        for old_id in old_ids:
            mark_decisions_stale_for_profile_change(
                conn,
                old_profile_id=old_id,
                new_profile_id=int(profile_id),
                actor=actor,
                commit=False,
            )
    conn.commit()
    return get_profile(conn, profile_id) or {}


activate_ahp_profile = activate_profile


def archive_profile(conn: sqlite3.Connection, profile_id: int, actor: str | None = None) -> dict[str, Any]:
    profile = get_profile(conn, profile_id)
    if not profile:
        raise ValueError(f"AHP profili bulunamadı: {profile_id}")
    conn.execute(
        "UPDATE ahp_weight_profiles SET status='archived', is_active=0, updated_at=? WHERE id=?",
        (_now(), int(profile_id)),
    )
    _log_profile_action(conn.cursor(), profile_id, "archived", profile.get("status"), "archived", actor, "AHP profili arşivlendi.")
    conn.commit()
    return get_profile(conn, profile_id) or {}


def clone_profile(
    conn: sqlite3.Connection,
    profile_id: int,
    new_scope: dict[str, Any] | None = None,
    new_year: int | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    profile = get_profile(conn, profile_id)
    if not profile:
        raise ValueError(f"AHP profili bulunamadı: {profile_id}")
    scope = dict(new_scope or {})
    return create_profile(
        conn,
        profile_name=f"{profile['profile_name']} kopyası",
        profile_code=None,
        scope_type=scope.get("scope_type", profile["scope_type"]),
        faculty_id=scope.get("faculty_id", profile.get("faculty_id")),
        department_id=scope.get("department_id", profile.get("department_id")),
        year=new_year if new_year is not None else scope.get("year", profile.get("year")),
        semester=scope.get("semester", profile.get("semester")),
        criteria_keys=profile["criteria_keys"],
        pairwise_matrix=profile["pairwise_matrix"],
        source="manual",
        status="draft",
        created_by=actor,
        notes=f"{profile['id']} numaralı profilden klonlandı.",
        parent_profile_id=int(profile_id),
    )


def resolve_active_profile(
    conn: sqlite3.Connection,
    *,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
    draft_run: bool = False,
) -> dict[str, Any]:
    seed_default_profile(conn)
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
        for row in _fetch_active_profile_rows(conn, scope_type, fac, dep, yy, sem):
            profile = _row_to_profile(row)
            policy = resolve_policy(conn, year=yy, faculty_id=fac, department_id=dep, semester=sem)
            use_check = can_use_profile_for_decision(profile, policy, draft_run=draft_run)
            if use_check["can_use"] or profile.get("source") == "default":
                profile["decision_use_warnings"] = use_check["reasons"]
                return profile
    return seed_default_profile(conn)


def resolve_ahp_profile(
    conn: sqlite3.Connection,
    faculty_id: int | None = None,
    department_id: int | None = None,
    year: int | None = None,
    semester: str | None = None,
) -> dict[str, Any]:
    return resolve_active_profile(
        conn,
        year=year,
        faculty_id=faculty_id,
        department_id=department_id,
        semester=semester,
    )


def get_profile_for_decision_run(conn: sqlite3.Connection, decision_run_id: int) -> dict[str, Any] | None:
    ensure_ahp_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ap.*
        FROM decision_runs dr
        JOIN ahp_weight_profiles ap ON ap.id = dr.ahp_profile_id
        WHERE dr.id=?
        LIMIT 1
        """,
        (int(decision_run_id),),
    )
    row = cur.fetchone()
    return _row_to_profile(row) if row else None


def list_profiles(conn: sqlite3.Connection, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    seed_default_profile(conn)
    filters = filters or {}
    clauses: list[str] = []
    params: list[Any] = []
    for key in ("scope_type", "faculty_id", "department_id", "year", "semester", "status", "is_active"):
        if key in filters and filters[key] is not None:
            clauses.append(f"{key}=?")
            params.append(filters[key])
    sql = "SELECT * FROM ahp_weight_profiles"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY is_active DESC, scope_type, year DESC, version DESC, id DESC"
    conn.row_factory = sqlite3.Row
    cur = conn.execute(sql, tuple(params))
    return [_row_to_profile(row) for row in cur.fetchall()]


list_ahp_profiles = list_profiles


def get_profile(conn: sqlite3.Connection, profile_id: int) -> dict[str, Any] | None:
    ensure_ahp_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM ahp_weight_profiles WHERE id=?", (int(profile_id),))
    row = cur.fetchone()
    return _row_to_profile(row) if row else None


def list_stale_decisions(conn: sqlite3.Connection, unresolved_only: bool = True) -> list[dict[str, Any]]:
    ensure_ahp_governance_schema(conn, commit=False)
    sql = """
        SELECT dsf.*, dr.run_name, dr.year, dr.faculty_id, dr.department_id, dr.semester
        FROM decision_staleness_flags dsf
        LEFT JOIN decision_runs dr ON dr.id = dsf.decision_run_id
    """
    if unresolved_only:
        sql += " WHERE dsf.resolved_at IS NULL"
    sql += " ORDER BY dsf.id DESC"
    conn.row_factory = sqlite3.Row
    return [_row_dict(row) for row in conn.execute(sql).fetchall()]


def resolve_stale_decision(conn: sqlite3.Connection, stale_id: int, resolved_by: str | None = None) -> dict[str, Any]:
    ensure_ahp_governance_schema(conn, commit=False)
    conn.execute(
        "UPDATE decision_staleness_flags SET resolved_at=?, resolved_by=? WHERE id=?",
        (_now(), resolved_by, int(stale_id)),
    )
    cur = conn.execute("SELECT decision_run_id FROM decision_staleness_flags WHERE id=?", (int(stale_id),))
    row = cur.fetchone()
    if row:
        conn.execute(
            "UPDATE decision_runs SET stale_flag=0, recalculate_required=0 WHERE id=?",
            (int(row[0]),),
        )
    conn.commit()
    cur = conn.execute("SELECT * FROM decision_staleness_flags WHERE id=?", (int(stale_id),))
    return _row_dict(cur.fetchone())


def mark_decisions_stale_for_profile_change(
    conn: sqlite3.Connection,
    *,
    old_profile_id: int,
    new_profile_id: int,
    actor: str | None = None,
    commit: bool = True,
) -> int:
    ensure_ahp_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, run_name
        FROM decision_runs
        WHERE ahp_profile_id=?
          AND COALESCE(stale_flag, 0)=0
        """,
        (int(old_profile_id),),
    )
    rows = cur.fetchall()
    for row in rows:
        run_id = int(row["id"])
        message = (
            f"Bu karar çalışması eski AHP profili #{old_profile_id} ile üretildi. "
            f"Yeni aktif profil #{new_profile_id}; yeniden hesaplama önerilir."
        )
        cur.execute(
            """
            UPDATE decision_runs
            SET stale_flag=1, recalculate_required=1
            WHERE id=?
            """,
            (run_id,),
        )
        cur.execute(
            """
            INSERT INTO decision_staleness_flags (
                decision_run_id, reason, old_reference_id, new_reference_id,
                message, requires_recalculation, created_at, resolved_by
            )
            VALUES (?, 'ahp_profile_changed', ?, ?, ?, 1, ?, NULL)
            """,
            (run_id, int(old_profile_id), int(new_profile_id), message, _now()),
        )
    if commit:
        conn.commit()
    return len(rows)


def _set_status(
    conn: sqlite3.Connection,
    profile_id: int,
    new_status: str,
    action: str,
    actor: str | None,
    message: str | None,
) -> None:
    profile = get_profile(conn, profile_id)
    if not profile:
        raise ValueError(f"AHP profili bulunamadı: {profile_id}")
    conn.execute(
        "UPDATE ahp_weight_profiles SET status=?, updated_at=? WHERE id=?",
        (new_status, _now(), int(profile_id)),
    )
    _log_profile_action(conn.cursor(), profile_id, action, profile.get("status"), new_status, actor, message)
    conn.commit()


def _fetch_active_profile_rows(
    conn: sqlite3.Connection,
    scope_type: str,
    faculty_id: int | None,
    department_id: int | None,
    year: int | None,
    semester: str | None,
) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM ahp_weight_profiles
        WHERE is_active=1
          AND status='active'
          AND scope_type=?
          AND COALESCE(faculty_id, -1)=COALESCE(?, -1)
          AND COALESCE(department_id, -1)=COALESCE(?, -1)
          AND COALESCE(year, -1)=COALESCE(?, -1)
          AND COALESCE(semester, '')=COALESCE(?, '')
        ORDER BY version DESC, id DESC
        """,
        (scope_type, faculty_id, department_id, year, semester),
    )
    return list(cur.fetchall())


def _next_profile_version(
    conn: sqlite3.Connection,
    scope_type: str,
    faculty_id: int | None,
    department_id: int | None,
    year: int | None,
    semester: str | None,
) -> int:
    cur = conn.execute(
        """
        SELECT MAX(version)
        FROM ahp_weight_profiles
        WHERE scope_type=?
          AND COALESCE(faculty_id, -1)=COALESCE(?, -1)
          AND COALESCE(department_id, -1)=COALESCE(?, -1)
          AND COALESCE(year, -1)=COALESCE(?, -1)
          AND COALESCE(semester, '')=COALESCE(?, '')
        """,
        (scope_type, faculty_id, department_id, year, semester),
    )
    return int((cur.fetchone()[0] or 0) + 1)


def _row_to_profile(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    data = _row_dict(row)
    criteria_keys = _json_load(data.get("criteria_keys_json"), DEFAULT_CRITERIA_KEYS)
    weights = _json_load(data.get("weights_json"), {})
    pairwise_matrix = _json_load(data.get("pairwise_matrix_json"), [])
    name = data.get("profile_name") or data.get("name") or ""
    profile = {
        **data,
        "id": int(data.get("id") or 0),
        "name": str(name),
        "profile_name": str(name),
        "scope_type": str(data.get("scope_type") or "global"),
        "version": int(data.get("version") or 1),
        "criteria_keys": list(criteria_keys or DEFAULT_CRITERIA_KEYS),
        "pairwise_matrix": pairwise_matrix,
        "weights": {str(k): float(v) for k, v in dict(weights or {}).items()},
        "consistency_index": _optional_float(data.get("consistency_index")),
        "consistency_ratio": _optional_float(data.get("consistency_ratio")),
        "is_consistent": _bool(data.get("is_consistent", 1)),
        "is_active": _bool(data.get("is_active", 0)),
        "status": str(data.get("status") or ("active" if _bool(data.get("is_active", 0)) else "archived")),
    }
    return profile


def _row_dict(row: sqlite3.Row | tuple[Any, ...] | None) -> dict[str, Any]:
    if row is None:
        return {}
    if hasattr(row, "keys"):
        return {key: row[key] for key in row.keys()}
    return {str(idx): value for idx, value in enumerate(row)}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _json_load(value: Any, default: Any) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    try:
        return bool(int(value or 0))
    except (TypeError, ValueError):
        return bool(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _log_profile_action(
    cur: sqlite3.Cursor,
    profile_id: int,
    action: str,
    old_status: str | None,
    new_status: str | None,
    actor: str | None,
    message: str | None,
) -> None:
    cur.execute(
        """
        INSERT INTO ahp_profile_approval_logs (
            profile_id, action, old_status, new_status, actor, message, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (int(profile_id), str(action), old_status, new_status, actor, message, _now()),
    )


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
