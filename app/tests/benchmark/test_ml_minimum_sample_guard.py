# -*- coding: utf-8 -*-
"""ML / Benchmark testleri — minimum sample guard ve algorithm governance."""
from __future__ import annotations

import pytest

from app.services.algorithm_governance_service import (
    BENCHMARK_ONLY,
    DEFAULT_ALGORITHMS,
    PRODUCTION_DECISION,
)

pytestmark = pytest.mark.benchmark

class TestMinimumSampleGuard:
    def _find(self, key):
        return next((a for a in DEFAULT_ALGORITHMS if a.algorithm_key == key), None)

    def test_random_forest_min_sample(self):
        assert self._find("random_forest").minimum_sample_count >= 100

    def test_xgboost_min_sample(self):
        assert self._find("xgboost").minimum_sample_count >= 500

    def test_logistic_regression_needs_per_class(self):
        algo = self._find("logistic_regression")
        assert algo.minimum_samples_per_class is not None and algo.minimum_samples_per_class >= 5

class TestAlgorithmGovernanceRoles:
    def _find(self, key):
        return next((a for a in DEFAULT_ALGORITHMS if a.algorithm_key == key), None)

    def test_ahp_production(self):
        assert self._find("ahp").usage_role == PRODUCTION_DECISION

    def test_topsis_production(self):
        assert self._find("topsis").usage_role == PRODUCTION_DECISION

    def test_xgboost_benchmark_only(self):
        assert self._find("xgboost").usage_role == BENCHMARK_ONLY

    def test_no_ml_in_production(self):
        for a in DEFAULT_ALGORITHMS:
            if a.algorithm_family == "ml":
                assert a.usage_role != PRODUCTION_DECISION, f"{a.algorithm_key} ML but production"

    def test_all_have_metrics(self):
        for a in DEFAULT_ALGORITHMS:
            assert len(a.recommended_metrics) > 0, f"{a.algorithm_key} no metrics"
