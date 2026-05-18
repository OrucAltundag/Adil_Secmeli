# -*- coding: utf-8 -*-
"""E2E karar pipeline testi — import → skor → karar → rapor."""
from __future__ import annotations

import pandas as pd
import pytest

from app.algorithms.mcdm.topsis import TOPSISRanker
from app.services.data_confidence_service import calculate_data_confidence
from app.services.explanation_engine import build_decision_explanation
from app.services.trend_analysis_service import analyze_trend_values
from app.tests.fixtures.test_db_builders import (
    GOLDEN_COURSES,
    GOLDEN_CRITERIA,
    GOLDEN_PERFORMANCE,
)

pytestmark = pytest.mark.e2e

class TestFullDecisionPipeline:
    """Tam karar pipeline: veri → trend → skor → karar → aciklama."""

    def test_pipeline_produces_decisions_for_all_courses(self):
        # 1. Golden dataset'ten TOPSIS input olustur
        data = []
        for c in GOLDEN_CRITERIA:
            did, yil, donem, toplam, gecen, ort, kont, kayitli, ak, as_ = c
            basari = gecen / toplam if toplam > 0 else 0
            talep = kayitli / kont if kont > 0 else 0
            anket = as_ / ak if ak > 0 else 0
            perf = [p for p in GOLDEN_PERFORMANCE if p[0] == did]
            values = {int(p[1]): p[2] for p in perf}
            trend = analyze_trend_values(values, target_year=2024)
            conf = calculate_data_confidence(
                has_success_data=toplam > 0, has_popularity_data=kont > 0,
                has_survey_data=ak > 0, has_trend_data=len(values) >= 2,
                has_recent_data=True, survey_count=ak,
            )
            data.append({
                "item_id": did, "basari": basari, "talep": min(talep, 1.0),
                "anket": anket, "trend": trend["trend_score"],
                "trend_label": trend["trend_label"],
                "confidence": conf,
            })
        df = pd.DataFrame([{"item_id": d["item_id"], "basari": d["basari"],
                            "talep": d["talep"], "anket": d["anket"],
                            "trend": d["trend"]} for d in data])

        # 2. TOPSIS calistir
        ranker = TOPSISRanker(weights=[0.30, 0.25, 0.20, 0.25])
        output = ranker.rank(df, top_k=len(df))

        # 3. Assertions
        assert len(output.recommendations) == len(GOLDEN_COURSES)
        for rec in output.recommendations:
            assert 0.0 <= rec["score"] <= 1.0 + 1e-10
            assert rec["rank"] >= 1

        # 4. Her ders icin aciklama uret
        for rec in output.recommendations:
            course = next((c for c in GOLDEN_COURSES if c[0] == rec["item_id"]), None)
            d = next((x for x in data if x["item_id"] == rec["item_id"]), None)
            explanation = build_decision_explanation(
                course_code=course[1] if course else None,
                course_name=course[2] if course else None,
                decision={"topsis_score": rec["score"] * 100, "recommended_status": 0, "final_status": 0},
                trend={"trend_label": d["trend_label"]} if d else None,
                confidence=d["confidence"] if d else None,
            )
            assert explanation["human_readable_text"], f"Ders {rec['item_id']} icin aciklama bos"
            assert explanation["main_reason"]

    def test_pipeline_scores_in_range(self):
        """Pipeline ciktisi tum skorlar gecerli aralikta."""
        df = pd.DataFrame({
            "item_id": [c[0] for c in GOLDEN_COURSES],
            "basari": [0.9, 0.87, 0.6, 0.4, 0.3, 0.4, 0.53, 0.6],
            "talep": [0.92, 0.92, 0.8, 0.6, 0.4, 0.5, 0.3, 0.8],
            "anket": [0.84, 0.88, 0.6, 0.4, 0.27, 0.33, 0, 0.6],
            "trend": [0.85, 0.81, 0.67, 0.50, 0.34, 0.45, 0.53, 0.60],
        })
        ranker = TOPSISRanker(weights=[0.3, 0.25, 0.2, 0.25])
        output = ranker.rank(df, top_k=len(df))
        for rec in output.recommendations:
            assert 0 <= rec["score"] <= 1.0 + 1e-10
