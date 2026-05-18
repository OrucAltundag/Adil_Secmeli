# -*- coding: utf-8 -*-
"""Golden dataset regression testi — kod degisiklikleri kararlari bozmasin."""
from __future__ import annotations

import pandas as pd
import pytest

from app.algorithms.mcdm.topsis import TOPSISRanker
from app.services.trend_analysis_service import analyze_trend_values
from app.tests.fixtures.test_db_builders import (
    GOLDEN_CRITERIA,
    GOLDEN_EXPECTED_DECISIONS,
    GOLDEN_PERFORMANCE,
)

pytestmark = pytest.mark.regression

class TestGoldenDatasetDecisions:
    """Golden dataset ile beklenen kararlar dogrulanir."""

    def _build_topsis_input(self):
        data = []
        for c in GOLDEN_CRITERIA:
            ders_id, yil, donem, toplam, gecen, ort, kont, kayitli, anket_k, anket_s = c
            basari = gecen / toplam if toplam > 0 else 0
            talep = kayitli / kont if kont > 0 else 0
            anket = anket_s / anket_k if anket_k > 0 else 0
            perf = [p for p in GOLDEN_PERFORMANCE if p[0] == ders_id]
            values = {int(p[1]): p[2] for p in perf}
            trend = analyze_trend_values(values)
            data.append({
                "item_id": ders_id, "basari": basari,
                "talep": min(talep, 1.0), "anket": anket,
                "trend": trend["trend_score"],
            })
        return pd.DataFrame(data)

    def test_topsis_ranking_deterministic(self):
        """Ayni golden dataset → ayni TOPSIS siralamasi."""
        df = self._build_topsis_input()
        weights = [0.30, 0.25, 0.20, 0.25]
        results = []
        for _ in range(3):
            ranker = TOPSISRanker(weights=list(weights))
            output = ranker.rank(df.copy(), top_k=len(df))
            results.append([r["item_id"] for r in output.recommendations])
        assert results[0] == results[1] == results[2]

    def test_high_score_course_ranks_first(self):
        """En yuksek skorlu ders (Ders 1) ilk sirada olmali."""
        df = self._build_topsis_input()
        ranker = TOPSISRanker(weights=[0.30, 0.25, 0.20, 0.25])
        output = ranker.rank(df, top_k=len(df))
        assert output.recommendations[0]["item_id"] == 1

    def test_low_score_course_ranks_last(self):
        """En dusuk skorlu ders (Ders 5) son siralarda olmali."""
        df = self._build_topsis_input()
        ranker = TOPSISRanker(weights=[0.30, 0.25, 0.20, 0.25])
        output = ranker.rank(df, top_k=len(df))
        last_ids = [r["item_id"] for r in output.recommendations[-3:]]
        assert 5 in last_ids

    def test_trend_labels_match_expected(self):
        """Golden dataset trend etiketleri beklenenlerle uyusmali."""
        for course_id, expected in GOLDEN_EXPECTED_DECISIONS.items():
            perf = [p for p in GOLDEN_PERFORMANCE if p[0] == course_id]
            values = {int(p[1]): p[2] for p in perf}
            result = analyze_trend_values(values, target_year=2024)
            assert result["trend_label"] == expected["trend"], \
                f"Ders {course_id}: beklenen={expected['trend']}, gercek={result['trend_label']}"

    def test_scores_in_valid_range(self):
        """Tum TOPSIS skorlari 0-1 arasinda olmali."""
        df = self._build_topsis_input()
        ranker = TOPSISRanker(weights=[0.30, 0.25, 0.20, 0.25])
        output = ranker.rank(df, top_k=len(df))
        for rec in output.recommendations:
            assert 0.0 <= rec["score"] <= 1.0 + 1e-10
