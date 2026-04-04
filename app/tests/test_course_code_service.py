import os
import sqlite3
import tempfile

from app.services.course_code_service import (
    apply_missing_course_codes,
    build_course_code,
    preview_missing_course_codes,
)


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
            fakulte_id INTEGER
        );
        """
    )
    cur.executemany(
        "INSERT INTO fakulte (fakulte_id, ad) VALUES (?, ?)",
        [
            (1, 'Mühendislik'),
            (2, 'İlahiyat'),
        ],
    )
    cur.executemany(
        "INSERT INTO bolum (bolum_id, fakulte_id, ad) VALUES (?, ?, ?)",
        [
            (10, 1, 'Bilgisayar Mühendisliği'),
            (20, 2, 'Çocuk Gelişimi'),
        ],
    )
    cur.executemany(
        "INSERT INTO ders (ders_id, kod, ad, bolum_id, fakulte_id) VALUES (?, ?, ?, ?, ?)",
        [
            (25, None, 'Veri Yapıları', 10, 1),
            (30, '', 'Din Eğitimi', 20, None),
            (31, 'MEVCUT31', 'Dolu Kodlu Ders', 10, 1),
        ],
    )
    conn.commit()
    conn.close()
    return path


def test_build_course_code_normalizes_turkish_initials():
    assert build_course_code('Mühendislik', 'Bilgisayar Mühendisliği', 25) == 'MB25'
    assert build_course_code('İlahiyat', 'Çocuk Gelişimi', 30) == 'IC30'


def test_apply_missing_course_codes_updates_only_blank_rows():
    db_path = _build_db()
    try:
        preview = preview_missing_course_codes(db_path)
        assert int(preview["missing_count"]) == 2

        result = apply_missing_course_codes(db_path)
        assert result["ok"] is True
        assert int(result["updated_count"]) == 2
        assert int(result["remaining_blank_count"]) == 0

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT ders_id, kod FROM ders ORDER BY ders_id")
        rows = cur.fetchall()
        conn.close()

        assert rows == [
            (25, 'MB25'),
            (30, 'IC30'),
            (31, 'MEVCUT31'),
        ]
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass
