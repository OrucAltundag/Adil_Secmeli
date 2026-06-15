# -*- coding: utf-8 -*-
"""Faz D regresyon testleri: algorithm_activity_service.

Spec madde 24-25:
- decision_runs'tan AHP profil + zaman + kapsam + ders sayisi zenginlestirilmis okunur.
- Son run ozet (banner) icin tek-satir UI metni uretilebilir.
- Yil/fakulte filtresi calismali.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile

import pytest

from app.services.algorithm_activity_service import (
    _detect_algorithms,
    _duration_seconds,
    get_last_run_summary,
    get_recent_activity,
)


def _build_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
        CREATE TABLE decision_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_name TEXT, year INTEGER, faculty_id INTEGER, department_id INTEGER,
            semester TEXT, algorithm_version TEXT,
            ahp_profile_id INTEGER, ahp_profile_version INTEGER,
            ahp_weights_snapshot_json TEXT, ahp_consistency_ratio REAL,
            ahp_profile_status_at_run TEXT, ahp_profile_source TEXT,
            decision_policy_id INTEGER, input_data_hash TEXT,
            status TEXT, started_at TEXT, completed_at TEXT,
            created_by TEXT, summary_json TEXT, error_message TEXT, stale_flag INTEGER
        );
        CREATE TABLE course_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_run_id INTEGER, course_id INTEGER
        );
        """
    )
    cur.execute("INSERT INTO fakulte VALUES (1, 'Tip')")
    cur.execute("INSERT INTO fakulte VALUES (2, 'Muh')")
    weights = json.dumps({"basari": 0.4, "trend": 0.2, "populerlik": 0.2, "anket": 0.2})
    # 2 run: Tip Guz, Tip Bahar (ayni dual wrapper'dan)
    cur.execute(
        "INSERT INTO decision_runs "
        "(run_name, year, faculty_id, semester, status, ahp_profile_id, "
        " ahp_profile_version, ahp_weights_snapshot_json, ahp_consistency_ratio, "
        " started_at, completed_at, summary_json) "
        "VALUES (?, 2024, 1, 'Guz', 'completed', 11, 1, ?, 0.05, "
        "'2026-06-15 10:00:00', '2026-06-15 10:00:05', ?)",
        ("test_guz", weights, json.dumps({"course_count": 12, "rf_used": True})),
    )
    guz_id = cur.lastrowid
    cur.execute(
        "INSERT INTO decision_runs "
        "(run_name, year, faculty_id, semester, status, ahp_profile_id, "
        " ahp_profile_version, ahp_weights_snapshot_json, ahp_consistency_ratio, "
        " started_at, completed_at, summary_json) "
        "VALUES (?, 2024, 1, 'Bahar', 'completed', 11, 1, ?, 0.05, "
        "'2026-06-15 10:00:05', '2026-06-15 10:00:12', ?)",
        ("test_bahar", weights, json.dumps({"course_count": 8})),
    )
    bahar_id = cur.lastrowid
    # course_decisions: Tip Guz icin 12, Tip Bahar icin 8 ders
    for _ in range(12):
        cur.execute("INSERT INTO course_decisions (decision_run_id, course_id) VALUES (?, 101)", (guz_id,))
    for _ in range(8):
        cur.execute("INSERT INTO course_decisions (decision_run_id, course_id) VALUES (?, 102)", (bahar_id,))
    # Failed run (farkli fakulte)
    cur.execute(
        "INSERT INTO decision_runs "
        "(run_name, year, faculty_id, semester, status, ahp_profile_id, "
        " started_at, completed_at, error_message) "
        "VALUES (?, 2023, 2, 'Guz', 'failed', 11, "
        "'2026-06-14 10:00:00', '2026-06-14 10:00:03', 'Kriter eksik')",
        ("eski_failed",),
    )
    conn.commit()
    conn.close()
    return path


@pytest.fixture()
def conn():
    path = _build_db()
    c = sqlite3.connect(path); c.row_factory = sqlite3.Row
    yield c
    c.close()
    try:
        os.unlink(path)
    except OSError:
        pass


