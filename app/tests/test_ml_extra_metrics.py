# -*- coding: utf-8 -*-
"""Final sunumu için eklenen ek performans metrikleri: FER, MAPE, White Test."""

from __future__ import annotations

import numpy as np

from app.services.ml_evaluation_service import (
    _classification_metrics,
    _false_error_rate,
    _regression_metrics,
    _white_test,
)


def test_false_error_rate_in_classification_metrics():
    yt = [0, 0, 1, 1, 0, 1, 0, 1]
    yp = [0, 1, 1, 1, 0, 0, 0, 1]
    m = _classification_metrics(yt, yp)
    assert "false_error_rate" in m
    assert 0.0 <= m["false_error_rate"] <= 1.0


def test_fer_zero_when_perfect():
    yt = [0, 1, 0, 1]
    assert _false_error_rate([[2, 0], [0, 2]]) == 0.0


def test_regression_has_mape_and_white_test():
    rng = np.random.default_rng(1)
    x = np.linspace(1, 10, 40)
    yt = 2 * x + rng.normal(0, 1, 40)
    yp = 2 * x
    m = _regression_metrics(yt, yp)
    assert "mape" in m and m["mape"] is not None and m["mape"] >= 0
    assert "white_test" in m and m["white_test"] is not None
    wt = m["white_test"]
    assert {"lm_statistic", "p_value", "heteroskedastic", "yorum"}.issubset(wt)
    assert 0.0 <= wt["p_value"] <= 1.0


def test_white_test_detects_heteroskedasticity():
    rng = np.random.default_rng(2)
    n = 80
    x = np.linspace(1, 10, n)
    # Varyans x ile buyuyor -> heteroskedasite
    yt = 2 * x + rng.normal(0, x, n)
    yp = 2 * x
    wt = _white_test(yt, yp)
    assert wt is not None
    assert wt["heteroskedastic"] is True


def test_white_test_none_on_tiny_sample():
    assert _white_test(np.array([1.0, 2.0]), np.array([1.0, 2.0])) is None
