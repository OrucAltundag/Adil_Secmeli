# -*- coding: utf-8 -*-

import os
import sqlite3
import tempfile

from app.api import routes
from app.services.calculation import (
    generate_next_year_curricula,
    get_faculty_year_topsis_results,
    persist_faculty_year_topsis_scores,
)
from app.services.course_type import build_elective_predicate


def _build_pool_db() -> str:
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
        """
    )

    cur.executemany(
        "INSERT INTO fakulte VALUES (?, ?)",
        [(1, "Muhendislik"), (2, "Saglik")],
    )
    cur.executemany(
        "INSERT INTO bolum VALUES (?, ?, ?)",
        [
            (10, 1, "Bilgisayar"),
            (11, 1, "Endustri"),
            (20, 2, "Hemsirelik"),
        ],
    )

    # 101 low score elective, 102 strong elective, 103 required,
    # 111/112 elective in another department of the same faculty.
    cur.executemany(
        "INSERT INTO ders VALUES (?, ?, ?, ?, ?)",
        [
            (101, 10, 1, "A-Elective-Low", "Secmeli"),
            (102, 10, 1, "A-Elective-Strong", "Secmeli"),
            (103, 10, 1, "A-Required", "Zorunlu"),
            (111, 11, 1, "B-Elective-High", "Secmeli"),
            (112, 11, 1, "B-Elective-Alt", "Secmeli"),
            (201, 20, 2, "C-Elective-OtherFaculty", "Secmeli"),
        ],
    )

    # Source year curricula (2024 Guz).
    cur.executemany(
        """
        INSERT INTO mufredat (mufredat_id, fakulte_id, akademik_yil, bolum_id, donem, durum, versiyon)
        VALUES (?, ?, 2024, ?, 'Guz', 'Resmi', 1)
        """,
        [
            (1, 1, 10),
            (2, 1, 11),
            (3, 2, 20),
        ],
    )
    cur.executemany(
        "INSERT INTO mufredat_ders (mders_id, mufredat_id, ders_id) VALUES (?, ?, ?)",
        [
            (1, 1, 101),
            (2, 1, 102),
            (3, 1, 103),  # required course in source curriculum
            (4, 2, 111),
            (5, 3, 201),
        ],
    )

    # Metrics for 2024 Guz.
    kriter_rows = [
        (1, 101, 2024, "Guz", 100, 20, 40.0, 50, 45, 1, 100, 20),   # low
        (2, 102, 2024, "Guz", 100, 90, 85.0, 50, 45, 1, 100, 90),   # strong
        (3, 103, 2024, "Guz", 100, 95, 88.0, 50, 45, 1, 100, 95),   # required
        (4, 111, 2024, "Guz", 100, 94, 92.0, 50, 45, 1, 100, 95),   # top
        (5, 112, 2024, "Guz", 100, 88, 86.0, 50, 45, 1, 100, 85),   # alt
        (6, 201, 2024, "Guz", 100, 80, 78.0, 50, 45, 1, 100, 80),
    ]
    cur.executemany(
        """
        INSERT INTO ders_kriterleri
        (id, ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, kontenjan, kayitli_ogrenci, aktif_mi, anket_katilimci, anket_dersi_secen)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        kriter_rows,
    )

    perf_rows = [
        (1, 101, 2024, "Guz", 40.0, 0.20),
        (2, 102, 2024, "Guz", 85.0, 0.90),
        (3, 103, 2024, "Guz", 88.0, 0.95),
        (4, 111, 2024, "Guz", 92.0, 0.94),
        (5, 112, 2024, "Guz", 86.0, 0.88),
        (6, 201, 2024, "Guz", 78.0, 0.80),
    ]
    cur.executemany("INSERT INTO performans VALUES (?, ?, ?, ?, ?, ?)", perf_rows)

    pop_rows = [
        (1, 101, 2024, "Guz", 12, 50, 0.24),
        (2, 102, 2024, "Guz", 45, 50, 0.90),
        (3, 103, 2024, "Guz", 49, 50, 0.98),
        (4, 111, 2024, "Guz", 48, 50, 0.96),
        (5, 112, 2024, "Guz", 40, 50, 0.80),
        (6, 201, 2024, "Guz", 35, 50, 0.70),
    ]
    cur.executemany("INSERT INTO populerlik VALUES (?, ?, ?, ?, ?, ?, ?)", pop_rows)

    havuz_rows = [
        ("101", 2024, 1, 10, "Guz", 1, 0, 60.0, "A-Elective-Low"),
        ("102", 2024, 1, 10, "Guz", 1, 0, 70.0, "A-Elective-Strong"),
        ("103", 2024, 1, 10, "Guz", 1, 0, 80.0, "A-Required"),
        ("111", 2024, 1, 11, "Guz", 0, 0, 85.0, "B-Elective-High"),
        ("112", 2024, 1, 11, "Guz", 0, 0, 75.0, "B-Elective-Alt"),
        ("201", 2024, 2, 20, "Guz", 1, 0, 68.0, "C-Elective-OtherFaculty"),
    ]
    cur.executemany(
        """
        INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, donem, statu, sayac, skor, ders_adi)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        havuz_rows,
    )

    conn.commit()
    conn.close()
    return path


def test_pool_only_elective_courses():
    path = _build_pool_db()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        pack = get_faculty_year_topsis_results(cur, fakulte_id=1, akademik_yil=2024, donem="G")
        assert pack.get("ok") is True
        scored_ids = {int(d) for d in pack.get("scores", {}).keys()}
        assert 103 not in scored_ids
        assert scored_ids.issubset({101, 102, 111, 112})
    finally:
        conn.close()
        try:
            os.unlink(path)
        except OSError:
            pass


def test_required_courses_not_visible_in_pool(monkeypatch):
    path = _build_pool_db()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        pack = get_faculty_year_topsis_results(cur, fakulte_id=1, akademik_yil=2024, donem="G")
        assert pack.get("ok") is True
        persist_faculty_year_topsis_scores(
            cur=cur,
            fakulte_id=1,
            akademik_yil=2024,
            skor_map=pack.get("scores", {}),
            ders_meta=pack.get("ders_meta", {}),
            donem="G",
        )
        conn.commit()
    finally:
        conn.close()

    monkeypatch.setattr(routes, "_get_db_path", lambda: path)
    payload = routes.havuz_listesi(yil=2024, fakulte_id=1, donem="G")
    ders_ids = {int(row[0]) for row in payload["data"]}
    assert 103 not in ders_ids
    assert ders_ids.issubset({101, 102, 111, 112})

    try:
        os.unlink(path)
    except OSError:
        pass


def test_cross_department_faculty_pool_candidate_selection():
    path = _build_pool_db()
    try:
        result = generate_next_year_curricula(path, fakulte_id=1, akademik_yil=2024, donem="G")
        assert result.get("ok") is True
        dept10 = next(item for item in result["departments"] if int(item["bolum_id"]) == 10)
        added_ids = {int(item["ders_id"]) for item in dept10["eklenenler"]}
        assert 111 in added_ids
        added_item = next(item for item in dept10["eklenenler"] if int(item["ders_id"]) == 111)
        assert any("Fakulte ortak havuzu" in reason for reason in added_item.get("reasons", []))
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def test_same_course_not_used_in_both_semesters():
    path = _build_pool_db()
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        # Pre-create next year Bahar curriculum with course 111 for department 10.
        cur.execute(
            """
            INSERT INTO mufredat (mufredat_id, fakulte_id, akademik_yil, bolum_id, donem, durum, versiyon)
            VALUES (10, 1, 2025, 10, 'Bahar', 'Manual', 1)
            """
        )
        cur.execute(
            "INSERT INTO mufredat_ders (mders_id, mufredat_id, ders_id) VALUES (10, 10, 111)"
        )
        conn.commit()
    finally:
        conn.close()

    try:
        result = generate_next_year_curricula(path, fakulte_id=1, akademik_yil=2024, donem="G")
        assert result.get("ok") is True

        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT md.ders_id
                FROM mufredat m
                JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
                WHERE m.bolum_id = 10
                  AND m.akademik_yil = 2025
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = 'g'
            ) g
            JOIN (
                SELECT md.ders_id
                FROM mufredat m
                JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
                WHERE m.bolum_id = 10
                  AND m.akademik_yil = 2025
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = 'b'
            ) b ON g.ders_id = b.ders_id
            """
        )
        overlap_count = int(cur.fetchone()[0] or 0)
        assert overlap_count == 0
        conn.close()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def test_pool_filtering_by_faculty_department_year(monkeypatch):
    path = _build_pool_db()
    monkeypatch.setattr(routes, "_get_db_path", lambda: path)

    payload_a = routes.havuz_listesi(yil=2024, fakulte_id=1, bolum_id=10, donem="G")
    payload_b = routes.havuz_listesi(yil=2024, fakulte_id=1, bolum_id=11, donem="G")

    # Column order from /havuz:
    # ders_id, ad, yil, fakulte_id, donem, statu, sayac, skor, kaynak_bolum_id, kaynak_bolum
    bolum_ids_a = {int(row[8]) for row in payload_a["data"]}
    bolum_ids_b = {int(row[8]) for row in payload_b["data"]}
    assert bolum_ids_a == {10}
    assert bolum_ids_b == {11}

    # Also assert elective-only visibility.
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        predicate = build_elective_predicate(cur=cur, alias="d")
        cur.execute(
            f"""
            SELECT COUNT(*)
            FROM havuz h
            LEFT JOIN ders d ON CAST(h.ders_id AS INTEGER) = d.ders_id
            WHERE h.fakulte_id = 1 AND h.yil = 2024
              AND LOWER(SUBSTR(TRIM(COALESCE(h.donem, '')), 1, 1)) = 'g'
              AND NOT ({predicate})
            """
        )
        non_elective_count = int(cur.fetchone()[0] or 0)
        assert non_elective_count >= 1  # raw DB has legacy required rows
    finally:
        conn.close()
        try:
            os.unlink(path)
        except OSError:
            pass


def test_pool_sorted_by_kesinlesme_score_desc(monkeypatch):
    path = _build_pool_db()
    monkeypatch.setattr(routes, "_get_db_path", lambda: path)
    payload = routes.havuz_listesi(yil=2024, fakulte_id=1, donem="G")

    # Column order from /havuz:
    # ders_id, ad, yil, fakulte_id, donem, statu, sayac, skor, kaynak_bolum_id, kaynak_bolum
    scores = [float(row[7]) for row in payload["data"] if row[7] is not None]
    assert scores == sorted(scores, reverse=True)

    try:
        os.unlink(path)
    except OSError:
        pass
