import os
import sqlite3
import tempfile

import pandas as pd

from app.services.criteria_import_service import (
    FACULTY_SCOPE_LABEL,
    get_active_criteria_import,
    import_criteria_excel,
    summarize_report_criteria_scope,
    write_criteria_template_excel,
)
from app.services.reporting_service import build_report_snapshot


class _DummyDB:
    def __init__(self, conn):
        self.conn = conn

    def run_sql(self, query, params=()):
        cur = self.conn.cursor()
        cur.execute(query, params)
        return cur, cur.fetchall()


def _build_db() -> str:
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
            bolum_id INTEGER,
            fakulte_id INTEGER,
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
        CREATE TABLE ders_kriterleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER,
            yil INTEGER,
            donem TEXT,
            toplam_ogrenci INTEGER DEFAULT 0,
            gecen_ogrenci INTEGER DEFAULT 0,
            basari_ortalamasi REAL DEFAULT 0.0,
            kontenjan INTEGER DEFAULT 0,
            kayitli_ogrenci INTEGER DEFAULT 0,
            anket_katilimci INTEGER DEFAULT 0,
            anket_dersi_secen INTEGER DEFAULT 0
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
        """
    )
    cur.execute("INSERT INTO fakulte VALUES (1, 'Muhendislik')")
    cur.executemany(
        "INSERT INTO bolum VALUES (?, 1, ?)",
        [
            (10, "Bilgisayar"),
            (11, "Endustri"),
        ],
    )
    cur.executemany(
        """
        INSERT INTO ders (ders_id, kod, ad, bolum_id, fakulte_id, DersTipi)
        VALUES (?, ?, ?, ?, 1, 'Secmeli')
        """,
        [
            (101, "C101", "Algoritmalar", 10),
            (201, "E201", "Uretim Planlama", 11),
        ],
    )
    cur.executemany(
        """
        INSERT INTO mufredat (fakulte_id, akademik_yil, bolum_id, donem, durum, versiyon)
        VALUES (1, 2024, ?, 'Guz', 'Resmi', 1)
        """,
        [
            (10,),
            (11,),
        ],
    )
    mid_rows = cur.execute(
        "SELECT mufredat_id, bolum_id FROM mufredat WHERE akademik_yil = 2024 ORDER BY bolum_id"
    ).fetchall()
    mid_map = {int(row[1]): int(row[0]) for row in mid_rows}
    cur.executemany(
        "INSERT INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?)",
        [
            (mid_map[10], 101),
            (mid_map[11], 201),
        ],
    )
    cur.executemany(
        """
        INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, donem, statu, sayac, skor, ders_adi)
        VALUES (?, 2024, 1, ?, 'Guz', 1, 0, ?, ?)
        """,
        [
            ("101", 10, 78.0, "Algoritmalar"),
            ("201", 11, 74.0, "Uretim Planlama"),
        ],
    )
    conn.commit()
    conn.close()
    return path


def _write_criteria_excel(
    rows: list[dict],
    *,
    meta_department: str | None = None,
    note: str | None = None,
) -> str:
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    meta_df = pd.DataFrame(
        [
            {
                "fakulte_adi": "Muhendislik",
                "bolum_adi": meta_department or FACULTY_SCOPE_LABEL,
                "yil": 2024,
                "donem": "Guz",
                "aciklama": note,
            }
        ]
    )
    with pd.ExcelWriter(path) as writer:
        meta_df.to_excel(writer, sheet_name="Meta", index=False)
        pd.DataFrame(rows).to_excel(writer, sheet_name="Kriterler", index=False)
    return path


def _cleanup(*paths: str | None):
    for path in paths:
        if not path:
            continue
        try:
            os.unlink(path)
        except OSError:
            pass


def test_import_criteria_tracks_document_and_report_summary():
    db_path = _build_db()
    excel_path = _write_criteria_excel(
        [
            {
                "fakulte_adi": "Muhendislik",
                "bolum_adi": "Bilgisayar",
                "yil": 2024,
                "donem": "Guz",
                "ders_kodu": "C101",
                "ders_adi": "Algoritmalar",
                "toplam_ogrenci": 80,
                "gecen_ogrenci": 60,
                "basari_ortalamasi": 72.5,
                "kontenjan": 50,
                "kayitli_ogrenci": 75,
            },
            {
                "fakulte_adi": "Muhendislik",
                "bolum_adi": "Endustri",
                "yil": 2024,
                "donem": "Guz",
                "ders_kodu": "E201",
                "ders_adi": "Uretim Planlama",
                "toplam_ogrenci": 90,
                "gecen_ogrenci": 54,
                "basari_ortalamasi": 68.0,
                "kontenjan": 40,
                "kayitli_ogrenci": 36,
            },
        ],
        note="Fakulte geneli ilk import",
    )
    try:
        result = import_criteria_excel(
            db_path=db_path,
            excel_path=excel_path,
            faculty_id=1,
            year=2024,
            term="Guz",
            source_filename="kriterler_v1.xlsx",
        )

        assert result["ok"] is True
        assert result["created_course_count"] == 2
        assert result["updated_course_count"] == 0

        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT row_no, matched_ders_id, row_status
                FROM criteria_import_rows
                WHERE import_id = ?
                ORDER BY row_no
                """,
                (int(result["import_id"]),),
            )
            assert cur.fetchall() == [
                (2, 101, "matched"),
                (3, 201, "matched"),
            ]

            cur.execute(
                """
                SELECT ders_id, criteria_import_id, criteria_veri_kaynagi, criteria_manual_override
                FROM ders_kriterleri
                WHERE yil = 2024
                ORDER BY ders_id
                """
            )
            assert cur.fetchall() == [
                (101, int(result["import_id"]), "criteria_import", 0),
                (201, int(result["import_id"]), "criteria_import", 0),
            ]

            active = get_active_criteria_import(conn, faculty_id=1, year=2024, term="Guz")
            assert active is not None
            assert int(active["import_id"]) == int(result["import_id"])
            assert active["department_name"] is None

            snapshot = build_report_snapshot(
                db=_DummyDB(conn),
                faculty_id=1,
                faculty_name="Muhendislik",
                year=2024,
                term="Guz",
            )
            summary = snapshot["criteria_import_summary"]
            assert summary["mode"] == "single"
            assert int(summary["active_import"]["import_id"]) == int(result["import_id"])
            assert "kriterler_v1.xlsx" in summary["display"]
            assert any("Kriter dosyasi:" in note for note in snapshot["notes"])
        finally:
            conn.close()
    finally:
        _cleanup(db_path, excel_path)


