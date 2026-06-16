# -*- coding: utf-8 -*-
"""Entropi objektif agirliklandirma birim testleri."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.algorithms.mcdm.entropy import EntropyWeightRanker

pytestmark = pytest.mark.unit


class TestEntropyWeights:
    def test_weights_sum_to_one(self):
        df = pd.DataFrame({
            "item_id": [1, 2, 3, 4],
            "basari": [0.9, 0.6, 0.3, 0.1],
            "trend": [0.7, 0.8, 0.5, 0.2],
            "anket": [0.5, 0.5, 0.5, 0.5],
        })
        ranker = EntropyWeightRanker().fit(df)
        assert ranker.weights is not None
        assert float(np.sum(ranker.weights)) == pytest.approx(1.0, abs=1e-9)

    def test_constant_criterion_gets_near_zero_weight(self):
        """Tum derslerde ayni olan kriter ayirt edici degildir → ~0 agirlik."""
        df = pd.DataFrame({
            "item_id": [1, 2, 3],
            "ayirt_edici": [0.9, 0.5, 0.1],
            "sabit": [0.5, 0.5, 0.5],
        })
        ranker = EntropyWeightRanker().fit(df)
        w = dict(zip(ranker.criteria_cols, ranker.weights))
        assert w["ayirt_edici"] > w["sabit"]
        assert w["sabit"] == pytest.approx(0.0, abs=1e-6)

    def test_ranking_orders_best_first(self):
        df = pd.DataFrame({
            "item_id": [1, 2, 3],
            "k1": [0.9, 0.5, 0.1],
            "k2": [0.8, 0.6, 0.2],
        })
        output = EntropyWeightRanker().rank(df, top_k=3)
        assert output.recommendations[0]["item_id"] == 1
        assert output.recommendations[0]["rank"] == 1

    def test_all_equal_no_crash(self):
        df = pd.DataFrame({
            "item_id": [1, 2, 3],
            "k1": [0.5, 0.5, 0.5],
            "k2": [0.5, 0.5, 0.5],
        })
        output = EntropyWeightRanker().rank(df, top_k=3)
        for rec in output.recommendations:
            assert not np.isnan(rec["score"]) and not np.isinf(rec["score"])

    def test_single_item(self):
        df = pd.DataFrame({"item_id": [42], "k1": [0.8], "k2": [0.6]})
        output = EntropyWeightRanker().rank(df, top_k=1)
        assert len(output.recommendations) == 1
        assert output.recommendations[0]["item_id"] == 42

    def test_artifacts_and_explain(self):
        df = pd.DataFrame({"item_id": [1, 2], "k1": [0.8, 0.3], "k2": [0.6, 0.9]})
        ranker = EntropyWeightRanker()
        output = ranker.rank(df, top_k=2)
        assert "weights" in output.artifacts
        assert len(ranker.explain()) > 0

    def test_registry_exposes_entropy(self):
        from app.benchmark.registry import AlgorithmRegistry

        registry = AlgorithmRegistry()
        names = {a["name"] for a in registry.list_algorithms(group="mcdm")}
        assert "EntropyWeighting" in names
        algo = registry.create("EntropyWeighting")
        assert algo.name == "EntropyWeighting"
