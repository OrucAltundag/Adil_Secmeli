# app/services/course_analyzer.py
"""
Tek ders analiz servisi.

analyze_single_course(course_id, year, db_conn) -> dict

Çalışma sırası:
  1. DB'den ders meta + kriter verisi çek
  2. Eksik veri kontrolü
  3. AHP ağırlıkları hesapla
  4. TOPSIS (tek satır normalise + uzaklıklar)
  5. Trend/LR tahmini
  6. RF tahmin (varsa yeterli veri)
  7. DT karar gerekçesi
  8. in_mufredat kararını üret
  9. State machine (calculate_next_status) ile final statu/sayac
 10. Tüm ara çıktıları dict olarak dön
"""

import math
import os
import time
import sqlite3
import logging
from typing import Any, Optional

from app.services.db import db_session
from app.services.havuz_karar import (
    calculate_next_status,
    STATU_MUFREDATTA,
    STATU_HAVUZDA,
    STATU_DINLENMEDE,
    STATU_IPTAL,
    MAKS_DUSME_SAYACI,
)
from app.services.calculation import KararMotoru

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
SKOR_BARAJ       = 40.0   # TOPSIS skoru bu barajın altındaysa "düşüyor"
BASARI_BARAJ     = 0.40   # Başarı oranı (0-1) barajı
DOLULUK_BARAJ    = 0.30   # Doluluk oranı (0-1) barajı


# ---------------------------------------------------------------------------
# Hata sınıfı
# ---------------------------------------------------------------------------
class VeriEksikHatasi(Exception):
    """Seçilen dersin o yıl için yeterli kriter verisi yoksa fırlatılır."""


