# -*- coding: utf-8 -*-

import inspect
import os
import sqlite3
import tempfile

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import routes
from app.services.ai_engine import HavuzAIEngine
from app.services.calculation import generate_next_year_curricula, run_all_algorithms_for_year
from app.services.curriculum_import_service import import_curriculum_excel
from app.services.yearly_workflow import (
    get_faculty_year_status,
    is_department_criteria_complete,
    is_faculty_criteria_complete,
    list_active_years_for_faculty,
    mark_criteria_status,
)


def _create_db() -> str:
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
            kod TEXT,
            DersTipi TEXT
        );
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
        CREATE TABLE ders_kriterleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER,
            yil INTEGER,
            donem TEXT,
            toplam_ogrenci INTEGER,
            gecen_ogrenci INTEGER,
            basari_ortalamasi REAL,
            kontenjan INTEGER,
            kayitli_ogrenci INTEGER,
            anket_katilimci INTEGER,
            anket_dersi_secen INTEGER
        );
        CREATE TABLE performans (
            pfrs_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER,
            akademik_yil INTEGER,
            donem TEXT,
            ortalama_not REAL,
            basari_orani REAL
        );
        CREATE TABLE populerlik (
            pop_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        CREATE TABLE skor (
            skor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER,
            akademik_yil INTEGER,
            donem TEXT,
            skor_top REAL
        );
        """
    )
    conn.commit()
    conn.close()
    return path


def _insert_curriculum(conn, fakulte_id: int, bolum_id: int, yil: int, ders_ids: list[int], donem: str = "Guz"):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO mufredat (fakulte_id, akademik_yil, bolum_id, donem, durum, versiyon)
        VALUES (?, ?, ?, ?, 'Resmi', 1)
        """,
        (int(fakulte_id), int(yil), int(bolum_id), str(donem)),
    )
    mid = int(cur.lastrowid)
    for ders_id in ders_ids:
        cur.execute(
            "INSERT INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?)",
            (mid, int(ders_id)),
        )


def _insert_complete_metrics(
    conn,
    ders_id: int,
    yil: int,
    donem: str = "Guz",
    toplam: int = 100,
    gecen: int = 80,
    ortalama: float = 75.0,
    kontenjan: int = 50,
    kayitli: int = 40,
):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ders_kriterleri
            (ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi,
             kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 100, 80)
        """,
        (
            int(ders_id),
            int(yil),
            str(donem),
            int(toplam),
            int(gecen),
            float(ortalama),
            int(kontenjan),
            int(kayitli),
        ),
    )
    basari = float(gecen) / float(toplam or 1)
    doluluk = float(kayitli) / float(kontenjan or 1)
    cur.execute(
        """
        INSERT INTO performans (ders_id, akademik_yil, donem, ortalama_not, basari_orani)
        VALUES (?, ?, ?, ?, ?)
        """,
        (int(ders_id), int(yil), str(donem), float(ortalama), float(basari)),
    )
    cur.execute(
        """
        INSERT INTO populerlik (ders_id, akademik_yil, donem, talep_sayisi, kontenjan, doluluk_orani)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (int(ders_id), int(yil), str(donem), int(kayitli), int(kontenjan), float(doluluk)),
    )


