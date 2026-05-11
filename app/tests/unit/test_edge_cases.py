# -*- coding: utf-8 -*-
"""Edge case testleri — uç durumlar ve hata dayanıklılığı."""

from __future__ import annotations

import pytest
import numpy as np
import pandas as pd

from app.algorithms.mcdm.topsis import TOPSISRanker
from app.algorithms.mcdm.ahp import AHPRanker
from app.services.trend_analysis_service import analyze_trend_values
from app.services.data_confidence_service import calculate_data_confidence


pytestmark = pytest.mark.unit


class TestEdgeCasesTOPSIS:
    """TOPSIS uc durumlari."""

    def test_all_topsis_values_identical(self):
        """Tum TOPSIS degerleri ayni → NaN/ZeroDivision yok."""
        df = pd.DataFrame({
            "item_id": [1, 2, 3],
            "k1": [0.5, 0.5, 0.5],
            "k2": [0.5, 0.5, 0.5],
            "k3": [0.5, 0.5, 0.5],
        })
        ranker = TOPSISRanker(weights=[1, 1, 1])
        output = ranker.rank(df, top_k=3)
        for rec in output.recommendations:
            assert not np.isnan(rec["score"])
            assert not np.isinf(rec["score"])

    def test_single_criterion(self):
        """Tek kriter ile calismali."""
        df = pd.DataFrame({"item_id": [1, 2], "k1": [0.9, 0.1]})
        ranker = TOPSISRanker(weights=[1.0])
        output = ranker.rank(df, top_k=2)
        assert output.recommendations[0]["item_id"] == 1


class TestEdgeCasesAHP:
    """AHP uc durumlari."""

    def test_ahp_cr_very_high(self):
        """Cok yuksek CR → sistem cokmez, uyari uretilir."""
        # Kasitli tutarsiz
        matrix = np.array([
            [1, 9, 1/9, 5],
            [1/9, 1, 9, 1/5],
            [9, 1/9, 1, 7],
            [1/5, 5, 1/7, 1],
        ])
        ranker = AHPRanker(pairwise_matrix=matrix)
        df = pd.DataFrame({"item_id": [1], "k1": [.5], "k2": [.5], "k3": [.5], "k4": [.5]})
        ranker.fit(df)
        assert ranker.state is not None
        assert ranker.state.consistency_ratio > 0.10


class TestEdgeCasesTrend:
    """Trend uc durumlari."""

    def test_no_performance_data(self):
        """Hic performans verisi yok."""
        result = analyze_trend_values({})
        assert result["trend_label"] == "insufficient_data"

    def test_single_year_trend(self):
        """Tek yil veri → dusuk guven."""
        result = analyze_trend_values({2024: 0.70})
        assert result["trend_label"] in ("insufficient_data", "new_course")


class TestEdgeCasesConfidence:
    """Data confidence uc durumlari."""

    def test_zero_survey_still_works(self):
        """Anket katilimi 0 ise sistem cokmez."""
        result = calculate_data_confidence(
            has_success_data=True, has_popularity_data=True,
            has_survey_data=False, has_trend_data=True,
            has_recent_data=True, survey_count=0,
        )
        assert 0.0 <= result["score"] <= 1.0

    def test_no_data_at_all(self):
        """Hic veri yok → en dusuk guven."""
        result = calculate_data_confidence(
            has_success_data=False, has_popularity_data=False,
            has_survey_data=False, has_trend_data=False,
            has_recent_data=False,
        )
        assert result["score"] == 0.0
        assert result["level"] == "low"


class TestEdgeCasesScoreCalculation:
    """Skor hesaplama uc durumlari."""

    def test_division_by_zero_capacity(self):
        """Kontenjan 0 ise division by zero olmamali."""
        # Dogrudan havuz_karar calculate_next_status ile kontrol
        from app.services.havuz_karar import calculate_next_status
        # Bu fonksiyon basari verisine dogrudan bakmaz ama crash olmamali
        status, counter = calculate_next_status(0, 0, False)
        assert status == 0  # havuzda kalir

    def test_none_input_safe(self):
        """None girdiler guvenli sonuc donmeli."""
        from app.services.havuz_karar import calculate_next_status
        status, counter = calculate_next_status(None, None, False)
        assert status == 0
        assert counter == 0
