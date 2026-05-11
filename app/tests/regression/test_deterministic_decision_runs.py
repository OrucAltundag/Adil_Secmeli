# -*- coding: utf-8 -*-
"""Deterministiklik testleri — ayni veri + ayni ayar = ayni karar."""
from __future__ import annotations
import pytest
import pandas as pd
from app.algorithms.mcdm.topsis import TOPSISRanker
from app.algorithms.mcdm.ahp import AHPRanker
from app.tests.fixtures.test_db_builders import GOLDEN_CRITERIA, GOLDEN_PERFORMANCE
from app.services.trend_analysis_service import analyze_trend_values

pytestmark = pytest.mark.regression

class TestDeterministicRuns:
    def _build_df(self):
        data = []
        for c in GOLDEN_CRITERIA:
            did, yil, donem, toplam, gecen, ort, kont, kayitli, ak, as_ = c
            basari = gecen / toplam if toplam > 0 else 0
            talep = kayitli / kont if kont > 0 else 0
            anket = as_ / ak if ak > 0 else 0
            perf = [p for p in GOLDEN_PERFORMANCE if p[0] == did]
            values = {int(p[1]): p[2] for p in perf}
            trend = analyze_trend_values(values)
            data.append({"item_id": did, "basari": basari, "talep": min(talep, 1.0),
                          "anket": anket, "trend": trend["trend_score"]})
        return pd.DataFrame(data)

    def test_topsis_deterministic_five_runs(self):
        df = self._build_df()
        snapshots = []
        for _ in range(5):
            r = TOPSISRanker(weights=[0.3, 0.25, 0.2, 0.25])
            out = r.rank(df.copy(), top_k=len(df))
            snapshots.append([(x["item_id"], round(x["score"], 10)) for x in out.recommendations])
        for s in snapshots[1:]:
            assert s == snapshots[0]

    def test_ahp_deterministic_three_runs(self):
        import numpy as np
        matrix = np.array([[1,3,5,2],[1/3,1,3,1],[1/5,1/3,1,1/2],[1/2,1,2,1]])
        df = self._build_df()
        snapshots = []
        for _ in range(3):
            r = AHPRanker(pairwise_matrix=matrix.copy())
            out = r.rank(df.copy(), top_k=len(df))
            snapshots.append([(x["item_id"], round(x["score"], 10)) for x in out.recommendations])
        for s in snapshots[1:]:
            assert s == snapshots[0]

    def test_tiebreak_is_deterministic(self):
        """Ayni skorlu dersler deterministik siralanmali."""
        df = pd.DataFrame({
            "item_id": [1, 2, 3],
            "k1": [0.5, 0.5, 0.5],
            "k2": [0.7, 0.7, 0.7],
        })
        results = []
        for _ in range(5):
            r = TOPSISRanker(weights=[0.5, 0.5])
            out = r.rank(df.copy(), top_k=3)
            results.append([x["item_id"] for x in out.recommendations])
        for res in results[1:]:
            assert res == results[0]
