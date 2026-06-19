import sqlite3

from app.services.curriculum_decision_review_service import (
    approve_curriculum_review,
    build_curriculum_review,
    reject_curriculum_review,
    replace_review_course,
)


def _db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE ders (ders_id INTEGER PRIMARY KEY, kod TEXT, ad TEXT, bolum_id INTEGER);
        CREATE TABLE mufredat (
            mufredat_id INTEGER PRIMARY KEY AUTOINCREMENT, fakulte_id INTEGER,
            bolum_id INTEGER, akademik_yil INTEGER, donem TEXT, durum TEXT, versiyon INTEGER
        );
        CREATE TABLE mufredat_ders (
            mders_id INTEGER PRIMARY KEY AUTOINCREMENT, mufredat_id INTEGER, ders_id INTEGER,
            UNIQUE(mufredat_id, ders_id)
        );
        CREATE TABLE decision_runs (
            id INTEGER PRIMARY KEY, year INTEGER, faculty_id INTEGER, department_id INTEGER,
            semester TEXT, status TEXT
        );
        CREATE TABLE course_decisions (
            id INTEGER PRIMARY KEY, decision_run_id INTEGER, course_id INTEGER,
            department_id INTEGER, final_status INTEGER, topsis_score REAL, main_reason TEXT
        );
        CREATE TABLE candidate_course_recommendations (
            id INTEGER PRIMARY KEY, decision_run_id INTEGER, course_id INTEGER,
            rank INTEGER, net_flow REAL, reason TEXT
        );
        CREATE TABLE skor (ders_id INTEGER, akademik_yil INTEGER, skor_top REAL);

        INSERT INTO ders VALUES (1, 'A', 'Ders A', 10);
        INSERT INTO ders VALUES (2, 'B', 'Ders B', 10);
        INSERT INTO ders VALUES (3, 'C', 'Ders C', 10);
        INSERT INTO ders VALUES (4, 'D', 'Ders D', 10);
        INSERT INTO ders VALUES (5, 'E', 'Ders E', 10);

        INSERT INTO mufredat VALUES (1, 1, 10, 2022, 'Guz', 'Aktif', 1);
        INSERT INTO mufredat VALUES (2, 1, 10, 2022, 'Bahar', 'Aktif', 1);
        INSERT INTO mufredat_ders(mufredat_id, ders_id) VALUES (1, 1), (1, 2), (2, 3);

        INSERT INTO decision_runs VALUES (100, 2022, 1, NULL, 'Guz', 'completed');
        INSERT INTO decision_runs VALUES (101, 2022, 1, NULL, 'Bahar', 'completed');
        INSERT INTO course_decisions VALUES (1, 100, 1, 10, 1, 75, 'koru');
        INSERT INTO course_decisions VALUES (2, 100, 2, 10, 0, 45, 'düşür');
        INSERT INTO course_decisions VALUES (3, 101, 3, 10, 1, 72, 'koru');
        INSERT INTO candidate_course_recommendations VALUES (1, 100, 4, 1, 0.80, 'aday D');
        INSERT INTO candidate_course_recommendations VALUES (2, 100, 5, 2, 0.70, 'aday E');
        INSERT INTO skor VALUES (4, 2022, 90), (5, 2022, 80);
        """
    )
    return conn


def test_preview_auto_replaces_drop_and_writes_only_after_approval():
    conn = _db()
    review = build_curriculum_review(conn, 2022, 1, 10)
    assert review["status"] == "pending"
    assert [item["course_id"] for item in review["payload"]["fall"]["items"]] == [1, 4]
    assert conn.execute("SELECT COUNT(*) FROM mufredat WHERE akademik_yil=2023").fetchone()[0] == 0

    updated = replace_review_course(
        conn,
        review["id"],
        semester="Güz",
        outgoing_course_id=1,
        incoming_course_id=5,
    )
    assert [item["course_id"] for item in updated["payload"]["fall"]["items"]] == [5, 4]
    assert conn.execute("SELECT COUNT(*) FROM mufredat WHERE akademik_yil=2023").fetchone()[0] == 0

    approved = approve_curriculum_review(conn, review["id"], reviewed_by="kurul")
    assert approved["status"] == "approved"
    rows = conn.execute(
        """
        SELECT m.donem, md.ders_id FROM mufredat m
        JOIN mufredat_ders md ON md.mufredat_id=m.mufredat_id
        WHERE m.akademik_yil=2023 ORDER BY m.donem, md.ders_id
        """
    ).fetchall()
    assert [tuple(row) for row in rows] == [("Bahar", 3), ("Guz", 4), ("Guz", 5)]


def test_rejection_keeps_target_curriculum_empty():
    conn = _db()
    review = build_curriculum_review(conn, 2022, 1, 10)
    rejected = reject_curriculum_review(conn, review["id"], reviewed_by="kurul", review_note="uygun değil")
    assert rejected["status"] == "rejected"
    assert conn.execute("SELECT COUNT(*) FROM mufredat WHERE akademik_yil=2023").fetchone()[0] == 0


def test_pending_review_blocks_duplicate_approval_queue_for_same_scope():
    conn = _db()
    first = build_curriculum_review(conn, 2022, 1, 10)
    conn.execute("INSERT INTO decision_runs VALUES (102, 2022, 1, NULL, 'Guz', 'completed')")
    conn.execute("INSERT INTO course_decisions VALUES (4, 102, 1, 10, 1, 88, 'yeni run')")
    conn.execute("INSERT INTO candidate_course_recommendations VALUES (3, 102, 5, 1, 0.90, 'yeni aday')")

    second = build_curriculum_review(conn, 2022, 1, 10)

    assert second["id"] == first["id"]
    assert conn.execute(
        """
        SELECT COUNT(*) FROM curriculum_decision_reviews
        WHERE source_year=2022 AND faculty_id=1 AND department_id=10 AND status='pending'
        """
    ).fetchone()[0] == 1
