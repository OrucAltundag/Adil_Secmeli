# -*- coding: utf-8 -*-
# =============================================================================
# app/tests/test_etl.py — ETL testleri
# =============================================================================
# Müfredat Excel import akışının veri bütünlüğünü koruyan senaryoları doğrular.
# =============================================================================

import os
import sqlite3
import tempfile

import pandas as pd

from app.etl.import_mufredat_excel import collect_curriculum_rows, run_import


def _build_etl_db():
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
            kod TEXT,
            ad TEXT,
            fakulte_id INTEGER
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
        """
    )
    cur.executemany(
        "INSERT INTO fakulte (fakulte_id, ad) VALUES (?, ?)",
        [(1, "Muhendislik"), (2, "Iktisat")],
    )
    cur.executemany(
        "INSERT INTO bolum (bolum_id, fakulte_id, ad) VALUES (?, ?, ?)",
        [(10, 1, "Bilgisayar"), (20, 2, "Isletme")],
    )
    cur.executemany(
        "INSERT INTO ders (ders_id, kod, ad, fakulte_id) VALUES (?, ?, ?, ?)",
        [
            (101, "BLM401", "Veri Madenciligi", 1),
            (102, "BLM402", "Dagitik Sistemler", 1),
            (201, "ISL401", "Pazarlama Analizi", 2),
        ],
    )
    cur.execute(
        "INSERT INTO mufredat (mufredat_id, fakulte_id, akademik_yil, bolum_id, donem, durum, versiyon) VALUES (1, 1, 2024, 10, 'Güz', 'Resmi', 1)"
    )
    cur.execute(
        "INSERT INTO mufredat_ders (mders_id, mufredat_id, ders_id) VALUES (1, 1, 101)"
    )
    cur.execute(
        "INSERT INTO mufredat (mufredat_id, fakulte_id, akademik_yil, bolum_id, donem, durum, versiyon) VALUES (2, 2, 2024, 20, 'Güz', 'Resmi', 1)"
    )
    cur.execute(
        "INSERT INTO mufredat_ders (mders_id, mufredat_id, ders_id) VALUES (2, 2, 201)"
    )
    conn.commit()
    conn.close()
    return path


def test_collect_curriculum_rows_normalized_layout():
    df = pd.DataFrame(
        [
            {
                "Fakülte": "Muhendislik",
                "Bölüm": "Bilgisayar",
                "Akademik Yıl": "2024/2025",
                "Dönem": "Güz",
                "Ders Kodu": "BLM401",
                "Ders Adı": "Veri Madenciligi",
            }
        ]
    )

    rows, info = collect_curriculum_rows(df)

    assert info["layout"] == "normalized"
    assert info["error"] is None
    assert len(rows) == 1
    assert rows[0]["yil"] == 2024
    assert rows[0]["ders_kodu"] == "BLM401"


def test_run_import_replaces_only_target_scope():
    db_path = _build_etl_db()
    fd, excel_path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)

    try:
        df = pd.DataFrame(
            [
                {
                    "Fakülte": "Muhendislik",
                    "Bölüm": "Bilgisayar",
                    "Akademik Yıl": 2024,
                    "Dönem": "Güz",
                    "Ders Kodu": "BLM402",
                    "Ders Adı": "Dagitik Sistemler",
                }
            ]
        )
        df.to_excel(excel_path, index=False)

        ok, msg, counts = run_import(excel_path=excel_path, db_path=db_path)

        assert ok is True, msg
        assert counts["scopes"] == 1

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT md.ders_id
            FROM mufredat m
            JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
            WHERE m.fakulte_id = 1 AND m.bolum_id = 10 AND m.akademik_yil = 2024 AND m.donem = 'Güz'
            """
        )
        target_scope = [row[0] for row in cur.fetchall()]
        cur.execute(
            """
            SELECT md.ders_id
            FROM mufredat m
            JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
            WHERE m.fakulte_id = 2 AND m.bolum_id = 20 AND m.akademik_yil = 2024 AND m.donem = 'Güz'
            """
        )
        untouched_scope = [row[0] for row in cur.fetchall()]
        conn.close()

        assert target_scope == [102]
        assert untouched_scope == [201]
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass
        try:
            os.unlink(excel_path)
        except OSError:
            pass
