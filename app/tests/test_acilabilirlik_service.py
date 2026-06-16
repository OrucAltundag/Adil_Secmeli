# -*- coding: utf-8 -*-
"""Açılabilirlik skoru servisi testleri (Faz 3)."""

from __future__ import annotations

import sqlite3

from app.services.acilabilirlik_service import (
    KATEGORI_DINLENME,
    KATEGORI_GUCLU,
    KATEGORI_HAVUZ,
    KATEGORI_IPTAL,
    KATEGORI_SARTLI,
    categorize_recommendation,
    compute_acilabilirlik_score,
    derive_talep_score,
    list_recommended_courses,
)


class TestComputeScore:
    def test_full_formula_with_defaults(self):
        # nihai_senaryo.md §4 ornegi:
        # 0.45*80 + 0.25*70 + 0.15*60 + 0.10*100 + 0.05*100
        # = 36 + 17.5 + 9 + 10 + 5 = 77.5
        score = compute_acilabilirlik_score(
            topsis_score=80,
            talep_score=70,
            veri_guveni=60,
        )
        assert score == 77.5

    def test_all_max_is_100(self):
        assert compute_acilabilirlik_score(100, 100, 100, 100, 100) == 100.0

    def test_all_zero_with_default_donem_kaynak(self):
        # topsis/talep/guven=0 ama donem+kaynak varsayilan 100
        # 0.10*100 + 0.05*100 = 15
        assert compute_acilabilirlik_score(0, 0, 0) == 15.0

    def test_clamps_out_of_range(self):
        # 150 -> 100, -20 -> 0
        score = compute_acilabilirlik_score(150, -20, 50, 0, 0)
        # 0.45*100 + 0.25*0 + 0.15*50 + 0 + 0 = 45 + 7.5 = 52.5
        assert score == 52.5

    def test_invalid_inputs_treated_as_zero_or_default(self):
        score = compute_acilabilirlik_score("x", None, float("nan"))
        # topsis=0, talep=0, guven=0, donem=default100, kaynak=default100
        assert score == 15.0


class TestDeriveTalep:
    def test_both_signals_averaged(self):
        # populerlik=0.8, anket=0.6 -> (80+60)/2 = 70
        assert derive_talep_score({"populerlik": 0.8, "anket": 0.6}) == 70.0

    def test_single_signal(self):
        assert derive_talep_score({"populerlik": 0.9}) == 90.0

    def test_missing_returns_zero(self):
        assert derive_talep_score({}) == 0.0
        assert derive_talep_score(None) == 0.0

    def test_clamps_above_one(self):
        assert derive_talep_score({"populerlik": 1.5}) == 100.0


class TestCategorize:
    def test_mufredatta_no_approval_is_strong(self):
        assert categorize_recommendation(1, approval_required=False) == KATEGORI_GUCLU

    def test_mufredatta_with_approval_is_conditional(self):
        assert categorize_recommendation(1, approval_required=True) == KATEGORI_SARTLI

    def test_havuz(self):
        assert categorize_recommendation(0) == KATEGORI_HAVUZ

    def test_dinlenme(self):
        assert categorize_recommendation(-1) == KATEGORI_DINLENME

    def test_iptal(self):
        assert categorize_recommendation(-2) == KATEGORI_IPTAL


class TestListRecommended:
    def _build_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE ders (ders_id INTEGER PRIMARY KEY, kod TEXT, ad TEXT)"
        )
        cur.execute(
            """
            CREATE TABLE course_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_run_id INTEGER, course_id INTEGER, year INTEGER,
                final_status INTEGER, topsis_score REAL,
                data_confidence_score REAL, acilabilirlik_score REAL,
                trend_label TEXT, approval_required INTEGER DEFAULT 0
            )
            """
        )
        cur.execute(
            "CREATE TABLE populerlik (ders_id INTEGER, akademik_yil INTEGER, doluluk_orani REAL)"
        )
        cur.execute("INSERT INTO ders VALUES (1, 'CS101', 'Veri Madenciligi')")
        cur.execute("INSERT INTO ders VALUES (2, 'CS102', 'Eski Ders')")
        conn.commit()
        return conn

    def test_uses_stored_score_and_sorts_desc(self):
        conn = self._build_db()
        cur = conn.cursor()
        # Ders 1: dusuk stored skor, Ders 2: yuksek stored skor -> 2 once gelmeli
        cur.execute(
            "INSERT INTO course_decisions "
            "(decision_run_id, course_id, year, final_status, topsis_score, "
            "data_confidence_score, acilabilirlik_score, approval_required) "
            "VALUES (5, 1, 2022, 1, 80, 0.8, 40.0, 0)"
        )
        cur.execute(
            "INSERT INTO course_decisions "
            "(decision_run_id, course_id, year, final_status, topsis_score, "
            "data_confidence_score, acilabilirlik_score, approval_required) "
            "VALUES (5, 2, 2022, 0, 50, 0.5, 90.0, 0)"
        )
        conn.commit()
        rows = list_recommended_courses(conn, 5)
        assert [r["course_id"] for r in rows] == [2, 1]
        assert rows[0]["acilabilirlik"] == 90.0
        assert rows[0]["oneri_kategori"] == KATEGORI_HAVUZ
        assert rows[1]["oneri_kategori"] == KATEGORI_GUCLU

    def test_null_score_falls_back_to_computation(self):
        conn = self._build_db()
        cur = conn.cursor()
        # acilabilirlik_score NULL -> topsis+guven+populerlik ile hesaplanmali
        cur.execute(
            "INSERT INTO course_decisions "
            "(decision_run_id, course_id, year, final_status, topsis_score, "
            "data_confidence_score, acilabilirlik_score) "
            "VALUES (7, 1, 2022, 1, 80, 0.6, NULL)"
        )
        cur.execute("INSERT INTO populerlik VALUES (1, 2022, 0.7)")
        conn.commit()
        rows = list_recommended_courses(conn, 7)
        # 0.45*80 + 0.25*70 + 0.15*60 + 0.10*100 + 0.05*100 = 77.5
        assert rows[0]["acilabilirlik"] == 77.5

    def test_empty_run_returns_empty(self):
        conn = self._build_db()
        assert list_recommended_courses(conn, 999) == []
