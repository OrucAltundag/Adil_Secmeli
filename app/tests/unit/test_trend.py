# -*- coding: utf-8 -*-
"""Trend analizi ve skor hesaplama birim testleri."""

from __future__ import annotations

import pytest

from app.services.trend_analysis_service import (
    TREND_DEFAULT_WEIGHTS,
    analyze_trend_values,
    weighted_trend_score,
)

pytestmark = pytest.mark.unit


class TestWeightedTrendScore:
    """50/30/20 agirlikli trend skoru."""

    def test_default_weights_are_50_30_20(self):
        assert TREND_DEFAULT_WEIGHTS == (0.50, 0.30, 0.20)

    def test_single_year_only(self):
        score = weighted_trend_score({2024: 0.80})
        assert score == pytest.approx(0.80, abs=0.01)

    def test_three_year_weighted(self):
        values = {2022: 0.60, 2023: 0.70, 2024: 0.80}
        score = weighted_trend_score(values)
        # 2024 (en guncel): %50 agirlik, 2023: %30, 2022: %20
        expected = 0.80 * 0.50 + 0.70 * 0.30 + 0.60 * 0.20
        assert score == pytest.approx(expected, abs=0.01)

    def test_missing_middle_year_renormalizes(self):
        """2 yil veri → kalan agirliklar yeniden normalize ediliyor mu."""
        values = {2022: 0.60, 2024: 0.80}
        score = weighted_trend_score(values)
        assert 0 < score <= 1.0

    def test_empty_returns_zero(self):
        assert weighted_trend_score({}) == 0.0

    def test_zero_values_return_zero(self):
        assert weighted_trend_score({2024: 0.0, 2023: 0.0}) == 0.0


class TestAnalyzeTrendValues:
    """Trend etiketleme ve senaryo testleri."""

    def test_no_data_insufficient(self):
        result = analyze_trend_values({})
        assert result["trend_label"] == "insufficient_data"
        assert result["data_points_count"] == 0

    def test_single_point_insufficient_or_new(self):
        result = analyze_trend_values({2024: 0.70}, target_year=2024, first_seen_year=2024)
        assert result["trend_label"] == "new_course"
        assert result["data_points_count"] == 1

    def test_single_point_not_new(self):
        result = analyze_trend_values({2024: 0.70}, target_year=2024, first_seen_year=2022)
        assert result["trend_label"] == "insufficient_data"

    def test_rising_trend(self):
        values = {2022: 0.50, 2023: 0.60, 2024: 0.70}
        result = analyze_trend_values(values)
        assert result["trend_label"] == "rising"

    def test_falling_trend(self):
        values = {2022: 0.80, 2023: 0.65, 2024: 0.50}
        result = analyze_trend_values(values)
        assert result["trend_label"] == "falling"

    def test_stable_trend(self):
        values = {2022: 0.70, 2023: 0.71, 2024: 0.70}
        result = analyze_trend_values(values)
        assert result["trend_label"] == "stable"

    def test_volatile_trend(self):
        values = {2022: 0.30, 2023: 0.90, 2024: 0.35}
        result = analyze_trend_values(values, volatility_threshold=0.15)
        assert result["trend_label"] == "volatile"

    def test_extreme_outlier_no_crash(self):
        """Aykiri deger sistemi cokmemeli."""
        values = {2022: 0.50, 2023: 0.90, 2024: 0.10}
        result = analyze_trend_values(values)
        assert result["trend_label"] in {"volatile", "falling", "rising", "stable"}
        assert 0 <= result["trend_score"] <= 1.0

    def test_values_clamped_to_0_1(self):
        """Aralik disi degerler 0-1 bandina cekiliyor mu."""
        values = {2022: -0.5, 2023: 1.5, 2024: 0.8}
        result = analyze_trend_values(values)
        for v in result["values_by_year"].values():
            assert 0.0 <= v <= 1.0

    def test_explanation_not_empty(self):
        result = analyze_trend_values({2022: 0.50, 2023: 0.60, 2024: 0.70})
        assert len(result["explanation"]) > 0


class TestDataConfidence:
    """Veri guveni hesaplama."""

    def test_all_sources_high_confidence(self):
        from app.services.data_confidence_service import calculate_data_confidence
        result = calculate_data_confidence(
            has_success_data=True,
            has_popularity_data=True,
            has_survey_data=True,
            has_trend_data=True,
            has_recent_data=True,
            survey_count=20,
            data_points_count=3,
        )
        assert result["level"] == "high"
        assert result["score"] >= 0.75

    def test_no_data_low_confidence(self):
        from app.services.data_confidence_service import calculate_data_confidence
        result = calculate_data_confidence(
            has_success_data=False,
            has_popularity_data=False,
            has_survey_data=False,
            has_trend_data=False,
            has_recent_data=False,
        )
        assert result["level"] == "low"
        assert result["score"] == 0.0
        assert len(result["missing_fields"]) > 0

    def test_partial_data_medium_confidence(self):
        from app.services.data_confidence_service import calculate_data_confidence
        result = calculate_data_confidence(
            has_success_data=True,
            has_popularity_data=True,
            has_survey_data=False,
            has_trend_data=True,
            has_recent_data=True,
        )
        assert result["level"] in ("medium", "high")
        assert result["score"] > 0.0

    def test_score_between_0_and_1(self):
        from app.services.data_confidence_service import calculate_data_confidence
        result = calculate_data_confidence(
            has_success_data=True, has_popularity_data=False,
            has_survey_data=True, has_trend_data=False,
            has_recent_data=True,
        )
        assert 0.0 <= result["score"] <= 1.0
