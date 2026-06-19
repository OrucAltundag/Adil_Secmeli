# -*- coding: utf-8 -*-
"""
Hibrit Karar Modeli (AHP-TOPSIS) ve karsilastirmali degerlendirme.

Final sunumu geregi: en az 1 HIBRIT model + en az 2 farkli algoritma, ve
bunlarin KARSILASTIRMALI degerlendirilmesi.

Bu servis, AYNI ders-kriter matrisi uzerinde uc modeli calistirir:

  1) Esit Agirlikli TOPSIS        — baseline (agirliksiz/notr)
  2) AHP-SAW (Agirlikli Toplam)   — baseline (AHP agirligi + basit toplam)
  3) AHP-TOPSIS HIBRIT            — bu projenin asil karar modeli
       (AHP = agirliklandirma yontemi) + (TOPSIS = siralama yontemi)

Karsilastirma: modellerin urettigi SIRALAMALAR arasinda Spearman ve
Kendall-Tau korelasyonu hesaplanir (siralamalar ne kadar ortusuyor?).

Tasarim: SAF fonksiyonlar — DB bagimliligi yok, tam test edilebilir. Mevcut
karar akisina (decision_run_service) DOKUNMAZ; ayri, sunum/kiyas amacli katman.
"""
from __future__ import annotations

from typing import Any, Sequence

import numpy as np

# Model adlari (sunum/rapor icin sabit)
MODEL_ESIT_TOPSIS = "Eşit Ağırlıklı TOPSIS"
MODEL_AHP_SAW = "AHP-SAW (Ağırlıklı Toplam)"
MODEL_HIBRIT = "AHP-TOPSIS Hibrit"


def _as_matrix(matrix: Sequence[Sequence[float]]) -> np.ndarray:
    m = np.asarray(matrix, dtype=float)
    if m.ndim != 2 or m.size == 0:
        raise ValueError("matrix 2 boyutlu ve bos olmamali (satir=ders, sutun=kriter).")
    return m


def _benefit_mask(n_criteria: int, benefit: Sequence[bool] | None) -> np.ndarray:
    if benefit is None:
        return np.ones(n_criteria, dtype=bool)
    if len(benefit) != n_criteria:
        raise ValueError("benefit uzunlugu kriter sayisina esit olmali.")
    return np.asarray(benefit, dtype=bool)


def _weights(n_criteria: int, weights: Sequence[float] | None) -> np.ndarray:
    if weights is None:
        return np.full(n_criteria, 1.0 / n_criteria)
    w = np.asarray(weights, dtype=float)
    if len(w) != n_criteria:
        raise ValueError("weights uzunlugu kriter sayisina esit olmali.")
    s = w.sum()
    return w / s if s > 0 else np.full(n_criteria, 1.0 / n_criteria)


def topsis_scores(
    matrix: Sequence[Sequence[float]],
    weights: Sequence[float] | None = None,
    benefit: Sequence[bool] | None = None,
) -> list[float]:
    """Klasik TOPSIS yakinlik katsayilari (0-1). 1 = en iyi."""
    m = _as_matrix(matrix)
    rows, cols = m.shape
    w = _weights(cols, weights)
    ben = _benefit_mask(cols, benefit)

    # Vektor normalizasyonu: her sutun / sqrt(sum kareler)
    norm = np.sqrt((m ** 2).sum(axis=0))
    norm[norm == 0] = 1.0
    r = m / norm
    v = r * w  # agirlikli normalize matris

    ideal = np.where(ben, v.max(axis=0), v.min(axis=0))
    anti = np.where(ben, v.min(axis=0), v.max(axis=0))

    d_pos = np.sqrt(((v - ideal) ** 2).sum(axis=1))
    d_neg = np.sqrt(((v - anti) ** 2).sum(axis=1))
    denom = d_pos + d_neg
    denom[denom == 0] = 1.0
    return [float(x) for x in (d_neg / denom)]


def weighted_sum_scores(
    matrix: Sequence[Sequence[float]],
    weights: Sequence[float] | None = None,
    benefit: Sequence[bool] | None = None,
) -> list[float]:
    """AHP-SAW (Simple Additive Weighting). Min-max normalize + agirlikli toplam.

    Maliyet kriterleri (benefit=False) tersine cevrilir. Cikti 0-1 araliginda.
    """
    m = _as_matrix(matrix)
    rows, cols = m.shape
    w = _weights(cols, weights)
    ben = _benefit_mask(cols, benefit)

    col_min = m.min(axis=0)
    col_max = m.max(axis=0)
    rng = col_max - col_min
    rng[rng == 0] = 1.0
    norm = (m - col_min) / rng  # 0-1
    # maliyet kriterlerini cevir
    norm = np.where(ben, norm, 1.0 - norm)
    return [float(x) for x in (norm * w).sum(axis=1)]


def rank_from_scores(scores: Sequence[float]) -> list[int]:
    """Skorlardan siralama (1 = en yuksek skor). Esitlikte ortalama degil,
    kararli (stable) sira; rapor okunabilirligi icin yeterli."""
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    ranks = [0] * len(scores)
    for sira, idx in enumerate(order, start=1):
        ranks[idx] = sira
    return ranks


def _rank_correlation(rank_a: Sequence[int], rank_b: Sequence[int]) -> dict[str, Any]:
    """Iki siralama arasinda Spearman ve Kendall-Tau korelasyonu."""
    out: dict[str, Any] = {"spearman": None, "kendall_tau": None}
    if len(rank_a) < 3:
        return out
    try:
        from scipy import stats

        sp = stats.spearmanr(rank_a, rank_b)
        kt = stats.kendalltau(rank_a, rank_b)
        out["spearman"] = float(getattr(sp, "correlation", sp[0]))  # type: ignore[arg-type]  # scipy stats result fallback
        out["kendall_tau"] = float(getattr(kt, "correlation", kt[0]))  # type: ignore[arg-type]
    except Exception:
        pass
    return out


