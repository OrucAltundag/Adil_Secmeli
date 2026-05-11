# -*- coding: utf-8 -*-
"""Explainability testleri — karar açıklama motoru."""

from __future__ import annotations

import pytest

from app.services.explanation_engine import build_decision_explanation


pytestmark = pytest.mark.unit


class TestExplainability:
    """Karar aciklanabilirligi."""

    def test_explanation_not_empty(self):
        """Her karar icin aciklama uretilmeli."""
        explanation = build_decision_explanation(
            course_code="BIL301", course_name="Yapay Zeka",
            decision={"topsis_score": 75.0, "recommended_status": 1, "final_status": 1},
        )
        assert explanation["human_readable_text"]
        assert explanation["main_reason"]

    def test_low_score_explains_reason(self):
        """Dusuk skor → aciklamada skor bilgisi olmali."""
        explanation = build_decision_explanation(
            course_code="BIL304", course_name="Mobil Programlama",
            decision={"topsis_score": 30.0, "recommended_status": -1, "final_status": -1},
        )
        assert "Dusuk" in explanation["main_reason"] or "skor" in explanation["main_reason"].lower()

    def test_falling_trend_in_explanation(self):
        """Falling trend → aciklamada trend etiketi olmali."""
        explanation = build_decision_explanation(
            course_code="BIL303", course_name="Bilgi Guvenligi",
            decision={"topsis_score": 50.0, "recommended_status": 0, "final_status": 0},
            trend={"trend_label": "falling"},
        )
        factors = explanation.get("negative_factors", [])
        secondary = explanation.get("secondary_reasons", [])
        combined = " ".join(factors + secondary)
        assert "dusus" in combined.lower() or "falling" in combined.lower() or "egilim" in combined.lower()

    def test_low_confidence_in_explanation(self):
        """Dusuk veri guveni → aciklamada guven bilgisi olmali."""
        explanation = build_decision_explanation(
            course_code="BIL307", course_name="Web Teknolojileri",
            decision={"topsis_score": 50.0, "recommended_status": 0, "final_status": 0},
            confidence={"level": "low"},
        )
        factors = explanation.get("negative_factors", [])
        secondary = explanation.get("secondary_reasons", [])
        combined = " ".join(factors + secondary)
        assert "guven" in combined.lower() or "veri" in combined.lower()

    def test_strategic_protection_in_explanation(self):
        """Stratejik ders → aciklamada koruma bilgisi olmali."""
        explanation = build_decision_explanation(
            course_code="BIL306", course_name="Robot Bilimi",
            decision={"topsis_score": 35.0, "recommended_status": 0, "final_status": 0},
            governance={"strategic_flag": True},
        )
        factors = explanation.get("positive_factors", [])
        secondary = explanation.get("secondary_reasons", [])
        combined = " ".join(factors + secondary)
        assert "stratejik" in combined.lower()

    def test_approval_required_in_explanation(self):
        """Onay gerekli → aciklamada onay bilgisi olmali."""
        explanation = build_decision_explanation(
            course_code="BIL305", course_name="Oyun Gelistirme",
            decision={
                "topsis_score": 20.0, "recommended_status": -2,
                "final_status": -1, "approval_required": True,
            },
        )
        secondary = explanation.get("secondary_reasons", [])
        combined = " ".join(secondary)
        assert "onay" in combined.lower()

    def test_high_score_positive_reason(self):
        """Yuksek skor → olumlu ana neden."""
        explanation = build_decision_explanation(
            course_code="BIL301", course_name="Yapay Zeka",
            decision={"topsis_score": 85.0, "recommended_status": 1, "final_status": 1},
        )
        assert "Yuksek" in explanation["main_reason"]
