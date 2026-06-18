# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from app.db.schema_compat import ensure_semester_planning_schema
from app.services.course_semester_availability_service import upsert_course_availability
from app.services.instructor_planning_service import (
    assign_course_instructor,
    create_instructor,
    upsert_instructor_availability,
)
from app.services.prerequisite_planning_service import create_prerequisite
from app.services.resource_planning_service import create_resource_requirement
from app.services.semester_planning_engine import generate_semester_plan, get_plan_run
from app.services.semester_planning_policy_service import (
    create_policy,
    resolve_policy,
    seed_default_policy,
    validate_policy,
)
from app.services.semester_planning_reporting_service import (
    export_constraint_violations,
    export_semester_plan,
    get_semester_plan_summary,
)


def _conn(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
        CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
        CREATE TABLE ders (
            ders_id INTEGER PRIMARY KEY,
            kod TEXT,
            ad TEXT,
            bolum_id INTEGER,
            fakulte_id INTEGER,
            DersTipi TEXT,
            kontenjan INTEGER
        );
        CREATE TABLE skor (
            skor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER,
            akademik_yil INTEGER,
            skor_top REAL
        );
        CREATE TABLE ders_kriterleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER,
            yil INTEGER,
            donem TEXT,
            kontenjan INTEGER,
            anket_dersi_secen INTEGER
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
        """
    )
    cur.execute("INSERT INTO fakulte VALUES (1, 'Mühendislik')")
    cur.execute("INSERT INTO bolum VALUES (10, 1, 'Bilgisayar')")
    for idx in range(1, 11):
        cur.execute(
            "INSERT INTO ders VALUES (?, ?, ?, 10, 1, 'Secmeli', ?)",
            (idx, f"BLM{idx:03d}", f"Ders {idx}", 40 + idx),
        )
        cur.execute("INSERT INTO skor (ders_id, akademik_yil, skor_top) VALUES (?, 2026, ?)", (idx, 100 - idx))
        cur.execute(
            "INSERT INTO ders_kriterleri (ders_id, yil, donem, kontenjan, anket_dersi_secen) VALUES (?, 2026, 'Guz', ?, ?)",
            (idx, 40 + idx, 20 + idx),
        )
    ensure_semester_planning_schema(conn)
    return conn


def test_default_policy_seed_and_validation():
    conn = _conn()
    policy = seed_default_policy(conn)
    assert policy["total_elective_target"] == 8
    assert policy["fall_min"] == 4
    assert policy["fall_max"] == 4
    assert policy["spring_min"] == 4
    assert policy["spring_max"] == 4

    bad = dict(policy)
    bad["fall_min"] = 5
    bad["fall_max"] = 4
    assert validate_policy(bad)["valid"] is False

    bad = dict(policy)
    bad["total_elective_target"] = 20
    assert validate_policy(bad)["valid"] is False


def test_policy_resolution_priority():
    conn = _conn()
    seed_default_policy(conn)
    faculty_policy = create_policy(
        conn,
        name="Fakülte 5+3",
        scope_type="faculty",
        faculty_id=1,
        year=2026,
        total_elective_target=8,
        fall_min=5,
        fall_max=5,
        spring_min=3,
        spring_max=3,
    )
    department_policy = create_policy(
        conn,
        name="Bölüm 3+5",
        scope_type="department",
        faculty_id=1,
        department_id=10,
        year=2026,
        total_elective_target=8,
        fall_min=3,
        fall_max=3,
        spring_min=5,
        spring_max=5,
    )
    resolved = resolve_policy(conn, year=2026, faculty_id=1, department_id=10)
    assert resolved["id"] == department_policy["id"]
    resolved_fac = resolve_policy(conn, year=2026, faculty_id=1, department_id=None)
    assert resolved_fac["id"] == faculty_policy["id"]


def test_planning_engine_default_policy_generates_4_plus_4_and_audit():
    conn = _conn()
    result = generate_semester_plan(conn, year=2026, faculty_id=1, department_id=10)
    assert result["ok"] is True
    assert len(result["fall_courses"]) == 4
    assert len(result["spring_courses"]) == 4
    assert result["plan_id"] is not None
    assert result["explanations"]
    assert len(result["alternative_plans"]) >= 3
    run = get_plan_run(conn, result["plan_id"])
    assert run and run["fall_count"] == 4 and run["spring_count"] == 4
    report = get_semester_plan_summary(conn, result["plan_id"])
    assert "report_text" in report
    assert "course_code" in export_semester_plan(conn, result["plan_id"])
    assert "constraint_type" in export_constraint_violations(conn, result["plan_id"])


def test_course_availability_blocks_forbidden_semester():
    conn = _conn()
    upsert_course_availability(conn, course_id=1, year=2026, allowed_fall=False, allowed_spring=True, preferred_semester="spring")
    result = generate_semester_plan(conn, year=2026, faculty_id=1, department_id=10)
    fall_ids = set(result["fall_course_ids"])
    spring_ids = set(result["spring_course_ids"])
    assert 1 not in fall_ids
    assert 1 in spring_ids


def test_instructor_availability_and_capacity_constraint():
    conn = _conn()
    policy = create_policy(
        conn,
        name="Hoca kontrollü",
        scope_type="department",
        faculty_id=1,
        department_id=10,
        year=2026,
        consider_instructor_availability=True,
    )
    instructor = create_instructor(conn, "Dr. Ada", faculty_id=1, department_id=10)
    assign_course_instructor(conn, 1, instructor["id"])
    upsert_instructor_availability(conn, instructor["id"], 2026, "fall", available=False, max_elective_courses=1)
    upsert_instructor_availability(conn, instructor["id"], 2026, "spring", available=True, max_elective_courses=1)
    upsert_course_availability(conn, 1, year=2026, allowed_fall=True, allowed_spring=True, preferred_semester="fall")
    result = generate_semester_plan(conn, year=2026, faculty_id=1, department_id=10, policy=policy)
    assert 1 not in result["fall_course_ids"]


def test_resource_and_prerequisite_violations_are_reported():
    conn = _conn()
    policy = create_policy(
        conn,
        name="Kaynak ve ön koşul kontrollü",
        scope_type="department",
        faculty_id=1,
        department_id=10,
        year=2026,
        consider_resource_constraints=True,
        consider_prerequisites=True,
        total_elective_target=2,
        fall_min=1,
        fall_max=1,
        spring_min=1,
        spring_max=1,
    )
    create_resource_requirement(conn, course_id=1, resource_type="computer_lab", hard_requirement=True)
    create_prerequisite(conn, course_id=2, prerequisite_course_id=1, prerequisite_type="hard")
    candidates = [{"course_id": 2, "score": 100}, {"course_id": 1, "score": 90}]
    result = generate_semester_plan(conn, year=2026, faculty_id=1, department_id=10, candidate_courses=candidates, policy=policy)
    types = {v["constraint_type"] for v in result["constraint_violations"]}
    assert "resource" in types or "prerequisite" in types


def test_demand_capacity_balance_and_same_course_repeat_policy():
    conn = _conn()
    policy = seed_default_policy(conn)
    candidates = [1, 1, 2, 3, 4, 5, 6, 7, 8]
    result = generate_semester_plan(conn, year=2026, faculty_id=1, department_id=10, candidate_courses=candidates, policy=policy)
    selected = result["fall_course_ids"] + result["spring_course_ids"]
    assert selected.count(1) == 1
    assert "demand_imbalance" in result["metrics"]
    assert "capacity_imbalance" in result["metrics"]


def test_api_smoke(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = _conn(path)
    conn.close()

    def _open():
        db = sqlite3.connect(path)
        db.row_factory = sqlite3.Row
        return db

    from app.api import routes
    from app.schemas.semester_planning import SemesterPlanGenerateRequest

    monkeypatch.setattr(routes, "_open_connection", _open)
    policies = routes.semester_planning_policies()
    assert policies["success"] is True
    generated = routes.semester_planning_generate(SemesterPlanGenerateRequest(year=2026, faculty_id=1, department_id=10))
    assert generated["success"] is True
    run_id = generated["data"]["plan_id"]
    detail = routes.semester_planning_run_detail(run_id)
    assert detail["success"] is True
    try:
        os.unlink(path)
    except OSError:
        pass


def test_ui_smoke_import_and_widget():
    try:
        import tkinter as tk

        from app.ui.tabs.semester_planning_page import SemesterPlanningPage

        root = tk.Tk()
        root.withdraw()
        page = SemesterPlanningPage(root, app=type("App", (), {"db": type("DB", (), {"conn": _conn()})()})())
        assert page is not None
        for tree in (page.fall_tree, page.spring_tree, page.unassigned_tree, page.violation_tree, page.scenario_tree):
            tree.insert("", "end", values=("eski",))
        page._last_plan_result = {"fall_courses": [{"course_id": 1}]}
        page._clear_plan_result_views()
        assert page._last_plan_result is None
        assert all(
            not tree.get_children()
            for tree in (page.fall_tree, page.spring_tree, page.unassigned_tree, page.violation_tree, page.scenario_tree)
        )
        root.destroy()
    except tk.TclError:
        pytest.skip("Tk display yok; UI smoke testi atlandı.")
