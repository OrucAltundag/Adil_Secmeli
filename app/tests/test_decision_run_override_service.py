import sqlite3

from app.services.decision_run_override_service import (
    approve_decision_run_override,
    cancel_decision_run_override,
    request_decision_run_override,
)
from app.ui.tabs.decision_center_page import DecisionCenterPage


class _SelectionStub:
    def __init__(self, selected=(), value=""):
        self._selected = selected
        self._value = value

    def selection(self):
        return self._selected

    def get(self):
        return self._value


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


def test_pending_override_can_be_cancelled_without_deleting_run():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE decision_runs (id INTEGER PRIMARY KEY, run_name TEXT, status TEXT)"
    )
    conn.execute("INSERT INTO decision_runs VALUES (8, 'bahar', 'completed')")
    request = request_decision_run_override(conn, 8, "Yanlis donem", requested_by="talep")

    cancelled = cancel_decision_run_override(conn, request["id"])

    assert cancelled["decision_run_id"] == 8
    assert conn.execute("SELECT COUNT(*) FROM decision_run_override_requests").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM decision_runs WHERE id=8").fetchone()[0] == 1


def test_approved_override_cannot_be_cancelled():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE decision_runs (id INTEGER PRIMARY KEY, run_name TEXT, status TEXT)"
    )
    conn.execute("INSERT INTO decision_runs VALUES (9, 'guz', 'completed')")
    request = request_decision_run_override(conn, 9, "Yanlis karar", requested_by="talep")
    approve_decision_run_override(conn, request["id"], reviewed_by="onay")

    try:
        cancel_decision_run_override(conn, request["id"])
    except ValueError as exc:
        assert "bekleyen" in str(exc).lower()
    else:
        raise AssertionError("Onaylanmis talep geri cekilememeliydi")


def test_clicked_run_row_has_priority_over_combobox_run():
    page = object.__new__(DecisionCenterPage)
    page.tree_runs = _SelectionStub(selected=("2",))
    page.cb_run = _SelectionStub(value="#1 · 2022 Guz")
    page._run_ids = {"#1 · 2022 Guz": 1}

    assert page._selected_run_id() == 2
