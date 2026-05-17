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

from app.core.config import resolve_sqlite_db_path
from app.services.db import db_session
from app.services.havuz_karar import (
    calculate_next_status,
    STATU_MUFREDATTA,
    STATU_HAVUZDA,
    STATU_DINLENMEDE,
    STATU_IPTAL,
    MAKS_DUSME_SAYACI,
)
from app.services.calculation import (
    KararMotoru,
    get_faculty_year_topsis_results,
    should_drop_course,
    DROP_SCORE_THRESHOLD,
    DROP_AVERAGE_GRADE_THRESHOLD,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
# Kesinlesme puani baraj degeri — calculation.py'deki DROP_SCORE_THRESHOLD ile ayni
SKOR_BARAJ = DROP_SCORE_THRESHOLD
# Ortalama not baraj degeri
ORTALAMA_NOT_BARAJ = DROP_AVERAGE_GRADE_THRESHOLD
# Kural tabanli RF/DT fallback icin basari orani alt siniri
BASARI_BARAJ = 0.40
# Kural tabanli RF/DT fallback icin doluluk orani alt siniri
DOLULUK_BARAJ = 0.30
ML_ADVISORY_NOTE = (
    "ML çıktıları destekleyici/deneysel niteliktedir; nihai karar AHP/TOPSIS + kurallar + state machine tarafından verilir."
)


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


def _not_calculated_step(message: str) -> dict:
    """Algoritma adimi calismadiginda UI'nin gosterebilecegi standart paket."""
    return {
        "status": "not_calculated",
        "message": message,
        "elapsed_ms": 0.0,
    }


def _missing_criteria(reason: str) -> dict:
    """
    Kriter bulunamadiginda analiz akisini kesmemek icin guvenli bos kriter paketi.
    Bu degerler karar uretmek icin kullanilmaz; sadece UI'nin tabloyu doldurmasini saglar.
    """
    return {
        "toplam_ogrenci": 0.0,
        "gecen_ogrenci": 0.0,
        "basari_ortalamasi": 0.0,
        "kontenjan": 0.0,
        "kayitli_ogrenci": 0.0,
        "basari_orani": 0.0,
        "doluluk_orani": 0.0,
        "anket_orani": 0.5,
        "_missing": True,
        "_missing_reason": reason,
    }


# ---------------------------------------------------------------------------
# Veritabanı veri çekiciler
# ---------------------------------------------------------------------------
def _fetch_course_meta(cur: sqlite3.Cursor, course_id: int) -> dict:
    """
    ders tablosundan ders_id, ad, tip, fakulte_id, bolum_id bilgilerini okur.
    """
    # ders tablosunda hangi tip kolonu var?
    cur.execute("PRAGMA table_info(ders)")
    cols = {r[1] for r in cur.fetchall()}
    if "DersTipi" in cols:
        tip_col = "DersTipi"
    elif "tip" in cols:
        tip_col = "tip"
    else:
        tip_col = None

    sel = ["ders_id", "ad"]
    sel.append(f"COALESCE({tip_col}, '') as tip" if tip_col else "'' as tip")
    sel.append("fakulte_id" if "fakulte_id" in cols else "NULL as fakulte_id")
    sel.append("bolum_id" if "bolum_id" in cols else "NULL as bolum_id")
    cur.execute(
        f"SELECT {', '.join(sel)} FROM ders WHERE ders_id = ?",
        (course_id,),
    )
    row = cur.fetchone()
    if not row:
        raise VeriEksikHatasi(f"Ders bulunamadi: ders_id={course_id}")
    return {
        "ders_id": int(row[0]),
        "ad": str(row[1]),
        "tip": str(row[2]),
        "fakulte_id": int(row[3]) if row[3] is not None else None,
        "bolum_id": int(row[4]) if row[4] is not None else None,
    }


def _fetch_criteria(cur: sqlite3.Cursor, course_id: int, year: int) -> dict:
    """
    ders_kriterleri -> performans -> populerlik sırasıyla okur.
    En az basari_orani ve doluluk_orani dolu olmalı; yoksa VeriEksikHatasi.
    """
    # 1. ders_kriterleri (Kriter sayfasından girilmiş)
    anket_kat = 0
    anket_secen = 0
    try:
        cur.execute(
            """SELECT toplam_ogrenci, gecen_ogrenci, basari_ortalamasi,
                      kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen
               FROM ders_kriterleri WHERE ders_id=? AND yil=? LIMIT 1""",
            (course_id, year)
        )
        row_dk = cur.fetchone()
        if row_dk and len(row_dk) >= 7:
            anket_kat = _safe_float(row_dk[5])
            anket_secen = _safe_float(row_dk[6])
    except (sqlite3.OperationalError, TypeError):
        # Eski şemada anket sütunları yoksa kısa sorgu dene
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

    # Anket tercih oranı: dersi seçen / ankete katılan (0-1). Yoksa nötr 0.5
    if anket_kat > 0 and anket_secen >= 0:
        anket_orani = min(1.0, max(0.0, anket_secen / anket_kat))
    else:
        anket_orani = 0.5  # Veri yoksa nötr

    return {
        "toplam_ogrenci":    toplam,
        "gecen_ogrenci":     gecen,
        "basari_ortalamasi": ort_not,
        "kontenjan":         kont,
        "kayitli_ogrenci":   kayitli,
        "basari_orani":      basari,
        "doluluk_orani":     doluluk,
        "anket_orani":       anket_orani,
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


def _fetch_observed_state(cur: sqlite3.Cursor, course_id: int, year: int) -> dict:
    """
    Secili yil icin eldeki gercek durumu okur.
    Havuz kaydi varsa onu, yoksa mufredat uyeligini kullanir.
    """
    try:
        cur.execute(
            """SELECT statu, sayac, skor FROM havuz
               WHERE CAST(ders_id AS INTEGER)=? AND yil=?
               ORDER BY rowid DESC LIMIT 1""",
            (course_id, year),
        )
        row = cur.fetchone()
        if row:
            return {
                "year": year,
                "statu": int(row[0] or 0),
                "sayac": int(row[1] or 0),
                "skor": _safe_float(row[2]) if row[2] is not None else None,
                "source": "havuz",
            }
    except sqlite3.OperationalError:
        try:
            cur.execute(
                """SELECT statu, sayac FROM havuz
                   WHERE CAST(ders_id AS INTEGER)=? AND yil=?
                   ORDER BY rowid DESC LIMIT 1""",
                (course_id, year),
            )
            row = cur.fetchone()
            if row:
                return {
                    "year": year,
                    "statu": int(row[0] or 0),
                    "sayac": int(row[1] or 0),
                    "skor": None,
                    "source": "havuz",
                }
        except Exception:
            pass

    try:
        cur.execute(
            """SELECT 1
               FROM mufredat m
               JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
               WHERE md.ders_id = ? AND m.akademik_yil = ?
               LIMIT 1""",
            (course_id, year),
        )
        if cur.fetchone():
            return {
                "year": year,
                "statu": STATU_MUFREDATTA,
                "sayac": 0,
                "skor": None,
                "source": "mufredat",
            }
    except Exception:
        pass

    return {
        "year": year,
        "statu": STATU_HAVUZDA,
        "sayac": 0,
        "skor": None,
        "source": "default",
    }


def _resolve_course_faculty_id(cur: sqlite3.Cursor, course_meta: dict, course_id: int, year: int) -> Optional[int]:
    """
    Dersin fakulte_id'sini cozumler: ders.fakulte_id > havuz > mufredat sirasiyla bakar.
    """
    meta_fak = course_meta.get("fakulte_id")
    if meta_fak is not None:
        return int(meta_fak)

    cur.execute(
        """
        SELECT fakulte_id
        FROM havuz
        WHERE CAST(ders_id AS INTEGER) = ? AND yil = ?
        LIMIT 1
        """,
        (course_id, year),
    )
    row = cur.fetchone()
    if row and row[0] is not None:
        return int(row[0])

    cur.execute(
        """
        SELECT m.fakulte_id
        FROM mufredat m
        JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
        WHERE md.ders_id = ? AND m.akademik_yil = ?
        LIMIT 1
        """,
        (course_id, year),
    )
    row = cur.fetchone()
    if row and row[0] is not None:
        return int(row[0])

    cur.execute(
        """
        SELECT m.fakulte_id
        FROM mufredat m
        JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
        WHERE md.ders_id = ?
        ORDER BY m.akademik_yil DESC
        LIMIT 1
        """,
        (course_id,),
    )
    row = cur.fetchone()
    if row and row[0] is not None:
        return int(row[0])
    return None


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
        return {"error": str(exc), "weights": {"basari": 0.5859, "trend": 0.2297,
                                                "populerlik": 0.1371, "anket": 0.0473},
                "CR": 0.0, "valid": False}


def _run_topsis_single(
    cur: sqlite3.Cursor,
    course_id: int,
    year: int,
    fakulte_id: Optional[int],
    donem: str = "G",
) -> dict:
    """
    Tek ders puanini, ilgili fakulte+yil evreninde toplu TOPSIS calistirarak
    merkezi kaynaktan alir.
    """
    t0 = time.perf_counter()
    if fakulte_id is None:
        return {
            "status": "not_calculated",
            "score_100": None,
            "raw_score_01": None,
            "message": "Fakulte bilgisi bulunamadigi icin kesinlesme puani henuz hesaplanmadi.",
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }

    try:
        pack = get_faculty_year_topsis_results(
            cur=cur,
            fakulte_id=int(fakulte_id),
            akademik_yil=int(year),
            donem=donem,
            include_course_ids={int(course_id)},
        )
        if not pack.get("ok"):
            return {
                "status": "not_calculated",
                "score_100": None,
                "raw_score_01": None,
                "message": pack.get("error", "TOPSIS sonucu hesaplanamadi."),
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
            }

        scores = pack.get("scores", {})
        if int(course_id) not in scores:
            return {
                "status": "not_calculated",
                "score_100": None,
                "raw_score_01": None,
                "message": "Secilen ders icin kesinlesme puani henuz hesaplanmadi.",
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
            }

        score_100 = _safe_float(scores.get(int(course_id)))
        metric = (pack.get("metric_map") or {}).get(int(course_id), {})
        return {
            "status": "ok",
            "raw_score_01": round(score_100 / 100.0, 6),
            "score_100": round(score_100, 2),
            "inputs": {
                "basari": round(_safe_float(metric.get("basari")), 4),
                "trend": round(_safe_float(metric.get("trend")), 4),
                "doluluk": round(_safe_float(metric.get("populerlik")), 4),
                "anket": round(_safe_float(metric.get("anket"), 0.5), 4),
            },
            "universe_size": len(pack.get("scores", {})),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except Exception as exc:
        logger.warning("TOPSIS hatasi: %s", exc)
        return {
            "status": "not_calculated",
            "error": str(exc),
            "score_100": None,
            "raw_score_01": None,
            "message": "Kesinlesme puani henuz hesaplanmadi.",
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }


def _run_trend_lr(gecmis_list: list) -> dict:
    """
    Trend/LR: yeterli veri varsa sklearn LinearRegression,
    yoksa agirlikli gecmis ortalamaya fallback.
    """
    t0 = time.perf_counter()
    try:
        if not gecmis_list:
            return {"predicted": 0.0, "predicted_100": 0.0,
                    "log": "Gecmis veri yok.", "method": "none", "elapsed_ms": 0}

        # LR tarafinda da eksik yil mantigi agirlikli ortalama ile ayni kalmali.
        # Is kurali geregi null/None/0 degerleri gecerli bir yil sayilmaz.
        valid_gecmis = []
        for item in gecmis_list:
            oran = item.get("oran")
            try:
                oran_val = float(oran)
            except (TypeError, ValueError):
                continue
            if math.isnan(oran_val) or math.isinf(oran_val) or oran_val <= 0.0:
                continue
            valid_gecmis.append({"yil": int(item["yil"]), "oran": min(max(oran_val, 0.0), 1.0)})

        if not valid_gecmis:
            return {"predicted": 0.0, "predicted_100": 0.0,
                    "log": "Gecmis veri yok.", "method": "none", "elapsed_ms": 0}

        motor = KararMotoru()
        trend_wa, log_wa = motor.gecmis_trend_hesapla(gecmis_list)

        if len(valid_gecmis) >= 3:
            try:
                from sklearn.linear_model import LinearRegression
                import numpy as np
                years = np.array([g["yil"] for g in valid_gecmis]).reshape(-1, 1)
                rates = np.array([g["oran"] for g in valid_gecmis])
                lr = LinearRegression()
                lr.fit(years, rates)
                next_year = max(g["yil"] for g in valid_gecmis) + 1
                lr_pred = float(np.clip(lr.predict([[next_year]])[0], 0, 1))
                coef = float(lr.coef_[0])
                trend_dir = "yukselis" if coef > 0.005 else ("dusus" if coef < -0.005 else "stabil")
                return {
                    "predicted": round(lr_pred, 4),
                    "predicted_100": round(lr_pred * 100, 2),
                    "log": f"LR tahmin ({next_year}): %{lr_pred*100:.1f} | Egim: {coef:+.4f} ({trend_dir}) | WA: %{trend_wa*100:.1f}",
                    "method": "sklearn_lr",
                    "coefficient": round(coef, 6),
                    "trend_direction": trend_dir,
                    "wa_fallback": round(trend_wa, 4),
                    "n_years": len(valid_gecmis),
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
                }
            except Exception as exc:
                logger.debug("sklearn LR basarisiz, WA fallback: %s", exc)

        return {
            "predicted": round(trend_wa, 4),
            "predicted_100": round(trend_wa * 100, 2),
            "log": log_wa,
            "method": "weighted_average",
            "n_years": len(valid_gecmis),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except Exception as exc:
        logger.warning("Trend hatasi: %s", exc)
        return {"error": str(exc), "predicted": 0.5, "predicted_100": 50.0,
                "method": "error"}


# Geriye donuk test ve kullanim uyumlulugu.
_run_trend = _run_trend_lr


def _run_rf(criteria: dict, prev_pool: dict, db_path: str = None) -> dict:
    """
    RF tahmini: yeterli havuz verisi varsa sklearn RandomForest,
    yoksa kural tabanli fallback.
    """
    t0 = time.perf_counter()
    try:
        basari = _safe_float(criteria.get("basari_orani"))
        doluluk = _safe_float(criteria.get("doluluk_orani"))
        ortalama_not = _safe_float(criteria.get("basari_ortalamasi"))
        anket = _safe_float(criteria.get("anket_orani", 0.5))
        trend = _safe_float(criteria.get("_trend", basari))
        sayac = int(prev_pool.get("sayac", 0))

        sklearn_used = False
        pred_score = None

        try:
            from app.db.database import SessionLocal
            session = SessionLocal()
            try:
                from app.services.ai_engine import HavuzAIEngine
                engine = HavuzAIEngine(session)
                if engine.train():
                    features = {
                        "basari_orani": basari,
                        "ortalama_not": ortalama_not,
                        "doluluk_orani": doluluk,
                        "anket_orani": anket,
                        "trend": trend,
                        "sayac": sayac,
                    }
                    pred_score = engine.predict_kesinlesme(features)
                    sklearn_used = True
            finally:
                session.close()
        except Exception as exc:
            logger.debug("sklearn RF basarisiz, kural tabanli fallback: %s", exc)

        if sklearn_used and pred_score is not None:
            if pred_score >= SKOR_BARAJ and ortalama_not >= ORTALAMA_NOT_BARAJ:
                pred_statu = STATU_MUFREDATTA
                prob_str = f"RF skoru ({pred_score:.1f}) baraj ({SKOR_BARAJ}) uzerinde"
            elif sayac >= MAKS_DUSME_SAYACI:
                pred_statu = STATU_IPTAL
                prob_str = "Kalici iptal (sayac limiti)"
            else:
                pred_statu = STATU_HAVUZDA
                prob_str = f"RF skoru ({pred_score:.1f}) baraj ({SKOR_BARAJ}) altinda"

            return {
                "predicted_statu": pred_statu,
                "predicted_label": _statu_label(pred_statu),
                "predicted_score": round(pred_score, 2),
                "rule": prob_str,
                "method": "sklearn_rf",
                "note": "sklearn RandomForest ile destekleyici tahmin yapıldı. " + ML_ADVISORY_NOTE,
                "ml_usage_role": "advisory_ml",
                "advisory_only": True,
                "should_influence_decision": False,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
            }

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
            "rule": prob_str,
            "method": "rule_based",
            "note": "Kural tabanlı tahmin (eğitim verisi yetersiz). " + ML_ADVISORY_NOTE,
            "ml_usage_role": "experimental",
            "advisory_only": True,
            "should_influence_decision": False,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except Exception as exc:
        logger.warning("RF hatasi: %s", exc)
        return {"error": str(exc), "predicted_statu": 0, "method": "error"}


def _run_rf_simple(criteria: dict, prev_pool: dict) -> dict:
    """
    Hafif/kural tabanli RF yardimcisi.
    Testler ve hafif cagrilar icin sklearn/AI engine katmanina girmeden
    `_run_rf` fallback mantigini dogrudan uygular.
    """
    basari = _safe_float(criteria.get("basari_orani"))
    doluluk = _safe_float(criteria.get("doluluk_orani"))
    sayac = int(prev_pool.get("sayac", 0))

    if sayac >= MAKS_DUSME_SAYACI:
        pred_statu = STATU_IPTAL
        rule = "Kalici iptal"
    elif basari >= 0.70 and doluluk >= 0.50:
        pred_statu = STATU_MUFREDATTA
        rule = "Yuksek basari + yuksek doluluk"
    elif basari >= BASARI_BARAJ and doluluk >= DOLULUK_BARAJ:
        pred_statu = STATU_MUFREDATTA
        rule = "Yeterli basari + yeterli doluluk"
    elif basari < BASARI_BARAJ:
        pred_statu = STATU_DINLENMEDE
        rule = "Dusuk basari orani"
    else:
        pred_statu = STATU_HAVUZDA
        rule = "Orta duzey performans"

    return {
        "predicted_statu": pred_statu,
        "predicted_label": _statu_label(pred_statu),
        "rule": rule,
        "method": "rule_based_simple",
    }


def _run_dt(criteria: dict, prev_pool: dict) -> dict:
    """
    DT tahmini: yeterli havuz verisi varsa sklearn DecisionTree,
    yoksa kural tabanli fallback.
    """
    t0 = time.perf_counter()
    try:
        basari = _safe_float(criteria.get("basari_orani"))
        doluluk = _safe_float(criteria.get("doluluk_orani"))
        ortalama_not = _safe_float(criteria.get("basari_ortalamasi"))
        anket = _safe_float(criteria.get("anket_orani", 0.5))
        trend = _safe_float(criteria.get("_trend", basari))
        sayac = int(prev_pool.get("sayac", 0))

        try:
            from app.db.database import SessionLocal
            session = SessionLocal()
            try:
                from app.services.ai_engine import HavuzAIEngine
                engine = HavuzAIEngine(session)
                if engine.train():
                    features = {
                        "basari_orani": basari,
                        "ortalama_not": ortalama_not,
                        "doluluk_orani": doluluk,
                        "anket_orani": anket,
                        "trend": trend,
                        "sayac": sayac,
                    }
                    pred_statu = engine.predict_statu(features)
                    return {
                        "predicted_statu": pred_statu,
                        "predicted_label": _statu_label(pred_statu),
                        "method": "sklearn_dt",
                        "note": "sklearn DecisionTree ile destekleyici statü tahmini yapıldı. " + ML_ADVISORY_NOTE,
                        "ml_usage_role": "advisory_ml",
                        "advisory_only": True,
                        "should_influence_decision": False,
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
                    }
            finally:
                session.close()
        except Exception as exc:
            logger.debug("sklearn DT basarisiz, kural tabanli fallback: %s", exc)

        if sayac >= MAKS_DUSME_SAYACI:
            pred_statu = STATU_IPTAL
        elif basari >= BASARI_BARAJ and doluluk >= DOLULUK_BARAJ:
            pred_statu = STATU_MUFREDATTA
        elif basari < BASARI_BARAJ:
            pred_statu = STATU_DINLENMEDE
        else:
            pred_statu = STATU_HAVUZDA

        return {
            "predicted_statu": pred_statu,
            "predicted_label": _statu_label(pred_statu),
            "method": "rule_based",
            "note": "Kural tabanlı tahmin (eğitim verisi yetersiz). " + ML_ADVISORY_NOTE,
            "ml_usage_role": "experimental",
            "advisory_only": True,
            "should_influence_decision": False,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except Exception as exc:
        logger.warning("DT hatasi: %s", exc)
        return {"error": str(exc), "predicted_statu": 0, "method": "error"}


def _build_dt_reason(criteria: dict, topsis: dict, in_mufredat: bool,
                     next_statu: int, next_sayac: int, prev_pool: dict) -> str:
    """Karar aciklamasini insan dilinde uretir."""
    if criteria.get("_missing"):
        reason = criteria.get("_missing_reason") or "Kriter verisi bulunamadi."
        return (
            f"Kriter verisi eksik: {reason} "
            "Bu nedenle RF/DT ve state machine nihai karar simulasyonu calistirilmadi; "
            "ekranda dersin mevcut havuz/mufredat durumu ve hesaplanabilen adimlar gosterildi."
        )

    basari = _safe_float(criteria.get("basari_orani")) * 100
    doluluk = _safe_float(criteria.get("doluluk_orani")) * 100
    ortalama_not = _safe_float(criteria.get("basari_ortalamasi"))
    raw_skor = topsis.get("score_100")
    score_available = raw_skor is not None and not (isinstance(raw_skor, float) and math.isnan(raw_skor))
    skor = _safe_float(raw_skor) if score_available else None
    skor_txt = f"{skor:.1f}" if score_available else "henuz hesaplanmadi"
    prev_statu = prev_pool.get("statu", 0)
    prev_sayac = prev_pool.get("sayac", 0)
    drop_reasons = list(topsis.get("drop_reasons") or [])

    if next_statu == STATU_IPTAL:
        return (
            f"Ders, kumulatif {next_sayac} kez mufredattan dustu ve "
            f"MAKS_DUSME_SAYACI ({MAKS_DUSME_SAYACI}) sinirini asti; "
            "kalici olarak iptal edildi."
        )
    if next_statu == STATU_DINLENMEDE:
        reason = list(drop_reasons)
        if not reason and score_available:
            _, reason = should_drop_course(
                score_100=skor,
                average_grade=ortalama_not,
                score_threshold=SKOR_BARAJ,
                average_grade_threshold=ORTALAMA_NOT_BARAJ,
            )
        if not reason and not score_available:
            reason.append("Kesinlesme puani henuz hesaplanmadi")
        if not reason:
            reason.append("Komisyon karari ile mufredattan cikarildi")
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
        if not score_available:
            return "Kesinlesme puani henuz hesaplanmadigi icin ders havuzda bekletiliyor."
        return (
            f"Ders havuzda bekliyor. Kesinlesme puani: {skor_txt}. "
            "Bu yil mufredata alinmadi."
        )
    if next_statu == STATU_MUFREDATTA:
        if prev_statu == STATU_MUFREDATTA:
            return (
                f"Ders mufredatta kalmaya devam ediyor. "
                f"Ortalama not: {ortalama_not:.1f}, Kesinlesme: {skor_txt}."
            )
        return (
            f"Ders havuzdan mufredata alindi. "
            f"Basari: %{basari:.1f}, Doluluk: %{doluluk:.1f}, Ortalama not: {ortalama_not:.1f}, Kesinlesme: {skor_txt}."
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
        Veritabani dosya yolu. None ise merkezi config/ortam degiskenleri kullanilir.

    Dönüş
    ------
    dict  — Tüm ara çıktıları ve nihai kararı içerir.
    dict with {"error": "..."} — Yalnizca kritik hata durumunda.
    Kriter eksikligi kritik hata degildir; sonuc kismi analiz olarak doner.
    """
    t_total = time.perf_counter()

    path = resolve_sqlite_db_path(db_path)
    if not path.exists():
        return {"error": "Veritabani bulunamadi veya yol gecersiz."}
    path = str(path)

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
        criteria_missing = False
        try:
            criteria = _fetch_criteria(cur, course_id, year)
            result["criteria"] = criteria
            result["criteria_status"] = {
                "ok": True,
                "message": "Kriter verisi bulundu.",
            }
        except VeriEksikHatasi as exc:
            criteria_missing = True
            msg = str(exc)
            criteria = _missing_criteria(msg)
            result["criteria"] = criteria
            result["criteria_status"] = {"ok": False, "message": msg}
            result["errors"].append(msg)
        except Exception as exc:
            criteria_missing = True
            msg = f"Kriter verisi alinamadi: {exc}"
            criteria = _missing_criteria(msg)
            result["criteria"] = criteria
            result["criteria_status"] = {"ok": False, "message": msg}
            result["errors"].append(msg)

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

        observed_state = _fetch_observed_state(cur, course_id, year)

        # ------------------------------------------------------------------
        # 5. AHP
        # ------------------------------------------------------------------
        ahp_result = _run_ahp(criteria)
        if criteria_missing and "error" not in ahp_result:
            ahp_result["note"] = (
                "AHP agirliklari global karar matrisinden gelir; ders kriteri eksik olsa da gosterildi."
            )
        result["steps"]["ahp"] = ahp_result
        if "error" in ahp_result:
            result["errors"].append(f"AHP: {ahp_result['error']}")

        # ------------------------------------------------------------------
        # 6. Trend/LR
        # ------------------------------------------------------------------
        trend_result = _run_trend_lr(gecmis_list)
        result["steps"]["trend"] = trend_result
        if "error" in trend_result:
            result["errors"].append(f"Trend: {trend_result['error']}")

        criteria["_trend"] = trend_result.get("predicted", criteria.get("basari_orani", 0.5))

        # ------------------------------------------------------------------
        # 7. TOPSIS
        # ------------------------------------------------------------------
        fakulte_id = _resolve_course_faculty_id(cur, result["course"], course_id, year)
        result["course"]["fakulte_id"] = fakulte_id
        topsis_result = _run_topsis_single(
            cur=cur,
            course_id=int(course_id),
            year=int(year),
            fakulte_id=fakulte_id,
            donem="G",
        )
        if criteria_missing and "error" not in topsis_result:
            topsis_result["message"] = (
                "Kriter verisi eksik; varsa skor merkezi TOPSIS/havuz fallback "
                "hesabindan gelir ve nihai karar simulasyonu icin kullanilmadi."
            )
        result["steps"]["topsis"] = topsis_result
        if "error" in topsis_result:
            result["errors"].append(f"TOPSIS: {topsis_result['error']}")
        if topsis_result.get("status") == "not_calculated":
            result["errors"].append(topsis_result.get("message", "Kesinlesme puani henuz hesaplanmadi."))

        score_available = topsis_result.get("score_100") is not None
        skor_final = _safe_float(topsis_result.get("score_100")) if score_available else None

        # ------------------------------------------------------------------
        # 8. RF
        # ------------------------------------------------------------------
        if criteria_missing:
            rf_result = _not_calculated_step(
                "Kriter verisi eksik oldugu icin RandomForest tahmini yapilmadi."
            )
        else:
            rf_result = _run_rf(criteria, prev_pool, db_path=path)
        result["steps"]["rf"] = rf_result
        if "error" in rf_result:
            result["errors"].append(f"RF: {rf_result['error']}")

        # ------------------------------------------------------------------
        # 9. in_mufredat karari
        # ------------------------------------------------------------------
        ortalama_not = _safe_float(criteria.get("basari_ortalamasi"))

        if year == 2022:
            cur.execute(
                "SELECT statu FROM havuz WHERE CAST(ders_id AS INTEGER)=? AND yil=2022 LIMIT 1",
                (course_id,)
            )
            row_gt = cur.fetchone()
            in_mufredat = bool((row_gt and int(row_gt[0]) == STATU_MUFREDATTA)
                               or observed_state.get("statu") == STATU_MUFREDATTA)
            is_ground_truth = True
            drop_reasons = []
        elif criteria_missing:
            in_mufredat = observed_state.get("statu") == STATU_MUFREDATTA
            is_ground_truth = False
            drop_reasons = ["Kriter verisi eksik"]
        else:
            if score_available:
                drop_flag, drop_reasons = should_drop_course(
                    score_100=skor_final,
                    average_grade=ortalama_not,
                    score_threshold=SKOR_BARAJ,
                    average_grade_threshold=ORTALAMA_NOT_BARAJ,
                )
                in_mufredat = not drop_flag
            else:
                drop_reasons = ["Kesinlesme puani henuz hesaplanmadi"]
                in_mufredat = False
            is_ground_truth = False
        topsis_result["drop_reasons"] = drop_reasons

        # ------------------------------------------------------------------
        # 10. State machine
        # ------------------------------------------------------------------
        if is_ground_truth:
            next_statu = int(observed_state.get("statu", 0))
            next_sayac = int(observed_state.get("sayac", 0))
            sm_note = "2022 Ground Truth: state machine hesabi yapilmadi."
        elif criteria_missing:
            next_statu = int(observed_state.get("statu", STATU_HAVUZDA))
            next_sayac = int(observed_state.get("sayac", 0))
            src = observed_state.get("source", "mevcut kayit")
            sm_note = (
                "Kriter verisi eksik oldugu icin state machine simulasyonu yapilmadi. "
                f"Mevcut durum kaynagi: {src}."
            )
        elif not score_available:
            next_statu = int(observed_state.get("statu", prev_pool.get("statu", 0)))
            next_sayac = int(observed_state.get("sayac", prev_pool.get("sayac", 0)))
            src = observed_state.get("source", "mevcut kayit")
            sm_note = (
                "Kesinlesme puani henuz hesaplanmadigi icin state machine simulasyonu yapilmadi. "
                f"Mevcut durum kaynagi: {src}."
            )
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
        # 11. DT (Karar Agaci) tahmini + karar gerekcesi
        # ------------------------------------------------------------------
        if criteria_missing:
            dt_result = _not_calculated_step(
                "Kriter verisi eksik oldugu icin DecisionTree tahmini yapilmadi."
            )
        else:
            dt_result = _run_dt(criteria, prev_pool)
        result["steps"]["dt"] = dt_result

        dt_reason = _build_dt_reason(
            criteria, topsis_result, in_mufredat,
            next_statu, next_sayac, prev_pool
        )
        result["steps"]["dt_reason"] = dt_reason

        # ------------------------------------------------------------------
        # 12. Karar paketi
        # ------------------------------------------------------------------
        result["decision"] = {
            "score_final": round(skor_final, 2) if score_available else None,
            "in_mufredat_this_year": in_mufredat,
            "is_ground_truth": is_ground_truth,
            "criteria_missing": criteria_missing,
            "observed_state": observed_state,
            "prev": prev_pool,
            "next": {"statu": next_statu, "sayac": next_sayac},
            "label": _statu_label(next_statu),
            "sm_note": sm_note,
            "drop_reasons": drop_reasons,
            "ml_note": ML_ADVISORY_NOTE,
            "ml_should_influence_decision": False,
        }

    result["total_elapsed_ms"] = round((time.perf_counter() - t_total) * 1000, 1)
    return result
