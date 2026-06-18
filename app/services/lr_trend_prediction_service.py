# -*- coding: utf-8 -*-
"""Linear Regression ile geçmiş kesinleşme puanlarından yeni yıl trend skoru tahmini.

LR_Trend_Skor_Tahmini_Raporu.docx davranışı:

- Hedef yıl için tahmin: son 3 yılın **kesinleşme puanları** (havuz.skor) kullanılır.
  Örn. 2024 tahmini için 2021, 2022, 2023 puanları okunur.
- Eksik yıl varsa **varsayılan değer 50** uygulanır (nötr; 0 değil — veri yokluğunu
  haksız cezaya çevirmesin).
- Yıllar sıralı tam sayıya eşlenir: 2021→1, 2022→2, 2023→3, **2024→4**.
- Basit doğrusal regresyon: ``y = β0 + β1·x``; en-küçük-kareler çözümü.
- Tahmin **0–100 aralığına sınırlandırılır**; ayrıca 0–1 normalize edilmiş trend
  skoru da döndürülür (karar algoritmalarında kullanılabilir).
- Trend yönü: eğim ±3 puan eşiğine göre Artan / Azalan / Stabil.

Bu servis salt-okunur: hiçbir şey yazmaz; UI/raporlama çağrısı için tasarlandı.
"""

from __future__ import annotations

import sqlite3
from typing import Any

DEFAULT_MISSING_SCORE = 50.0
SCORE_MIN = 0.0
SCORE_MAX = 100.0
HISTORY_YEARS = 3
TREND_DELTA_THRESHOLD = 3.0  # |β1| < 3 puan ⇒ Stabil

DIRECTION_RISING = "rising"
DIRECTION_FALLING = "falling"
DIRECTION_STABLE = "stable"

DIRECTION_LABEL_TR = {
    DIRECTION_RISING: "Artan",
    DIRECTION_FALLING: "Azalan",
    DIRECTION_STABLE: "Stabil",
}


def _fetch_finalized_score(cur: sqlite3.Cursor, course_id: int, year: int) -> float | None:
    """Verilen ders + yıl için kesinleşme puanını (0–100) döndürür; yoksa None."""
    try:
        cur.execute(
            "SELECT MAX(skor) FROM havuz WHERE CAST(ders_id AS INTEGER) = ? AND yil = ? AND skor IS NOT NULL",
            (int(course_id), int(year)),
        )
        row = cur.fetchone()
    except sqlite3.OperationalError:
        return None
    if not row or row[0] is None:
        return None
    try:
        v = float(row[0])
    except (TypeError, ValueError):
        return None
    # havuz.skor zaten 0–100 ölçeğinde; güvenlik için sınırla.
    return max(SCORE_MIN, min(SCORE_MAX, v))


def _linear_regression(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """En-küçük-kareler doğrusal regresyon: y = β0 + β1·x. (intercept, slope) döner."""
    n = len(xs)
    if n == 0 or len(ys) != n:
        return 0.0, 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    var_x = sum((x - mean_x) ** 2 for x in xs)
    if var_x <= 0:
        # Tüm x'ler aynı (örn. tek nokta): eğim 0, intercept = ortalama.
        return mean_y, 0.0
    cov_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = cov_xy / var_x
    intercept = mean_y - slope * mean_x
    return intercept, slope


def predict_next_year_trend(
    cur: sqlite3.Cursor,
    course_id: int,
    target_year: int,
    history_years: int = HISTORY_YEARS,
    default_missing: float = DEFAULT_MISSING_SCORE,
) -> dict[str, Any]:
    """LR ile ``target_year`` için tahmini trend skoru.

    Returns:
        {
          "predicted_score_100": float (0..100),  # 2024 LR tahmini
          "trend_score_normalized": float (0..1), # karar algoritmaları için
          "slope": float, "intercept": float,
          "direction": "rising"/"falling"/"stable",
          "direction_label_tr": "Artan"/"Azalan"/"Stabil",
          "history": [{year, score, is_default}, ...],  # eski->yeni, target hariç
          "missing_year_count": int,  # varsayılana düşen yıl sayısı
          "confidence": "yuksek"/"orta"/"dusuk",  # varsayılan sayısı arttıkça düşer
          "model_clamped": bool,  # tahmin 0..100'e kırpıldıysa
          "raw_prediction": float,  # kırpılmamış model çıktısı
          "explanation": str,
        }
    """
    target_year = int(target_year)
    history: list[dict[str, Any]] = []
    xs: list[float] = []
    ys: list[float] = []
    missing = 0
    # Yıllar sıralı tam sayıya eşlenir: en eski (target-history)→1, …, target_year→history+1
    for offset in range(history_years, 0, -1):
        year = target_year - offset
        x_index = float(history_years - offset + 1)  # 1..history_years
        score = _fetch_finalized_score(cur, int(course_id), year)
        if score is None:
            score = float(default_missing)
            missing += 1
            is_default = True
        else:
            is_default = False
        history.append({"year": year, "score": float(score), "is_default": is_default, "x": x_index})
        xs.append(x_index)
        ys.append(float(score))

    intercept, slope = _linear_regression(xs, ys)
    target_x = float(history_years + 1)  # 2024 = 4
    raw_pred = intercept + slope * target_x
    pred = max(SCORE_MIN, min(SCORE_MAX, raw_pred))
    model_clamped = (raw_pred != pred)

    if abs(slope) < TREND_DELTA_THRESHOLD:
        direction = DIRECTION_STABLE
    elif slope > 0:
        direction = DIRECTION_RISING
    else:
        direction = DIRECTION_FALLING

    # Güven: tüm yıllar gerçekse "yüksek", yarıdan fazlası varsayılansa "düşük".
    if missing == 0:
        confidence = "yuksek"
    elif missing < history_years / 2:
        confidence = "orta"
    else:
        confidence = "dusuk"

    expl_parts = [
        f"LR modeli {history_years} yıllık kesinleşme puanı üzerinden eğitildi.",
        f"Eğim (β1) = {slope:+.3f} puan/yıl, kesişim (β0) = {intercept:.2f}.",
        f"{target_year} için ham tahmin = {raw_pred:.2f}",
    ]
    if model_clamped:
        expl_parts.append(f"(0..100 aralığına kırpıldı → {pred:.2f}).")
    else:
        expl_parts.append(f"= {pred:.2f}.")
    if missing > 0:
        expl_parts.append(
            f"{missing} yıl için veri yoktu; varsayılan {default_missing:.0f} kullanıldı."
        )

    return {
        "predicted_score_100": round(pred, 2),
        "trend_score_normalized": round(pred / 100.0, 4),
        "slope": round(slope, 4),
        "intercept": round(intercept, 4),
        "direction": direction,
        "direction_label_tr": DIRECTION_LABEL_TR[direction],
        "history": history,
        "missing_year_count": missing,
        "confidence": confidence,
        "model_clamped": model_clamped,
        "raw_prediction": round(raw_pred, 4),
        "target_year": target_year,
        "default_missing_value": float(default_missing),
        "explanation": " ".join(expl_parts),
    }
