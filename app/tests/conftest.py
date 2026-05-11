# -*- coding: utf-8 -*-
"""
Adil Seçmeli — Pytest ortak fixture'lar.

Her test izole SQLite DB üzerinde çalışır.
Ana data/adil_secmeli.db dosyasına ASLA yazılmaz.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest


# ---------------------------------------------------------------------------
# Temel DB fixture
# ---------------------------------------------------------------------------

def _create_base_schema(conn: sqlite3.Connection) -> None:
    """Temel veritabani şemasını oluşturur (minimal)."""
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS fakulte (
            fakulte_id INTEGER PRIMARY KEY, ad TEXT, kampus TEXT
        );
        CREATE TABLE IF NOT EXISTS bolum (
            bolum_id INTEGER PRIMARY KEY, ad TEXT, fakulte_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS ders (
            ders_id INTEGER PRIMARY KEY, kod TEXT, ad TEXT, kredi INTEGER,
            akts INTEGER, fakulte_id INTEGER, bolum_id INTEGER, tip TEXT,
            DersTipi TEXT
        );
        CREATE TABLE IF NOT EXISTS mufredat (
            mufredat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fakulte_id INTEGER, akademik_yil INTEGER,
            bolum_id INTEGER, donem TEXT
        );
        CREATE TABLE IF NOT EXISTS mufredat_ders (
            mders_id INTEGER PRIMARY KEY AUTOINCREMENT,
            mufredat_id INTEGER, ders_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS havuz (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id TEXT, yil INTEGER, statu INTEGER,
            sayac INTEGER, fakulte_id INTEGER, bolum_id INTEGER,
            skor REAL, ders_adi TEXT, donem TEXT DEFAULT 'Guz'
        );
        CREATE TABLE IF NOT EXISTS skor (
            skor_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER, akademik_yil INTEGER, donem TEXT DEFAULT 'Guz',
            b_norm REAL, p_norm REAL, a_norm REAL, g_norm REAL,
            skor_top REAL, hesap_tarih TEXT
        );
        CREATE TABLE IF NOT EXISTS ders_kriterleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER NOT NULL, yil INTEGER NOT NULL,
            donem TEXT NOT NULL DEFAULT 'Guz',
            toplam_ogrenci INTEGER DEFAULT 0,
            gecen_ogrenci INTEGER DEFAULT 0,
            basari_ortalamasi REAL DEFAULT 0.0,
            kontenjan INTEGER DEFAULT 0,
            kayitli_ogrenci INTEGER DEFAULT 0,
            anket_katilimci INTEGER DEFAULT 0,
            anket_dersi_secen INTEGER DEFAULT 0,
            anket_veri_kaynagi TEXT DEFAULT 'manual',
            anket_manual_locked INTEGER NOT NULL DEFAULT 0,
            anket_import_id INTEGER,
            anket_imported_at TEXT,
            criteria_import_id INTEGER,
            criteria_veri_kaynagi TEXT DEFAULT 'manual',
            criteria_manual_override INTEGER NOT NULL DEFAULT 0,
            criteria_updated_at TEXT,
            UNIQUE(ders_id, yil, donem)
        );
        CREATE TABLE IF NOT EXISTS performans (
            pfrs_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER, akademik_yil INTEGER,
            basari_orani REAL, ortalama_not REAL
        );
        CREATE TABLE IF NOT EXISTS populerlik (
            pop_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ders_id INTEGER, akademik_yil INTEGER,
            doluluk_orani REAL, kontenjan INTEGER
        );
    """)
    conn.commit()


@pytest.fixture
def empty_db(tmp_path):
    """Temiz, bos SQLite veritabani (gecici dosya)."""
    db_path = str(tmp_path / "test_empty.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _create_base_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def memory_db():
    """In-memory SQLite DB fixture."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    _create_base_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def golden_db(tmp_path):
    """Golden dataset ile seed edilmis DB."""
    from app.tests.fixtures.test_db_builders import create_golden_db
    db_path = str(tmp_path / "golden.db")
    conn = create_golden_db(db_path)
    yield conn
    conn.close()


@pytest.fixture
def state_machine_db(tmp_path):
    """Pool state machine testleri icin hazir DB."""
    from app.tests.fixtures.test_db_builders import create_state_machine_db
    db_path = str(tmp_path / "state_machine.db")
    conn = create_state_machine_db(db_path)
    yield conn
    conn.close()
