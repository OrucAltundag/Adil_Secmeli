# -*- coding: utf-8 -*-
"""Yıllık müfredat/havuz durumu, repository ve bütünlük kontrolü testleri."""

from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from app.repositories.curriculum_repository import (
    check_course_in_fall_curriculum,
    check_course_in_spring_curriculum,
    course_exists_in_any_term,
    get_fall_curriculum_courses,
    get_period_planning_summary,
    get_pool_courses_with_curriculum_flags,
    get_pool_courses_with_curriculum_status,
    get_spring_curriculum_courses,
    get_unified_pool_by_year,
    save_period_planning_result,
)
from app.services.course_curriculum_status_service import (
    STATUS_CONFLICT,
    STATUS_IN_FALL,
    STATUS_IN_POOL,
    get_course_yearly_curriculum_status,
    get_courses_status_batch,
)
from app.services.course_semester_availability_service import (
    get_courses_availability_batch,
    upsert_course_availability,
)
from app.services.semester_planning_engine import generate_semester_plan
from app.services.yearly_curriculum_integrity_service import (
    check_yearly_curriculum_integrity,
)


def _build_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
        CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
        CREATE TABLE ders (
            ders_id INTEGER PRIMARY KEY, bolum_id INTEGER, fakulte_id INTEGER,
            ad TEXT, kod TEXT, kontenjan INTEGER, kredi INTEGER, akts INTEGER, DersTipi TEXT
        );
        CREATE TABLE mufredat (
            mufredat_id INTEGER PRIMARY KEY, fakulte_id INTEGER, akademik_yil INTEGER,
            bolum_id INTEGER, donem TEXT, durum TEXT, versiyon INTEGER
        );
        CREATE TABLE mufredat_ders (
            mders_id INTEGER PRIMARY KEY AUTOINCREMENT, mufredat_id INTEGER, ders_id INTEGER
        );
        CREATE TABLE havuz (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id TEXT, yil INTEGER,
            fakulte_id INTEGER, bolum_id INTEGER, donem TEXT, statu INTEGER,
            sayac INTEGER, skor REAL, ders_adi TEXT
        );
        CREATE TABLE skor (
            skor_id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id INTEGER,
            akademik_yil INTEGER, donem TEXT, skor_top REAL
        );
        """
    )
    cur.execute("INSERT INTO fakulte VALUES (1, 'Muh')")
    cur.execute("INSERT INTO bolum VALUES (10, 1, 'Bilgisayar')")
    # 1 güz dersi (101), 1 bahar dersi (102), 1 çakışma (103 her iki dönem),
    # 1 sadece havuz (104), 1 havuz dışı (105)
    for cid in (101, 102, 103, 104, 105):
        cur.execute(
            "INSERT INTO ders VALUES (?, 10, 1, ?, ?, 40, 3, 5, 'Secmeli')",
            (cid, f"Ders-{cid}", f"DRS{cid}"),
        )
    cur.executemany(
        "INSERT INTO mufredat (mufredat_id, fakulte_id, akademik_yil, bolum_id, donem, durum, versiyon) "
        "VALUES (?, 1, 2024, 10, ?, 'Resmi', 1)",
        [(1, "Guz"), (2, "Bahar")],
    )
    cur.executemany(
        "INSERT INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?)",
        [(1, 101), (1, 103), (2, 102), (2, 103)],
    )
    for cid, term, statu in (
        (101, "Guz", 1), (102, "Bahar", 1), (103, "Guz", 1),
        (104, "Guz", 0), (104, "Bahar", 0),
    ):
        cur.execute(
            "INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, donem, statu, sayac, skor, ders_adi) "
            "VALUES (?, 2024, 1, 10, ?, ?, 0, 70.0, ?)",
            (str(cid), term, statu, f"Ders-{cid}"),
        )
    for cid in (101, 102, 103, 104, 105):
        cur.execute(
            "INSERT INTO skor (ders_id, akademik_yil, donem, skor_top) VALUES (?, 2024, 'Guz', ?)",
            (cid, 50.0 + cid),
        )
    conn.commit()
    conn.close()
    return path


@pytest.fixture()
def conn():
    path = _build_db()
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    yield connection
    connection.close()
    try:
        os.unlink(path)
    except OSError:
        pass


def test_status_in_fall_blocks_readd(conn):
    status = get_course_yearly_curriculum_status(conn, 2024, 101, department_id=10)
    assert status["status_code"] == STATUS_IN_FALL
    assert status["in_fall_curriculum"] is True
    assert status["in_yearly_curriculum"] is True
    assert status["can_be_added_to_fall"] is False
    assert status["can_be_added_to_spring"] is False


def test_availability_batch_honors_scope_row(conn):
    # 104 havuzda, müfredatta yok -> normalde her iki döneme eklenebilir.
    # Bahar uygunluğunu kapatan bir kayıt girince batch bunu yansıtmalı.
    upsert_course_availability(
        conn, 104, year=2024, faculty_id=1, department_id=10,
        allowed_fall=True, allowed_spring=False,
    )
    conn.commit()
    avail = get_courses_availability_batch(conn, [104, 105], year=2024, department_id=10, faculty_id=1)
    assert avail[104]["allowed_fall"] is True
    assert avail[104]["allowed_spring"] is False
    # 105 için kayıt yok -> varsayılan (her iki dönem açık)
    assert avail[105]["allowed_spring"] is True

    # Toplu durum hesabı bu uygunluğu kullanmalı.
    status = get_courses_status_batch(conn, 2024, [104], department_id=10, faculty_id=1)
    assert status[104]["can_be_added_to_fall"] is True
    assert status[104]["can_be_added_to_spring"] is False


def test_status_conflict_both_terms(conn):
    status = get_course_yearly_curriculum_status(conn, 2024, 103, department_id=10)
    assert status["status_code"] == STATUS_CONFLICT
    assert status["in_fall_curriculum"] and status["in_spring_curriculum"]


def test_status_pool_only_is_new_candidate(conn):
    status = get_course_yearly_curriculum_status(conn, 2024, 104, department_id=10)
    assert status["status_code"] == STATUS_IN_POOL
    assert status["in_yearly_curriculum"] is False
    assert status["can_be_added_to_fall"] is True


def test_pool_courses_with_status_labels(conn):
    rows = {r["course_id"]: r for r in get_pool_courses_with_curriculum_status(conn, 2024, department_id=10)}
    assert rows[101]["status_code"] == STATUS_IN_FALL
    assert rows[104]["status_code"] == STATUS_IN_POOL


def test_period_summary_counts(conn):
    summary = get_period_planning_summary(conn, 2024, department_id=10)
    assert summary["fall_count"] == 2   # 101, 103
    assert summary["spring_count"] == 2  # 102, 103
    assert summary["conflict_count"] == 1  # 103
    assert summary["yearly_total"] == 3  # 101,102,103
    assert summary["new_suggestion_count"] == 1  # 104


def test_fall_spring_helpers(conn):
    fall = {r["course_id"] for r in get_fall_curriculum_courses(conn, 2024, department_id=10)}
    spring = {r["course_id"] for r in get_spring_curriculum_courses(conn, 2024, department_id=10)}
    assert fall == {101, 103}
    assert spring == {102, 103}


def test_course_exists_in_any_term(conn):
    assert course_exists_in_any_term(conn, 2024, 101, department_id=10) is True
    assert course_exists_in_any_term(conn, 2024, 104, department_id=10) is False


def test_integrity_detects_conflict(conn):
    report = check_yearly_curriculum_integrity(conn, 2024, department_id=10)
    assert report["ok"] is False
    types = {i["type"] for i in report["issues"]}
    assert "duplicate_in_both_terms" in types
    conflict = next(i for i in report["issues"] if i["type"] == "duplicate_in_both_terms")
    assert 103 in conflict["course_ids"]


def test_save_rejects_cross_term_overlap(conn):
    with pytest.raises(ValueError):
        save_period_planning_result(
            conn, 2024, faculty_id=1, department_id=10,
            fall_course_ids=[201], spring_course_ids=[201],
        )


def test_save_writes_curriculum(conn):
    result = save_period_planning_result(
        conn, 2024, faculty_id=1, department_id=10,
        fall_course_ids=[101, 104], spring_course_ids=[102],
    )
    conn.commit()
    assert result["ok"] is True
    fall = {r["course_id"] for r in get_fall_curriculum_courses(conn, 2024, department_id=10)}
    assert fall == {101, 104}


def test_unified_pool_bundle(conn):
    bundle = get_unified_pool_by_year(conn, 2024, department_id=10)
    assert bundle["year"] == 2024
    assert {r["course_id"] for r in bundle["fall_curriculum"]} == {101, 103}
    assert {r["course_id"] for r in bundle["spring_curriculum"]} == {102, 103}
    assert bundle["summary"]["conflict_count"] == 1
    pool_by_id = {r["course_id"]: r for r in bundle["pool_courses"]}
    assert set(pool_by_id) == {101, 102, 103, 104, 105}
    # kredi/akts + bayraklar + öneri/karar alanları mevcut
    assert pool_by_id[101]["credit"] == 3
    assert pool_by_id[101]["ects"] == 5
    assert pool_by_id[101]["final_decision"] == "Güz müfredatında mevcut"
    assert pool_by_id[104]["recommendation_status"] == "Müfredata önerilebilir"
    assert pool_by_id[105]["catalog_candidate"] is True
    assert pool_by_id[105]["pool_status"] == 0
    assert pool_by_id[105]["recommendation_status"] == "Müfredata önerilebilir"
    assert "explanation" in pool_by_id[101]


def test_pool_flags_and_checks(conn):
    flags = {r["course_id"]: r for r in get_pool_courses_with_curriculum_flags(conn, 2024, department_id=10)}
    assert flags[103]["status_code"] == STATUS_CONFLICT
    assert check_course_in_fall_curriculum(conn, 2024, 101, department_id=10) is True
    assert check_course_in_spring_curriculum(conn, 2024, 101, department_id=10) is False
    assert check_course_in_spring_curriculum(conn, 2024, 102, department_id=10) is True


def test_engine_respect_existing_curriculum_filters(conn):
    policy = {
        "id": None,
        "total_elective_target": 4,
        "fall_min": 2, "fall_max": 2,
        "spring_min": 2, "spring_max": 2,
        "same_course_repeat_policy": "disallow",
        "consider_course_availability": False,
        "consider_instructor_availability": False,
        "consider_resource_constraints": False,
        "consider_prerequisites": False,
        "consider_time_conflicts": False,
        "hard_constraint_policy": "soft",
    }
    result = generate_semester_plan(
        conn, year=2024, faculty_id=1, department_id=10,
        candidate_courses=[{"course_id": c, "score": float(c)} for c in (101, 102, 103, 104, 105)],
        policy=policy, persist=False, generate_alternatives=False,
        respect_existing_curriculum=True,
    )
    already = set(result["already_in_curriculum_ids"])
    assert already == {101, 102, 103}
    placed = {int(a["course_id"]) for a in result["fall_courses"] + result["spring_courses"]}
    assert placed.isdisjoint({101, 102, 103})
