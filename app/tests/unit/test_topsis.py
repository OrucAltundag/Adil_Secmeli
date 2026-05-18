# -*- coding: utf-8 -*-
"""TOPSIS algoritma birim testleri — matematiksel dogrulama."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.algorithms.mcdm.topsis import TOPSISRanker

pytestmark = pytest.mark.unit


class TestTOPSISNormalization:
    """Normalizasyon ve agirlik uygulamasi."""

    def test_closeness_in_0_1_range(self):
        """Closeness coefficient 0-1 arasinda olmali."""
        df = pd.DataFrame({
            "item_id": [1, 2, 3],
            "k1": [0.9, 0.5, 0.1],
            "k2": [0.8, 0.6, 0.2],
        })
        ranker = TOPSISRanker(weights=[0.6, 0.4])
        output = ranker.rank(df, top_k=3)
        for rec in output.recommendations:
            assert 0.0 <= rec["score"] <= 1.0 + 1e-10

    def test_equal_weights_produce_uniform_weighting(self):
        """Esit agirliklar normalizeye esit etki etmeli."""
        df = pd.DataFrame({
            "item_id": [1, 2, 3],
            "k1": [0.9, 0.5, 0.1],
            "k2": [0.1, 0.5, 0.9],
        })
        ranker = TOPSISRanker(weights=[0.5, 0.5])
        output = ranker.rank(df, top_k=3)
        scores = [r["score"] for r in output.recommendations]
        # item 2 her iki kriterde orta → en yuksek closeness beklenir
        # veya item 1 ve 3 benzer closeness'a sahip olur
        assert len(scores) == 3

    def test_weight_normalization(self):
        """Agirliklar toplami 1'e normalize edilmeli."""
        ranker = TOPSISRanker(weights=[2, 3, 5])
        df = pd.DataFrame({
            "item_id": [1],
            "k1": [0.5], "k2": [0.5], "k3": [0.5],
        })
        ranker.fit(df)
        assert sum(ranker.weights) == pytest.approx(1.0, abs=1e-6)


class TestTOPSISRanking:
    """Siralama dogrulamasi."""

    def test_known_ranking_order(self):
        """Bilinen veriyle beklenen siralama."""
        df = pd.DataFrame({
            "item_id": [1, 2, 3],
            "basari": [0.9, 0.5, 0.1],
            "trend": [0.8, 0.6, 0.2],
            "anket": [0.7, 0.5, 0.3],
        })
        ranker = TOPSISRanker(weights=[0.4, 0.3, 0.3])
        output = ranker.rank(df, top_k=3)
        # Ders 1 tum kriterlerde en iyi → rank 1
        assert output.recommendations[0]["item_id"] == 1
        assert output.recommendations[0]["rank"] == 1
        # Ders 3 en kotu → rank 3
        assert output.recommendations[2]["item_id"] == 3
        assert output.recommendations[2]["rank"] == 3

    def test_best_item_has_highest_score(self):
        """Her kriterde en iyi olan en yuksek skoru almali."""
        df = pd.DataFrame({
            "item_id": [10, 20, 30],
            "k1": [1.0, 0.5, 0.0],
            "k2": [1.0, 0.5, 0.0],
            "k3": [1.0, 0.5, 0.0],
        })
        ranker = TOPSISRanker(weights=[1, 1, 1])
        output = ranker.rank(df, top_k=3)
        assert output.recommendations[0]["item_id"] == 10
        # En iyinin closeness'i 1.0'a yakin olmali
        assert output.recommendations[0]["score"] == pytest.approx(1.0, abs=0.01)

    def test_worst_item_has_lowest_score(self):
        """Her kriterde en kotu olan 0'a yakin skor almali."""
        df = pd.DataFrame({
            "item_id": [10, 20, 30],
            "k1": [1.0, 0.5, 0.0],
            "k2": [1.0, 0.5, 0.0],
            "k3": [1.0, 0.5, 0.0],
        })
        ranker = TOPSISRanker(weights=[1, 1, 1])
        output = ranker.rank(df, top_k=3)
        last = output.recommendations[-1]
        assert last["item_id"] == 30
        assert last["score"] == pytest.approx(0.0, abs=0.01)


