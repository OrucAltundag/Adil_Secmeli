# -*- coding: utf-8 -*-

import os
import sqlite3
import tempfile

import pandas as pd

from app.services.curriculum_import_service import import_curriculum_excel


def _build_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
        CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
        CREATE TABLE ders (ders_id INTEGER PRIMARY KEY, kod TEXT, ad TEXT, bolum_id INTEGER, fakulte_id INTEGER);
        CREATE TABLE mufredat (
            mufredat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fakulte_id INTEGER,
            akademik_yil INTEGER,
            bolum_id INTEGER,
            donem TEXT,
            durum TEXT,
            versiyon INTEGER
        );
        CREATE TABLE mufredat_ders (
            mders_id INTEGER PRIMARY KEY AUTOINCREMENT,
            mufredat_id INTEGER,
            ders_id INTEGER
        );
        """
    )
    cur.execute("INSERT INTO fakulte VALUES (1, 'Muhendislik')")
    cur.execute("INSERT INTO bolum VALUES (10, 1, 'Bilgisayar')")
    cur.executemany(
        "INSERT INTO ders (ders_id, kod, ad, bolum_id, fakulte_id) VALUES (?, ?, ?, ?, ?)",
        [
            (101, "C101", "Algoritmalar", 10, 1),
            (102, "C102", "Veri Yapilari", 10, 1),
            (103, "C103", "Aglar", 10, 1),
            (104, "C104", "Yapay Zeka", 10, 1),
        ],
    )
    conn.commit()
    conn.close()
    return path


def _write_excel(rows: list[dict]) -> str:
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    df = pd.DataFrame(rows)
    with pd.ExcelWriter(path) as writer:
        df.to_excel(writer, index=False, sheet_name="Mufredat")
    return path


def test_import_curriculum_excel_insert_and_compare_same():
    db_path = _build_db()
    excel_path = _write_excel(
        [
            {"Fakulte": "Muhendislik", "Bolum": "Bilgisayar", "Yil": 2022, "Donem": "Guz", "Ders Kodu": "C101"},
            {"Fakulte": "Muhendislik", "Bolum": "Bilgisayar", "Yil": 2022, "Donem": "Guz", "Ders Kodu": "C102"},
            {"Fakulte": "Muhendislik", "Bolum": "Bilgisayar", "Yil": 2022, "Donem": "Bahar", "Ders Kodu": "C103"},
            {"Fakulte": "Muhendislik", "Bolum": "Bilgisayar", "Yil": 2022, "Donem": "Bahar", "Ders Kodu": "C104"},
        ]
    )
    try:
        first = import_curriculum_excel(db_path=db_path, excel_path=excel_path, target_year=2022)
        assert first["ok"] is True
        assert first["scopes_created"] >= 1

        second = import_curriculum_excel(db_path=db_path, excel_path=excel_path, target_year=2022)
        assert second["ok"] is True
        assert second["scopes_unchanged"] >= 1
        assert second["links_added"] == 0
        assert second["links_removed"] == 0
    finally:
        for p in (db_path, excel_path):
            try:
                os.unlink(p)
            except OSError:
                pass


def test_import_curriculum_excel_rejects_cross_semester_duplicate():
    db_path = _build_db()
    excel_path = _write_excel(
        [
            {"Fakulte": "Muhendislik", "Bolum": "Bilgisayar", "Yil": 2022, "Donem": "Guz", "Ders Kodu": "C101"},
            {"Fakulte": "Muhendislik", "Bolum": "Bilgisayar", "Yil": 2022, "Donem": "Bahar", "Ders Kodu": "C101"},
        ]
    )
    try:
        result = import_curriculum_excel(db_path=db_path, excel_path=excel_path, target_year=2022)
        assert result["ok"] is False
        assert "Cross-semester" in result["message"] or any("Cross-semester" in e for e in result.get("errors", []))
    finally:
        for p in (db_path, excel_path):
            try:
                os.unlink(p)
            except OSError:
                pass