def compare_models(
    course_ids: Sequence[Any],
    matrix: Sequence[Sequence[float]],
    criteria_keys: Sequence[str],
    ahp_weights: Sequence[float],
    benefit: Sequence[bool] | None = None,
) -> dict[str, Any]:
    """Uc modeli ayni veri uzerinde calistirip karsilastirmali rapor doner.

    Returns:
        {
          'criteria_keys': [...],
          'models': {
             '<model adi>': {'scores': [...], 'ranking': [...]},
             ...
          },
          'comparisons': [
             {'pair': 'A vs B', 'spearman': .., 'kendall_tau': ..}, ...
          ],
          'ranking_table': [  # ders bazinda her modelin sirasi
             {'course_id': .., 'esit_topsis': .., 'ahp_saw': .., 'hibrit': ..}, ...
          ],
        }
    """
    m = _as_matrix(matrix)
    if len(course_ids) != m.shape[0]:
        raise ValueError("course_ids sayisi matrix satir sayisina esit olmali.")
    ben = _benefit_mask(m.shape[1], benefit)

    # H9: topsis_scores / weighted_sum_scores ic dunyada _as_matrix / _benefit_mask
    # cagiriyor; m ve ben numpy ndarray olmasina ragmen runtime'da gecerli
    # Sequence davranisi sergiler. Pylance ndarray <-> Sequence[Sequence[float]]
    # daraltmasini tanimaz; tolist() ile aciklik kaziniyor.
    matrix_seq: Sequence[Sequence[float]] = m.tolist()
    benefit_seq: Sequence[bool] = ben.tolist()

    s_equal = topsis_scores(matrix_seq, weights=None, benefit=benefit_seq)          # baseline 1
    s_saw = weighted_sum_scores(matrix_seq, weights=ahp_weights, benefit=benefit_seq)  # baseline 2
    s_hybrid = topsis_scores(matrix_seq, weights=ahp_weights, benefit=benefit_seq)  # HIBRIT

    models = {
        MODEL_ESIT_TOPSIS: {"scores": s_equal, "ranking": rank_from_scores(s_equal)},
        MODEL_AHP_SAW: {"scores": s_saw, "ranking": rank_from_scores(s_saw)},
        MODEL_HIBRIT: {"scores": s_hybrid, "ranking": rank_from_scores(s_hybrid)},
    }

    pairs = [
        (MODEL_HIBRIT, MODEL_ESIT_TOPSIS),
        (MODEL_HIBRIT, MODEL_AHP_SAW),
        (MODEL_ESIT_TOPSIS, MODEL_AHP_SAW),
    ]
    comparisons = []
    for a, b in pairs:
        corr = _rank_correlation(models[a]["ranking"], models[b]["ranking"])
        comparisons.append({"pair": f"{a} ↔ {b}", **corr})

    ranking_table = []
    for i, cid in enumerate(course_ids):
        ranking_table.append({
            "course_id": cid,
            "esit_topsis_sira": models[MODEL_ESIT_TOPSIS]["ranking"][i],
            "ahp_saw_sira": models[MODEL_AHP_SAW]["ranking"][i],
            "hibrit_sira": models[MODEL_HIBRIT]["ranking"][i],
            "hibrit_skor": round(models[MODEL_HIBRIT]["scores"][i], 4),
        })
    ranking_table.sort(key=lambda r: r["hibrit_sira"])

    return {
        "criteria_keys": list(criteria_keys),
        "ahp_weights": [float(x) for x in _weights(m.shape[1], ahp_weights)],
        "models": models,
        "comparisons": comparisons,
        "ranking_table": ranking_table,
    }


def format_comparison_report(result: dict[str, Any], top_n: int = 15) -> str:
    """Karsilastirma sonucunu insan-okur metne cevirir (sunum/booklet icin)."""
    lines = [
        "HIBRIT KARAR MODELI — KARSILASTIRMALI DEGERLENDIRME",
        "=" * 60,
        "Kriterler: " + ", ".join(result.get("criteria_keys", [])),
        "AHP agirliklari: " + ", ".join(f"{w:.3f}" for w in result.get("ahp_weights", [])),
        "",
        "Modeller:",
        f"  1) {MODEL_ESIT_TOPSIS}  (baseline)",
        f"  2) {MODEL_AHP_SAW}  (baseline)",
        f"  3) {MODEL_HIBRIT}  (HIBRIT — bu projenin modeli)",
        "",
        "Siralama Korelasyonlari (1.0 = tam ortusme):",
    ]
    for c in result.get("comparisons", []):
        sp = c.get("spearman")
        kt = c.get("kendall_tau")
        sp_s = f"{sp:.3f}" if isinstance(sp, float) else "-"
        kt_s = f"{kt:.3f}" if isinstance(kt, float) else "-"
        lines.append(f"  {c['pair']}:  Spearman={sp_s}  Kendall={kt_s}")
    lines += ["", f"Ders Siralamasi (ilk {top_n}, hibrit'e gore):",
              f"  {'Ders':<10} {'Hibrit':>7} {'EsitTOPSIS':>11} {'AHP-SAW':>8} {'Skor':>7}"]
    for row in result.get("ranking_table", [])[:top_n]:
        lines.append(
            f"  {str(row['course_id']):<10} {row['hibrit_sira']:>7} "
            f"{row['esit_topsis_sira']:>11} {row['ahp_saw_sira']:>8} {row['hibrit_skor']:>7.4f}"
        )
    return "\n".join(lines)
