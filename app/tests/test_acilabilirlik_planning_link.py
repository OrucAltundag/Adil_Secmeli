# -*- coding: utf-8 -*-
"""Faz 4: Açılabilirlik skoru → Dönem Planlama aday skorlaması bağı."""

from __future__ import annotations

import sqlite3

from app.services.semester_planning_engine import (
    _fetch_candidate_courses,
    _latest_acilabilirlik_scores,
)


def _build_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
        CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
        CREATE TABLE ders (
            ders_id INTEGER PRIMARY KEY, kod TEXT, ad TEXT,
            bolum_id INTEGER, fakulte_id INTEGER, DersTipi TEXT, kontenjan INTEGER
        );
        CREATE TABLE skor (
            skor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER, akademik_yil INTEGER, skor_top REAL
        );
        CREATE TABLE decision_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year INTEGER, faculty_id INTEGER, department_id INTEGER
        );
        CREATE TABLE course_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_run_id INTEGER, course_id INTEGER, year INTEGER,
            topsis_score REAL, acilabilirlik_score REAL
        );
        """
    )
    cur.execute("INSERT INTO fakulte VALUES (1, 'Mühendislik')")
    cur.execute("INSERT INTO bolum VALUES (10, 1, 'Bilgisayar')")
    # iki secmeli ders
    cur.execute("INSERT INTO ders VALUES (1, 'BLM1', 'Ders 1', 10, 1, 'Secmeli', 40)")
    cur.execute("INSERT INTO ders VALUES (2, 'BLM2', 'Ders 2', 10, 1, 'Secmeli', 40)")
    # skor tablosu: Ders 1 yuksek (90), Ders 2 dusuk (30)
    cur.execute("INSERT INTO skor (ders_id, akademik_yil, skor_top) VALUES (1, 2022, 90)")
    cur.execute("INSERT INTO skor (ders_id, akademik_yil, skor_top) VALUES (2, 2022, 30)")
    conn.commit()
    return conn


def _add_decision_run(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("INSERT INTO decision_runs (year, faculty_id) VALUES (2022, 1)")
    run_id = int(cur.lastrowid)
    # Açılabilirlik skoru skor tablosunu TERSINE cevirir:
    # Ders 1 dusuk (20), Ders 2 yuksek (85)
    cur.execute(
        "INSERT INTO course_decisions (decision_run_id, course_id, year, topsis_score, acilabilirlik_score) "
        "VALUES (?, 1, 2022, 90, 20)",
        (run_id,),
    )
    cur.execute(
        "INSERT INTO course_decisions (decision_run_id, course_id, year, topsis_score, acilabilirlik_score) "
        "VALUES (?, 2, 2022, 30, 85)",
        (run_id,),
    )
    conn.commit()


def test_no_decision_run_falls_back_to_skor():
    conn = _build_db()
    assert _latest_acilabilirlik_scores(conn, 2022, faculty_id=1) == {}
    candidates = _fetch_candidate_courses(conn, year=2022, faculty_id=1)
    by_id = {c["course_id"]: c for c in candidates}
    assert by_id[1]["score"] == 90.0
    assert by_id[1]["score_source"] == "skor"
    assert by_id[2]["score"] == 30.0


def test_decision_run_acilabilirlik_overrides_skor():
    conn = _build_db()
    _add_decision_run(conn)
    acil = _latest_acilabilirlik_scores(conn, 2022, faculty_id=1)
    assert acil == {1: 20.0, 2: 85.0}
    candidates = _fetch_candidate_courses(conn, year=2022, faculty_id=1)
    by_id = {c["course_id"]: c for c in candidates}
    # Açılabilirlik skor tablosunu ezmeli: Ders 1 -> 20, Ders 2 -> 85
    assert by_id[1]["score"] == 20.0
    assert by_id[1]["score_source"] == "acilabilirlik"
    assert by_id[2]["score"] == 85.0
    assert by_id[2]["score_source"] == "acilabilirlik"


def test_latest_run_wins_when_multiple():
    conn = _build_db()
    _add_decision_run(conn)
    # Daha yeni bir run; Ders 1 -> 70
    cur = conn.cursor()
    cur.execute("INSERT INTO decision_runs (year, faculty_id) VALUES (2022, 1)")
    run2 = int(cur.lastrowid)
    cur.execute(
        "INSERT INTO course_decisions (decision_run_id, course_id, year, topsis_score, acilabilirlik_score) "
        "VALUES (?, 1, 2022, 90, 70)",
        (run2,),
    )
    conn.commit()
    acil = _latest_acilabilirlik_scores(conn, 2022, faculty_id=1)
    # Sadece en son run dikkate alinmali
    assert acil == {1: 70.0}
