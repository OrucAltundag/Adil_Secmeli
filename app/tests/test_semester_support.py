# -*- coding: utf-8 -*-

import os
import sqlite3
import tempfile

import pytest

from app.db.schema_compat import ensure_havuz_semester_schema, ensure_skor_schema
from app.services.calculation import rebuild_school_curricula_dual_semester
from app.services.havuz_karar import (
    calculate_next_status_semester,
    enforce_cross_semester_constraints,
)


def _build_dual_semester_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
        CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
        CREATE TABLE ders (
            ders_id INTEGER PRIMARY KEY,
            bolum_id INTEGER,
            fakulte_id INTEGER,
            ad TEXT,
            DersTipi TEXT
        );
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
        CREATE TABLE ders_kriterleri (
            id INTEGER PRIMARY KEY,
            ders_id INTEGER,
            yil INTEGER,
            donem TEXT,
            toplam_ogrenci INTEGER,
            gecen_ogrenci INTEGER,
            basari_ortalamasi REAL,
            kontenjan INTEGER,
            kayitli_ogrenci INTEGER,
            aktif_mi INTEGER,
            anket_katilimci INTEGER,
            anket_dersi_secen INTEGER
        );
        CREATE TABLE performans (
            pfrs_id INTEGER PRIMARY KEY,
            ders_id INTEGER,
            akademik_yil INTEGER,
            donem TEXT,
            ortalama_not REAL,
            basari_orani REAL
        );
        CREATE TABLE populerlik (
            pop_id INTEGER PRIMARY KEY,
            ders_id INTEGER,
            akademik_yil INTEGER,
            donem TEXT,
            talep_sayisi INTEGER,
            kontenjan INTEGER,
            doluluk_orani REAL
        );
        CREATE TABLE havuz (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        CREATE TABLE curriculum_generation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT,
            payload_json TEXT
        );
        """
    )

    cur.execute("INSERT INTO fakulte VALUES (1, 'Muhendislik')")
    cur.execute("INSERT INTO bolum VALUES (10, 1, 'Bilgisayar')")

    dersler = [
        (101, 10, 1, "Ders-101", "Secmeli"),
        (102, 10, 1, "Ders-102", "Secmeli"),
        (103, 10, 1, "Ders-103", "Secmeli"),
        (104, 10, 1, "Ders-104", "Secmeli"),
        (105, 10, 1, "Ders-105", "Secmeli"),
        (106, 10, 1, "Ders-106", "Secmeli"),
        (107, 10, 1, "Ders-107", "Secmeli"),
        (108, 10, 1, "Ders-108", "Secmeli"),
    ]
    cur.executemany("INSERT INTO ders VALUES (?, ?, ?, ?, ?)", dersler)

    cur.executemany(
        "INSERT INTO mufredat (mufredat_id, fakulte_id, akademik_yil, bolum_id, donem, durum, versiyon) VALUES (?, 1, 2024, 10, ?, 'Resmi', 1)",
        [
            (1, "Guz"),
            (2, "Bahar"),
        ],
    )
    cur.executemany(
        "INSERT INTO mufredat_ders (mders_id, mufredat_id, ders_id) VALUES (?, ?, ?)",
        [
            (1, 1, 101),
            (2, 1, 102),
            (3, 1, 103),
            (4, 1, 104),
            (5, 2, 105),
            (6, 2, 106),
            (7, 2, 107),
            (8, 2, 108),
        ],
    )

    kriter_id = 1
    perf_id = 1
    pop_id = 1
    for ders_id in range(101, 109):
        for term in ("Guz", "Bahar"):
            cur.execute(
                """
                INSERT INTO ders_kriterleri
                (id, ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, kontenjan, kayitli_ogrenci, aktif_mi, anket_katilimci, anket_dersi_secen)
                VALUES (?, ?, 2024, ?, 100, 85, 78, 50, 45, 1, 100, 80)
                """,
                (kriter_id, ders_id, term),
            )
            cur.execute(
                "INSERT INTO performans VALUES (?, ?, 2024, ?, 78, 0.85)",
                (perf_id, ders_id, term),
            )
            cur.execute(
                "INSERT INTO populerlik VALUES (?, ?, 2024, ?, 42, 50, 0.84)",
                (pop_id, ders_id, term),
            )
            kriter_id += 1
            perf_id += 1
            pop_id += 1

    for ders_id in range(101, 109):
        for term, status in (("Guz", 1 if ders_id <= 104 else 0), ("Bahar", 1 if ders_id >= 105 else 0)):
            cur.execute(
                """
                INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, donem, statu, sayac, skor, ders_adi)
                VALUES (?, 2024, 1, 10, ?, ?, 0, 75.0, ?)
                """,
                (str(ders_id), term, status, f"Ders-{ders_id}"),
            )

    conn.commit()
    conn.close()
    return path


def test_rebuild_school_curricula_dual_semester_balances_4_plus_4():
    db_path = _build_dual_semester_db()
    try:
        summary = rebuild_school_curricula_dual_semester(
            db_path=db_path,
            base_year=2024,
            max_rounds=2,
            block_size=4,
        )
        assert summary.get("ok") is True

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) AS term, COUNT(DISTINCT md.ders_id)
            FROM mufredat m
            JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
            WHERE m.fakulte_id = 1 AND m.akademik_yil = 2025
            GROUP BY term
            ORDER BY term
            """
        )
        counts = {row[0]: row[1] for row in cur.fetchall()}
        assert counts.get("g") == 4
        assert counts.get("b") == 4

        cur.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT md.ders_id
                FROM mufredat m
                JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
                WHERE m.fakulte_id = 1 AND m.akademik_yil = 2025
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = 'g'
            ) g
            JOIN (
                SELECT md.ders_id
                FROM mufredat m
                JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
                WHERE m.fakulte_id = 1 AND m.akademik_yil = 2025
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = 'b'
            ) b ON g.ders_id = b.ders_id
            """
        )
        overlap = int(cur.fetchone()[0] or 0)
        assert overlap == 0
        conn.close()
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


def test_cross_semester_state_machine_conflict_guard():
    with pytest.raises(ValueError):
        calculate_next_status_semester(
            prev_statu=1,
            prev_sayac=0,
            selected_in_current_semester=True,
            selected_in_other_semester=True,
        )

    constrained = enforce_cross_semester_constraints({"Guz": [101, 102], "Bahar": [102, 103]})
    assert constrained["Guz"] == [101, 102]
    assert constrained["Bahar"] == [103]


def test_havuz_semester_schema_backward_compat():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE havuz (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id TEXT,
            yil INTEGER,
            fakulte_id INTEGER,
            bolum_id INTEGER,
            statu INTEGER,
            sayac INTEGER,
            skor REAL,
            ders_adi TEXT
        );
        INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, statu, sayac, skor, ders_adi)
        VALUES ('101', 2024, 1, 10, 0, 0, 50.0, 'Ders-101');
        INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, statu, sayac, skor, ders_adi)
        VALUES ('101', 2024, 1, 10, 0, 0, 55.0, 'Ders-101');
        """
    )
    conn.commit()

    result = ensure_havuz_semester_schema(conn)
    assert result["column_added"] == 1
    assert result["duplicates_removed"] >= 1

    cur.execute("PRAGMA table_info(havuz)")
    cols = {row[1] for row in cur.fetchall()}
    assert "donem" in cols

    cur.execute("SELECT COUNT(*) FROM havuz")
    assert int(cur.fetchone()[0]) == 1
    conn.close()
    try:
        os.unlink(path)
    except OSError:
        pass


def test_skor_schema_adds_missing_hesap_tarih():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE skor (
            skor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER NOT NULL,
            akademik_yil INTEGER NOT NULL,
            skor_top REAL
        );
        INSERT INTO skor (ders_id, akademik_yil, skor_top) VALUES (101, 2022, 77.5);
        """
    )
    conn.commit()

    result = ensure_skor_schema(conn)
    assert result["columns_added"] >= 2

    cur.execute("PRAGMA table_info(skor)")
    cols = {row[1] for row in cur.fetchall()}
    assert "hesap_tarih" in cols
    assert "donem" in cols
    conn.close()

    try:
        os.unlink(path)
    except OSError:
        pass
