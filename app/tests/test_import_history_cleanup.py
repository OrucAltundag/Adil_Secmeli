# -*- coding: utf-8 -*-
"""Import geçmişi temizleme (arşiv tablosuna taşıma) testleri."""

from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from app.repositories.import_repository import (
    count_protected_import_batches,
    get_cleanable_import_batches,
    get_import_history,
)
from app.services.import_history_service import cleanup_import_history, preview_cleanup


def _build_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE import_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_type TEXT, original_filename TEXT, status TEXT,
            quality_score REAL, row_count INTEGER, uploaded_at TEXT, created_at TEXT
        );
        CREATE TABLE import_quality_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, import_batch_id INTEGER, score REAL
        );
        CREATE TABLE import_rollback_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, import_batch_id INTEGER, action TEXT
        );
        CREATE TABLE criteria_import (
            id INTEGER PRIMARY KEY AUTOINCREMENT, import_batch_id INTEGER
        );
        CREATE TABLE decision_run_import_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT, decision_run_id INTEGER, import_batch_id INTEGER
        );
        -- Gerçek veri tablosu: temizlemeden ETKİLENMEMELİ
        CREATE TABLE ders (ders_id INTEGER PRIMARY KEY, ad TEXT);
        """
    )
    batches = [
        (1, "criteria", "a.xlsx", "approved"),
        (2, "survey", "b.xlsx", "failed"),
        (3, "survey", "c.xlsx", "superseded"),
        (4, "survey", "d.xlsx", "superseded"),
        (5, "survey", "e.xlsx", "active"),
        (6, "survey", "f.xlsx", "rejected"),
        (7, "survey", "g.xlsx", "superseded"),
    ]
    cur.executemany(
        "INSERT INTO import_batches (id, import_type, original_filename, status) VALUES (?, ?, ?, ?)",
        batches,
    )
    # batch 7 superseded ama bir karara bağlı -> KORUNMALI
    cur.execute("INSERT INTO decision_run_import_sources (decision_run_id, import_batch_id) VALUES (99, 7)")
    # çocuk loglar
    for bid in (2, 3, 4, 6, 7):
        cur.execute("INSERT INTO import_quality_checks (import_batch_id, score) VALUES (?, 50)", (bid,))
        cur.execute("INSERT INTO import_rollback_logs (import_batch_id, action) VALUES (?, 'x')", (bid,))
    cur.execute("INSERT INTO criteria_import (import_batch_id) VALUES (1)")
    cur.execute("INSERT INTO ders (ders_id, ad) VALUES (1, 'Ders')")
    conn.commit()
    conn.close()
    return path


@pytest.fixture()
def conn():
    path = _build_db()
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    yield connection
    connection.close()
    try:
        os.unlink(path)
    except OSError:
        pass


def test_cleanable_excludes_protected_and_decision_linked(conn):
    cleanable = {int(r["id"]) for r in get_cleanable_import_batches(conn)}
    # 2(failed),3,4(superseded),6(rejected) temizlenebilir; 7 karara bağlı -> hariç
    assert cleanable == {2, 3, 4, 6}


def test_protected_count(conn):
    # approved(1) + active(5) + decision-linked(7) = 3
    assert count_protected_import_batches(conn) == 3


def test_preview(conn):
    pv = preview_cleanup(conn)
    assert pv["cleanable_count"] == 4
    assert pv["protected_count"] == 3


def test_cleanup_archives_and_purges(conn):
    result = cleanup_import_history(conn, user="tester")
    conn.commit()
    assert result["ok"] is True
    assert result["archived"] == 4
    assert result["protected"] == 3

    remaining = {int(r["id"]) for r in get_import_history(conn)}
    assert remaining == {1, 5, 7}  # korunanlar kaldı

    cur = conn.cursor()
    cur.execute("SELECT id, archived_by FROM import_batches_archive ORDER BY id")
    archived = cur.fetchall()
    assert {int(r[0]) for r in archived} == {2, 3, 4, 6}
    assert all(r[1] == "tester" for r in archived)

    # temizlenenlerin çocuk logları gitti, korunanların (7) kaldı
    cur.execute("SELECT DISTINCT import_batch_id FROM import_quality_checks ORDER BY import_batch_id")
    assert [int(r[0]) for r in cur.fetchall()] == [7]

    # gerçek veri tablosu dokunulmadı
    cur.execute("SELECT COUNT(*) FROM ders")
    assert int(cur.fetchone()[0]) == 1


def test_cleanup_idempotent_second_run(conn):
    cleanup_import_history(conn, user="t")
    conn.commit()
    second = cleanup_import_history(conn, user="t")
    conn.commit()
    assert second["archived"] == 0
    assert "Temizlenecek eski import kaydı yok" in second["message"]
