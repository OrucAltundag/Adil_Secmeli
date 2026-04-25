# -*- coding: utf-8 -*-

import os
import sqlite3
import tempfile

from app.services.reporting import build_report_snapshot


class DummyDB:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def run_sql(self, query, params=None):
        cur = self.conn.cursor()
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        if query.strip().lower().startswith("select"):
            return [d[0] for d in cur.description], cur.fetchall()
        self.conn.commit()
        return [], []


def _build_reporting_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
        CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
        CREATE TABLE ders (ders_id INTEGER PRIMARY KEY, ad TEXT, bolum_id INTEGER, fakulte_id INTEGER);
        CREATE TABLE mufredat (
            mufredat_id INTEGER PRIMARY KEY,
            fakulte_id INTEGER,
            akademik_yil INTEGER,
            bolum_id INTEGER,
            donem TEXT,
            durum TEXT,
            versiyon INTEGER
        );
        CREATE TABLE mufredat_ders (
            mders_id INTEGER PRIMARY KEY,
            mufredat_id INTEGER,
            ders_id INTEGER
        );
        CREATE TABLE havuz (
            id INTEGER PRIMARY KEY,
            ders_id TEXT,
            yil INTEGER,
            fakulte_id INTEGER,
            bolum_id INTEGER,
            donem TEXT,
            statu INTEGER,
            sayac INTEGER,
            skor REAL,
            ders_adi TEXT
        );
        """
    )
    cur.executemany(
        "INSERT INTO fakulte (fakulte_id, ad) VALUES (?, ?)",
        [(1, "Muhendislik"), (2, "Iktisat")],
    )
    cur.executemany(
        "INSERT INTO bolum (bolum_id, fakulte_id, ad) VALUES (?, ?, ?)",
        [(10, 1, "Ortak Bolum"), (20, 2, "Ortak Bolum")],
    )
    cur.executemany(
        "INSERT INTO ders (ders_id, ad, bolum_id, fakulte_id) VALUES (?, ?, ?, ?)",
        [
            (101, "Algoritmalar", 10, 1),
            (102, "Veri Bilimi", 10, 1),
            (103, "Ag Sistemleri", 10, 1),
            (201, "Muhasebe", 20, 2),
        ],
    )
    cur.executemany(
        "INSERT INTO mufredat (mufredat_id, fakulte_id, akademik_yil, bolum_id, donem, durum, versiyon) VALUES (?, ?, ?, ?, ?, 'Resmi', 1)",
        [
            (1, 1, 2024, 10, "Güz"),
            (2, 1, 2024, 10, "Bahar"),
            (3, 2, 2024, 20, "Güz"),
        ],
    )
    cur.executemany(
        "INSERT INTO mufredat_ders (mders_id, mufredat_id, ders_id) VALUES (?, ?, ?)",
        [
            (1, 1, 101),
            (2, 2, 102),
            (3, 3, 201),
        ],
    )
    cur.executemany(
        "INSERT INTO havuz (id, ders_id, yil, fakulte_id, bolum_id, donem, statu, sayac, skor, ders_adi) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (1, "101", 2024, 1, 10, "Guz", 1, 0, 82.0, "Algoritmalar"),
            (2, "102", 2024, 1, 10, "Bahar", 0, 0, 55.0, "Veri Bilimi"),
            (3, "103", 2024, 1, 10, "Guz", -1, 1, 41.0, "Ag Sistemleri"),
            (4, "104", 2024, 1, 10, "Bahar", -2, 2, None, "Yapay Zeka"),
            (5, "201", 2024, 2, 20, "Guz", 1, 0, 91.0, "Muhasebe"),
        ],
    )
    conn.commit()
    conn.close()
    return path


def test_build_report_snapshot_respects_faculty_and_term():
    path = _build_reporting_db()
    db = DummyDB(path)
    try:
        snapshot = build_report_snapshot(
            db=db,
            faculty_id=1,
            faculty_name="Muhendislik",
            year=2024,
            term="Güz",
            department_name="Ortak Bolum",
        )

        curriculum_ids = [row["ders_id"] for row in snapshot["curriculum_rows"]]
        pool_sources = {row["ders_id"]: row["kaynak"] for row in snapshot["pool_rows"]}

        assert curriculum_ids == [101]
        assert pool_sources[101] == "TOPSIS"
        assert pool_sources[103].startswith("Anket")
    finally:
        db.conn.close()
        try:
            os.unlink(path)
        except OSError:
            pass


def test_build_report_snapshot_counts_statuses():
    path = _build_reporting_db()
    db = DummyDB(path)
    try:
        snapshot = build_report_snapshot(
            db=db,
            faculty_id=1,
            faculty_name="Muhendislik",
            year=2024,
            term="Bahar",
            department_name="Ortak Bolum",
        )

        stats = snapshot["stats"]

        assert stats["total"] == 2
        assert stats["chosen_count"] == 0
        assert stats["rest_count"] == 0
        assert stats["cancelled_count"] == 1
        assert stats["avg_score"] == 55.0
        assert any("Bahar" in note for note in snapshot["notes"])
    finally:
        db.conn.close()
        try:
            os.unlink(path)
        except OSError:
            pass
