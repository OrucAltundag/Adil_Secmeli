# -*- coding: utf-8 -*-
"""
Otomatik Karar Destek Modulu
============================

AHP-agirlikli havuz skoru (+ varsa ML tahmini) sinyallerini
birlestirerek her secmeli ders icin OTOMATIK karar onerisi uretir:

  AC            -> skor yuksek; acilmasi/mufredata alinmasi onerilir
  HAVUZDA_TUT   -> orta skor; havuzda beklesin
  IPTAL_ADAYI   -> dusuk skor + dusuk populerlik; iptal degerlendirilmeli

Cikti, gerekce ve guven skoru ile birlikte; karar verici icin ozet.
Bu modul kararlari OTOMATIK UYGULAMAZ — yalnizca destekleyici oneridir.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from app.services.pool_recommendation_service import recommend_from_pool

AC_ESIGI = 60.0          # >= bu skor -> AC
IPTAL_ESIGI = 35.0       # < bu skor (+dusuk populerlik) -> IPTAL_ADAYI


def _ml_sinyali(conn: sqlite3.Connection, ders_id: int, year: int) -> float:
    """Varsa ML tahmininden -1..+1 araliginda destek sinyali (yoksa 0)."""
    try:
        from app.services.ml_prediction_service import get_predictions_for_course

        preds = get_predictions_for_course(conn, int(ders_id), int(year))
        if not preds:
            return 0.0
        etkili = [p for p in preds if p.get("should_influence_decision")]
        if not etkili:
            return 0.0
        # ortalama guven * yon (pozitif tahmin +; aksi -)
        toplam = 0.0
        for p in etkili:
            guv = float(p.get("confidence_score") or 0.0)
            txt = str(p.get("predicted_value_text") or "").lower()
            yon = 1.0 if any(k in txt for k in ("evet", "yuksek", "artacak", "1")) else -1.0
            toplam += yon * guv
        return max(-1.0, min(1.0, toplam / len(etkili)))
    except Exception:
        return 0.0


def auto_decision_support(
    conn: sqlite3.Connection,
    *,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    semester: str | None = None,
    use_ml: bool = True,
) -> dict[str, Any]:
    """
    Otomatik karar onerileri uretir.

    Returns:
        {
          "ozet": {ac, havuzda_tut, iptal_adayi, toplam, veri_yok,
                   ml_kullanildi},
          "agirliklar": {...},
          "kararlar": [ {ders_id, kod, ad, skor, ml_sinyal, nihai_skor,
                         karar, guven, gerekce}, ... ]   # nihai_skor desc
        }
    """
    rapor = recommend_from_pool(
        conn, year=year, faculty_id=faculty_id,
        department_id=department_id, semester=semester,
        top_n=0,  # tum siralama
        oner_esigi=AC_ESIGI,
    )
    agirlik = rapor["agirliklar"]
    kararlar: list[dict[str, Any]] = []
    sayac = {"AC": 0, "HAVUZDA_TUT": 0, "IPTAL_ADAYI": 0}

    for o in rapor["tum_siralama"]:
        skor = float(o["skor"])
        ml = _ml_sinyali(conn, o["ders_id"], year) if use_ml else 0.0
        # ML sinyali skoru +-10 puan kaydirabilir
        nihai = max(0.0, min(100.0, skor + ml * 10.0))
        populerlik = float(o["kriterler"].get("populerlik", 0.0))

        if nihai >= AC_ESIGI:
            karar = "AC"
        elif nihai < IPTAL_ESIGI and populerlik < 40.0:
            karar = "IPTAL_ADAYI"
        else:
            karar = "HAVUZDA_TUT"
        sayac[karar] += 1

        # Guven: skorun esiklere uzakligi + ML uyumu (0-1)
        if karar == "AC":
            mesafe = (nihai - AC_ESIGI) / 40.0
        elif karar == "IPTAL_ADAYI":
            mesafe = (IPTAL_ESIGI - nihai) / 35.0
        else:
            mesafe = 1.0 - abs(nihai - 50.0) / 50.0
        guven = round(max(0.05, min(0.99, 0.55 + 0.4 * mesafe
                                    + 0.15 * abs(ml))), 3)

        ml_aciklama = (
            f" ML destegi {ml:+.2f}." if abs(ml) > 1e-9 else
            " ML tahmini yok (yalniz AHP skoru)."
        )
        if karar == "AC":
            oz = "Skor yuksek; ACILMASI / mufredata alinmasi onerilir."
        elif karar == "IPTAL_ADAYI":
            oz = ("Skor ve populerlik dusuk; IPTAL adayi olarak "
                  "degerlendirilmeli.")
        else:
            oz = "Orta skor; HAVUZDA beklemesi onerilir."
        gerekce = (
            f"AHP skoru {skor:.1f}, nihai {nihai:.1f} "
            f"(esik AC>={AC_ESIGI:.0f}, iptal<{IPTAL_ESIGI:.0f}).{ml_aciklama} {oz}"
        )

        kararlar.append({
            "ders_id": o["ders_id"],
            "kod": o["kod"],
            "ad": o["ad"],
            "statu": o["statu"],
            "skor": round(skor, 2),
            "ml_sinyal": round(ml, 3),
            "nihai_skor": round(nihai, 2),
            "karar": karar,
            "guven": guven,
            "gerekce": gerekce,
        })

    kararlar.sort(key=lambda x: x["nihai_skor"], reverse=True)
    return {
        "ozet": {
            "ac": sayac["AC"],
            "havuzda_tut": sayac["HAVUZDA_TUT"],
            "iptal_adayi": sayac["IPTAL_ADAYI"],
            "toplam": len(kararlar),
            "veri_yok": rapor["veri_yok"],
            "ml_kullanildi": bool(use_ml),
        },
        "agirliklar": agirlik,
        "esikler": {"ac": AC_ESIGI, "iptal": IPTAL_ESIGI},
        "kararlar": kararlar,
    }
