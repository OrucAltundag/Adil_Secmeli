# -*- coding: utf-8 -*-
"""
Test veritabani builder fonksiyonlari.

Her builder fonksiyonu tamamen izole, gecici bir SQLite DB olusturur.
Ana data/adil_secmeli.db dosyasina ASLA dokunmaz.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _create_base_schema(conn: sqlite3.Connection) -> None:
    """Minimum tablo yapisi."""
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


# ============================================================================
# Golden Dataset
# ============================================================================

# 8 ders — her biri farkli senaryo temsil eder
GOLDEN_COURSES = [
    # (ders_id, kod, ad, bolum_id, fakulte_id, tip)
    (1, "BIL301", "Yapay Zeka", 10, 1, "secmeli"),
    (2, "BIL302", "Veri Tabani", 10, 1, "secmeli"),
    (3, "BIL303", "Bilgi Guvenligi", 10, 1, "secmeli"),
    (4, "BIL304", "Mobil Programlama", 10, 1, "secmeli"),
    (5, "BIL305", "Oyun Gelistirme", 10, 1, "secmeli"),
    (6, "BIL306", "Robot Bilimi", 10, 1, "secmeli"),
    (7, "BIL307", "Web Teknolojileri", 10, 1, "secmeli"),
    (8, "BIL308", "Bulut Bilisim", 10, 1, "secmeli"),
]

# Kriter verileri (yil=2024, donem=Guz)
GOLDEN_CRITERIA = [
    # (ders_id, yil, donem, toplam, gecen, ort, kontenjan, kayitli, anket_kat, anket_secen)
    # Ders 1: Yuksek basari — mufredatta kalmali
    (1, 2024, "Guz", 60, 54, 78.5, 65, 60, 45, 38),
    # Ders 2: Yuksek basari — mufredatta kalmali
    (2, 2024, "Guz", 55, 48, 75.0, 60, 55, 40, 35),
    # Ders 3: Orta skor — havuza dusmeli
    (3, 2024, "Guz", 40, 24, 55.0, 50, 40, 30, 18),
    # Ders 4: Dusuk skor — dinlenmeye alinmali
    (4, 2024, "Guz", 30, 12, 40.0, 50, 30, 20, 8),
    # Ders 5: Cok dusuk skor — iptal adayi
    (5, 2024, "Guz", 20, 6, 30.0, 50, 20, 15, 4),
    # Ders 6: Stratejik ders — korumali
    (6, 2024, "Guz", 25, 10, 35.0, 50, 25, 18, 6),
    # Ders 7: Eksik veri — dusuk guvenli
    (7, 2024, "Guz", 15, 8, 50.0, 50, 15, 0, 0),
    # Ders 8: Ayni skor senaryosu (Ders 3 ile ayni basari orani)
    (8, 2024, "Guz", 40, 24, 55.0, 50, 40, 30, 18),
]

# Performans gecmisi (trend analizi icin)
GOLDEN_PERFORMANCE = [
    # Ders 1: Yukselis trendi
    (1, 2022, 0.78), (1, 2023, 0.85), (1, 2024, 0.90),
    # Ders 2: Stabil
    (2, 2022, 0.80), (2, 2023, 0.82), (2, 2024, 0.80),
    # Ders 3: Dusus trendi
    (3, 2022, 0.80), (3, 2023, 0.70), (3, 2024, 0.60),
    # Ders 4: Belirgin dusus
    (4, 2022, 0.65), (4, 2023, 0.50), (4, 2024, 0.40),
    # Ders 5: Cok dusuk
    (5, 2022, 0.40), (5, 2023, 0.35), (5, 2024, 0.30),
    # Ders 6: Dusuk ama stratejik
    (6, 2022, 0.50), (6, 2023, 0.45), (6, 2024, 0.40),
    # Ders 7: Tek yil — yeni ders
    (7, 2024, 0.53),
    # Ders 8: Stabil
    (8, 2022, 0.60), (8, 2023, 0.60), (8, 2024, 0.60),
]

# Beklenen siralamalar (TOPSIS ile esit agirliklar):
# Ders 1 > Ders 2 > Ders 3 = Ders 8 > Ders 4 > Ders 5
GOLDEN_EXPECTED_DECISIONS = {
    1: {"expected_status": "mufredatta", "trend": "rising"},
    2: {"expected_status": "mufredatta", "trend": "stable"},
    3: {"expected_status": "havuzda", "trend": "falling"},
    4: {"expected_status": "dinlenmede", "trend": "falling"},
    5: {"expected_status": "iptal_adayi", "trend": "falling"},
    6: {"expected_status": "korumali", "trend": "falling"},
    7: {"expected_status": "dusuk_guven", "trend": "insufficient_data"},
    8: {"expected_status": "havuzda", "trend": "stable"},
}


def create_empty_test_db(db_path: str | None = None) -> sqlite3.Connection:
    """Bos test DB olusturur."""
    conn = sqlite3.connect(db_path or ":memory:")
    conn.row_factory = sqlite3.Row
    _create_base_schema(conn)
    return conn


def seed_golden_dataset(conn: sqlite3.Connection) -> dict[str, Any]:
    """Golden dataset ile DB'yi doldurur."""
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO fakulte VALUES (1, 'Muhendislik', 'Ana Kampus')")
    cur.execute("INSERT OR IGNORE INTO bolum VALUES (10, 'Bilgisayar', 1)")

    for c in GOLDEN_COURSES:
        cur.execute(
            "INSERT OR IGNORE INTO ders VALUES (?, ?, ?, 3, 5, ?, ?, ?, ?)",
            (c[0], c[1], c[2], c[4], c[3], c[5], c[5]),
        )

    for k in GOLDEN_CRITERIA:
        cur.execute(
            """INSERT OR REPLACE INTO ders_kriterleri
            (ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci,
             basari_ortalamasi, kontenjan, kayitli_ogrenci,
             anket_katilimci, anket_dersi_secen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            k,
        )

    for p in GOLDEN_PERFORMANCE:
        cur.execute(
            "INSERT INTO performans (ders_id, akademik_yil, basari_orani) VALUES (?, ?, ?)",
            p,
        )

    conn.commit()
    return {
        "course_count": len(GOLDEN_COURSES),
        "criteria_count": len(GOLDEN_CRITERIA),
        "performance_count": len(GOLDEN_PERFORMANCE),
    }


def create_golden_db(db_path: str | None = None) -> sqlite3.Connection:
    """Golden dataset ile hazir DB olusturur."""
    conn = create_empty_test_db(db_path)
    seed_golden_dataset(conn)
    return conn


def seed_minimal_academic_structure(conn: sqlite3.Connection) -> None:
    """Minimum fakulte/bolum/ders yapisi olusturur."""
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO fakulte VALUES (1, 'Muhendislik', 'Ana')")
    cur.execute("INSERT OR IGNORE INTO fakulte VALUES (2, 'Saglik', 'Ana')")
    cur.execute("INSERT OR IGNORE INTO bolum VALUES (10, 'Bilgisayar', 1)")
    cur.execute("INSERT OR IGNORE INTO bolum VALUES (20, 'Hemsirelik', 2)")
    cur.execute("INSERT OR IGNORE INTO ders VALUES (101, 'BIL101', 'Algoritmalar', 3, 5, 1, 10, 'secmeli', 'secmeli')")
    cur.execute("INSERT OR IGNORE INTO ders VALUES (201, 'HEM201', 'Patoloji', 3, 5, 2, 20, 'secmeli', 'secmeli')")
    conn.commit()


def seed_edge_case_dataset(conn: sqlite3.Connection) -> None:
    """Uc durum verileri seed eder."""
    cur = conn.cursor()
    seed_minimal_academic_structure(conn)
    # Kontenjan 0 — division by zero riski
    cur.execute("""INSERT OR REPLACE INTO ders_kriterleri
        (ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi,
         kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen)
        VALUES (101, 2024, 'Guz', 30, 25, 75.0, 0, 0, 0, 0)""")
    # Gecen > Toplam — mantiksal tutarsizlik
    cur.execute("""INSERT OR REPLACE INTO ders_kriterleri
        (ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi,
         kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen)
        VALUES (201, 2024, 'Guz', 20, 25, 110.0, 50, 60, 10, 5)""")
    conn.commit()


def seed_large_synthetic_dataset(conn: sqlite3.Connection, size: int = 1000) -> None:
    """Buyuk sentetik veri seti olusturur (performans testleri icin)."""
    import random
    rng = random.Random(42)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO fakulte VALUES (1, 'Muhendislik', 'Ana')")
    cur.execute("INSERT OR IGNORE INTO bolum VALUES (10, 'Bilgisayar', 1)")
    for i in range(1, size + 1):
        cur.execute(
            "INSERT OR IGNORE INTO ders VALUES (?, ?, ?, 3, 5, 1, 10, 'secmeli', 'secmeli')",
            (i, f"BIL{i:04d}", f"Ders {i}"),
        )
        toplam = rng.randint(10, 80)
        gecen = rng.randint(0, toplam)
        cur.execute(
            """INSERT OR REPLACE INTO ders_kriterleri
            (ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci,
             basari_ortalamasi, kontenjan, kayitli_ogrenci,
             anket_katilimci, anket_dersi_secen)
            VALUES (?, 2024, 'Guz', ?, ?, ?, ?, ?, ?, ?)""",
            (i, toplam, gecen, rng.uniform(20, 95), rng.randint(20, 80),
             rng.randint(5, 70), rng.randint(0, 50), rng.randint(0, 40)),
        )
    conn.commit()


def create_state_machine_db(db_path: str | None = None) -> sqlite3.Connection:
    """Pool state machine testleri icin DB. Governance tablolari da olusturulur."""
    conn = create_empty_test_db(db_path)
    seed_golden_dataset(conn)
    try:
        from app.db.schema_compat import (
            ensure_pool_state_governance_schema,
            ensure_decision_governance_schema,
            ensure_architecture_schema,
        )
        ensure_architecture_schema(conn, commit=True)
        ensure_decision_governance_schema(conn, commit=True)
        ensure_pool_state_governance_schema(conn, commit=True)
    except Exception:
        # Schema compat fonksiyonlari henuz yuklenemeyebilir, sessizce gec.
        pass
    return conn
