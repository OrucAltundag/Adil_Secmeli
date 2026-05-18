# -*- coding: utf-8 -*-
"""Fairness testleri — bölüm temsili, yeni ders fırsatı, düşük güvenli karar oranı."""

from __future__ import annotations

import pytest

from app.services.fairness_report_service import generate_fairness_report

pytestmark = pytest.mark.unit


def _setup_decision_tables(conn):
    """decision_runs ve course_decisions tablolarini gercek semayla olustur."""
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS decision_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_name TEXT NOT NULL, year INTEGER NOT NULL,
        faculty_id INTEGER, department_id INTEGER, semester TEXT,
        algorithm_version TEXT NOT NULL, ahp_profile_id INTEGER,
        decision_policy_id INTEGER, input_data_hash TEXT,
        status TEXT NOT NULL DEFAULT 'started',
        started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT, created_by TEXT,
        summary_json TEXT, error_message TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS course_decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_run_id INTEGER NOT NULL, course_id INTEGER NOT NULL,
        year INTEGER NOT NULL, faculty_id INTEGER, department_id INTEGER,
        semester TEXT, old_status INTEGER, recommended_status INTEGER,
        final_status INTEGER, topsis_score REAL, trend_score REAL,
        trend_label TEXT, data_confidence_score REAL,
        decision_stability TEXT, approval_required INTEGER NOT NULL DEFAULT 0,
        approval_status TEXT, approval_by TEXT, approval_at TEXT,
        approval_reason TEXT, override_applied INTEGER NOT NULL DEFAULT 0,
        override_reason TEXT, main_reason TEXT, rule_triggered TEXT,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    return cur


class TestFairnessMetrics:
    """Fairness report icerigi dogrulama."""

    def test_fairness_report_has_required_fields(self, memory_db):
        cur = _setup_decision_tables(memory_db)
        cur.execute("""INSERT INTO decision_runs
            (run_name, year, algorithm_version, status)
            VALUES ('test_run', 2024, 'v1', 'completed')""")
        run_id = cur.lastrowid
        for i, (score, status, conf) in enumerate([
            (85.0, 1, 0.90), (60.0, 0, 0.70), (35.0, -1, 0.40), (20.0, -2, 0.30),
        ], 1):
            cur.execute("""INSERT INTO course_decisions
                (decision_run_id, course_id, year, department_id, semester,
                 recommended_status, final_status, topsis_score,
                 data_confidence_score, decision_stability, approval_required)
                VALUES (?, ?, 2024, 10, 'Guz', ?, ?, ?, ?, 'medium', 0)""",
                (run_id, i, status, status, score, conf))
        memory_db.commit()

        report = generate_fairness_report(cur, decision_run_id=run_id, year=2024)
        assert report["summary_text"], "summary_text bos olmamali"
        assert report["report"]["total_courses"] == 4
        assert "low_data_confidence_count" in report["report"]
        assert "cancel_candidate_count" in report["report"]

    def test_low_confidence_count_detected(self, memory_db):
        cur = _setup_decision_tables(memory_db)
        cur.execute("""INSERT INTO decision_runs
            (run_name, year, algorithm_version, status)
            VALUES ('test_run', 2024, 'v1', 'completed')""")
        run_id = cur.lastrowid
        for i in range(1, 4):
            cur.execute("""INSERT INTO course_decisions
                (decision_run_id, course_id, year, department_id, semester,
                 recommended_status, final_status, topsis_score,
                 data_confidence_score, decision_stability, approval_required)
                VALUES (?, ?, 2024, 10, 'Guz', 0, 0, 50.0, 0.30, 'low', 0)""",
                (run_id, i))
        memory_db.commit()
        report = generate_fairness_report(cur, decision_run_id=run_id, year=2024)
        assert report["report"]["low_data_confidence_count"] >= 3
