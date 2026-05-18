# -*- coding: utf-8 -*-

import os
import sqlite3
import tempfile

from app.db.schema_compat import ensure_decision_governance_schema
from app.services.ahp_profile_service import (
    create_ahp_profile,
    ensure_default_ahp_profile,
    resolve_ahp_profile,
)
from app.services.data_confidence_service import calculate_data_confidence
from app.services.decision_policy_service import (
    classify_score,
    create_decision_policy,
    ensure_default_decision_policy,
    resolve_decision_policy,
)
from app.services.decision_run_service import (
    _apply_governance,
    record_decision_run_for_faculty_year,
)
from app.services.explanation_engine import build_decision_explanation
from app.services.havuz_karar import STATU_DINLENMEDE, STATU_HAVUZDA, STATU_IPTAL
from app.services.trend_analysis_service import analyze_trend_values


def _tmp_conn():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    ensure_decision_governance_schema(conn)
    return path, conn


def _create_integration_db():
    path, conn = _tmp_conn()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE fakulte (fakulte_id INTEGER PRIMARY KEY, ad TEXT);
        CREATE TABLE bolum (bolum_id INTEGER PRIMARY KEY, fakulte_id INTEGER, ad TEXT);
        CREATE TABLE ders (
            ders_id INTEGER PRIMARY KEY,
            kod TEXT,
            ad TEXT,
            fakulte_id INTEGER,
            bolum_id INTEGER,
            DersTipi TEXT
        );
        CREATE TABLE mufredat (
            mufredat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            fakulte_id INTEGER,
            bolum_id INTEGER,
            akademik_yil INTEGER,
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
    cur.execute("INSERT INTO fakulte VALUES (1, 'Muhendislik')")
    cur.execute("INSERT INTO bolum VALUES (10, 1, 'Bilgisayar')")
    cur.execute("INSERT INTO ders VALUES (101, 'BLM101', 'Algoritmalar', 1, 10, 'Secmeli')")
    cur.execute("INSERT INTO mufredat (fakulte_id, bolum_id, akademik_yil, donem, durum, versiyon) VALUES (1, 10, 2025, 'Guz', 'Resmi', 1)")
    cur.execute("INSERT INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, 101)", (cur.lastrowid,))
    cur.executemany(
        "INSERT INTO performans (ders_id, akademik_yil, donem, ortalama_not, basari_orani) VALUES (101, ?, 'Guz', ?, ?)",
        [(2024, 75.0, 0.72), (2025, 82.0, 0.82)],
    )
    cur.execute(
        """
        INSERT INTO populerlik (ders_id, akademik_yil, donem, talep_sayisi, kontenjan, doluluk_orani)
        VALUES (101, 2025, 'Guz', 45, 50, 0.90)
        """
    )
    cur.execute(
        """
        INSERT INTO ders_kriterleri
            (ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi,
             kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen)
        VALUES (101, 2025, 'Guz', 100, 82, 82.0, 50, 45, 30, 24)
        """
    )
    cur.execute(
        "INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, donem, statu, sayac, skor, ders_adi) VALUES ('101', 2025, 1, 10, 'Guz', 1, 0, 80.0, 'Algoritmalar')"
    )
    conn.commit()
    return path, conn


def test_ahp_default_profile_and_scope_resolution():
    path, conn = _tmp_conn()
    try:
        profile = ensure_default_ahp_profile(conn)
        assert profile["is_consistent"] is True
        assert abs(sum(profile["weights"].values()) - 1.0) < 1e-9
        department_profile = create_ahp_profile(
            conn,
            name="Bolum 2026",
            scope_type="department",
            faculty_id=1,
            department_id=10,
            year=2026,
            weights={"basari": 0.5, "trend": 0.2, "populerlik": 0.2, "anket": 0.1},
        )
        resolved = resolve_ahp_profile(conn, faculty_id=1, department_id=10, year=2026)
        assert resolved["id"] == department_profile["id"]
        assert resolved["consistency_ratio"] <= 0.10
    finally:
        conn.close()
        os.unlink(path)


def test_decision_policy_defaults_and_scope_resolution():
    path, conn = _tmp_conn()
    try:
        default = ensure_default_decision_policy(conn)
        assert default["rest_threshold"] == 40.0
        faculty_policy = create_decision_policy(
            conn,
            name="Fakulte 2026",
            scope_type="faculty",
            faculty_id=1,
            year=2026,
            rest_threshold=45.0,
        )
        resolved = resolve_decision_policy(conn, faculty_id=1, department_id=10, year=2026)
        assert resolved["id"] == faculty_policy["id"]
        assert classify_score(20.0, resolved)["recommended_status"] == STATU_IPTAL
    finally:
        conn.close()
        os.unlink(path)


def test_data_confidence_levels():
    high = calculate_data_confidence(True, True, True, True, True, survey_count=20, data_points_count=3)
    low = calculate_data_confidence(False, False, True, False, False, survey_count=2, data_points_count=0)
    assert high["level"] == "high"
    assert low["level"] == "low"
    assert "basari" in low["missing_fields"]


def test_trend_labels():
    assert analyze_trend_values({2023: 0.45, 2024: 0.60, 2025: 0.75})["trend_label"] == "rising"
    assert analyze_trend_values({2023: 0.75, 2024: 0.60, 2025: 0.45})["trend_label"] == "falling"
    assert analyze_trend_values({2023: 0.60, 2024: 0.61, 2025: 0.60})["trend_label"] == "stable"
    assert analyze_trend_values({2023: 0.20, 2024: 0.85, 2025: 0.25})["trend_label"] == "volatile"
    assert analyze_trend_values({})["trend_label"] == "insufficient_data"


def test_explanation_for_low_score_trend_and_confidence():
    explanation = build_decision_explanation(
        course_code="BLM412",
        course_name="Veri Madenciligi",
        decision={
            "course_id": 412,
            "recommended_status": STATU_DINLENMEDE,
            "final_status": STATU_DINLENMEDE,
            "topsis_score": 35.0,
            "approval_required": True,
            "rule_triggered": "rest_threshold",
        },
        trend={"trend_label": "falling"},
        confidence={"level": "low"},
    )
    assert "Dusuk TOPSIS" in explanation["main_reason"]
    assert "akademik inceleme" in explanation["human_readable_text"]
    assert "Bu karar akademik onay gerektirir" in explanation["human_readable_text"]


def test_governance_blocks_automatic_cancel_for_manual_new_and_strategic():
    policy = {"require_manual_approval_for_cancel": True, "new_course_grace_period_years": 2, "low_data_confidence_threshold": 0.5}
    result = _apply_governance(
        recommended_status=STATU_IPTAL,
        old_status=STATU_HAVUZDA,
        year=2026,
        policy=policy,
        governance={"strategic_flag": True, "accreditation_flag": False, "protected_until_year": None},
        confidence={"score": 0.80},
        first_seen_year=2026,
    )
    assert result["approval_required"] is True
    assert result["final_status"] != STATU_IPTAL
    assert "Stratejik" in result["approval_reason"]


def test_decision_run_integration_writes_core_records():
    path, conn = _create_integration_db()
    try:
        result = record_decision_run_for_faculty_year(conn, year=2025, faculty_id=1, semester="Guz")
        conn.commit()
        assert result["ok"] is True
        run_id = result["decision_run_id"]
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM course_decisions WHERE decision_run_id = ?", (run_id,))
        assert cur.fetchone()[0] == 1
        cur.execute("SELECT COUNT(*) FROM course_decision_explanations")
        assert cur.fetchone()[0] == 1
        cur.execute("SELECT COUNT(*) FROM decision_fairness_reports WHERE decision_run_id = ?", (run_id,))
        assert cur.fetchone()[0] == 1
    finally:
        conn.close()
        os.unlink(path)