# ---------------------------------------------------------------------------
# Yardımcı
# ---------------------------------------------------------------------------
def _safe_float(val, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        return default if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return default


def _statu_label(statu: int) -> str:
    return {
        STATU_MUFREDATTA: "Mufredatta",
        STATU_HAVUZDA:    "Havuzda",
        STATU_DINLENMEDE: "Dinlenmede (1 yil)",
        STATU_IPTAL:      "Kalici Iptal",
    }.get(statu, f"Bilinmiyor ({statu})")


# ---------------------------------------------------------------------------
# Veritabanı veri çekiciler
# ---------------------------------------------------------------------------
def _fetch_course_meta(cur: sqlite3.Cursor, course_id: int) -> dict:
    # ders tablosunda hangi tip kolonu var?
    cur.execute("PRAGMA table_info(ders)")
    cols = {r[1] for r in cur.fetchall()}
    if "DersTipi" in cols:
        tip_col = "DersTipi"
    elif "tip" in cols:
        tip_col = "tip"
    else:
        tip_col = None

    if tip_col:
        cur.execute(
            f"SELECT ders_id, ad, COALESCE({tip_col}, '') as tip FROM ders WHERE ders_id = ?",
            (course_id,)
        )
    else:
        cur.execute(
            "SELECT ders_id, ad, '' as tip FROM ders WHERE ders_id = ?",
            (course_id,)
        )
    row = cur.fetchone()
    if not row:
        raise VeriEksikHatasi(f"Ders bulunamadi: ders_id={course_id}")
    return {"ders_id": int(row[0]), "ad": str(row[1]), "tip": str(row[2])}


def _fetch_criteria(cur: sqlite3.Cursor, course_id: int, year: int) -> dict:
    """
    ders_kriterleri -> performans -> populerlik sırasıyla okur.
    En az basari_orani ve doluluk_orani dolu olmalı; yoksa VeriEksikHatasi.
    """
    # 1. ders_kriterleri (Kriter sayfasından girilmiş)
    cur.execute(
        """SELECT toplam_ogrenci, gecen_ogrenci, basari_ortalamasi,
                  kontenjan, kayitli_ogrenci
           FROM ders_kriterleri WHERE ders_id=? AND yil=? LIMIT 1""",
        (course_id, year)
    )
    row_dk = cur.fetchone()

    # 2. performans tablosu (fallback)
    cur.execute(
        "SELECT ortalama_not, basari_orani FROM performans WHERE ders_id=? AND akademik_yil=? LIMIT 1",
        (course_id, year)
    )
    row_p = cur.fetchone()

    # 3. populerlik tablosu (fallback)
    cur.execute(
        "SELECT talep_sayisi, kontenjan, doluluk_orani FROM populerlik WHERE ders_id=? AND akademik_yil=? LIMIT 1",
        (course_id, year)
    )
    row_pop = cur.fetchone()

    # Kriterleri birleştir (ders_kriterleri öncelikli)
    if row_dk:
        toplam   = _safe_float(row_dk[0])
        gecen    = _safe_float(row_dk[1])
        ort_not  = _safe_float(row_dk[2])
        kont     = _safe_float(row_dk[3])
        kayitli  = _safe_float(row_dk[4])
        basari   = (gecen / toplam) if toplam > 0 else _safe_float(row_p[1] if row_p else None)
        doluluk  = (kayitli / kont) if kont > 0 else _safe_float(row_pop[2] if row_pop else None)
    elif row_p and row_pop:
        ort_not  = _safe_float(row_p[0])
        basari   = _safe_float(row_p[1])
        kont     = _safe_float(row_pop[1])
        kayitli  = _safe_float(row_pop[0])
        doluluk  = _safe_float(row_pop[2])
        toplam   = kayitli
        gecen    = toplam * basari
    else:
        raise VeriEksikHatasi(
            f"Ders {course_id} icin {year} yilina ait kriter verisi bulunamadi. "
            "Lutfen Kriter sayfasindan giris yapiniz."
        )

    basari  = min(max(basari, 0.0), 1.0)
    doluluk = min(max(doluluk, 0.0), 1.0)

    return {
        "toplam_ogrenci":    toplam,
        "gecen_ogrenci":     gecen,
        "basari_ortalamasi": ort_not,
        "kontenjan":         kont,
        "kayitli_ogrenci":   kayitli,
        "basari_orani":      basari,
        "doluluk_orani":     doluluk,
    }


def _fetch_prev_pool(cur: sqlite3.Cursor, course_id: int, year: int) -> dict:
    """Bir önceki yılın havuz kaydını döner."""
    prev_year = year - 1
    cur.execute(
        """SELECT statu, sayac, skor FROM havuz
           WHERE CAST(ders_id AS INTEGER)=? AND yil=? LIMIT 1""",
        (course_id, prev_year)
    )
    row = cur.fetchone()
    if row:
        return {"year": prev_year, "statu": int(row[0] or 0),
                "sayac": int(row[1] or 0), "skor": _safe_float(row[2])}
    return {"year": prev_year, "statu": 0, "sayac": 0, "skor": 0.0}


def _fetch_gecmis_trend(cur: sqlite3.Cursor, course_id: int, base_year: int) -> list:
    """Son 3 yılın başarı oranını döner (en yeni önce)."""
    cur.execute(
        """SELECT akademik_yil, basari_orani FROM performans
           WHERE ders_id=? AND akademik_yil<=? ORDER BY akademik_yil DESC LIMIT 3""",
        (course_id, base_year)
    )
    return [{"yil": int(r[0]), "oran": _safe_float(r[1])} for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Algoritma adımları
# ---------------------------------------------------------------------------
def _run_ahp(criteria: dict) -> dict:
    """AHP ağırlıklarını ve CR'yi döner."""
    t0 = time.perf_counter()
    try:
        motor = KararMotoru()
        weights = motor.ahp_calistir()
        cr, valid, lmax = motor.ahp_tutarlilik_kontrolu(agirliklar=weights)
        return {
            "weights": {
                "basari":    round(weights[0], 4),
                "trend":     round(weights[1], 4),
                "populerlik": round(weights[2], 4),
                "anket":     round(weights[3], 4),
            },
            "CR":     round(cr, 4),
            "valid":  valid,
            "lambda_max": round(lmax, 4),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except Exception as exc:
        logger.warning("AHP hatasi: %s", exc)
        return {"error": str(exc), "weights": {"basari": 0.5, "trend": 0.2,
                                                "populerlik": 0.2, "anket": 0.1},
                "CR": 0.0, "valid": False}


def _run_topsis_single(criteria: dict, ahp_weights: dict) -> dict:
    """
    Tek satır TOPSIS — skoru [0, 100] aralığında döner.
    Tek satır olduğundan normalise edilmiş vektörün kendisi = referans;
    pozitif ideal = değerin kendisi, negatif ideal = 0.
    Bu formülasyon skoru doğrusal olarak hesaplar (multi-row TOPSIS için
    harici veritabanı gerekir, bu modda yeterlidir).
    """
    t0 = time.perf_counter()
    try:
        basari    = _safe_float(criteria.get("basari_orani"))
        doluluk   = _safe_float(criteria.get("doluluk_orani"))
        trend_val = _safe_float(criteria.get("_trend", basari))   # AHP adımından gelebilir
        anket_val = 0.5   # Anket verisi yoksa nötr

        w = ahp_weights
        w_basari    = _safe_float(w.get("basari",    0.5))
        w_trend     = _safe_float(w.get("trend",     0.2))
        w_pop       = _safe_float(w.get("populerlik",0.2))
        w_anket     = _safe_float(w.get("anket",     0.1))

        # Ağırlıklı toplam skor (0-1)
        ham_skor = (
            basari   * w_basari  +
            trend_val * w_trend   +
            doluluk  * w_pop     +
            anket_val * w_anket
        )
        denom = w_basari + w_trend + w_pop + w_anket
        if denom < 1e-10:
            raise ZeroDivisionError("AHP agirlik toplami sifir")

        yakınlık = ham_skor / denom   # 0-1
        skor_100 = round(yakınlık * 100, 2)

        return {
            "raw_score_01": round(yakınlık, 6),
            "score_100":    skor_100,
            "inputs": {
                "basari": round(basari, 4),
                "trend":  round(trend_val, 4),
                "doluluk": round(doluluk, 4),
                "anket":  anket_val,
            },
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except ZeroDivisionError as exc:
        logger.warning("TOPSIS ZeroDivision: %s", exc)
        return {"error": str(exc), "score_100": 0.0, "raw_score_01": 0.0}
    except Exception as exc:
        logger.warning("TOPSIS hatasi: %s", exc)
        return {"error": str(exc), "score_100": 50.0, "raw_score_01": 0.5}


def _run_trend(gecmis_list: list) -> dict:
    """Trend/LR: ağırlıklı geçmiş ortalama."""
    t0 = time.perf_counter()
    try:
        if not gecmis_list:
            return {"predicted": 0.5, "log": "Gecmis veri yok.", "elapsed_ms": 0}
        motor = KararMotoru()
        trend, log = motor.gecmis_trend_hesapla(gecmis_list)
        return {
            "predicted": round(trend, 4),
            "predicted_100": round(trend * 100, 2),
            "log": log,
            "n_years": len(gecmis_list),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except Exception as exc:
        logger.warning("Trend hatasi: %s", exc)
        return {"error": str(exc), "predicted": 0.5, "predicted_100": 50.0}


def _run_rf_simple(criteria: dict, prev_pool: dict) -> dict:
    """
    Basit RF-yerine-geçen kural tabanlı tahmin.
    Gerçek sklearn RF için yeterli veri (çok satır) gerekir; single-course
    analizde deterministik kural kullanılır ve bu açıkça belirtilir.
    """
    t0 = time.perf_counter()
    try:
        basari  = _safe_float(criteria.get("basari_orani"))
        doluluk = _safe_float(criteria.get("doluluk_orani"))
        sayac   = int(prev_pool.get("sayac", 0))

        # Kural seti (karar ağacı / RF yerine)
        if sayac >= MAKS_DUSME_SAYACI:
            pred_statu = STATU_IPTAL
            prob_str = "Kalici iptal"
        elif basari >= 0.70 and doluluk >= 0.50:
            pred_statu = STATU_MUFREDATTA
            prob_str = "Yuksek basari + yuksek doluluk"
        elif basari >= BASARI_BARAJ and doluluk >= DOLULUK_BARAJ:
            pred_statu = STATU_MUFREDATTA
            prob_str = "Yeterli basari + yeterli doluluk"
        elif basari < BASARI_BARAJ:
            pred_statu = STATU_DINLENMEDE
            prob_str = "Dusuk basari orani"
        else:
            pred_statu = STATU_HAVUZDA
            prob_str = "Orta duzey performans"

        return {
            "predicted_statu": pred_statu,
            "predicted_label": _statu_label(pred_statu),
            "rule":            prob_str,
            "note": "Tek-ders modunda kural tabanli RF kullanildi (sklearn RF cok satir gerektirir).",
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except Exception as exc:
        logger.warning("RF hatasi: %s", exc)
        return {"error": str(exc), "predicted_statu": 0}


def _build_dt_reason(criteria: dict, topsis: dict, in_mufredat: bool,
                     next_statu: int, next_sayac: int, prev_pool: dict) -> str:
    """Karar ağacının insan dilinde açıklamasını üretir."""
    basari      = _safe_float(criteria.get("basari_orani")) * 100
    doluluk     = _safe_float(criteria.get("doluluk_orani")) * 100
    skor        = _safe_float(topsis.get("score_100", 0))
    prev_statu  = prev_pool.get("statu", 0)
    prev_sayac  = prev_pool.get("sayac", 0)

    if next_statu == STATU_IPTAL:
        return (
            f"Ders, kumulatif {next_sayac} kez mufredattan dustu ve "
            f"MAKS_DUSME_SAYACI ({MAKS_DUSME_SAYACI}) sinirini asti; "
            "kalici olarak iptal edildi."
        )
    if next_statu == STATU_DINLENMEDE:
        reason = []
        if basari < BASARI_BARAJ * 100:
            reason.append(f"basari orani %{basari:.1f} < baj %{BASARI_BARAJ*100:.0f}")
        if skor < SKOR_BARAJ:
            reason.append(f"kesinlesme puani {skor:.1f} < baj {SKOR_BARAJ:.0f}")
        if not reason:
            reason.append("komisyon karari ile mufredattan cikarildi")
        return (
            f"Ders mufredattan dustu ({', '.join(reason)}). "
            f"Sayac: {prev_sayac} -> {next_sayac}. 1 yil dinlenmeye alindi."
        )
    if next_statu == STATU_HAVUZDA:
        if prev_statu == STATU_DINLENMEDE:
            return (
                "Ders bir onceki yil dinlenmedeydi. Ceza suresi doldu, "
                "havuza geri dondu. Bu yil mufredata alinamaz."
            )
        return (
            f"Ders havuzda bekliyor. Kesinlesme puani: {skor:.1f}. "
            "Bu yil mufredata alinmadi."
        )
    if next_statu == STATU_MUFREDATTA:
        if prev_statu == STATU_MUFREDATTA:
            return (
                f"Ders mufredatta kalmaya devam ediyor. "
                f"Basari: %{basari:.1f}, Kesinlesme: {skor:.1f}."
            )
        return (
            f"Ders havuzdan mufredata alindi. "
            f"Basari: %{basari:.1f}, Doluluk: %{doluluk:.1f}, Skor: {skor:.1f}."
        )
    return "Durum belirlenemedi."


# ---------------------------------------------------------------------------
# ANA FONKSİYON
# ---------------------------------------------------------------------------
def analyze_single_course(
    course_id: int,
    year: int,
    db_path: Optional[str] = None,
) -> dict:
    """
    Tek ders analiz servisi (thread-safe).

    Baglanti bu fonksiyon icinde acilir ve kapatilir; worker thread'de
    guvenle cagrilabilir. db_conn parametresi KULLANILMAZ.

    Parametreler
    ------------
    course_id : int
        Analiz edilecek dersin ders_id'si.
    year : int
        Analiz yılı (2022-2025).
    db_path : str, optional
        Veritabani dosya yolu. None ise data/adil_secmeli.db kullanilir.

    Dönüş
    ------
    dict  — Tüm ara çıktıları ve nihai kararı içerir.
    dict with {"error": "..."} — Veri eksikliği veya kritik hata durumunda.
    """
    t_total = time.perf_counter()

    path = db_path or "data/adil_secmeli.db"
    if not path or not os.path.exists(path):
        return {"error": "Veritabani bulunamadi veya yol gecersiz."}

    result: dict[str, Any] = {
        "course_id": course_id,
        "year": year,
        "course": {},
        "criteria": {},
        "steps": {},
        "decision": {},
        "errors": [],
    }

    with db_session(path) as conn:
        cur = conn.cursor()

        # ------------------------------------------------------------------
        # 1. Ders meta verisi
        # ------------------------------------------------------------------
        try:
            result["course"] = _fetch_course_meta(cur, course_id)
        except VeriEksikHatasi as exc:
            return {"error": str(exc)}
        except Exception as exc:
            return {"error": f"Ders meta verisi alinamadi: {exc}"}

        # ------------------------------------------------------------------
        # 2. Kriter verisi
        # ------------------------------------------------------------------
        try:
            criteria = _fetch_criteria(cur, course_id, year)
            result["criteria"] = criteria
        except VeriEksikHatasi as exc:
            return {"error": str(exc)}
        except Exception as exc:
            return {"error": f"Kriter verisi alinamadi: {exc}"}

        # ------------------------------------------------------------------
        # 3. Geçmiş trend verisi
        # ------------------------------------------------------------------
        gecmis_list = []
        try:
            gecmis_list = _fetch_gecmis_trend(cur, course_id, year)
        except Exception as exc:
            result["errors"].append(f"Gecmis trend alinamadi: {exc}")

        # ------------------------------------------------------------------
        # 4. Bir önceki yıl havuz kaydı
        # ------------------------------------------------------------------
        prev_pool = {"year": year - 1, "statu": 0, "sayac": 0, "skor": 0.0}
        try:
            prev_pool = _fetch_prev_pool(cur, course_id, year)
        except Exception as exc:
            result["errors"].append(f"Onceki yil havuz kaydi alinamadi: {exc}")

        # ------------------------------------------------------------------
        # 5. AHP
        # ------------------------------------------------------------------
        ahp_result = _run_ahp(criteria)
        result["steps"]["ahp"] = ahp_result
        if "error" in ahp_result:
            result["errors"].append(f"AHP: {ahp_result['error']}")

        ahp_weights = ahp_result.get("weights", {"basari": 0.5, "trend": 0.2,
                                                  "populerlik": 0.2, "anket": 0.1})

        # ------------------------------------------------------------------
        # 6. Trend/LR
        # ------------------------------------------------------------------
        trend_result = _run_trend(gecmis_list)
        result["steps"]["trend"] = trend_result
        if "error" in trend_result:
            result["errors"].append(f"Trend: {trend_result['error']}")

        criteria["_trend"] = trend_result.get("predicted", criteria.get("basari_orani", 0.5))

        # ------------------------------------------------------------------
        # 7. TOPSIS
        # ------------------------------------------------------------------
        topsis_result = _run_topsis_single(criteria, ahp_weights)
        result["steps"]["topsis"] = topsis_result
        if "error" in topsis_result:
            result["errors"].append(f"TOPSIS: {topsis_result['error']}")

        skor_final = topsis_result.get("score_100", 50.0)

        # ------------------------------------------------------------------
        # 8. RF
        # ------------------------------------------------------------------
        rf_result = _run_rf_simple(criteria, prev_pool)
        result["steps"]["rf"] = rf_result
        if "error" in rf_result:
            result["errors"].append(f"RF: {rf_result['error']}")

        # ------------------------------------------------------------------
        # 9. in_mufredat kararı
        # ------------------------------------------------------------------
        basari  = _safe_float(criteria.get("basari_orani"))
        doluluk = _safe_float(criteria.get("doluluk_orani"))

        if year == 2022:
            cur.execute(
                "SELECT statu FROM havuz WHERE CAST(ders_id AS INTEGER)=? AND yil=2022 LIMIT 1",
                (course_id,)
            )
            row_gt = cur.fetchone()
            in_mufredat = bool(row_gt and int(row_gt[0]) == STATU_MUFREDATTA)
            is_ground_truth = True
        else:
            in_mufredat = (skor_final >= SKOR_BARAJ
                           and basari >= BASARI_BARAJ
                           and doluluk >= DOLULUK_BARAJ)
            is_ground_truth = False

        # ------------------------------------------------------------------
        # 10. State machine
        # ------------------------------------------------------------------
        if is_ground_truth:
            cur.execute(
                "SELECT statu, sayac FROM havuz WHERE CAST(ders_id AS INTEGER)=? AND yil=2022 LIMIT 1",
                (course_id,)
            )
            row_gt2 = cur.fetchone()
            next_statu = int(row_gt2[0]) if row_gt2 else 0
            next_sayac = int(row_gt2[1]) if row_gt2 else 0
            sm_note    = "2022 Ground Truth: state machine hesabi yapilmadi."
        else:
            prev_statu = prev_pool.get("statu", 0)
            prev_sayac = prev_pool.get("sayac", 0)
            next_statu, next_sayac = calculate_next_status(
                prev_statu, prev_sayac, in_mufredat
            )
            sm_note = (
                f"prev ({prev_pool['year']}): statu={prev_statu}, sayac={prev_sayac} | "
                f"in_mufredat={in_mufredat} | "
                f"next: statu={next_statu}, sayac={next_sayac}"
            )

        # ------------------------------------------------------------------
        # 11. DT karar gerekçesi
        # ------------------------------------------------------------------
        dt_reason = _build_dt_reason(
            criteria, topsis_result, in_mufredat,
            next_statu, next_sayac, prev_pool
        )
        result["steps"]["dt_reason"] = dt_reason

        # ------------------------------------------------------------------
        # 12. Karar paketi
        # ------------------------------------------------------------------
        result["decision"] = {
            "score_final":          round(skor_final, 2),
            "in_mufredat_this_year": in_mufredat,
            "is_ground_truth":       is_ground_truth,
            "prev":  prev_pool,
            "next": {"statu": next_statu, "sayac": next_sayac},
            "label": _statu_label(next_statu),
            "sm_note": sm_note,
        }

    result["total_elapsed_ms"] = round((time.perf_counter() - t_total) * 1000, 1)
    return result
