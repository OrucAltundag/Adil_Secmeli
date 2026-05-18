# -*- coding: utf-8 -*-
"""State machine transition matrix testleri — 11 senaryo."""

from __future__ import annotations


import pytest

from app.services.havuz_karar import (
    STATU_DINLENMEDE,
    STATU_HAVUZDA,
    STATU_IPTAL,
    STATU_MUFREDATTA,
    calculate_next_status,
)
from app.services.pool_state_machine_service import evaluate_course_state_transition

pytestmark = pytest.mark.unit


def _eval(conn, **ctx):
    """Kisa yardimci: state transition evaluate et."""
    ctx.setdefault("course_id", 1)
    ctx.setdefault("year", 2024)
    return evaluate_course_state_transition(conn, ctx)


class TestStateMachineTransitions:
    """Havuz state machine — 11 governance transition senaryosu."""

    def test_s01_curriculum_low_score_one_year(self, state_machine_db):
        """Mufredatta + 1 yil dusuk skor → havuz/dinlenme, kalici iptal degil."""
        r = _eval(state_machine_db, current_status=STATU_MUFREDATTA,
                  topsis_score=40.0, trend_label="falling",
                  data_confidence_score=0.80, counter_before=0)
        assert r["final_status"] != STATU_IPTAL
        assert r["final_status"] in (STATU_HAVUZDA, STATU_DINLENMEDE)
        assert r["explanation"]

    def test_s02_pool_two_years_low_score(self, state_machine_db):
        """Havuzda + 2 yil dusuk skor → dinlenme veya revizyon onerisi."""
        r = _eval(state_machine_db, current_status=STATU_HAVUZDA,
                  topsis_score=40.0, trend_label="falling",
                  years_in_pool=2, counter_before=0,
                  data_confidence_score=0.80)
        assert r["final_status"] in (STATU_DINLENMEDE, STATU_HAVUZDA)
        assert r["explanation"]

    def test_s03_resting_three_years_low_high_confidence(self, state_machine_db):
        """Dinlenmede + 3 yil dusuk skor + yuksek veri guveni → cancel_candidate."""
        r = _eval(state_machine_db, current_status=STATU_DINLENMEDE,
                  topsis_score=25.0, trend_label="falling",
                  years_in_rest=3, counter_before=1,
                  data_confidence_score=0.90)
        assert r["lifecycle_label"] == "cancel_candidate" or r["recommended_status"] == STATU_IPTAL
        assert r["approval_required"] is True
        # final_status dogrudan -2 olmamali (onay bekliyor)
        assert r["final_status"] != STATU_IPTAL
        assert r["explanation"]

    def test_s04_resting_low_confidence_blocks_cancel(self, state_machine_db):
        """Dinlenmede + dusuk veri guveni → cancel engellenir."""
        r = _eval(state_machine_db, current_status=STATU_DINLENMEDE,
                  topsis_score=25.0, trend_label="falling",
                  years_in_rest=3, counter_before=1,
                  data_confidence_score=0.40)
        assert r["final_status"] != STATU_IPTAL
        assert "güven" in r["explanation"].lower() or "veri" in r["explanation"].lower()

    def test_s05_strategic_course_no_auto_cancel(self, state_machine_db):
        """Stratejik ders + dusuk skor → otomatik iptal yok."""
        r = _eval(state_machine_db, current_status=STATU_HAVUZDA,
                  topsis_score=20.0, trend_label="falling",
                  years_in_pool=5, counter_before=0,
                  data_confidence_score=0.90,
                  governance_flags={"strategic_flag": True})
        assert r["final_status"] != STATU_IPTAL
        assert r["metadata"]["protected"] is True

    def test_s06_accreditation_no_auto_cancel(self, state_machine_db):
        """Akreditasyon dersi + dusuk skor → otomatik iptal yok."""
        r = _eval(state_machine_db, current_status=STATU_HAVUZDA,
                  topsis_score=20.0, trend_label="falling",
                  years_in_pool=5, counter_before=0,
                  data_confidence_score=0.90,
                  governance_flags={"accreditation_flag": True})
        assert r["final_status"] != STATU_IPTAL
        assert r["approval_required"] or r["metadata"]["protected"]

    def test_s07_new_course_grace_period(self, state_machine_db):
        """Yeni ders + dusuk skor → grace period, kalici iptal onerilmez."""
        r = _eval(state_machine_db, current_status=STATU_HAVUZDA,
                  topsis_score=25.0, trend_label="falling",
                  years_in_pool=5, counter_before=0,
                  data_confidence_score=0.90,
                  governance_flags={"new_course_flag": True, "first_offered_year": 2023})
        assert r["final_status"] != STATU_IPTAL

    def test_s08_revised_course_grace(self, state_machine_db):
        """Revize ders + dusuk skor → revision grace period."""
        r = _eval(state_machine_db, current_status=STATU_HAVUZDA,
                  topsis_score=30.0, trend_label="falling",
                  years_in_pool=5, counter_before=0,
                  data_confidence_score=0.90,
                  governance_flags={"revised_course_flag": True, "revision_year": 2023})
        assert r["final_status"] != STATU_IPTAL

    def test_s09_pool_high_score_rising_reactivation(self, state_machine_db):
        """Havuzdaki ders + yuksek skor + rising trend → reactivation_candidate."""
        r = _eval(state_machine_db, current_status=STATU_HAVUZDA,
                  topsis_score=85.0, trend_label="rising",
                  years_in_pool=1, counter_before=0,
                  data_confidence_score=0.90)
        assert r["lifecycle_label"] in ("reactivation_candidate", "curriculum")
        assert r["recommended_status"] == STATU_MUFREDATTA

    def test_s10_cancelled_no_auto_return(self, state_machine_db):
        """Kalici iptal edilmis ders + yuksek skor → otomatik donus yok."""
        r = _eval(state_machine_db, current_status=STATU_IPTAL,
                  topsis_score=90.0, trend_label="rising",
                  counter_before=2, data_confidence_score=0.95)
        # final_status otomatik olarak mufredatta olmamali
        assert r["final_status"] == STATU_IPTAL or r["approval_required"]

    def test_s11_override_changes_final(self, state_machine_db):
        """Manuel override → final_status override ile degisir."""
        r = _eval(state_machine_db, current_status=STATU_HAVUZDA,
                  topsis_score=40.0, trend_label="falling",
                  years_in_pool=1, counter_before=0,
                  data_confidence_score=0.80,
                  manual_override={
                      "overridden_final_status": STATU_MUFREDATTA,
                      "reason": "Kurul karari ile mufredatta tutulacak.",
                  })
        assert r["final_status"] == STATU_MUFREDATTA
        assert r["override_applied"] is True
        assert "override" in r["rule_applied"]

    # ================================================================
    # Ortak kontroller
    # ================================================================

    def test_explanation_never_empty(self, state_machine_db):
        """Her transition icin explanation bos olmamali."""
        for status in (STATU_MUFREDATTA, STATU_HAVUZDA, STATU_DINLENMEDE, STATU_IPTAL):
            r = _eval(state_machine_db, current_status=status,
                      topsis_score=50.0, trend_label="stable",
                      data_confidence_score=0.70, counter_before=0)
            assert r["explanation"], f"Status {status} icin explanation bos"

    def test_rule_applied_never_empty(self, state_machine_db):
        """Her transition icin rule_applied dolu olmali."""
        r = _eval(state_machine_db, current_status=STATU_HAVUZDA,
                  topsis_score=50.0, trend_label="stable",
                  data_confidence_score=0.70, counter_before=0)
        assert r["rule_applied"]

    def test_statuses_are_valid_ints(self, state_machine_db):
        """old/recommended/final status gecerli integer olmali."""
        r = _eval(state_machine_db, current_status=STATU_HAVUZDA,
                  topsis_score=50.0, trend_label="stable",
                  data_confidence_score=0.70)
        valid = {STATU_MUFREDATTA, STATU_HAVUZDA, STATU_DINLENMEDE, STATU_IPTAL}
        assert r["old_status"] in valid
        assert r["recommended_status"] in valid
        assert r["final_status"] in valid


class TestLegacyStateMachine:
    """Eski/basit state machine — calculate_next_status geriye uyumluluk."""

    def test_curriculum_stays_when_selected(self):
        assert calculate_next_status(STATU_MUFREDATTA, 0, True) == (STATU_MUFREDATTA, 0)

    def test_curriculum_drops_to_rest(self):
        assert calculate_next_status(STATU_MUFREDATTA, 0, False) == (STATU_DINLENMEDE, 1)

    def test_second_drop_cancels(self):
        assert calculate_next_status(STATU_MUFREDATTA, 1, False) == (STATU_IPTAL, 2)

    def test_pool_to_curriculum(self):
        assert calculate_next_status(STATU_HAVUZDA, 0, True) == (STATU_MUFREDATTA, 0)

    def test_cancelled_stays_cancelled(self):
        assert calculate_next_status(STATU_IPTAL, 2, True) == (STATU_IPTAL, 2)

    def test_resting_returns_to_pool(self):
        assert calculate_next_status(STATU_DINLENMEDE, 1, False) == (STATU_HAVUZDA, 1)