def _insert_pool_row(
    conn,
    ders_id: int,
    yil: int,
    fakulte_id: int,
    bolum_id: int,
    statu: int,
    skor: float | None = None,
    donem: str = "Guz",
):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, donem, statu, sayac, skor, ders_adi)
        SELECT ?, ?, ?, ?, ?, ?, 0, ?, ad FROM ders WHERE ders_id = ?
        """,
        (
            str(int(ders_id)),
            int(yil),
            int(fakulte_id),
            int(bolum_id),
            str(donem),
            int(statu),
            skor,
            int(ders_id),
        ),
    )


def _write_import_excel(rows: list[dict]) -> str:
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    df = pd.DataFrame(rows)
    with pd.ExcelWriter(path) as writer:
        df.to_excel(writer, index=False, sheet_name="Mufredat")
    return path


def test_import_resets_criteria_status():
    db_path = _create_db()
    excel_path = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO fakulte VALUES (1, 'Muhendislik')")
        cur.execute("INSERT INTO bolum VALUES (10, 1, 'Bilgisayar')")
        cur.executemany(
            "INSERT INTO ders (ders_id, bolum_id, fakulte_id, ad, kod, DersTipi) VALUES (?, ?, ?, ?, ?, 'Secmeli')",
            [
                (101, 10, 1, "Algoritmalar", "C101"),
                (102, 10, 1, "Veri Yapilari", "C102"),
            ],
        )
        _insert_curriculum(conn, 1, 10, 2022, [101, 102], "Guz")
        _insert_complete_metrics(conn, 101, 2022, "Guz")
        _insert_complete_metrics(conn, 102, 2022, "Guz")
        _insert_pool_row(conn, 101, 2022, 1, 10, 1, 88.0)
        _insert_pool_row(conn, 102, 2022, 1, 10, 1, 84.0)
        cur.executemany(
            "INSERT INTO skor (ders_id, akademik_yil, donem, skor_top) VALUES (?, 2022, 'Guz', ?)",
            [(101, 88.0), (102, 84.0)],
        )
        conn.commit()
        conn.close()

        excel_path = _write_import_excel(
            [
                {"Fakulte": "Muhendislik", "Bolum": "Bilgisayar", "Yil": 2022, "Donem": "Guz", "Ders Kodu": "C101"},
                {"Fakulte": "Muhendislik", "Bolum": "Bilgisayar", "Yil": 2022, "Donem": "Guz", "Ders Kodu": "C102"},
            ]
        )
        result = import_curriculum_excel(db_path=db_path, excel_path=excel_path, target_year=2022)
        assert result["ok"] is True
        assert result["criteria_rows_deleted"] >= 2

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ders_kriterleri WHERE yil = 2022")
        assert int(cur.fetchone()[0] or 0) == 0
        cur.execute(
            """
            SELECT criteria_status, algorithm_run_status
            FROM criteria_faculty_status
            WHERE fakulte_id = 1 AND yil = 2022
            """
        )
        row = cur.fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "not_started"
        assert row[1] == "not_run"
    finally:
        for p in (db_path, excel_path):
            if p:
                try:
                    os.unlink(p)
                except OSError:
                    pass


def test_department_completion_status():
    db_path = _create_db()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO fakulte VALUES (1, 'Muhendislik')")
        cur.execute("INSERT INTO bolum VALUES (10, 1, 'Bilgisayar')")
        cur.executemany(
            "INSERT INTO ders (ders_id, bolum_id, fakulte_id, ad, kod, DersTipi) VALUES (?, ?, ?, ?, ?, 'Secmeli')",
            [(101, 10, 1, "Ders-101", "C101"), (102, 10, 1, "Ders-102", "C102")],
        )
        _insert_curriculum(conn, 1, 10, 2022, [101, 102], "Guz")
        _insert_complete_metrics(conn, 101, 2022, "Guz")
        conn.commit()

        status1 = mark_criteria_status(conn, yil=2022, fakulte_id=1, bolum_id=10)
        assert status1["department"]["criteria_status"] == "partial"
        assert is_department_criteria_complete(conn, 2022, 1, 10) is False

        _insert_complete_metrics(conn, 102, 2022, "Guz")
        conn.commit()
        status2 = mark_criteria_status(conn, yil=2022, fakulte_id=1, bolum_id=10)
        assert status2["department"]["criteria_status"] == "completed"
        assert status2["department_completed_now"] is True
        assert is_department_criteria_complete(conn, 2022, 1, 10) is True
        conn.close()
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


def test_faculty_completion_status():
    db_path = _create_db()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO fakulte VALUES (1, 'Muhendislik')")
        cur.executemany("INSERT INTO bolum VALUES (?, 1, ?)", [(10, "Bilgisayar"), (11, "Endustri")])
        cur.executemany(
            "INSERT INTO ders (ders_id, bolum_id, fakulte_id, ad, kod, DersTipi) VALUES (?, ?, 1, ?, ?, 'Secmeli')",
            [(101, 10, "Ders-101", "C101"), (201, 11, "Ders-201", "C201")],
        )
        _insert_curriculum(conn, 1, 10, 2022, [101], "Guz")
        _insert_curriculum(conn, 1, 11, 2022, [201], "Guz")
        _insert_complete_metrics(conn, 101, 2022, "Guz")
        conn.commit()

        mark_criteria_status(conn, yil=2022, fakulte_id=1, bolum_id=10)
        assert is_faculty_criteria_complete(conn, 2022, 1, refresh=True) is False

        _insert_complete_metrics(conn, 201, 2022, "Guz")
        conn.commit()
        status = mark_criteria_status(conn, yil=2022, fakulte_id=1, bolum_id=11)
        assert status["faculty"]["criteria_status"] == "completed"
        assert status["faculty_completed_now"] is True
        assert is_faculty_criteria_complete(conn, 2022, 1, refresh=True) is True
        conn.close()
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


def test_no_auto_calculation_after_criteria_entry():
    db_path = _create_db()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO fakulte VALUES (1, 'Muhendislik')")
        cur.execute("INSERT INTO bolum VALUES (10, 1, 'Bilgisayar')")
        cur.execute(
            "INSERT INTO ders (ders_id, bolum_id, fakulte_id, ad, kod, DersTipi) VALUES (101, 10, 1, 'Ders-101', 'C101', 'Secmeli')"
        )
        _insert_curriculum(conn, 1, 10, 2022, [101], "Guz")
        _insert_pool_row(conn, 101, 2022, 1, 10, 1, None)
        _insert_complete_metrics(conn, 101, 2022, "Guz")
        conn.commit()

        mark_criteria_status(conn, yil=2022, fakulte_id=1, bolum_id=10)
        status = get_faculty_year_status(conn, 1, 2022, refresh=True)
        assert status["algorithm_run_status"] == "not_run"
        cur.execute("SELECT COUNT(*) FROM mufredat WHERE akademik_yil = 2023")
        assert int(cur.fetchone()[0] or 0) == 0
        cur.execute("SELECT COUNT(*) FROM havuz WHERE yil = 2022 AND skor IS NOT NULL")
        assert int(cur.fetchone()[0] or 0) == 0
        conn.close()
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


def _build_two_faculty_algorithm_db() -> str:
    db_path = _create_db()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO fakulte VALUES (?, ?)",
        [(1, "Muhendislik"), (2, "Saglik")],
    )
    cur.executemany(
        "INSERT INTO bolum VALUES (?, ?, ?)",
        [(10, 1, "Bilgisayar"), (20, 2, "Hemsirelik")],
    )
    cur.executemany(
        "INSERT INTO ders (ders_id, bolum_id, fakulte_id, ad, kod, DersTipi) VALUES (?, ?, ?, ?, ?, 'Secmeli')",
        [
            (101, 10, 1, "M-101", "M101"),
            (102, 10, 1, "M-102", "M102"),
            (201, 20, 2, "S-201", "S201"),
            (202, 20, 2, "S-202", "S202"),
        ],
    )
    _insert_curriculum(conn, 1, 10, 2022, [101, 102], "Guz")
    _insert_curriculum(conn, 2, 20, 2022, [201, 202], "Guz")
    _insert_pool_row(conn, 101, 2022, 1, 10, 1)
    _insert_pool_row(conn, 102, 2022, 1, 10, 1)
    _insert_pool_row(conn, 201, 2022, 2, 20, 1)
    _insert_pool_row(conn, 202, 2022, 2, 20, 1)
    _insert_complete_metrics(conn, 101, 2022, "Guz", ortalama=80)
    _insert_complete_metrics(conn, 102, 2022, "Guz", ortalama=82)
    conn.commit()

    # Faculty-1 complete, Faculty-2 incomplete
    mark_criteria_status(conn, yil=2022, fakulte_id=1, bolum_id=10)
    mark_criteria_status(conn, yil=2022, fakulte_id=2, bolum_id=20)
    conn.close()
    return db_path


def test_algorithm_runs_only_for_completed_faculty():
    db_path = _build_two_faculty_algorithm_db()
    try:
        summary = run_all_algorithms_for_year(yil=2022, db_path=db_path, donem="G")
        processed_ids = {int(item.get("fakulte_id")) for item in (summary.get("processed") or [])}
        skipped_reasons = [str(item.get("reason")) for item in (summary.get("skipped") or [])]
        assert 1 in processed_ids
        assert any("kriter girisi eksik oldugundan hesaplama yapilmadi" in text for text in skipped_reasons)
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


def test_next_year_created_after_algorithm_run():
    db_path = _build_two_faculty_algorithm_db()
    try:
        summary = run_all_algorithms_for_year(yil=2022, db_path=db_path, donem="G")
        assert summary.get("processed")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*)
            FROM mufredat m
            JOIN bolum b ON b.bolum_id = m.bolum_id
            WHERE b.fakulte_id = 1 AND m.akademik_yil = 2023
            """
        )
        assert int(cur.fetchone()[0] or 0) > 0
        conn.close()
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


