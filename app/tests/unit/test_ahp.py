# -*- coding: utf-8 -*-
"""AHP algoritma birim testleri — matematiksel dogrulama ve edge case."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.algorithms.mcdm.ahp import AHPRanker, RI_TABLE


pytestmark = pytest.mark.unit


# ============================================================================
# 1. Pairwise matrix dogrulama
# ============================================================================

class TestAHPMatrixValidation:
    """AHP ikili karsilastirma matrisi dogruluk kontrolleri."""

    def test_identity_matrix_equal_weights(self):
        """Birim matris → tum agirliklar esit olmali."""
        n = 4
        matrix = np.ones((n, n))
        ranker = AHPRanker(pairwise_matrix=matrix)
        df = pd.DataFrame({
            "item_id": [1, 2, 3],
            "k1": [0.8, 0.5, 0.3],
            "k2": [0.7, 0.6, 0.4],
            "k3": [0.9, 0.4, 0.5],
            "k4": [0.6, 0.7, 0.2],
        })
        ranker.fit(df)
        assert ranker.state is not None
        weights = ranker.state.weights
        assert len(weights) == n
        # Birim matris: tum agirliklar 1/n = 0.25
        for w in weights:
            assert w == pytest.approx(0.25, abs=0.01)
        assert sum(weights) == pytest.approx(1.0, abs=1e-6)

    def test_weight_sum_is_one(self):
        """Uretilen agirliklar toplami 1 olmali."""
        matrix = np.array([
            [1, 3, 5],
            [1/3, 1, 3],
            [1/5, 1/3, 1],
        ])
        ranker = AHPRanker(pairwise_matrix=matrix)
        df = pd.DataFrame({
            "item_id": [1, 2],
            "k1": [0.8, 0.3],
            "k2": [0.5, 0.7],
            "k3": [0.6, 0.4],
        })
        ranker.fit(df)
        assert ranker.state is not None
        assert sum(ranker.state.weights) == pytest.approx(1.0, abs=1e-6)

    def test_known_3x3_weights(self):
        """Bilinen 3x3 Saaty matrisi icin agirliklar dogrulama."""
        # Saaty referans ornek: K1 >> K2 >> K3
        matrix = np.array([
            [1, 3, 5],
            [1/3, 1, 3],
            [1/5, 1/3, 1],
        ])
        ranker = AHPRanker(pairwise_matrix=matrix)
        df = pd.DataFrame({
            "item_id": [1],
            "k1": [0.5],
            "k2": [0.5],
            "k3": [0.5],
        })
        ranker.fit(df)
        w = ranker.state.weights
        # Beklenen: w1 > w2 > w3
        assert w[0] > w[1] > w[2], f"Agirlik sirasi hatali: {w}"
        # Beklenen degeler yaklaşık: [0.637, 0.258, 0.105]
        assert w[0] == pytest.approx(0.637, abs=0.05)
        assert w[1] == pytest.approx(0.258, abs=0.05)
        assert w[2] == pytest.approx(0.105, abs=0.05)

    def test_known_4x4_weights(self):
        """4x4 matris icin bilinen agirliklar."""
        matrix = np.array([
            [1, 2, 3, 4],
            [1/2, 1, 2, 3],
            [1/3, 1/2, 1, 2],
            [1/4, 1/3, 1/2, 1],
        ])
        ranker = AHPRanker(pairwise_matrix=matrix)
        df = pd.DataFrame({
            "item_id": [1],
            "k1": [0.5], "k2": [0.5], "k3": [0.5], "k4": [0.5],
        })
        ranker.fit(df)
        w = ranker.state.weights
        assert w[0] > w[1] > w[2] > w[3]
        assert sum(w) == pytest.approx(1.0, abs=1e-6)


# ============================================================================
# 2. Consistency Ratio (CR) testleri
# ============================================================================

class TestAHPConsistency:
    """Tutarlilik orani kontrolleri."""

    def test_consistent_matrix_cr_below_threshold(self):
        """Tutarli matris → CR <= 0.10."""
        matrix = np.array([
            [1, 3, 5],
            [1/3, 1, 3],
            [1/5, 1/3, 1],
        ])
        ranker = AHPRanker(pairwise_matrix=matrix)
        df = pd.DataFrame({"item_id": [1], "k1": [0.5], "k2": [0.5], "k3": [0.5]})
        ranker.fit(df)
        assert ranker.state.consistency_ratio <= 0.10 + 1e-6

    def test_inconsistent_matrix_cr_above_threshold(self):
        """Tutarsiz matris → CR > 0.10."""
        # Kasitli tutarsiz matris
        matrix = np.array([
            [1, 9, 1/9],
            [1/9, 1, 9],
            [9, 1/9, 1],
        ])
        ranker = AHPRanker(pairwise_matrix=matrix)
        df = pd.DataFrame({"item_id": [1], "k1": [0.5], "k2": [0.5], "k3": [0.5]})
        ranker.fit(df)
        assert ranker.state.consistency_ratio > 0.10

    def test_n1_safe(self):
        """n=1 matriste hata yok."""
        matrix = np.array([[1]])
        ranker = AHPRanker(pairwise_matrix=matrix)
        df = pd.DataFrame({"item_id": [1, 2], "k1": [0.8, 0.3]})
        ranker.fit(df)
        assert ranker.state.consistency_ratio == pytest.approx(0.0, abs=1e-6)

    def test_n2_safe(self):
        """n=2 matriste CR = 0 (RI=0)."""
        matrix = np.array([[1, 3], [1/3, 1]])
        ranker = AHPRanker(pairwise_matrix=matrix)
        df = pd.DataFrame({"item_id": [1], "k1": [0.5], "k2": [0.5]})
        ranker.fit(df)
        assert ranker.state.consistency_ratio == pytest.approx(0.0, abs=1e-6)


# ============================================================================
# 3. Siralama (ranking) testleri
# ============================================================================

class TestAHPRanking:
    """AHP siralama/skor dogrulama."""

    def test_ranking_order_with_known_data(self):
        """Bilinen agirliklarla siralama dogrulamasi."""
        matrix = np.array([
            [1, 3, 5],
            [1/3, 1, 3],
            [1/5, 1/3, 1],
        ])
        df = pd.DataFrame({
            "item_id": [1, 2, 3],
            "basari": [0.9, 0.5, 0.3],
            "trend": [0.8, 0.6, 0.4],
            "anket": [0.7, 0.7, 0.5],
        })
        ranker = AHPRanker(pairwise_matrix=matrix)
        output = ranker.rank(df, top_k=3)
        assert len(output.recommendations) == 3
        # item_id=1 en yuksek olmali
        assert output.recommendations[0]["item_id"] == 1
        assert output.recommendations[0]["rank"] == 1
        # Skorlar pozitif
        for rec in output.recommendations:
            assert rec["score"] >= 0.0

    def test_criteria_count_mismatch_raises_error(self):
        """Matris boyutu != kriter sayisi → ValueError."""
        matrix = np.array([[1, 2], [1/2, 1]])  # 2x2
        df = pd.DataFrame({
            "item_id": [1],
            "k1": [0.5], "k2": [0.5], "k3": [0.5],  # 3 kriter
        })
        ranker = AHPRanker(pairwise_matrix=matrix)
        ranker.fit(df)  # fit eder 2x2
        with pytest.raises(ValueError, match="Criteria count mismatch"):
            ranker.rank(df, top_k=1)

    def test_confidence_decreases_with_high_cr(self):
        """Yuksek CR → dusuk confidence."""
        # Tutarsiz matris
        matrix = np.array([
            [1, 9, 1/9],
            [1/9, 1, 9],
            [9, 1/9, 1],
        ])
        df = pd.DataFrame({
            "item_id": [1, 2],
            "k1": [0.8, 0.3],
            "k2": [0.5, 0.7],
            "k3": [0.6, 0.4],
        })
        ranker = AHPRanker(pairwise_matrix=matrix)
        output = ranker.rank(df, top_k=2)
        # confidence = 1 - CR, tutarsiz matriste dusuk olmali
        assert output.confidence < 0.90

    def test_explain_returns_nonempty_string(self):
        """explain() bos string donmemeli."""
        matrix = np.array([[1, 2], [1/2, 1]])
        df = pd.DataFrame({"item_id": [1], "k1": [0.5], "k2": [0.7]})
        ranker = AHPRanker(pairwise_matrix=matrix)
        ranker.fit(df)
        explanation = ranker.explain(df)
        assert len(explanation) > 0
        assert "CR=" in explanation

    def test_score_method_returns_valid_float(self):
        """score() 0-1 arasinda float donmeli."""
        matrix = np.array([[1, 3], [1/3, 1]])
        df = pd.DataFrame({"item_id": [1], "k1": [0.5], "k2": [0.5]})
        ranker = AHPRanker(pairwise_matrix=matrix)
        s = ranker.score(df)
        assert 0.0 <= s <= 1.0


# ============================================================================
# 4. RI tablosu dogrulama
# ============================================================================

class TestAHPRITable:
    """Random Index tablosu dogrulama."""

    def test_ri_table_known_values(self):
        assert RI_TABLE[1] == 0.0
        assert RI_TABLE[2] == 0.0
        assert RI_TABLE[3] == pytest.approx(0.58, abs=0.01)
        assert RI_TABLE[4] == pytest.approx(0.90, abs=0.01)
        assert RI_TABLE[5] == pytest.approx(1.12, abs=0.01)

    def test_ri_table_has_entries_1_to_10(self):
        for n in range(1, 11):
            assert n in RI_TABLE
