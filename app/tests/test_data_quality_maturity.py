# -*- coding: utf-8 -*-
"""Veri olgunluk formülü v2 — müfredat-tabanlı, anket zorunlu değil.

Kullanıcı kuralları:
- Kriter/performans/popülerlik YALNIZCA müfredattaki dersler için zorunlu.
- Müfredat dışı (havuz) dersler eksik veri yüzünden olgunluğu DÜŞÜRMEZ.
- Anket hiçbir ders için zorunlu değil; eksikliği olgunluğu düşürmez.
"""

from __future__ import annotations

import sqlite3

from app.services.data_quality_integration_service import (
    assess_data_readiness_cursor,
    generate_coverage_report_cursor,
)

YEAR = 2022


def _build(curriculum_full: bool = True, pool_courses: int = 50, with_survey: bool = False):
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
        CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
        CREATE TABLE ders (ders_id INTEGER PRIMARY KEY, kod TEXT, ad TEXT, fakulte_id INTEGER, bolum_id INTEGER);
        CREATE TABLE mufredat (mufredat_id INTEGER PRIMARY KEY AUTOINCREMENT, fakulte_id INTEGER,
                               bolum_id INTEGER, akademik_yil INTEGER, donem TEXT);
        CREATE TABLE mufredat_ders (mders_id INTEGER PRIMARY KEY AUTOINCREMENT, mufredat_id INTEGER, ders_id INTEGER);
        CREATE TABLE ders_kriterleri (id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id INTEGER, yil INTEGER);
        CREATE TABLE performans (id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id INTEGER, akademik_yil INTEGER, basari_orani REAL);
        CREATE TABLE populerlik (id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id INTEGER, akademik_yil INTEGER, doluluk_orani REAL);
        CREATE TABLE anket_sonuclari (id INTEGER PRIMARY KEY AUTOINCREMENT, ders_id INTEGER, oy_sayisi INTEGER);
        """
    )
    cur.execute("INSERT INTO fakulte VALUES (1, 'Test')")
    cur.execute("INSERT INTO bolum VALUES (10, 1, 'Bolum')")
    cur.execute("INSERT INTO mufredat (fakulte_id, bolum_id, akademik_yil, donem) VALUES (1, 10, ?, 'Guz')", (YEAR,))
    mid = int(cur.lastrowid)

    # 2 müfredat dersi
    for cid in (101, 102):
        cur.execute("INSERT INTO ders VALUES (?, ?, ?, 1, 10)", (cid, f"K{cid}", f"Ders {cid}"))
        cur.execute("INSERT INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?)", (mid, cid))
    # kriter/perf/pop: tam ya da bir ders eksik
    hedef = (101, 102) if curriculum_full else (101,)
    for cid in hedef:
        cur.execute("INSERT INTO ders_kriterleri (ders_id, yil) VALUES (?, ?)", (cid, YEAR))
        cur.execute("INSERT INTO performans (ders_id, akademik_yil, basari_orani) VALUES (?, ?, 0.8)", (cid, YEAR))
        cur.execute("INSERT INTO populerlik (ders_id, akademik_yil, doluluk_orani) VALUES (?, ?, 0.9)", (cid, YEAR))

    # Müfredat DIŞI havuz dersleri — veri YOK, olgunluğu düşürmemeli
    for i in range(pool_courses):
        cur.execute("INSERT INTO ders VALUES (?, ?, ?, 1, 10)", (1000 + i, f"H{i}", f"Havuz {i}"))

    if with_survey:
        cur.execute("INSERT INTO anket_sonuclari (ders_id, oy_sayisi) VALUES (101, 40)")
    conn.commit()
    return conn


def test_pool_courses_do_not_lower_maturity():
    conn = _build(curriculum_full=True, pool_courses=50, with_survey=False)
    cur = conn.cursor()
    r = assess_data_readiness_cursor(cur, YEAR, faculty_id=1)
    # 2 müfredat dersi tam → kriter/perf/pop %100; 50 havuz dersi etkilememeli.
    assert r["required_courses"] == 2
    assert r["total_courses"] >= 52
    assert r["criteria_score"] == 100.0
    assert r["performance_score"] == 100.0
    assert r["popularity_score"] == 100.0
    assert r["readiness_score"] == 100.0
    assert r["readiness_level"] == "decision_ready"


def test_survey_absence_does_not_lower_maturity():
    conn = _build(curriculum_full=True, pool_courses=10, with_survey=False)
    cur = conn.cursor()
    r = assess_data_readiness_cursor(cur, YEAR, faculty_id=1)
    # Anket hiç yok ama olgunluk yine 100 olmalı (anket zorunlu değil).
    assert r["survey_required"] is False
    assert r["survey_score"] == 0.0
    assert r["readiness_score"] == 100.0


def test_missing_curriculum_criterion_lowers_score():
    conn = _build(curriculum_full=False, pool_courses=0, with_survey=False)
    cur = conn.cursor()
    r = assess_data_readiness_cursor(cur, YEAR, faculty_id=1)
    # 2 müfredat dersinden 1'i eksik → kriter %50.
    assert r["required_courses"] == 2
    assert r["criteria_score"] == 50.0


def test_coverage_uses_curriculum_denominator():
    conn = _build(curriculum_full=True, pool_courses=30, with_survey=True)
    cur = conn.cursor()
    c = generate_coverage_report_cursor(cur, YEAR, faculty_id=1)
    assert c["required_courses"] == 2
    assert c["total_all_courses"] >= 32
    assert c["courses_with_criteria"] == 2
    assert c["coverage_percentage"] == 100.0
    assert c["survey_required"] is False