def test_new_year_visible_but_scores_empty_until_new_criteria():
    db_path = _build_two_faculty_algorithm_db()
    try:
        run_all_algorithms_for_year(yil=2022, db_path=db_path, donem="G")
        conn = sqlite3.connect(db_path)
        status_2023 = get_faculty_year_status(conn, fakulte_id=1, yil=2023, refresh=False)
        assert int(status_2023.get("year_active", 0)) == 1
        assert int(status_2023.get("yil", 0)) == 2023

        years = list_active_years_for_faculty(conn, 1)
        assert 2023 in years

        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM havuz WHERE fakulte_id = 1 AND yil = 2023")
        total = int(cur.fetchone()[0] or 0)
        cur.execute("SELECT COUNT(*) FROM havuz WHERE fakulte_id = 1 AND yil = 2023 AND skor IS NOT NULL")
        scored = int(cur.fetchone()[0] or 0)
        conn.close()
        assert total > 0
        assert scored == 0
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


def test_ai_engine_filters_to_selected_faculty_year_curriculum():
    db_path = _create_db()
    session = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO fakulte VALUES (?, ?)",
            [(1, "Muhendislik"), (2, "Saglik")],
        )
        cur.executemany(
            "INSERT INTO bolum VALUES (?, ?, ?)",
            [(10, 1, "Bilgisayar"), (20, 2, "Hemsirelik")],
        )
        cur.executemany(
            "INSERT INTO ders (ders_id, bolum_id, fakulte_id, ad, kod, DersTipi) VALUES (?, ?, ?, ?, ?, 'Secmeli')",
            [
                (101, 10, 1, "Algoritmalar", "M101"),
                (102, 10, 1, "Yapay Zeka", "M102"),
                (201, 20, 2, "Onkoloji", "S201"),
            ],
        )
        _insert_curriculum(conn, 1, 10, 2022, [101], "Guz")
        _insert_curriculum(conn, 2, 20, 2022, [201], "Guz")

        for ders_id, fakulte_id, bolum_id in [(101, 1, 10), (102, 1, 10), (201, 2, 20)]:
            _insert_complete_metrics(conn, ders_id, 2022, "Guz")
            _insert_pool_row(conn, ders_id, 2022, fakulte_id, bolum_id, 1, 80.0)
        conn.commit()
        conn.close()

        engine = create_engine(f"sqlite:///{db_path}")
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        ai = HavuzAIEngine(session)

        df_scoped = ai._load_training_data(fakulte_id=1, yil=2022, curriculum_only=True)
        assert set(int(v) for v in df_scoped["ders_id"].tolist()) == {101}
        assert set(int(v) for v in df_scoped["fakulte_id"].tolist()) == {1}
        assert set(int(v) for v in df_scoped["yil"].tolist()) == {2022}

        df_faculty_year = ai._load_training_data(fakulte_id=1, yil=2022, curriculum_only=False)
        assert set(int(v) for v in df_faculty_year["ders_id"].tolist()) == {101, 102}
    finally:
        try:
            if session is not None:
                session.close()
        except Exception:
            pass
        try:
            os.unlink(db_path)
        except OSError:
            pass


