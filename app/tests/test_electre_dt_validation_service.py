import json
import sqlite3

from app.services.electre_dt_validation_service import (
    build_peer_comparison_features,
    evaluate_course_with_dt,
    peer_assessment,
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
        CREATE TABLE curriculum_decision_reviews (
            id INTEGER PRIMARY KEY,
            department_id INTEGER NOT NULL,
            fall_run_id INTEGER,
            spring_run_id INTEGER,
            status TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        INSERT INTO decision_runs (id, status, stale_flag) VALUES (1, 'completed', 0);
        INSERT INTO curriculum_decision_reviews (
            id, department_id, fall_run_id, spring_run_id, status, payload_json
        ) VALUES (1, 10, 1, NULL, 'approved', '{}');
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
    approved_items = [
        {"course_id": 1000 + idx}
        for idx in range(count)
        if idx % 2 == 0
    ]
    conn.execute(
        "UPDATE curriculum_decision_reviews SET payload_json=? WHERE id=1",
        (json.dumps({"fall": {"items": approved_items}, "spring": {"items": []}}),),
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
            policy={"curriculum_keep_threshold": 70, "pool_threshold": 50, "rest_threshold": 40},
        )
        assert result["comparison"] == "agree"
        assert result["predicted_status"] == 1
        assert result["fallback_advisory"] is True
        assert float(result["confidence"]) < 0.70
        assert "yetersiz" in result["explanation"].lower()
        assert result["peer_assessment"]["advisory_only"] is True
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
        assert set(context.class_counts) == {0, 1}

        result = evaluate_course_with_dt(
            context,
            raw_values={"basari": 0.92, "trend": 0.80, "populerlik": 0.88, "anket": 0.82},
            lr_trend_forecast=0.84,
            peer_features={
                "peer_count": 7,
                "topsis_peer_percentile": 0.90,
                "topsis_delta_median": 0.18,
                "basari_delta_median": 0.12,
                "trend_delta_median": 0.10,
                "populerlik_delta_median": 0.11,
                "anket_delta_median": 0.09,
            },
            topsis_score=92,
            data_confidence=0.95,
            old_status=0,
            electre_status=1,
        )
        assert result["predicted_status"] == 1
        assert result["comparison"] == "agree"
        assert float(result["confidence"]) >= 0.5
        assert result["rule_path"]
        assert result["peer_assessment"]["level"] == "strong"
        assert result["lr_trend_forecast"] == 0.84
        assert result["should_influence_decision"] is False
    finally:
        conn.close()


def test_peer_features_use_other_seven_courses_as_leave_one_out_context():
    rows = []
    for course_id, score in enumerate((20, 30, 40, 50, 60, 70, 80, 90), start=1):
        normalized = score / 100.0
        rows.append(
            {
                "course_id": course_id,
                "topsis_score": score,
                "raw_values": {
                    "basari": normalized,
                    "trend": normalized,
                    "populerlik": normalized,
                    "anket": normalized,
                },
            }
        )

    features = build_peer_comparison_features(rows)

    assert features[8]["topsis_peer_percentile"] == 1.0
    assert features[1]["topsis_peer_percentile"] == 0.0
    assert features[8]["peer_count"] == 7.0
    # En yuksek ders kendi medyanina katilmaz: diger 7 skorun medyani 50'dir.
    assert abs(features[8]["topsis_delta_median"] - 0.40) < 1e-12
    assert abs(features[8]["basari_delta_median"] - 0.40) < 1e-12
    assert abs(features[1]["trend_delta_median"] + 0.40) < 1e-12
    assert peer_assessment(features[8])["level"] == "strong"
    assert peer_assessment(features[1])["level"] == "weak"


def test_dt_does_not_train_from_unapproved_algorithm_outputs():
    conn = _conn()
    try:
        _seed_history(conn, year=2023)
        conn.execute("UPDATE curriculum_decision_reviews SET status='pending'")
        conn.commit()

        context = prepare_dt_validation_context(
            conn,
            target_year=2025,
            faculty_id=1,
            department_id=10,
            semester="Guz",
        )

        assert context.available is False
        assert context.sample_count == 0
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
