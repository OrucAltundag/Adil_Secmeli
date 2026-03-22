# -*- coding: utf-8 -*-
# =============================================================================
# app/tests/test_similarity.py — Benzerlik motoru testleri
# =============================================================================
# SimilarityEngine için birim testleri; geçici SQLite veritabanı ile benzerlik
# hesaplarının doğrulanması.
# =============================================================================

import os
import sqlite3
import tempfile

from app.services.similarity_engine import SimilarityEngine


def _make_similarity_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE ders (
            ders_id INTEGER PRIMARY KEY,
            ad TEXT,
            bilgi TEXT
        );

        CREATE TABLE ders_iliski (
            kaynak_ders_id INTEGER,
            hedef_ders_id INTEGER,
            skor REAL,
            PRIMARY KEY (kaynak_ders_id, hedef_ders_id)
        );
        """
    )

    ders_rows = [
        (1, "Veri Yapilari", "bagli liste yigin kuyruk agac graf algoritma"),
        (2, "Algoritmalar", "graf algoritma dinamik programlama agac"),
        (3, "Veritabani", "sql iliski normalizasyon indeks sorgu"),
        (4, "Makine Ogrenmesi", "regresyon siniflandirma ogrenme model"),
    ]
    cur.executemany("INSERT INTO ders (ders_id, ad, bilgi) VALUES (?,?,?)", ders_rows)

    conn.commit()
    conn.close()
    return path


def test_get_similar_courses_returns_ranked_list():
    path = _make_similarity_db()
    try:
        engine = SimilarityEngine(path)
        results = engine.get_similar_courses(1, top_n=2)

        assert len(results) == 2
        assert all(r["ders_id"] != 1 for r in results)
        assert results[0]["skor"] >= results[1]["skor"]
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def test_compute_and_save_persists_relations():
    path = _make_similarity_db()
    try:
        engine = SimilarityEngine(path)
        engine.compute_and_save(1, top_n=3)

        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ders_iliski WHERE kaynak_ders_id = 1")
        saved_count = int(cur.fetchone()[0] or 0)
        cur.execute("SELECT MIN(skor), MAX(skor) FROM ders_iliski WHERE kaynak_ders_id = 1")
        min_skor, max_skor = cur.fetchone()
        conn.close()

        assert saved_count == 3
        assert min_skor is not None and max_skor is not None
        assert 0.0 <= float(min_skor) <= 1.0
        assert 0.0 <= float(max_skor) <= 1.0
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
