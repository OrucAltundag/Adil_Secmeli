# -*- coding: utf-8 -*-
"""AHP profil, karar çalışması ve sensitivity raporlama servisi."""

from __future__ import annotations

import csv
import io
import sqlite3
from typing import Any

from app.db.schema_compat import ensure_ahp_governance_schema
from app.services.ahp_impact_explanation_service import explain_weight_profile
from app.services.ahp_profile_service import get_profile, resolve_active_profile
from app.services.ahp_sensitivity_service import get_latest_sensitivity_for_run


def get_ahp_profile_report(conn: sqlite3.Connection, profile_id: int) -> dict[str, Any]:
    ensure_ahp_governance_schema(conn, commit=False)
    profile = get_profile(conn, profile_id)
    if not profile:
        raise ValueError(f"AHP profili bulunamadı: {profile_id}")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, action, old_status, new_status, actor, message, created_at
        FROM ahp_profile_approval_logs
        WHERE profile_id=?
        ORDER BY id DESC
        """,
        (int(profile_id),),
    )
    logs = [_row_dict(row) for row in cur.fetchall()]
    cur.execute(
        """
        SELECT id, run_name, year, faculty_id, department_id, semester, status, started_at
        FROM decision_runs
        WHERE ahp_profile_id=?
        ORDER BY id DESC
        """,
        (int(profile_id),),
    )
    runs = [_row_dict(row) for row in cur.fetchall()]
    return {
        "profile": profile,
        "impact": explain_weight_profile(conn, int(profile_id)),
        "approval_logs": logs,
        "decision_runs": runs,
    }


def get_active_ahp_profile_summary(
    conn: sqlite3.Connection,
    *,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
) -> dict[str, Any]:
    profile = resolve_active_profile(
        conn,
        year=year,
        faculty_id=faculty_id,
        department_id=department_id,
        semester=semester,
    )
    return explain_weight_profile(conn, int(profile["id"]))


def get_decision_run_ahp_summary(conn: sqlite3.Connection, run_id: int) -> dict[str, Any]:
    ensure_ahp_governance_schema(conn, commit=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM decision_runs WHERE id=?", (int(run_id),))
    run = cur.fetchone()
    if not run:
        raise ValueError(f"Karar çalışması bulunamadı: {run_id}")
    run_dict = _row_dict(run)
    profile = get_profile(conn, int(run_dict["ahp_profile_id"])) if run_dict.get("ahp_profile_id") else None
    return {
        "decision_run": run_dict,
        "profile": profile,
        "weights_snapshot_json": run_dict.get("ahp_weights_snapshot_json"),
        "consistency_ratio": run_dict.get("ahp_consistency_ratio"),
        "sensitivity": get_latest_sensitivity_for_run(conn, int(run_id)),
    }


def compare_ahp_profiles(conn: sqlite3.Connection, profile_a_id: int, profile_b_id: int) -> dict[str, Any]:
    a = get_profile(conn, profile_a_id)
    b = get_profile(conn, profile_b_id)
    if not a or not b:
        raise ValueError("Karşılaştırılacak AHP profillerinden biri bulunamadı.")
    keys = sorted(set(a.get("weights", {})) | set(b.get("weights", {})))
    rows = []
    for key in keys:
        av = float(a.get("weights", {}).get(key, 0.0))
        bv = float(b.get("weights", {}).get(key, 0.0))
        rows.append(
            {
                "criterion_key": key,
                "profile_a_weight": av,
                "profile_b_weight": bv,
                "delta": bv - av,
                "delta_percent_point": round((bv - av) * 100.0, 2),
            }
        )
    return {"profile_a": a, "profile_b": b, "differences": rows}


def export_ahp_profile_matrix(conn: sqlite3.Connection, profile_id: int, format: str = "csv") -> str:
    profile = get_profile(conn, profile_id)
    if not profile:
        raise ValueError(f"AHP profili bulunamadı: {profile_id}")
    keys = list(profile.get("criteria_keys") or [])
    matrix = list(profile.get("pairwise_matrix") or [])
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Kriter", *keys])
    for idx, key in enumerate(keys):
        writer.writerow([key, *(matrix[idx] if idx < len(matrix) else [])])
    return output.getvalue()


def export_ahp_sensitivity_report(conn: sqlite3.Connection, run_id: int, format: str = "csv") -> str:
    result = get_latest_sensitivity_for_run(conn, run_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Ders ID", "Baz Skor", "Min Skor", "Max Skor", "Skor Aralığı", "Kararlılık", "Açıklama"])
    if result:
        for item in result.get("items", []):
            writer.writerow(
                [
                    item.get("course_id"),
                    item.get("base_score"),
                    item.get("min_score"),
                    item.get("max_score"),
                    item.get("score_range"),
                    item.get("stability_level"),
                    item.get("explanation"),
                ]
            )
    return output.getvalue()


def _row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}
