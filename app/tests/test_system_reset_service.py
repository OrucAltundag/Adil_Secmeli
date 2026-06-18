# -*- coding: utf-8 -*-
"""Sistem sıfırlamasında seçmeli havuzunun yeniden kurulması."""

import sqlite3

from app.services.system_reset_service import reset_system


def test_reset_rebuilds_elective_pool_for_existing_scopes():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
        CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
        CREATE TABLE ders (
            ders_id INTEGER PRIMARY KEY, ad TEXT, fakulte_id INTEGER,
            bolum_id INTEGER, DersTipi TEXT
        );
        CREATE TABLE mufredat (
            mufredat_id INTEGER PRIMARY KEY, fakulte_id INTEGER,
            bolum_id INTEGER, akademik_yil INTEGER
        );
        CREATE TABLE mufredat_ders (mufredat_id INTEGER, ders_id INTEGER);
        CREATE TABLE havuz (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id TEXT, yil INTEGER,
            fakulte_id INTEGER, bolum_id INTEGER, donem TEXT, statu INTEGER,
            sayac INTEGER, skor REAL, ders_adi TEXT
        );
        CREATE TABLE skor (id INTEGER PRIMARY KEY, ders_id INTEGER);

        INSERT INTO fakulte VALUES (1, 'Mühendislik');
        INSERT INTO bolum VALUES (10, 1, 'Bilgisayar');
        INSERT INTO ders VALUES (101, 'Makine Öğrenmesi', 1, 10, 'Seçmeli');
        INSERT INTO ders VALUES (102, 'Bulut Bilişim', 1, 10, 'Elective');
        INSERT INTO ders VALUES (103, 'Matematik', 1, 10, 'Zorunlu');
        INSERT INTO mufredat VALUES (1, 1, 10, 2024);
        INSERT INTO mufredat_ders VALUES (1, 101);
        INSERT INTO havuz
            (ders_id, yil, fakulte_id, bolum_id, donem, statu, sayac, skor, ders_adi)
        VALUES ('101', 2024, 1, 10, 'Guz', 1, 3, 88, 'Makine Öğrenmesi');
        INSERT INTO skor VALUES (1, 101);
        """
    )

    result = reset_system(conn, user="test")

    rows = conn.execute(
        "SELECT CAST(ders_id AS INTEGER), yil, fakulte_id, bolum_id, statu, sayac, skor "
        "FROM havuz ORDER BY CAST(ders_id AS INTEGER)"
    ).fetchall()
    assert rows == [
        (101, 2024, 1, 10, 0, 0, None),
        (102, 2024, 1, 10, 0, 0, None),
    ]
    assert conn.execute("SELECT COUNT(*) FROM mufredat").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM skor").fetchone()[0] == 0
    assert result["restored_pool_rows"] == 2
    assert result["restored_pool_scopes"] == 1
