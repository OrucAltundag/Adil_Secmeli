import json
import sqlite3

from app.services.electre_dt_validation_service import (
    evaluate_course_with_dt,
    prepare_dt_validation_context,
)


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE decision_runs (
            id INTEGER PRIMARY KEY,
            status TEXT,
            stale_flag INTEGER DEFAULT 0
        );
        CREATE TABLE course_decisions (
            id INTEGER PRIMARY KEY,
            decision_run_id INTEGER,
            course_id INTEGER,
            year INTEGER,
            semester TEXT,
            faculty_id INTEGER,
            department_id INTEGER,
            old_status INTEGER,
            final_status INTEGER,
            topsis_score REAL,
            data_confidence_score REAL
        );
        CREATE TABLE course_score_breakdowns (
            id INTEGER PRIMARY KEY,
            decision_run_id INTEGER,
            course_id INTEGER,
            raw_values_json TEXT
        );
        INSERT INTO decision_runs (id, status, stale_flag) VALUES (1, 'completed', 0);
        """
    )
    return conn


def _seed_history(conn: sqlite3.Connection, *, year: int = 2023, count: int = 120) -> None:
    for idx in range(count):
        high = idx % 2 == 0
        course_id = 1000 + idx
        status = 1 if high else -1
        values = {
            "basari": 0.90 if high else 0.35,
            "trend": 0.75 if high else 0.30,
            "populerlik": 0.85 if high else 0.40,
            "anket": 0.80 if high else 0.35,
        }
        conn.execute(
            """
            INSERT INTO course_decisions (
                id, decision_run_id, course_id, year, semester, faculty_id,
                department_id, old_status, final_status, topsis_score,
                data_confidence_score
            ) VALUES (?, 1, ?, ?, 'Guz', 1, 10, 0, ?, ?, 0.90)
            """,
            (idx + 1, course_id, year, status, 90.0 if high else 30.0),
        )
        conn.execute(
            """
            INSERT INTO course_score_breakdowns (
                id, decision_run_id, course_id, raw_values_json
            ) VALUES (?, 1, ?, ?)
            """,
            (idx + 1, course_id, json.dumps(values)),
        )
    conn.commit()


def test_dt_context_rejects_same_year_and_reports_unavailable():
    conn = _conn()
    try:
        _seed_history(conn, year=2025)
        context = prepare_dt_validation_context(
            conn,
            target_year=2025,
            faculty_id=1,
            department_id=10,
            semester="Guz",
        )
        assert context.available is False
        assert context.sample_count == 0

        result = evaluate_course_with_dt(
            context,
            raw_values={"basari": 0.9, "trend": 0.8, "populerlik": 0.9, "anket": 0.8},
            topsis_score=90,
            data_confidence=0.9,
            old_status=0,
            electre_status=1,
        )
        assert result["comparison"] == "unavailable"
        assert result["predicted_status"] is None
        assert "yetersiz" in result["explanation"].lower()
    finally:
        conn.close()


def test_dt_context_trains_once_and_returns_readable_rule_and_agreement():
    conn = _conn()
    try:
        _seed_history(conn, year=2023)
        context = prepare_dt_validation_context(
            conn,
            target_year=2025,
            faculty_id=1,
            department_id=10,
            semester="Guz",
        )
        assert context.available is True
        assert context.sample_count == 120
        assert set(context.class_counts) == {-1, 1}

        result = evaluate_course_with_dt(
            context,
            raw_values={"basari": 0.92, "trend": 0.80, "populerlik": 0.88, "anket": 0.82},
            topsis_score=92,
            data_confidence=0.95,
            old_status=0,
            electre_status=1,
        )
        assert result["predicted_status"] == 1
        assert result["comparison"] == "agree"
        assert float(result["confidence"]) >= 0.5
        assert result["rule_path"]
        assert result["should_influence_decision"] is False
    finally:
        conn.close()


def test_dt_comparison_flags_more_positive_result():
    conn = _conn()
    try:
        _seed_history(conn, year=2023)
        context = prepare_dt_validation_context(
            conn,
            target_year=2025,
            faculty_id=1,
            department_id=10,
            semester="Guz",
        )
        result = evaluate_course_with_dt(
            context,
            raw_values={"basari": 0.92, "trend": 0.80, "populerlik": 0.88, "anket": 0.82},
            topsis_score=92,
            data_confidence=0.95,
            old_status=0,
            electre_status=0,
        )
        assert result["predicted_status"] == 1
        assert result["comparison"] == "dt_more_positive"
    finally:
        conn.close()