def test_import_api_requires_explicit_target_year():
    signature = inspect.signature(routes.mufredat_yukle)
    param = signature.parameters["hedef_yil"]
    assert hasattr(param.default, "default")
    assert param.default.default != 2022
    assert "PydanticUndefined" in repr(param.default)


def test_only_one_cross_department_course_allowed():
    db_path = _create_db()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("INSERT INTO fakulte VALUES (1, 'Muhendislik')")
        cur.executemany("INSERT INTO bolum VALUES (?, 1, ?)", [(10, "Bilgisayar"), (11, "Endustri")])
        cur.executemany(
            "INSERT INTO ders (ders_id, bolum_id, fakulte_id, ad, kod, DersTipi) VALUES (?, ?, 1, ?, ?, 'Secmeli')",
            [
                (101, 10, "A-101", "A101"),
                (102, 10, "A-102", "A102"),
                (103, 10, "A-103", "A103"),
                (104, 10, "A-104", "A104"),
                (105, 10, "A-105", "A105"),
                (201, 11, "B-201", "B201"),
                (202, 11, "B-202", "B202"),
                (203, 11, "B-203", "B203"),
            ],
        )

        _insert_curriculum(conn, 1, 10, 2022, [101, 102, 103, 104], "Guz")
        _insert_curriculum(conn, 1, 11, 2022, [201], "Guz")

        _insert_complete_metrics(conn, 101, 2022, "Guz", gecen=20, ortalama=40.0, kayitli=10)
        _insert_complete_metrics(conn, 102, 2022, "Guz", gecen=22, ortalama=41.0, kayitli=12)
        _insert_complete_metrics(conn, 103, 2022, "Guz", gecen=88, ortalama=82.0, kayitli=44)
        _insert_complete_metrics(conn, 104, 2022, "Guz", gecen=86, ortalama=80.0, kayitli=43)
        _insert_complete_metrics(conn, 105, 2022, "Guz", gecen=85, ortalama=79.0, kayitli=42)
        _insert_complete_metrics(conn, 201, 2022, "Guz", gecen=95, ortalama=90.0, kayitli=48)
        _insert_complete_metrics(conn, 202, 2022, "Guz", gecen=94, ortalama=89.0, kayitli=47)
        _insert_complete_metrics(conn, 203, 2022, "Guz", gecen=93, ortalama=88.0, kayitli=46)

        for ders_id, statu in [(101, 1), (102, 1), (103, 1), (104, 1), (105, 0), (201, 0), (202, 0), (203, 0)]:
            _insert_pool_row(conn, ders_id, 2022, 1, 10 if ders_id < 200 else 11, statu)
        conn.commit()
        conn.close()

        result = generate_next_year_curricula(
            db_path=db_path,
            fakulte_id=1,
            akademik_yil=2022,
            donem="G",
        )
        assert result.get("ok") is True

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*)
            FROM mufredat m
            JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
            JOIN ders d ON d.ders_id = md.ders_id
            WHERE m.bolum_id = 10
              AND m.akademik_yil = 2023
              AND d.bolum_id <> 10
            """
        )
        dis_bolum_adet = int(cur.fetchone()[0] or 0)
        conn.close()
        assert dis_bolum_adet <= 1
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass
