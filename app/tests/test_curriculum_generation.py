import os
import sqlite3
import tempfile

from app.services.calculation import (
    auto_generate_next_year_curricula,
    generate_next_year_curricula,
    get_faculty_year_topsis_results,
)
from app.services.course_analyzer import analyze_single_course


def _build_generation_db() -> str:
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
            id INTEGER PRIMARY KEY,
            ders_id TEXT,
            yil INTEGER,
            fakulte_id INTEGER,
            bolum_id INTEGER,
            statu INTEGER,
            sayac INTEGER,
            skor REAL,
            ders_adi TEXT
        );
        """
    )

    cur.execute("INSERT INTO fakulte VALUES (2, 'Muhendislik')")
    cur.execute("INSERT INTO bolum VALUES (10, 2, 'Bilgisayar')")

    dersler = [
        (101, 10, 2, "DropAvg", "Secmeli"),
        (102, 10, 2, "DropScore", "Secmeli"),
        (103, 10, 2, "Keep", "Secmeli"),
        (104, 10, 2, "Aday1", "Secmeli"),
        (105, 10, 2, "Aday2", "Secmeli"),
    ]
    cur.executemany("INSERT INTO ders VALUES (?,?,?,?,?)", dersler)

    cur.execute(
        "INSERT INTO mufredat (mufredat_id, fakulte_id, akademik_yil, bolum_id, donem, durum, versiyon) VALUES (1,2,2023,10,'G','Resmi',1)"
    )
    cur.executemany(
        "INSERT INTO mufredat_ders (mders_id, mufredat_id, ders_id) VALUES (?,?,?)",
        [(1, 1, 101), (2, 1, 102), (3, 1, 103)],
    )

    kriterler = [
        # ders_id, toplam, gecen, ort_not, kont, kayitli, anket_kat, anket_sec
        (101, 100, 95, 40.0, 50, 45, 100, 90),   # score yuksek olsa da ortalama not dusuk
        (102, 100, 20, 80.0, 50, 10, 100, 20),   # ortalama not iyi ama score dusuk
        (103, 100, 88, 82.0, 50, 44, 100, 85),   # kalacak
        (104, 100, 85, 78.0, 50, 42, 100, 80),   # aday
        (105, 100, 82, 76.0, 50, 40, 100, 75),   # aday
    ]
    for idx, (ders_id, toplam, gecen, ort_not, kont, kayitli, an_kat, an_sec) in enumerate(kriterler, start=1):
        cur.execute(
            """
            INSERT INTO ders_kriterleri
            (id, ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, kontenjan, kayitli_ogrenci, aktif_mi, anket_katilimci, anket_dersi_secen)
            VALUES (?, ?, 2023, 'G', ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (idx, ders_id, toplam, gecen, ort_not, kont, kayitli, an_kat, an_sec),
        )

    perf_rows = [
        (1, 101, 2023, "G", 40.0, 0.95),
        (2, 102, 2023, "G", 80.0, 0.20),
        (3, 103, 2023, "G", 82.0, 0.88),
        (4, 104, 2023, "G", 78.0, 0.85),
        (5, 105, 2023, "G", 76.0, 0.82),
        (6, 101, 2022, "G", 65.0, 0.70),
        (7, 102, 2022, "G", 70.0, 0.65),
        (8, 103, 2022, "G", 72.0, 0.68),
        (9, 104, 2022, "G", 71.0, 0.67),
        (10, 105, 2022, "G", 70.0, 0.66),
    ]
    cur.executemany("INSERT INTO performans VALUES (?,?,?,?,?,?)", perf_rows)

    pop_rows = [
        (1, 101, 2023, "G", 45, 50, 0.90),
        (2, 102, 2023, "G", 10, 50, 0.20),
        (3, 103, 2023, "G", 44, 50, 0.88),
        (4, 104, 2023, "G", 42, 50, 0.84),
        (5, 105, 2023, "G", 40, 50, 0.80),
    ]
    cur.executemany("INSERT INTO populerlik VALUES (?,?,?,?,?,?,?)", pop_rows)

    havuz_rows = [
        (1, "101", 2023, 2, 10, 1, 0, None, "DropAvg"),
        (2, "102", 2023, 2, 10, 1, 1, None, "DropScore"),
        (3, "103", 2023, 2, 10, 1, 0, None, "Keep"),
        (4, "104", 2023, 2, 10, 0, 0, None, "Aday1"),
        (5, "105", 2023, 2, 10, 0, 0, None, "Aday2"),
    ]
    cur.executemany("INSERT INTO havuz VALUES (?,?,?,?,?,?,?,?,?)", havuz_rows)

    conn.commit()
    conn.close()
    return path


def test_single_and_bulk_topsis_consistency():
    path = _build_generation_db()
    conn = sqlite3.connect(path)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        pack = get_faculty_year_topsis_results(cur, fakulte_id=2, akademik_yil=2023, donem="G")
        assert pack.get("ok") is True
        bulk_score = pack["scores"][103]
    finally:
        conn.close()

    try:
        single = analyze_single_course(103, 2023, path)
        assert "error" not in single
        assert single["decision"]["score_final"] == bulk_score
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def test_drop_rule_reasons_and_state_machine():
    path = _build_generation_db()
    try:
        result = generate_next_year_curricula(path, fakulte_id=2, akademik_yil=2023, donem="G")
        assert result.get("ok") is True

        dept = result["departments"][0]
        dropped = {item["ders_id"]: item for item in dept["dusenler"]}
        assert 101 in dropped
        assert 102 in dropped
        assert any("Gecme not ortalamasi 45 altinda" in r for r in dropped[101]["reasons"])
        assert any("Kesinlesme puani 40 altinda" in r for r in dropped[102]["reasons"])

        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT statu, sayac FROM havuz WHERE ders_id='101' AND yil=2024")
        s1 = cur.fetchone()
        cur.execute("SELECT statu, sayac FROM havuz WHERE ders_id='102' AND yil=2024")
        s2 = cur.fetchone()
        conn.close()

        assert s1 == (-1, 1)   # ilk dusus -> dinlenme
        assert s2 == (-2, 2)   # ikinci dusus -> kalici iptal
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def test_auto_and_manual_generation_and_year_based_scores():
    path = _build_generation_db()
    try:
        auto = auto_generate_next_year_curricula(path, donem="G")
        assert auto.get("ok") is True
        assert any(item.get("year_from") == 2023 and item.get("year_to") == 2024 for item in auto.get("generated", []))

        manual = generate_next_year_curricula(path, fakulte_id=2, akademik_yil=2023, donem="G")
        assert manual.get("ok") is True

        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM havuz WHERE yil=2023 AND skor IS NOT NULL")
        y2023_scored = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM havuz WHERE yil=2024 AND skor IS NOT NULL")
        y2024_scored = cur.fetchone()[0]
        conn.close()

        assert y2023_scored > 0
        assert y2024_scored == 0
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