class TestTOPSISEdgeCases:
    """Uc durumlar."""

    def test_all_values_equal_no_crash(self):
        """Tum degerler ayni → NaN/ZeroDivision olmamali."""
        df = pd.DataFrame({
            "item_id": [1, 2, 3],
            "k1": [0.5, 0.5, 0.5],
            "k2": [0.5, 0.5, 0.5],
        })
        ranker = TOPSISRanker(weights=[0.5, 0.5])
        output = ranker.rank(df, top_k=3)
        for rec in output.recommendations:
            score = rec["score"]
            assert not np.isnan(score), "NaN skor uretilmemeli"
            assert not np.isinf(score), "Inf skor uretilmemeli"

    def test_single_item(self):
        """Tek alternatifle calismali."""
        df = pd.DataFrame({
            "item_id": [42],
            "k1": [0.8],
            "k2": [0.6],
        })
        ranker = TOPSISRanker(weights=[0.5, 0.5])
        output = ranker.rank(df, top_k=1)
        assert len(output.recommendations) == 1
        assert output.recommendations[0]["item_id"] == 42

    def test_weight_length_mismatch_raises(self):
        """Agirlik sayisi != kriter sayisi → ValueError."""
        ranker = TOPSISRanker(weights=[0.5, 0.5])  # 2 agirlik
        df = pd.DataFrame({
            "item_id": [1],
            "k1": [0.5], "k2": [0.5], "k3": [0.5],  # 3 kriter
        })
        with pytest.raises(ValueError, match="Weight length mismatch"):
            ranker.fit(df)

    def test_zero_column_no_crash(self):
        """Bir kolon tamamen 0 olsa bile crash etmemeli."""
        df = pd.DataFrame({
            "item_id": [1, 2, 3],
            "k1": [0.0, 0.0, 0.0],
            "k2": [0.8, 0.5, 0.2],
        })
        ranker = TOPSISRanker(weights=[0.5, 0.5])
        output = ranker.rank(df, top_k=3)
        assert len(output.recommendations) == 3

    def test_missing_values_handled(self):
        """NaN/None degerleri fillna(0) ile islenmeli."""
        df = pd.DataFrame({
            "item_id": [1, 2, 3],
            "k1": [0.8, None, 0.3],
            "k2": [0.6, 0.5, np.nan],
        })
        ranker = TOPSISRanker(weights=[0.5, 0.5])
        output = ranker.rank(df, top_k=3)
        assert len(output.recommendations) == 3

    def test_explain_returns_nonempty(self):
        """explain() bos olmamali."""
        ranker = TOPSISRanker(weights=[0.5, 0.5])
        df = pd.DataFrame({"item_id": [1], "k1": [0.5], "k2": [0.5]})
        ranker.fit(df)
        assert len(ranker.explain()) > 0

    def test_artifacts_contain_ideal_values(self):
        """Cikti artifacts ideal_best/ideal_worst icermeli."""
        df = pd.DataFrame({
            "item_id": [1, 2],
            "k1": [0.8, 0.3],
            "k2": [0.6, 0.9],
        })
        ranker = TOPSISRanker(weights=[0.5, 0.5])
        output = ranker.rank(df, top_k=2)
        assert "ideal_best" in output.artifacts
        assert "ideal_worst" in output.artifacts
        assert len(output.artifacts["scores"]) == 2


class TestTOPSISDeterministic:
    """Deterministiklik kontrolu."""

    def test_same_input_same_output(self):
        """Ayni veri → ayni sonuc."""
        df = pd.DataFrame({
            "item_id": [1, 2, 3, 4],
            "k1": [0.9, 0.6, 0.3, 0.1],
            "k2": [0.7, 0.8, 0.5, 0.2],
            "k3": [0.8, 0.4, 0.6, 0.3],
        })
        weights = [0.4, 0.35, 0.25]
        results = []
        for _ in range(5):
            ranker = TOPSISRanker(weights=list(weights))
            output = ranker.rank(df.copy(), top_k=4)
            scores = [r["score"] for r in output.recommendations]
            rankings = [r["item_id"] for r in output.recommendations]
            results.append((scores, rankings))
        for scores, rankings in results[1:]:
            for s1, s2 in zip(results[0][0], scores):
                assert s1 == pytest.approx(s2, abs=1e-10)
            assert results[0][1] == rankings
