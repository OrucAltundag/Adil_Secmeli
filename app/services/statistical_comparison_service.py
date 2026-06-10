# -*- coding: utf-8 -*-
"""Benchmark sonuçları için güven aralığı ve istatistiksel karşılaştırma servisleri."""

from __future__ import annotations

import math
import random
from typing import Any, Iterable


def bootstrap_confidence_interval(values: Iterable[float], confidence: float = 0.95, n_bootstrap: int = 1000) -> dict[str, Any]:
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return {"mean": None, "lower": None, "upper": None, "confidence": confidence, "warning": "Güven aralığı için veri yok."}
    if len(vals) == 1:
        return {"mean": vals[0], "lower": vals[0], "upper": vals[0], "confidence": confidence, "warning": "Tek değer için CI bilgi verici değildir."}
    rng = random.Random(42)
    means = []
    for _ in range(int(n_bootstrap)):
        sample = [vals[rng.randrange(len(vals))] for _ in vals]
        means.append(sum(sample) / len(sample))
    means.sort()
    alpha = (1.0 - confidence) / 2.0
    low_idx = int(alpha * len(means))
    high_idx = min(len(means) - 1, int((1.0 - alpha) * len(means)) - 1)
    return {"mean": sum(vals) / len(vals), "lower": means[low_idx], "upper": means[high_idx], "confidence": confidence}


def compare_two_models(metric_values_a: Iterable[float], metric_values_b: Iterable[float], test_type: str = "auto") -> dict[str, Any]:
    a = [float(v) for v in metric_values_a]
    b = [float(v) for v in metric_values_b]
    n = min(len(a), len(b))
    if n == 0:
        return {"test": "none", "p_value": None, "significant": False, "summary": "Karşılaştırma için ortak fold/metrik yok."}
    a = a[:n]
    b = b[:n]
    effect = calculate_effect_size(a, b)
    try:
        from scipy import stats

        if n < 3:
            p_value = None
            test = "descriptive"
        elif test_type == "paired_t" or (test_type == "auto" and n >= 20):
            test = "paired_t_test"
            # scipy.stats result namedtuple — Pylance stubs `_` placeholder uretiyor,
            # `.pvalue` runtime'da daima vardir. getattr ile sahte uyari elimine edilir.
            p_value = float(getattr(stats.ttest_rel(a, b), "pvalue", 1.0))
        else:
            test = "wilcoxon_signed_rank"
            p_value = float(getattr(stats.wilcoxon(a, b, zero_method="zsplit"), "pvalue", 1.0))
        significant = bool(p_value is not None and p_value < 0.05)
        return {
            "test": test,
            "p_value": p_value,
            "significant": significant,
            "effect_size": effect,
            "summary": _comparison_summary(a, b, p_value, significant),
        }
    except Exception as exc:
        diff = [x - y for x, y in zip(a, b)]
        ci = bootstrap_confidence_interval(diff)
        significant = bool(ci["lower"] is not None and (ci["lower"] > 0 or ci["upper"] < 0))
        return {
            "test": "bootstrap_fallback",
            "p_value": None,
            "significant": significant,
            "effect_size": effect,
            "confidence_interval": ci,
            "warning": f"scipy testi kullanılamadı; bootstrap fallback uygulandı: {exc}",
            "summary": _comparison_summary(a, b, None, significant),
        }


def compare_classifiers_mcnemar(y_true: Iterable[Any], pred_a: Iterable[Any], pred_b: Iterable[Any]) -> dict[str, Any]:
    yt = list(y_true)
    pa = list(pred_a)
    pb = list(pred_b)
    n = min(len(yt), len(pa), len(pb))
    b = c = 0
    for truth, a, pred in zip(yt[:n], pa[:n], pb[:n]):
        a_ok = truth == a
        b_ok = truth == pred
        if a_ok and not b_ok:
            b += 1
        elif not a_ok and b_ok:
            c += 1
    if b + c == 0:
        return {"test": "mcnemar", "statistic": 0.0, "p_value": 1.0, "summary": "İki sınıflandırıcı aynı hata örüntüsüne sahip."}
    statistic = ((abs(b - c) - 1) ** 2) / (b + c)
    try:
        from scipy.stats import chi2

        p_value = float(1 - chi2.cdf(statistic, df=1))
    except Exception:
        p_value = math.exp(-0.5 * statistic)
    return {"test": "mcnemar", "b": b, "c": c, "statistic": statistic, "p_value": p_value, "significant": p_value < 0.05}


def wilcoxon_signed_rank(values_a: Iterable[float], values_b: Iterable[float]) -> dict[str, Any]:
    return compare_two_models(values_a, values_b, test_type="wilcoxon")


def paired_t_test(values_a: Iterable[float], values_b: Iterable[float]) -> dict[str, Any]:
    return compare_two_models(values_a, values_b, test_type="paired_t")


def friedman_test(results_matrix: list[list[float]]) -> dict[str, Any]:
    if len(results_matrix) < 2:
        return {"test": "friedman", "p_value": None, "warning": "Friedman testi için en az iki algoritma gerekir."}
    try:
        from scipy.stats import friedmanchisquare

        stat = friedmanchisquare(*results_matrix)
        return {"test": "friedman", "statistic": float(stat.statistic), "p_value": float(stat.pvalue), "significant": float(stat.pvalue) < 0.05}
    except Exception as exc:
        return {"test": "friedman", "p_value": None, "warning": f"Friedman testi çalıştırılamadı: {exc}"}


def nemenyi_posthoc_if_available(results_matrix: list[list[float]]) -> dict[str, Any]:
    return {"available": False, "warning": "Nemenyi post-hoc bağımlılığı kurulmadı; Friedman sonucu ve pairwise testler raporlanır."}


def calculate_effect_size(values_a: Iterable[float], values_b: Iterable[float]) -> float:
    a = [float(v) for v in values_a]
    b = [float(v) for v in values_b]
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    diff = [a[i] - b[i] for i in range(n)]
    mean = sum(diff) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in diff) / max(1, n - 1))
    return float(mean / sd) if sd else 0.0


def generate_statistical_summary(comparison: dict[str, Any]) -> str:
    return str(comparison.get("summary") or "İstatistiksel karşılaştırma üretildi.")


def _comparison_summary(a: list[float], b: list[float], p_value: float | None, significant: bool) -> str:
    mean_a = sum(a) / len(a)
    mean_b = sum(b) / len(b)
    direction = "daha yüksek" if mean_a > mean_b else "daha düşük"
    if p_value is None:
        significance = "istatistiksel anlamlılık p-değeri hesaplanamadı"
    elif significant:
        significance = "fark istatistiksel olarak anlamlı görünüyor"
    else:
        significance = "fark istatistiksel olarak anlamlı değildir"
    return f"A modeli ortalama {direction} metrik almıştır ({mean_a:.3f} vs {mean_b:.3f}); {significance}."