def test_pending_import_with_unmatched_row_reaches_review_queue():
    db_path = _build_db()
    excel_path = _write_criteria_excel(
        [
            {
                "fakulte_adi": "Muhendislik",
                "bolum_adi": "Bilgisayar",
                "yil": 2024,
                "donem": "Guz",
                "ders_kodu": "C101",
                "ders_adi": "Algoritmalar",
                "toplam_ogrenci": 80,
                "gecen_ogrenci": 60,
                "basari_ortalamasi": 72.5,
                "kontenjan": 50,
                "kayitli_ogrenci": 75,
            },
            {
                "fakulte_adi": "Muhendislik",
                "bolum_adi": "Bilgisayar",
                "yil": 2024,
                "donem": "Guz",
                "ders_kodu": "C999",
                "ders_adi": "Kapsamda Olmayan Ders",
                "toplam_ogrenci": 40,
                "gecen_ogrenci": 20,
                "basari_ortalamasi": 60.0,
                "kontenjan": 30,
                "kayitli_ogrenci": 28,
            },
        ]
    )
    try:
        result = import_criteria_excel(
            db_path=db_path,
            excel_path=excel_path,
            faculty_id=1,
            year=2024,
            term="Guz",
            source_filename="partial_match.xlsx",
            apply_now=False,
        )

        assert result["ok"] is True
        assert result["matched_count"] == 1
        assert result["unmatched_count"] == 1
        assert result["import_status"] == "pending_review"

        conn = sqlite3.connect(db_path)
        try:
            batch = conn.execute(
                "SELECT status, error_message FROM import_batches WHERE id = ?",
                (int(result["import_batch_id"]),),
            ).fetchone()
            assert batch == ("pending_review", None)
            issue = conn.execute(
                "SELECT issue_type, severity FROM import_row_issues WHERE import_batch_id = ?",
                (int(result["import_batch_id"]),),
            ).fetchone()
            assert issue == ("course_not_matched", "warning")
        finally:
            conn.close()
    finally:
        _cleanup(db_path, excel_path)


