import sqlite3

from app.services.decision_run_override_service import (
    approve_decision_run_override,
    request_decision_run_override,
)


def test_approved_override_removes_temporary_run_and_outputs():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE decision_runs (id INTEGER PRIMARY KEY, run_name TEXT, status TEXT);
        CREATE TABLE course_decisions (id INTEGER PRIMARY KEY, decision_run_id INTEGER);
        CREATE TABLE course_decision_explanations (id INTEGER PRIMARY KEY, course_decision_id INTEGER);
        CREATE TABLE decision_fairness_reports (id INTEGER PRIMARY KEY, decision_run_id INTEGER);
        CREATE TABLE fairness_metric_items (id INTEGER PRIMARY KEY, fairness_report_id INTEGER);
        CREATE TABLE decision_staleness_flags (id INTEGER PRIMARY KEY, decision_run_id INTEGER);
        CREATE TABLE low_confidence_decision_flags (id INTEGER PRIMARY KEY, decision_run_id INTEGER, course_decision_id INTEGER);
        INSERT INTO decision_runs VALUES (7, 'gecici', 'completed');
        INSERT INTO course_decisions VALUES (11, 7);
        INSERT INTO course_decision_explanations VALUES (13, 11);
        INSERT INTO decision_fairness_reports VALUES (17, 7);
        INSERT INTO fairness_metric_items VALUES (19, 17);
        INSERT INTO decision_staleness_flags VALUES (23, 7);
        INSERT INTO low_confidence_decision_flags VALUES (29, 7, 11);
        """
    )
    request = request_decision_run_override(conn, 7, "Yanlis veri", requested_by="talep")
    approve_decision_run_override(conn, request["id"], reviewed_by="onay")
    assert conn.execute("SELECT COUNT(*) FROM decision_runs").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM course_decisions").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM course_decision_explanations").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM decision_fairness_reports").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM fairness_metric_items").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM decision_staleness_flags").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM low_confidence_decision_flags").fetchone()[0] == 0