def test_recent_activity_returns_runs_newest_first(conn):
    runs = get_recent_activity(conn, limit=10)
    assert len(runs) == 3
    # id DESC: en son insert edilen failed_2023 once, sonra Tip Bahar, sonra Tip Guz
    assert runs[0]["status"] == "failed"
    assert runs[0]["yil"] == 2023
    assert runs[1]["donem"] == "Bahar" and runs[1]["yil"] == 2024
    assert runs[2]["donem"] == "Guz" and runs[2]["yil"] == 2024


def test_year_filter(conn):
    runs_2024 = get_recent_activity(conn, year=2024)
    runs_2023 = get_recent_activity(conn, year=2023)
    assert len(runs_2024) == 2
    assert all(r["yil"] == 2024 for r in runs_2024)
    assert len(runs_2023) == 1
    assert runs_2023[0]["status"] == "failed"


def test_faculty_filter(conn):
    runs = get_recent_activity(conn, faculty_id=1)
    assert all(r["fakulte_id"] == 1 for r in runs)
    assert {r["donem"] for r in runs} == {"Guz", "Bahar"}


def test_run_includes_ahp_snapshot(conn):
    runs = get_recent_activity(conn, year=2024)
    r = runs[0]
    assert r["ahp_profile_id"] == 11
    assert r["ahp_profile_version"] == 1
    assert r["ahp_cr"] == pytest.approx(0.05)
    # weights JSON parse edilmis dict olmali
    assert isinstance(r["ahp_weights"], dict)
    assert r["ahp_weights"]["basari"] == pytest.approx(0.4)


def test_course_count_from_course_decisions(conn):
    runs = get_recent_activity(conn, year=2024)
    # Bahar (en yeni) 8 ders, Guz 12
    by_term = {r["donem"]: r for r in runs}
    assert by_term["Bahar"]["ders_sayisi"] == 8
    assert by_term["Guz"]["ders_sayisi"] == 12


def test_duration_seconds_calculation(conn):
    runs = get_recent_activity(conn, year=2024)
    by_term = {r["donem"]: r for r in runs}
    # Guz: 10:00:00 -> 10:00:05 = 5sn; Bahar: 5 -> 12 = 7sn
    assert by_term["Guz"]["sure_sn"] == pytest.approx(5.0)
    assert by_term["Bahar"]["sure_sn"] == pytest.approx(7.0)


def test_detect_algorithms_includes_ml_when_summary_marks_it(conn):
    runs = get_recent_activity(conn, year=2024)
    by_term = {r["donem"]: r for r in runs}
    # Guz summary'sinde rf_used=True -> 'RF' algoritma listesinde olmali
    assert "RF" in by_term["Guz"]["algoritmalar"]
    # Bahar'da ML yok
    assert "RF" not in by_term["Bahar"]["algoritmalar"]
    # AHP+TOPSIS+Trend her ikisinde sabit olmali
    for algos in (by_term["Guz"]["algoritmalar"], by_term["Bahar"]["algoritmalar"]):
        assert "AHP" in algos and "TOPSIS" in algos and "Trend" in algos


def test_last_run_summary_text(conn):
    s = get_last_run_summary(conn, year=2024, faculty_id=1)
    assert s is not None
    assert "Son:" in s["ozet_metni"]
    assert "Tip" in s["ozet_metni"]
    assert "profil #11" in s["ozet_metni"]
    # weights_compact kisaltilmis kriter isimleri icermeli
    assert "bas=0.400" in s["weights_compact"]


def test_last_run_returns_none_when_no_runs(conn):
    s = get_last_run_summary(conn, year=2099)
    assert s is None


def test_failed_run_carries_error_message(conn):
    runs = get_recent_activity(conn, year=2023)
    assert len(runs) == 1
    assert runs[0]["status"] == "failed"
    assert "Kriter" in (runs[0]["error_message"] or "")


def test_duration_seconds_helper():
    # Hatali format -> None
    assert _duration_seconds(None, "2026-06-15 10:00:00") is None
    assert _duration_seconds("bozuk", "2026-06-15 10:00:00") is None
    # Dogru format
    d = _duration_seconds("2026-06-15 10:00:00", "2026-06-15 10:00:05")
    assert d == pytest.approx(5.0)


def test_detect_algorithms_helper():
    # Bos summary -> sadece sabit ucu
    assert _detect_algorithms({}) == ["AHP", "TOPSIS", "Trend"]
    # ML bayrakli
    assert "LR" in _detect_algorithms({"lr_used": True})
    assert "DT" in _detect_algorithms({"ml_dt_used": True})
