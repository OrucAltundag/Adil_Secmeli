# -*- coding: utf-8 -*-
"""Performans smoke testleri — büyük veri ile temel zamanlama."""
from __future__ import annotations
import time
import pytest
import pandas as pd
from app.algorithms.mcdm.topsis import TOPSISRanker

pytestmark = [pytest.mark.performance, pytest.mark.slow]

class TestPerformanceSmoke:
    def test_1000_courses_topsis_under_5_seconds(self):
        """1000 derslik TOPSIS 5 saniye altinda tamamlanmali."""
        import random
        rng = random.Random(42)
        n = 1000
        data = {"item_id": list(range(1, n+1))}
        for k in ("basari", "talep", "anket", "trend"):
            data[k] = [rng.random() for _ in range(n)]
        df = pd.DataFrame(data)
        start = time.perf_counter()
        ranker = TOPSISRanker(weights=[0.3, 0.25, 0.2, 0.25])
        output = ranker.rank(df, top_k=n)
        elapsed = time.perf_counter() - start
        assert elapsed < 5.0, f"TOPSIS 1000 ders icin {elapsed:.2f}s surdu"
        assert len(output.recommendations) == n

    def test_5000_courses_no_crash(self):
        """5000 derslik veri crash etmemeli."""
        import random
        rng = random.Random(42)
        n = 5000
        data = {"item_id": list(range(1, n+1))}
        for k in ("k1", "k2", "k3"):
            data[k] = [rng.random() for _ in range(n)]
        df = pd.DataFrame(data)
        ranker = TOPSISRanker(weights=[0.4, 0.3, 0.3])
        output = ranker.rank(df, top_k=n)
        assert len(output.recommendations) == n
