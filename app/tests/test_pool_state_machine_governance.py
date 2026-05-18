# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from app.api import routes
from app.db.schema_compat import ensure_reporting_schema
from app.services.havuz_karar import calculate_next_status
from app.services.pool_state_machine_service import (
    approve_state_approval,
    create_course_state_override,
    evaluate_course_state_transition,
    list_pending_approvals,
    list_state_transitions,
    save_state_transition,
    upsert_governance_flags,
)
from app.services.pool_state_policy_service import (
    create_pool_state_policy,
    resolve_policy,
)


def _db() -> tuple[str, sqlite3.Connection]:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
        CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
        CREATE TABLE ders (
            ders_id INTEGER PRIMARY KEY,
            bolum_id INTEGER,
            fakulte_id INTEGER,
            kod TEXT,
            ad TEXT,
            DersTipi TEXT,
            tip TEXT
        );
        CREATE TABLE havuz (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER,
            fakulte_id INTEGER,
            bolum_id INTEGER,
            yil INTEGER,
            donem TEXT,
            statu INTEGER,
            sayac INTEGER,
            skor REAL,
            ders_adi TEXT
        );
        """
    )
    conn.execute("INSERT INTO fakulte VALUES (1, 'Muhendislik')")
    conn.execute("INSERT INTO bolum VALUES (10, 1, 'Bilgisayar')")
    conn.executemany(
        "INSERT INTO ders VALUES (?, 10, 1, ?, ?, ?, ?)",
        [
            (101, "BLM101", "Secmeli A", "Secmeli", "Secmeli"),
            (102, "BLM102", "Zorunlu B", "Zorunlu", "Zorunlu"),
            (103, "BLM103", "Secmeli C", "Secmeli", "Secmeli"),
        ],
    )
    conn.executemany(
        "INSERT INTO havuz (ders_id, fakulte_id, bolum_id, yil, donem, statu, sayac, skor, ders_adi) VALUES (?, 1, 10, 2026, 'Guz', ?, ?, ?, ?)",
        [
            (101, -1, 2, 20.0, "Secmeli A"),
            (102, 1, 0, 20.0, "Zorunlu B"),
            (103, 0, 2, 82.0, "Secmeli C"),
        ],
    )
    ensure_reporting_schema(conn)
    conn.commit()
    return path, conn


def _base_context(**overrides):
    data = {
        "course_id": 101,
        "year": 2026,
        "semester": "Guz",
        "faculty_id": 1,
        "department_id": 10,
        "current_status": -1,
        "counter_before": 2,
        "years_in_rest": 2,
        "topsis_score": 20.0,
        "trend_label": "falling",
        "trend_score": 0.2,
        "data_confidence_score": 0.90,
        "data_confidence_level": "high",
        "in_mufredat_this_year": False,
    }
    data.update(overrides)
    return data


def test_pool_policy_resolution_priority():
    path, conn = _db()
    try:
        default = resolve_policy(conn, 2026, faculty_id=1, department_id=10, semester="Guz")
        assert default["scope_type"] == "global"
        faculty = create_pool_state_policy(conn, "Fakulte", scope_type="faculty", faculty_id=1, year=2026, low_score_threshold=40)
        department = create_pool_state_policy(
            conn,
            "Bolum",
            scope_type="department",
            faculty_id=1,
            department_id=10,
            year=2026,
            low_score_threshold=30,
        )
        resolved = resolve_policy(conn, 2026, faculty_id=1, department_id=10, semester="Guz")
        assert resolved["id"] == department["id"]
        assert resolved["id"] != faculty["id"]
    finally:
        conn.close()
        os.unlink(path)


def test_protected_courses_are_not_cancelled():
    path, conn = _db()
    try:
        upsert_governance_flags(conn, 102, required_course_flag=True)
        result = evaluate_course_state_transition(
            conn,
            _base_context(course_id=102, current_status=1, counter_before=1, topsis_score=15, data_confidence_score=0.95),
        )
        assert result["final_status"] != -2
        assert result["lifecycle_label"] == "protected"
        assert "Koruma" in result["explanation"]

        upsert_governance_flags(conn, 101, accreditation_flag=True, strategic_flag=True)
        result = evaluate_course_state_transition(conn, _base_context())
        assert result["final_status"] != -2
        assert result["lifecycle_label"] == "protected"
    finally:
        conn.close()
        os.unlink(path)


def test_new_course_grace_and_low_confidence_block_hard_decisions():
    path, conn = _db()
    try:
        upsert_governance_flags(conn, 101, new_course_flag=True, first_offered_year=2025)
        result = evaluate_course_state_transition(conn, _base_context(year=2026))
        assert result["recommended_status"] != -2
        assert result["final_status"] != -2
        assert "Grace period" in result["explanation"]

        upsert_governance_flags(conn, 101, new_course_flag=False, first_offered_year=None)
        low_conf = evaluate_course_state_transition(conn, _base_context(data_confidence_score=0.20, data_confidence_level="low"))
        assert low_conf["final_status"] != -2
        assert "veri güveni" in low_conf["explanation"].lower()
    finally:
        conn.close()
        os.unlink(path)


def test_cancel_approval_and_transition_history():
    path, conn = _db()
    try:
        result = evaluate_course_state_transition(conn, _base_context())
        assert result["recommended_status"] == -2
        assert result["final_status"] != -2
        assert result["approval_required"] is True
        transition_id = save_state_transition(conn, result)
        approvals = list_pending_approvals(conn, year=2026)
        assert approvals and approvals[0]["transition_id"] == transition_id
        history = list_state_transitions(conn, course_id=101)
        assert history
        assert history[0]["policy_id"]
        assert history[0]["explanation"]
        assert history[0]["governance_flags_snapshot_json"]

        approved = approve_state_approval(conn, int(approvals[0]["id"]), reviewed_by="kurul", review_note="uygun")
        assert approved["approval_status"] == "approved"
        row = conn.execute("SELECT statu, final_status FROM havuz WHERE ders_id = 101 AND yil = 2026").fetchone()
        assert int(row["statu"]) == -2
        assert int(row["final_status"]) == -2
    finally:
        conn.close()
        os.unlink(path)


def test_override_and_reactivation_rules():
    path, conn = _db()
    try:
        with pytest.raises(ValueError):
            create_course_state_override(conn, 101, 2026, 1, "")
        create_course_state_override(conn, 101, 2026, 1, "Akreditasyon çıktısı ile ilişkili", approved_by="kurul")
        result = evaluate_course_state_transition(conn, _base_context(current_status=0, years_in_pool=2))
        assert result["final_status"] == 1
        assert result["override_applied"] is True

        reactivation = evaluate_course_state_transition(
            conn,
            _base_context(
                course_id=103,
                current_status=0,
                counter_before=2,
                years_in_pool=2,
                topsis_score=85.0,
                trend_label="rising",
                data_confidence_score=0.95,
            ),
        )
        assert reactivation["recommended_status"] == 1
        assert reactivation["lifecycle_label"] == "reactivation_candidate"

        cancelled = evaluate_course_state_transition(
            conn,
            _base_context(course_id=103, current_status=-2, topsis_score=95.0, trend_label="rising", data_confidence_score=0.95),
        )
        assert cancelled["final_status"] == -2
    finally:
        conn.close()
        os.unlink(path)


def test_backward_compatibility_and_api_smoke(monkeypatch):
    assert calculate_next_status(1, 1, False) == (-2, 2)
    path, conn = _db()
    try:
        result = evaluate_course_state_transition(conn, _base_context())
        save_state_transition(conn, result)
        conn.commit()
    finally:
        conn.close()
    monkeypatch.setattr(routes, "_get_db_path", lambda: path)
    try:
        summary = routes.havuz_lifecycle_summary(year=2026, faculty_id=1, department_id=10, semester="Guz")
        assert summary["total_count"] >= 1
        transitions = routes.havuz_state_transition_list(year=2026, faculty_id=1)
        assert transitions["data"]
        approvals = routes.havuz_approvals(year=2026, faculty_id=1)
        assert approvals["data"]
    finally:
        os.unlink(path)


def test_decision_center_pool_lifecycle_importable():
    from app.ui.tabs.decision_center_page import DecisionCenterPage

    assert DecisionCenterPage is not None
