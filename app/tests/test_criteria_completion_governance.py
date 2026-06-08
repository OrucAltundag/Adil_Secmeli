# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sqlite3
import tempfile

from app.api import routes
from app.db.schema_compat import ensure_reporting_schema
from app.services.criteria_completion_policy_service import (
    create_completion_policy,
    resolve_policy,
)
from app.services.criteria_completion_service import (
    can_run_algorithm,
    get_completion_history,
    get_completion_matrix,
    get_completion_summary,
)
from app.services.criteria_override_service import approve_override, request_override
from app.services.criteria_task_service import (
    generate_tasks_for_missing_criteria,
    get_tasks,
)
from app.services.criteria_validation_service import validate_criterion_value


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
            DersTipi TEXT
        );
        CREATE TABLE mufredat (
            mufredat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fakulte_id INTEGER,
            akademik_yil INTEGER,
            bolum_id INTEGER,
            donem TEXT,
            durum TEXT,
            versiyon INTEGER
        );
        CREATE TABLE mufredat_ders (
            mders_id INTEGER PRIMARY KEY AUTOINCREMENT,
            mufredat_id INTEGER,
            ders_id INTEGER
        );
        CREATE TABLE ders_kriterleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER,
            yil INTEGER,
            donem TEXT,
            toplam_ogrenci INTEGER,
            gecen_ogrenci INTEGER,
            basari_ortalamasi REAL,
            kontenjan INTEGER,
            kayitli_ogrenci INTEGER,
            anket_katilimci INTEGER,
            anket_dersi_secen INTEGER
        );
        """
    )
    conn.execute("INSERT INTO fakulte VALUES (1, 'Muhendislik')")
    conn.execute("INSERT INTO bolum VALUES (10, 1, 'Bilgisayar')")
    conn.executemany(
        "INSERT INTO ders VALUES (?, 10, 1, ?, ?, 'Secmeli')",
        [
            (101, "BLM101", "Algoritmalar"),
            (102, "BLM102", "Veri Yapilari"),
            (103, "BLM103", "Yapay Zeka"),
        ],
    )
    conn.execute(
        """
        INSERT INTO mufredat (fakulte_id, akademik_yil, bolum_id, donem, durum, versiyon)
        VALUES (1, 2026, 10, 'Guz', 'Resmi', 1)
        """
    )
    mid = conn.execute("SELECT mufredat_id FROM mufredat").fetchone()[0]
    for course_id in (101, 102, 103):
        conn.execute("INSERT INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?)", (mid, course_id))
    ensure_reporting_schema(conn)
    conn.commit()
    return path, conn


def _insert_criteria(
    conn: sqlite3.Connection,
    course_id: int,
    total: int | None = 100,
    passed: int | None = 80,
    average: float | None = 82.0,
    capacity: int | None = 50,
    enrolled: int | None = 45,
):
    conn.execute(
        """
        INSERT OR REPLACE INTO ders_kriterleri (
            ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci,
            basari_ortalamasi, kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen
        )
        VALUES (?, 2026, 'Guz', ?, ?, ?, ?, ?, 100, 50)
        """,
        (course_id, total, passed, average, capacity, enrolled),
    )


def test_completion_ratio_and_levels():
    path, conn = _db()
    try:
        empty = get_completion_summary(conn, "department", 2026, faculty_id=1, department_id=10, semester="Guz")
        assert empty["completion_ratio"] == 0.0
        assert empty["completion_level"] == "not_started"

        _insert_criteria(conn, 101, total=100, passed=None, average=None, capacity=None, enrolled=None)
        low = get_completion_summary(conn, "department", 2026, faculty_id=1, department_id=10, semester="Guz")
        assert 0.0 < low["completion_ratio"] < 0.50
        assert low["completion_level"] == "low_partial"

        _insert_criteria(conn, 102)
        _insert_criteria(conn, 103, total=100, passed=80, average=82.0, capacity=None, enrolled=None)
        medium = get_completion_summary(conn, "department", 2026, faculty_id=1, department_id=10, semester="Guz")
        assert medium["completion_level"] in {"medium_partial", "high_partial"}

        _insert_criteria(conn, 101, total=100, passed=80, average=82.0, capacity=50, enrolled=None)
        _insert_criteria(conn, 103)
        high = get_completion_summary(conn, "department", 2026, faculty_id=1, department_id=10, semester="Guz")
        assert high["completion_ratio"] < 1.0
        assert high["completion_level"] == "high_partial"
    finally:
        conn.close()
        os.unlink(path)


def test_completed_matrix_and_algorithm_gate():
    path, conn = _db()
    try:
        for course_id in (101, 102, 103):
            _insert_criteria(conn, course_id)
        summary = get_completion_summary(conn, "department", 2026, faculty_id=1, department_id=10, semester="Guz")
        assert summary["completion_ratio"] == 1.0
        assert summary["completion_level"] in {"completed", "completed_with_warnings"}
        assert summary["can_run_algorithm"] is True
        matrix = get_completion_matrix(conn, "department", 2026, faculty_id=1, department_id=10, semester="Guz")
        assert any(row["criterion_key"] == "average_grade" and row["is_valid"] for row in matrix)
        gate = can_run_algorithm(conn, 2026, faculty_id=1, department_id=10, semester="Guz")
        assert gate["can_run"] is True
    finally:
        conn.close()
        os.unlink(path)


def test_validation_invalid_values_block_completion():
    path, conn = _db()
    try:
        _insert_criteria(conn, 101, total=10, passed=15)
        result = get_completion_summary(conn, "department", 2026, faculty_id=1, department_id=10, semester="Guz")
        assert result["invalid_required_fields"] >= 1
        assert result["can_run_algorithm"] is False
        assert any(issue["issue_type"] == "inconsistent_values" for issue in result["validation_issues"])

        assert validate_criterion_value("capacity", -1).status == "invalid"
        assert validate_criterion_value("average_grade", 120).status == "invalid"
        assert validate_criterion_value("average_grade", 85).status == "valid"
    finally:
        conn.close()
        os.unlink(path)


def test_policy_priority_and_default_creation():
    path, conn = _db()
    try:
        default_policy = resolve_policy(conn, "department", 2026, faculty_id=1, department_id=10)
        assert default_policy["required_fields"]
        create_completion_policy(
            conn,
            "Fakulte Gevsek",
            scope_type="faculty",
            faculty_id=1,
            year=2026,
            required_completion_ratio=0.50,
        )
        department_policy = create_completion_policy(
            conn,
            "Bolum Siki",
            scope_type="department",
            faculty_id=1,
            department_id=10,
            year=2026,
            required_completion_ratio=0.95,
        )
        resolved = resolve_policy(conn, "department", 2026, faculty_id=1, department_id=10)
        assert resolved["id"] == department_policy["id"]
        assert float(resolved["required_completion_ratio"]) == 0.95
    finally:
        conn.close()
        os.unlink(path)


def test_missing_data_risk_tasks_and_history():
    path, conn = _db()
    try:
        _insert_criteria(conn, 101, average=None)
        first = get_completion_summary(conn, "department", 2026, faculty_id=1, department_id=10, semester="Guz")
        assert first["missing_data_risk"]["risk_level"] in {"medium", "high", "critical"}
        tasks = generate_tasks_for_missing_criteria(conn, first)
        conn.commit()
        assert tasks
        assert get_tasks(conn, year=2026, faculty_id=1)
        for course_id in (101, 102, 103):
            _insert_criteria(conn, course_id)
        second = get_completion_summary(conn, "department", 2026, faculty_id=1, department_id=10, semester="Guz")
        assert second["completion_ratio"] >= first["completion_ratio"]
        history = get_completion_history(conn, scope_type="department", year=2026, faculty_id=1, department_id=10)
        assert history
    finally:
        conn.close()
        os.unlink(path)


def test_override_pending_and_approved_gate():
    path, conn = _db()
    try:
        _insert_criteria(conn, 101)
        gate = can_run_algorithm(conn, 2026, faculty_id=1, department_id=10, semester="Guz")
        assert gate["can_run"] is False
        override = request_override(
            conn,
            "department",
            2026,
            faculty_id=1,
            department_id=10,
            semester="Guz",
            reason="Kurul kararıyla eksik veriyle çalıştırılacak.",
            requested_by="bolum_baskani",
        )
        conn.commit()
        assert override["approval_status"] == "pending"
        assert can_run_algorithm(conn, 2026, faculty_id=1, department_id=10, semester="Guz")["can_run"] is False
        approve_override(conn, override["id"], approved_by="dekan")
        conn.commit()
        approved_gate = can_run_algorithm(conn, 2026, faculty_id=1, department_id=10, semester="Guz")
        assert approved_gate["can_run"] is True
        assert approved_gate["override_active"] is True
    finally:
        conn.close()
        os.unlink(path)


def test_criteria_completion_api_smoke(monkeypatch):
    path, conn = _db()
    try:
        for course_id in (101, 102, 103):
            _insert_criteria(conn, course_id)
        conn.commit()
    finally:
        conn.close()
    monkeypatch.setattr(routes, "_get_db_path", lambda: path)
    try:
        summary = routes.kriter_tamlik(year=2026, faculty_id=1, department_id=10, semester="Guz")
        assert summary["completion_ratio"] == 1.0
        matrix = routes.kriter_tamlik_matrix(year=2026, faculty_id=1, department_id=10, semester="Guz")
        assert matrix["data"]
        gate = routes.kriter_tamlik_can_run(year=2026, faculty_id=1, department_id=10, semester="Guz")
        assert gate["can_run"] is True
    finally:
        os.unlink(path)


def test_criteria_page_completion_panel_importable():
    from app.ui.tabs.criteria_page import CriteriaPage

    assert CriteriaPage is not None