def test_faculty_reimport_preserves_department_override_metrics():
    db_path = _build_db()
    faculty_v1 = _write_criteria_excel(
        [
            {
                "fakulte_adi": "Muhendislik",
                "bolum_adi": "Bilgisayar",
                "yil": 2024,
                "donem": "Guz",
                "ders_kodu": "C101",
                "ders_adi": "Algoritmalar",
                "toplam_ogrenci": 100,
                "gecen_ogrenci": 80,
                "basari_ortalamasi": 70.0,
                "kontenjan": 50,
                "kayitli_ogrenci": 45,
            },
            {
                "fakulte_adi": "Muhendislik",
                "bolum_adi": "Endustri",
                "yil": 2024,
                "donem": "Guz",
                "ders_kodu": "E201",
                "ders_adi": "Uretim Planlama",
                "toplam_ogrenci": 120,
                "gecen_ogrenci": 90,
                "basari_ortalamasi": 66.0,
                "kontenjan": 60,
                "kayitli_ogrenci": 55,
            },
        ]
    )
    department_v1 = _write_criteria_excel(
        [
            {
                "fakulte_adi": "Muhendislik",
                "bolum_adi": "Bilgisayar",
                "yil": 2024,
                "donem": "Guz",
                "ders_kodu": "C101",
                "ders_adi": "Algoritmalar",
                "toplam_ogrenci": 50,
                "gecen_ogrenci": 25,
                "basari_ortalamasi": 55.0,
                "kontenjan": 30,
                "kayitli_ogrenci": 45,
            }
        ],
        meta_department="Bilgisayar",
    )
    faculty_v2 = _write_criteria_excel(
        [
            {
                "fakulte_adi": "Muhendislik",
                "bolum_adi": "Bilgisayar",
                "yil": 2024,
                "donem": "Guz",
                "ders_kodu": "C101",
                "ders_adi": "Algoritmalar",
                "toplam_ogrenci": 200,
                "gecen_ogrenci": 190,
                "basari_ortalamasi": 95.0,
                "kontenjan": 70,
                "kayitli_ogrenci": 65,
            },
            {
                "fakulte_adi": "Muhendislik",
                "bolum_adi": "Endustri",
                "yil": 2024,
                "donem": "Guz",
                "ders_kodu": "E201",
                "ders_adi": "Uretim Planlama",
                "toplam_ogrenci": 140,
                "gecen_ogrenci": 100,
                "basari_ortalamasi": 75.0,
                "kontenjan": 80,
                "kayitli_ogrenci": 60,
            },
        ]
    )
    try:
        faculty_first = import_criteria_excel(
            db_path=db_path,
            excel_path=faculty_v1,
            faculty_id=1,
            year=2024,
            term="Guz",
            source_filename="faculty_v1.xlsx",
        )
        department_import = import_criteria_excel(
            db_path=db_path,
            excel_path=department_v1,
            faculty_id=1,
            year=2024,
            term="Guz",
            department_id=10,
            source_filename="department_v1.xlsx",
        )
        faculty_second = import_criteria_excel(
            db_path=db_path,
            excel_path=faculty_v2,
            faculty_id=1,
            year=2024,
            term="Guz",
            source_filename="faculty_v2.xlsx",
        )

        assert faculty_first["ok"] is True
        assert department_import["ok"] is True
        assert faculty_second["ok"] is True
        assert faculty_second["replace"]["previous_imports_superseded"] == 1
        assert faculty_second["skipped_department_overrides"] == 1

        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT criteria_import_id, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, kontenjan, kayitli_ogrenci
                FROM ders_kriterleri
                WHERE ders_id = 101 AND yil = 2024
                """
            )
            assert cur.fetchone() == (
                int(department_import["import_id"]),
                50,
                25,
                55.0,
                30,
                45,
            )

            cur.execute(
                """
                SELECT ortalama_not, basari_orani
                FROM performans
                WHERE ders_id = 101 AND akademik_yil = 2024
                """
            )
            assert cur.fetchone() == (55.0, 0.5)

            cur.execute(
                """
                SELECT talep_sayisi, kontenjan, doluluk_orani
                FROM populerlik
                WHERE ders_id = 101 AND akademik_yil = 2024
                """
            )
            assert cur.fetchone() == (45, 30, 1.0)

            cur.execute(
                """
                SELECT row_status
                FROM criteria_import_rows
                WHERE import_id = ? AND matched_ders_id = 101
                LIMIT 1
                """,
                (int(faculty_second["import_id"]),),
            )
            assert cur.fetchone()[0] == "skipped_override"

            cur.execute(
                """
                SELECT criteria_import_id, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, kontenjan, kayitli_ogrenci
                FROM ders_kriterleri
                WHERE ders_id = 201 AND yil = 2024
                """
            )
            assert cur.fetchone() == (
                int(faculty_second["import_id"]),
                140,
                100,
                75.0,
                80,
                60,
            )

            summary = summarize_report_criteria_scope(conn, faculty_id=1, year=2024, term="Guz")
            assert summary["mode"] == "mixed"
            assert summary["department_specific_count"] == 1
        finally:
            conn.close()
    finally:
        _cleanup(db_path, faculty_v1, department_v1, faculty_v2)


def test_write_criteria_template_contains_scope_and_course_columns():
    db_path = _build_db()
    fd, target_path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    try:
        write_criteria_template_excel(
            target_path=target_path,
            db_path=db_path,
            faculty_id=1,
            department_id=10,
            year=2024,
            term="Guz",
        )

        data_df = pd.read_excel(target_path, sheet_name="Kriter")
        assert list(data_df.columns) == [
            "fakulte", "bolum", "yil", "donem", "ders_kodu", "ders_adi",
            "toplam_ogrenci", "gecen_ogrenci", "basari_ortalamasi",
            "kontenjan", "kayitli_ogrenci",
            "katilim_sayisi", "toplam_hafta", "katilim_yuzdesi",
            "devamsiz_ogrenci_sayisi",
        ]
        assert data_df[["fakulte", "bolum", "yil", "donem", "ders_kodu"]].to_dict("records") == [
            {
                "fakulte": "Muhendislik",
                "bolum": "Bilgisayar",
                "yil": 2024,
                "donem": "Güz",
                "ders_kodu": "C101",
            }
        ]
    finally:
        _cleanup(db_path, target_path)
