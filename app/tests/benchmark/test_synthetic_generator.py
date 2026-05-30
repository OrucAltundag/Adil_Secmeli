# -*- coding: utf-8 -*-
"""Benchmark sentetik veri üretimi güvenlik testleri."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.datasets.synthetic_generator import SyntheticDataGenerator

pytestmark = pytest.mark.benchmark


class CapturingRng:
    def __init__(self) -> None:
        self.probabilities = None

    def choice(self, values, *, size, replace, p):
        self.probabilities = np.asarray(p, dtype=float)
        return np.resize(np.asarray(values), int(size))


@pytest.mark.parametrize("alpha", [0.0, 0.25, 0.95])
def test_bootstrap_sample_normalizes_probabilities_for_alpha_values(alpha):
    base = pd.DataFrame(
        {
            "student_id": [1, 2, 3, 4, 5],
            "course_id": [10, 10, 10, 20, 30],
            "score": [0.1, 0.2, 0.3, 0.4, 0.5],
        }
    )
    rng = CapturingRng()

    sampled = SyntheticDataGenerator()._bootstrap_sample(base, target_size=8, class_imbalance_alpha=alpha, rng=rng)

    assert len(sampled) == 8
    assert rng.probabilities is not None
    assert np.isclose(rng.probabilities.sum(), 1.0)
    assert np.all(rng.probabilities >= 0.0)


def test_normalize_probabilities_falls_back_to_uniform_for_invalid_weights():
    generator = SyntheticDataGenerator()
    probabilities = generator._normalize_probabilities(np.array([np.nan, np.inf, -1.0, 0.0]))

    assert np.isclose(probabilities.sum(), 1.0)
    assert np.allclose(probabilities, np.ones(4) / 4)
