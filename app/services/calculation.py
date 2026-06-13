# -*- coding: utf-8 -*-
# =============================================================================
# app/services/calculation.py â€” Karar Motoru (AHP, TOPSIS) ve Otomatik Puanlama
# =============================================================================
# Bu modÃ¼l: performans + populerlik tablolarÄ±ndan veri okuyarak AHP aÄŸÄ±rlÄ±klarÄ±
# ve TOPSIS sÄ±ralamasÄ± hesaplar. run_automatic_scoring ile otomatik skor atama yapar.
# Ä°lgili: criteria_page (kriter giriÅŸi), havuz_karar (statÃ¼ gÃ¼ncelleme)
# =============================================================================

import logging
import math
import os
import random
import sqlite3
import traceback
from typing import Any

import numpy as np
import pandas as pd

from app.core.config import resolve_sqlite_db_path
from app.db.schema_compat import ensure_pool_state_governance_schema
from app.services.course_type import (
    build_elective_predicate,
    filter_elective_course_ids,
    get_existing_type_columns,
)
from app.services.data_confidence_service import calculate_course_data_confidence
from app.services.db import get_raw_connection
from app.services.havuz_karar import calculate_next_status
from app.services.pool_state_machine_service import (
    evaluate_course_state_transition,
    get_governance_flags,
    save_state_transition,
)
from app.services.pool_state_policy_service import (
    resolve_policy as resolve_pool_state_policy,
)
from app.services.trend_analysis_service import analyze_course_trend
from app.services.yearly_workflow import (
    ensure_yearly_workflow_schema,
    get_faculty_year_status,
    get_missing_criteria,
    is_faculty_criteria_complete,
    mark_algorithm_run,
    record_cross_department_usage,
)

logger = logging.getLogger(__name__)

# ---------- BÃ–LÃœM 1: Karar Motoru (AHP + TOPSIS) ----------
# AHP Random Index degeri, 4 kriter icin sabit tablo degeri
RI_4 = 0.90
# Saaty ikili karsilastirma matrisi:
# - Basari / Trend = 3
# - Basari / Populerlik = 5
# - Basari / Anket = 9
# - Trend / Populerlik = 2
# - Trend / Anket = 5
# - Populerlik / Anket = 4
AHP_PAIRWISE_MATRIX = np.array(
    [
        [1.0, 3.0, 5.0, 9.0],
        [1.0 / 3.0, 1.0, 2.0, 5.0],
        [1.0 / 5.0, 1.0 / 2.0, 1.0, 4.0],
        [1.0 / 9.0, 1.0 / 5.0, 1.0 / 4.0, 1.0],
    ],
    dtype=float,
)
# Kesinlesme puani baraj degeri â€” bu skorun altinda kalan dersler mufredattan duser
DROP_SCORE_THRESHOLD = 40.0
# Ortalama not baraj degeri â€” bu notun altindaki dersler mufredattan duser
DROP_AVERAGE_GRADE_THRESHOLD = 45.0

# Mufredat disi (havuz) dersler icin varsayilan kesinlesme puani merkezi
POOL_DEFAULT_SCORE = 50.0
# Havuz derslerinin anket bazli puan yayilim araligi (50 Â± bu deger)
POOL_ANKET_SCORE_SPREAD = 10.0
# Trend hesabi icin varsayilan 3 yillik agirlik seti.
TREND_DEFAULT_WEIGHTS = (0.50, 0.30, 0.20)
# Ayni bolum mufredatina fakulte ortak havuzundan en fazla bu kadar dis bolum dersi girebilir.
MAX_CROSS_DEPARTMENT_COURSES = 1

class KararMotoru:
    def __init__(self, db=None):
        self.db = db

    def ahp_matrisi(self):
        """Saaty kurallarina gore kurulan 4x4 ikili karsilastirma matrisini doner."""
        return np.array(AHP_PAIRWISE_MATRIX, copy=True)

    def ahp_calistir(self, profile=None):
        """
        AHP agirliklarini ozvektor yontemi ile hesaplar.

        Adimlar:
        1. Ikili karsilastirma matrisinin ozdeger/ozvektorlerini bul
        2. En buyuk ozdegere karsilik gelen ana ozvektoru sec
        3. Ozvektoru 1.0 toplamina normalize et
        """
        if profile and isinstance(profile, dict) and profile.get("weights"):
            weights = profile.get("weights") or {}
            keys = ["basari", "trend", "populerlik", "anket"]
            values = [float(weights.get(key, 0.0)) for key in keys]
            total = sum(values) or 1.0
            return [value / total for value in values]
        matris = self.ahp_matrisi()
        eigenvalues, eigenvectors = np.linalg.eig(matris)

        # Perron-Frobenius teoremi geregi pozitif reciproqual AHP matrisinde
        # en buyuk ozdegere karsilik gelen ozvektor asil agirlik vektorudur.
        principal_index = int(np.argmax(np.real(eigenvalues)))
        principal_vector = np.real_if_close(eigenvectors[:, principal_index]).astype(float)
        principal_vector = np.abs(principal_vector)

        total = float(principal_vector.sum()) or 1.0
        agirliklar = principal_vector / total
        return agirliklar.tolist()

    def ahp_tutarlilik_kontrolu(self, matris=None, agirliklar=None):
        """
        TutarlÄ±lÄ±k OranÄ± (CR) hesaplar. CR < 0.10 kabul edilebilir.
        DÃ¶ner: (cr: float, gecerli: bool, lambda_max: float)
        """
        if matris is None:
            matris = self.ahp_matrisi()
        else:
            matris = np.array(matris, dtype=float)
        if agirliklar is None:
            agirliklar = self.ahp_calistir()
        agirliklar = np.array(agirliklar, dtype=float)

        # lambda_max, A*w vektorunun w ile eleman bazli bolumunun ortalamasidir.
        weighted_sum = matris.dot(agirliklar)
        lambda_vals = weighted_sum / np.where(np.abs(agirliklar) > 1e-10, agirliklar, 1e-10)
        n = len(agirliklar)
        lambda_max = float(np.mean(lambda_vals))
        ci = (lambda_max - n) / (n - 1) if n > 1 else 0
        cr = ci / RI_4 if RI_4 else 0
        return cr, cr < 0.10, lambda_max

    def gecmis_trend_hesapla(self, gecmis_list):
        """
        Gecmis yillarin agirlikli ortalamasini hesaplar.
        gecmis_list: [{"yil": 2024, "oran": 0.85}, {"yil": 2023, "oran": 0.70}, ...]
        En yeni yil en yuksek varsayilan agirligi alir.

        Re-scaling kurali:
        - Null/None/0/gecersiz oranlar "eksik veri" kabul edilir.
        - Sadece gecerli yillarin varsayilan agirliklari toplanir.
        - Her gecerli yilin agirligi bu toplama bolunerek normalize edilir.
        - Boylece eksik yil varsa kalan agirliklar dinamik olarak yeniden dagitilir.
        """
        if not gecmis_list:
            return 0.0, "Gecmis veri yok."

        def _coerce_ratio(raw_value):
            """
            Is kurali geregi 0 da eksik veri sayilir; yalnizca pozitif ve sonlu
            oranlar hesaplamaya katilir.
            """
            if raw_value is None:
                return None
            try:
                ratio = float(raw_value)
            except (TypeError, ValueError):
                return None
            if math.isnan(ratio) or math.isinf(ratio) or ratio <= 0.0:
                return None
            return max(0.0, min(1.0, ratio))

        slots = []
        for idx, item in enumerate(list(gecmis_list)[: len(TREND_DEFAULT_WEIGHTS)]):
            varsayilan_agirlik = TREND_DEFAULT_WEIGHTS[idx]
            yil = item.get("yil", f"Yil {idx + 1}")
            oran = _coerce_ratio(item.get("oran"))
            slots.append(
                {
                    "yil": yil,
                    "oran": oran,
                    "varsayilan_agirlik": varsayilan_agirlik,
                }
            )

        gecerli_yillar = [slot for slot in slots if slot["oran"] is not None]
        if not gecerli_yillar:
            return 0.0, "Gecmis veri yok."

        toplam_varsayilan_agirlik = sum(slot["varsayilan_agirlik"] for slot in gecerli_yillar)
        if toplam_varsayilan_agirlik <= 0:
            return 0.0, "Gecmis veri yok."

        yeniden_olceklendi = not math.isclose(toplam_varsayilan_agirlik, 1.0, rel_tol=1e-9, abs_tol=1e-9)
        toplam_puan = 0.0
        log_parcalari = []

        for slot in slots:
            oran = slot["oran"]
            if oran is None:
                log_parcalari.append(f"{slot['yil']}: veri yok")
                continue

            yeni_agirlik = slot["varsayilan_agirlik"] / toplam_varsayilan_agirlik
            toplam_puan += oran * yeni_agirlik

            if yeniden_olceklendi:
                log_parcalari.append(
                    f"{slot['yil']}: %{oran*100:.1f} x {yeni_agirlik:.1%} "
                    f"(re-scaled, varsayilan {slot['varsayilan_agirlik']:.0%})"
                )
            else:
                log_parcalari.append(f"{slot['yil']}: %{oran*100:.1f} x {yeni_agirlik:.0%}")

        trend = toplam_puan
        log = " | ".join(log_parcalari) + f"  -> Trend: {trend:.4f}"
        return trend, log

    def topsis_calistir(self, df, agirliklar, criteria_keys=None, benefit_map=None):
        """
        TOPSIS: Veri akÄ±ÅŸÄ± AHP'den gelen aÄŸÄ±rlÄ±klarla.
        1) KarekÃ¶k toplamlarÄ± ile normalize
        2) AÄŸÄ±rlÄ±klÄ± normalize matris
        3) Pozitif/Negatif ideal Ã§Ã¶zÃ¼mler
        4) Ã–klid uzaklÄ±klarÄ±
        5) YakÄ±nlÄ±k KatsayÄ±sÄ± (0-1)
        """
        if df.empty:
            return pd.DataFrame(), {}

        def _safe_div(a, b, default=0.0):
            return a / b if b and abs(b) > 1e-10 else default

        sutunlar = [c for c in list(criteria_keys or ["basari", "trend", "populerlik", "anket"]) if c in df.columns]
        if not sutunlar:
            return pd.DataFrame(), {}
        raw_weights = list(agirliklar or [])
        if len(raw_weights) != len(sutunlar):
            raw_weights = raw_weights[: len(sutunlar)] + [1.0] * max(0, len(sutunlar) - len(raw_weights))
        w_sum = sum(raw_weights) or 1.0
        w = [float(a) / w_sum for a in raw_weights]
        benefit_map = dict(benefit_map or {})

        # 1. Vector normalization: r_ij = x_ij / sqrt(sum(x_ij^2))
        sqrt_sums = {}
        for c in sutunlar:
            sq = sum((float(x) ** 2) for x in df[c].fillna(0))
            sqrt_sums[c] = math.sqrt(sq) if sq > 1e-10 else 1.0

        R = df.copy()
        for c in sutunlar:
            R[c] = df[c].fillna(0).apply(lambda x: _safe_div(float(x), sqrt_sums[c], 0.0))

        # 2. AÄŸÄ±rlÄ±klÄ± matris: V_ij = w_j * r_ij
        V = pd.DataFrame()
        for i, c in enumerate(sutunlar):
            V[c] = R[c] * w[i]

        # 3. Ideal çözümler. Benefit kriterlerde yüksek, cost kriterlerde düşük değer iyidir.
        A_plus = {
            c: V[c].max() if bool(benefit_map.get(c, True)) else V[c].min()
            for c in sutunlar
        }
        A_minus = {
            c: V[c].min() if bool(benefit_map.get(c, True)) else V[c].max()
            for c in sutunlar
        }

        sonuclar = []
        for i, (idx, row) in enumerate(df.iterrows()):
            v_row = V.iloc[i]
            s_plus = math.sqrt(sum((v_row[c] - A_plus[c]) ** 2 for c in sutunlar))
            s_minus = math.sqrt(sum((v_row[c] - A_minus[c]) ** 2 for c in sutunlar))
            denom = s_plus + s_minus
            ci = _safe_div(s_minus, denom, 0.0)
            skor_100 = ci * 100
            sonuclar.append({
                "ders_id": int(row["ders_id"]) if "ders_id" in row else 0,
                "Ders": row.get("ders", ""),
                "AHP_TOPSIS_Skor": round(ci, 6),
                "Kesinlesme_Puani": round(skor_100, 2),
                "S+": round(s_plus, 6),
                "S-": round(s_minus, 6),
            })

        df_sonuc = pd.DataFrame(sonuclar).sort_values(by="AHP_TOPSIS_Skor", ascending=False)
        meta = {
            "agirliklar": w,
            "sutunlar": sutunlar,
            "A_plus": A_plus,
            "A_minus": A_minus,
            "benefit_map": {c: bool(benefit_map.get(c, True)) for c in sutunlar},
        }
        return df_sonuc, meta


def ders_cakisma_kontrolu(ders_listesi, conn=None):
    """
    AynÄ± gÃ¼n ve saatte Ã§akÄ±ÅŸan dersleri tespit eder.
    ders_listesi: [(ders_id, gun, baslangic_saati, bitis_saati), ...]
    DÃ¶ner: [(ders_id_a, ders_id_b), ...] Ã§akÄ±ÅŸan Ã§iftler
    """
    if not ders_listesi or len(ders_listesi) < 2:
        return []

    def _saat_dakika(s):
        if not s:
            return 0, 0
        s = str(s).strip()
        if ":" in s:
            p = s.split(":")
            return int(p[0] or 0), int(p[1] or 0)
        try:
            return int(float(s)), 0
        except (ValueError, TypeError):
            return 0, 0

    def _cakisma(gun1, b1, e1, gun2, b2, e2):
        if (gun1 or "").strip() != (gun2 or "").strip():
            return False
        sb1, sm1 = _saat_dakika(b1)
        se1, em1 = _saat_dakika(e1)
        sb2, sm2 = _saat_dakika(b2)
        se2, em2 = _saat_dakika(e2)
        dk1_bas = sb1 * 60 + sm1
        dk1_bit = se1 * 60 + em1
        dk2_bas = sb2 * 60 + sm2
        dk2_bit = se2 * 60 + em2
        return not (dk1_bit <= dk2_bas or dk2_bit <= dk1_bas)

    cakisanlar = []
    for i in range(len(ders_listesi)):
        for j in range(i + 1, len(ders_listesi)):
            d1, d2 = ders_listesi[i], ders_listesi[j]
            if len(d1) >= 4 and len(d2) >= 4:
                if _cakisma(d1[1], d1[2], d1[3], d2[1], d2[2], d2[3]):
                    cakisanlar.append((d1[0], d2[0]))
    return cakisanlar


# =========================================================
# 2. VERÄ° YÃœKLEYÄ°CÄ° (HAVUZ EKLEME/SÄ°LME YAPMAZ)
# =========================================================
def yukle_gercek_2022_mufredati(conn, excel_path):
    if not os.path.exists(excel_path):
        print(f"[WARN] Dosya yok: {excel_path}")
        return False

    print("[INFO] Excel okunuyor...")
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"[ERROR] Excel hatasi: {e}")
        return False

    df.columns = [str(c).lower().strip() for c in df.columns]
    cursor = conn.cursor()

    print("[INFO] 2022 mufredat temizligi (havuz korunuyor)...")
    # Sadece mÃ¼fredat tablolarÄ±nÄ± temizliyoruz, havuza dokunmuyoruz.
    cursor.execute("""
        DELETE FROM mufredat_ders
        WHERE mufredat_id IN (SELECT mufredat_id FROM mufredat WHERE akademik_yil = 2022)
    """)
    cursor.execute("DELETE FROM mufredat WHERE akademik_yil = 2022")
    conn.commit()

    cursor.execute("SELECT bolum_id, ad, fakulte_id FROM bolum")
    db_bolumler = {
        str(r[1]).lower().strip(): {"bolum_id": int(r[0]), "fakulte_id": int(r[2])}
        for r in cursor.fetchall()
    }

    cursor.execute("SELECT ders_id, ad FROM ders")
    db_dersler = {str(r[1]).lower().strip(): int(r[0]) for r in cursor.fetchall()}

    col_bolum = next((c for c in ("bolum", "bölüm") if c in df.columns), "bolum")
    ders_cols = []
    for i in range(1, 6):
        ders_cols.append(
            next(
                (c for c in (f"secmeli ders {i}", f"seçmeli ders {i}") if c in df.columns),
                f"secmeli ders {i}",
            )
        )
    count_ders = 0

    for _, row in df.iterrows():
        bolum_adi = str(row.get(col_bolum, "") or "").strip()
        if not bolum_adi:
            continue

        bolum_id = None
        bolum_fakulte_id = None
        bolum_adi_low = bolum_adi.lower()
        for k, info in db_bolumler.items():
            if k in bolum_adi_low or bolum_adi_low in k:
                bolum_id = int(info["bolum_id"])
                bolum_fakulte_id = int(info["fakulte_id"])
                break
        if not bolum_id or bolum_fakulte_id is None:
            continue

        cursor.execute(
            "INSERT INTO mufredat (fakulte_id, bolum_id, akademik_yil, donem, durum) VALUES (?, ?, 2022, 'Guz', 'Resmi')",
            (bolum_fakulte_id, bolum_id)
        )
        muf_id = cursor.lastrowid

        for col in ders_cols:
            if col not in df.columns:
                continue
            raw = row.get(col)
            if pd.isna(raw) or str(raw).strip() == "":
                continue

            d_key = str(raw).strip().lower()
            d_id = db_dersler.get(d_key)

            if not d_id:
                # yakÄ±n eÅŸleÅŸme dene
                for k, v in db_dersler.items():
                    if d_key == k:
                        d_id = v
                        break

            if d_id:
                # MÃ¼fredata ekle (BurasÄ± serbest)
                cursor.execute(
                    "INSERT INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?) ON CONFLICT DO NOTHING",
                    (muf_id, d_id)
                )

                # --- GÃœVENLÄ° MOD: SADECE UPDATE ---
                # Havuza yeni satÄ±r eklemiyoruz. Sadece varsa gÃ¼ncelliyoruz.
                cursor.execute(
                    "UPDATE havuz SET statu = 1, sayac = 0 WHERE ders_id = ? AND fakulte_id = ? AND yil = 2022",
                    (d_id, bolum_fakulte_id)
                )

                # Ä°pucu: EÄŸer havuzda bu ders yoksa, yukarÄ±daki komut hiÃ§bir ÅŸey yapmaz (hata vermez).
                # Bu tam olarak istediÄŸimiz ÅŸey.

                # 2022 performans verilerini oluÅŸtur (Performans tablosu havuza dahil deÄŸil, o yÃ¼zden burasÄ± kalabilir)
                cursor.execute(
                    "SELECT count(*) FROM performans WHERE ders_id=? AND akademik_yil=2022",
                    (d_id,)
                )
                if cursor.fetchone()[0] == 0:
                    ort = random.uniform(50, 95)
                    talep = int(50 * random.uniform(0.5, 1.5))
                    cursor.execute(
                        "INSERT INTO performans (ders_id, akademik_yil, ortalama_not, basari_orani) VALUES (?, 2022, ?, ?)",
                        (d_id, ort, ort / 100)
                    )
                    kontenjan = 50
                    doluluk = min(talep / (kontenjan or 1), 1.0)
                    cursor.execute(
                        "INSERT INTO populerlik (ders_id, akademik_yil, talep_sayisi, kontenjan, doluluk_orani) VALUES (?, 2022, ?, ?, ?)",
                        (d_id, talep, kontenjan, doluluk)
                    )
                    cursor.execute(
                        "INSERT INTO skor (ders_id, akademik_yil, skor_top) VALUES (?, 2022, 0)",
                        (d_id,)
                    )

                count_ders += 1

    conn.commit()
    print(f"[OK] 2022 hazir: {count_ders} ders islendi (havuz yapisi bozulmadan guncellendi).")
    return True


# =========================================================
# 3. ANA OTOMASYON (GÃœVENLÄ° MOD)
# =========================================================
def run_automatic_scoring(db_path=None):
    """
    Acilis veya manuel tetikleme: base_year sonrasi mufredati sifirlar,
    kriterleri hazir fakulte/yillar icin zincirleme sonraki yil uretir,
    sonucu curriculum_generation_log tablosuna yazar.
    """
    return rebuild_school_curricula(
        db_path=db_path,
        base_year=2022,
        donem="G",
        max_rounds=8,
    )



def _normalize_mufredat_faculty_ids(cur):
    """
    Legacy veri setlerinde mufredat.fakulte_id yanlis yazilmis olabiliyor.
    bolum tablosunu kaynak kabul ederek bu alanÄ± normalize eder.
    """
    try:
        cur.execute(
            """
            UPDATE mufredat
            SET fakulte_id = (
                SELECT b.fakulte_id
                FROM bolum b
                WHERE b.bolum_id = mufredat.bolum_id
                LIMIT 1
            )
            WHERE EXISTS (
                SELECT 1
                FROM bolum b2
                WHERE b2.bolum_id = mufredat.bolum_id
            )
              AND COALESCE(fakulte_id, -1) <> COALESCE((
                SELECT b3.fakulte_id
                FROM bolum b3
                WHERE b3.bolum_id = mufredat.bolum_id
                LIMIT 1
              ), -1)
            """
        )
        return int(cur.rowcount or 0)
    except Exception:
        return 0


def _safe_float2(value, default=0.0):
    """
    None, NaN, Inf ve string degerleri guvenli float'a cevirir. Gecersiz degerlerde default doner.
    """
    try:
        if value is None:
            return float(default)
        val = float(value)
        if math.isnan(val) or math.isinf(val):
            return float(default)
        return val
    except (TypeError, ValueError):
        return float(default)


def _resolve_elective_col(cur):
    """
    Legacy helper: ders tablosunda secmeli/zorunlu tip sutununun ilk bulunan adini dondurur.
    """
    cols = get_existing_type_columns(cur)
    return cols[0] if cols else None


def _normalize_term_key(value):
    return "b" if str(value or "").strip().lower().startswith("b") else "g"


def _table_has_column(cur, table_name, column_name):
    cur.execute(f"PRAGMA table_info({table_name})")
    return column_name in {str(row[1]) for row in cur.fetchall()}


def _table_exists(cur, table_name):
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (str(table_name),),
    )
    return cur.fetchone() is not None


def _havuz_has_donem_col(cur):
    return _table_has_column(cur, "havuz", "donem")


def _havuz_unique_includes_donem(cur):
    """Return True only when havuz uniqueness is term-scoped.

    Some legacy DBs have a ``donem`` column but still enforce uniqueness on
    (ders_id, fakulte_id, yil). In that shape, WHERE clauses scoped by donem can
    miss the existing row and the following INSERT fails.
    """
    try:
        indexes = cur.execute("PRAGMA index_list(havuz)").fetchall()
        has_term_scoped_unique = False
        for idx in indexes:
            if not idx or not int(idx[2] or 0):
                continue
            columns = {str(row[2]) for row in cur.execute(f"PRAGMA index_info({idx[1]})").fetchall()}
            if {"ders_id", "fakulte_id", "yil"}.issubset(columns) and "donem" not in columns:
                return False
            if {"ders_id", "fakulte_id", "yil", "donem"}.issubset(columns):
                has_term_scoped_unique = True
        return has_term_scoped_unique
    except Exception:
        return False


def _drop_legacy_havuz_term_agnostic_unique(cur):
    """havuz tablosundaki donem ICERMEYEN UNIQUE index'leri dusurur.

    (ders_id, fakulte_id, yil) uzerinde donemsiz bir UNIQUE index, bir dersin ayni
    yil icinde hem Guz hem Bahar satirina sahip olmasini engeller ve uretim hattindaki
    term-scoping mantigini devre disi birakir. Donem-scoped unique index kanonik
    kabul edilir. Idempotent.
    """
    for idx in cur.execute("PRAGMA index_list(havuz)").fetchall():
        if not idx or not int(idx[2] or 0):  # idx[2] = unique bayragi
            continue
        idx_name = str(idx[1])
        idx_cols = {str(r[2]) for r in cur.execute(f"PRAGMA index_info({idx_name})").fetchall()}
        if {"ders_id", "fakulte_id", "yil"}.issubset(idx_cols) and "donem" not in idx_cols:
            cur.execute(f'DROP INDEX IF EXISTS "{idx_name}"')


def _fetch_other_term_curriculum_map(cur, fakulte_id, akademik_yil, current_term):
    """
    Next-year generation sirasinda, diger donemde zaten secili dersleri bolum bazli getirir.
    """
    current_key = _normalize_term_key(current_term)
    other_key = "b" if current_key == "g" else "g"
    cur.execute(
        """
        SELECT m.bolum_id, md.ders_id
        FROM mufredat m
        JOIN bolum b ON b.bolum_id = m.bolum_id
        JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
        WHERE b.fakulte_id = ?
          AND m.akademik_yil = ?
          AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = ?
        """,
        (int(fakulte_id), int(akademik_yil), other_key),
    )
    out = {}
    for row in cur.fetchall():
        if row[0] is None or row[1] is None:
            continue
        out.setdefault(int(row[0]), set()).add(int(row[1]))
    return out


def _has_generation_criteria(cur, ders_id, yil, donem):
    """
    Yeni yil mufredat uretimi icin zorunlu kriter kontrolu.
    Sadece ders_kriterleri kaydini kabul eder; performans/pop fallback'i kullanmaz.
    """
    try:
        cur.execute(
            """
            SELECT toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, kontenjan, kayitli_ogrenci
            FROM ders_kriterleri
            WHERE ders_id = ? AND yil = ?
              AND (COALESCE(TRIM(donem), '') = '' OR LOWER(SUBSTR(TRIM(donem), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)))
            ORDER BY CASE
                WHEN LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)) THEN 0
                ELSE 1
            END, id DESC
            LIMIT 1
            """,
            (int(ders_id), int(yil), str(donem), str(donem)),
        )
        row = cur.fetchone()
        if not row:
            return False

        toplam = _safe_float2(row[0], 0.0)
        gecen = _safe_float2(row[1], 0.0)
        ortalama_not = _safe_float2(row[2], 0.0)
        kontenjan = _safe_float2(row[3], 0.0)
        kayitli = _safe_float2(row[4], 0.0)

        return toplam > 0 and kontenjan > 0 and gecen >= 0 and kayitli >= 0 and ortalama_not > 0
    except Exception:
        return False


def _has_full_criteria(cur, ders_id, yil, donem):
    try:
        ders_id = int(ders_id)
        yil = int(yil)
        cur.execute(
            """
            SELECT toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, kontenjan, kayitli_ogrenci
            FROM ders_kriterleri
            WHERE ders_id = ? AND yil = ?
              AND (COALESCE(TRIM(donem), '') = '' OR LOWER(SUBSTR(TRIM(donem), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)))
            ORDER BY CASE WHEN LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)) THEN 0 ELSE 1 END, id DESC
            LIMIT 1
            """,
            (ders_id, yil, str(donem), str(donem)),
        )
        row = cur.fetchone()

        if row:
            toplam = _safe_float2(row[0], 0.0)
            gecen = _safe_float2(row[1], 0.0)
            ortalama_not = _safe_float2(row[2], 0.0)
            kontenjan = _safe_float2(row[3], 0.0)
            kayitli = _safe_float2(row[4], 0.0)
            if ortalama_not <= 0:
                cur.execute(
                    """
                    SELECT ortalama_not
                    FROM performans
                    WHERE ders_id = ? AND akademik_yil = ?
                    ORDER BY pfrs_id DESC
                    LIMIT 1
                    """,
                    (ders_id, yil),
                )
                pf = cur.fetchone()
                ortalama_not = _safe_float2(pf[0] if pf else None, 0.0)

            if toplam > 0 and kontenjan > 0 and gecen >= 0 and kayitli >= 0 and ortalama_not > 0:
                return True

        # Fallback: kriter satiri eksik/parsiyel olsa bile performans + populerlik
        # verisi varsa dersi "hesaplanabilir" kabul et.
        cur.execute(
            """
            SELECT ortalama_not, basari_orani
            FROM performans
            WHERE ders_id = ? AND akademik_yil = ?
            ORDER BY pfrs_id DESC
            LIMIT 1
            """,
            (ders_id, yil),
        )
        pf = cur.fetchone()

        try:
            cur.execute(
                """
                SELECT kontenjan, doluluk_orani
                FROM populerlik
                WHERE ders_id = ? AND akademik_yil = ?
                ORDER BY pop_id DESC
                LIMIT 1
                """,
                (ders_id, yil),
            )
        except Exception:
            cur.execute(
                """
                SELECT NULL as kontenjan, doluluk_orani
                FROM populerlik
                WHERE ders_id = ? AND akademik_yil = ?
                ORDER BY rowid DESC
                LIMIT 1
                """,
                (ders_id, yil),
            )
        pop = cur.fetchone()

        ortalama_not = _safe_float2(pf[0] if pf else None, 0.0)
        basari_orani = _safe_float2(pf[1] if pf else None, -1.0)
        kontenjan = _safe_float2(pop[0] if pop else None, 0.0)
        doluluk = _safe_float2(pop[1] if pop else None, -1.0)

        perf_ok = ortalama_not > 0 and basari_orani >= 0
        pop_ok = kontenjan > 0 or doluluk >= 0
        if perf_ok and pop_ok:
            return True

        cur.execute(
            """SELECT basari_orani FROM performans
               WHERE ders_id = ? AND akademik_yil < ? AND basari_orani IS NOT NULL
               ORDER BY akademik_yil DESC LIMIT 1""",
            (ders_id, yil),
        )
        prev_pf = cur.fetchone()
        if prev_pf and _safe_float2(prev_pf[0], -1) >= 0:
            return True

        return False
    except Exception:
        return False


def _read_course_metrics(cur, ders_id, yil, donem, motor):
    """
    Tek ders icin AHP/TOPSIS girdilerini derler: basari, trend, populerlik, anket, ortalama_not.
    Oncelik sirasi: ders_kriterleri > performans > populerlik. Mevcut yil verisi yoksa onceki yildan propagasyon yapar.
    """
    dk = None
    try:
        cur.execute(
            """
            SELECT toplam_ogrenci, gecen_ogrenci, basari_ortalamasi,
                   kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen
            FROM ders_kriterleri
            WHERE ders_id = ? AND yil = ?
              AND (COALESCE(TRIM(donem), '') = '' OR LOWER(SUBSTR(TRIM(donem), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)))
            ORDER BY CASE WHEN LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)) THEN 0 ELSE 1 END, id DESC
            LIMIT 1
            """,
            (int(ders_id), int(yil), str(donem), str(donem)),
        )
        dk = cur.fetchone()
    except Exception:
        try:
            cur.execute(
                """
                SELECT toplam_ogrenci, gecen_ogrenci, basari_ortalamasi,
                       kontenjan, kayitli_ogrenci
                FROM ders_kriterleri
                WHERE ders_id = ? AND yil = ?
                  AND (COALESCE(TRIM(donem), '') = '' OR LOWER(SUBSTR(TRIM(donem), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1)))
                ORDER BY id DESC
                LIMIT 1
                """,
                (int(ders_id), int(yil), str(donem)),
            )
            row = cur.fetchone()
            dk = (row[0], row[1], row[2], row[3], row[4], 0, 0) if row else None
        except Exception:
            pass

    if dk is None:
        try:
            cur.execute(
                """
                SELECT toplam_ogrenci, gecen_ogrenci, basari_ortalamasi,
                       kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen
                FROM ders_kriterleri
                WHERE ders_id = ? AND yil < ?
                ORDER BY yil DESC, id DESC
                LIMIT 1
                """,
                (int(ders_id), int(yil)),
            )
            dk = cur.fetchone()
        except Exception:
            pass

    try:
        cur.execute(
            """
            SELECT ortalama_not, basari_orani
            FROM performans
            WHERE ders_id = ? AND akademik_yil = ?
            ORDER BY pfrs_id DESC
            LIMIT 1
            """,
            (int(ders_id), int(yil)),
        )
    except Exception:
        cur.execute(
            """
            SELECT ortalama_not, basari_orani
            FROM performans
            WHERE ders_id = ? AND akademik_yil = ?
            ORDER BY rowid DESC
            LIMIT 1
            """,
            (int(ders_id), int(yil)),
        )
    pf = cur.fetchone()

    try:
        cur.execute(
            """
            SELECT doluluk_orani
            FROM populerlik
            WHERE ders_id = ? AND akademik_yil = ?
            ORDER BY pop_id DESC
            LIMIT 1
            """,
            (int(ders_id), int(yil)),
        )
    except Exception:
        cur.execute(
            """
            SELECT doluluk_orani
            FROM populerlik
            WHERE ders_id = ? AND akademik_yil = ?
            ORDER BY rowid DESC
            LIMIT 1
            """,
            (int(ders_id), int(yil)),
        )
    pop = cur.fetchone()

    ortalama_not = _safe_float2(pf[0] if pf else None, 0.0)
    basari = _safe_float2(pf[1] if pf else None, 0.0)
    doluluk = _safe_float2(pop[0] if pop else None, 0.0)
    anket = 0.5

    if dk:
        toplam = _safe_float2(dk[0], 0.0)
        gecen = _safe_float2(dk[1], 0.0)
        ortalama_not = _safe_float2(dk[2], ortalama_not)
        kontenjan = _safe_float2(dk[3], 0.0)
        kayitli = _safe_float2(dk[4], 0.0)
        if toplam > 0:
            basari = gecen / toplam
        if kontenjan > 0:
            doluluk = kayitli / kontenjan

        anket_kat = _safe_float2(dk[5], 0.0)
        anket_secen = _safe_float2(dk[6], 0.0)
        if anket_kat > 0:
            anket = max(0.0, min(1.0, anket_secen / anket_kat))

    basari = max(0.0, min(1.0, basari))
    doluluk = max(0.0, min(1.0, doluluk))

    cur.execute(
        """
        SELECT akademik_yil, basari_orani
        FROM performans
        WHERE ders_id = ? AND akademik_yil <= ? AND basari_orani IS NOT NULL
        ORDER BY akademik_yil DESC
        LIMIT 3
        """,
        (int(ders_id), int(yil)),
    )
    gecmis = [{"yil": int(r[0]), "oran": _safe_float2(r[1], basari)} for r in cur.fetchall()]
    trend, _ = motor.gecmis_trend_hesapla(gecmis)
    trend = max(0.0, min(1.0, _safe_float2(trend, 0.0)))

    no_current_year_data = (
        not dk and not pf and not pop
    )
    if no_current_year_data and gecmis:
        basari = max(0.0, min(1.0, _safe_float2(trend, gecmis[0]["oran"])))

        prev_yil = gecmis[0]["yil"]
        try:
            cur.execute(
                """SELECT ortalama_not FROM performans
                   WHERE ders_id = ? AND akademik_yil = ?
                   ORDER BY pfrs_id DESC LIMIT 1""",
                (int(ders_id), prev_yil),
            )
            prev_pf = cur.fetchone()
            if prev_pf and _safe_float2(prev_pf[0], 0) > 0:
                ortalama_not = _safe_float2(prev_pf[0], ortalama_not)
        except Exception:
            pass
        try:
            cur.execute(
                """SELECT doluluk_orani FROM populerlik
                   WHERE ders_id = ? AND akademik_yil = ?
                   ORDER BY pop_id DESC LIMIT 1""",
                (int(ders_id), prev_yil),
            )
            prev_pop = cur.fetchone()
            if prev_pop and _safe_float2(prev_pop[0], 0) > 0:
                doluluk = max(0.0, min(1.0, _safe_float2(prev_pop[0], doluluk)))
        except Exception:
            pass

    return {
        "ders_id": int(ders_id),
        "basari": basari,
        "trend": trend,
        "populerlik": doluluk,
        "anket": max(0.0, min(1.0, _safe_float2(anket, 0.5))),
        "ortalama_not": max(0.0, min(100.0, _safe_float2(ortalama_not, 0.0))),
    }


def evaluate_drop_reasons(
    score_100,
    average_grade,
    score_threshold=DROP_SCORE_THRESHOLD,
    average_grade_threshold=DROP_AVERAGE_GRADE_THRESHOLD,
):
    """
    Dersin mufredattan dusme nedenlerini degerlendirip neden listesi doner.
    """
    reasons = []
    if _safe_float2(score_100, 0.0) < float(score_threshold):
        reasons.append(f"Kesinlesme puani {float(score_threshold):.0f} altinda")
    if _safe_float2(average_grade, 0.0) < float(average_grade_threshold):
        reasons.append(f"Gecme not ortalamasi {float(average_grade_threshold):.0f} altinda")
    return reasons


def should_drop_course(
    score_100,
    average_grade,
    score_threshold=DROP_SCORE_THRESHOLD,
    average_grade_threshold=DROP_AVERAGE_GRADE_THRESHOLD,
):
    """
    Dersin dusup dusmeyecegini ve nedenlerini doner. (drop_flag, reasons) tuple.
    """
    reasons = evaluate_drop_reasons(
        score_100,
        average_grade,
        score_threshold=score_threshold,
        average_grade_threshold=average_grade_threshold,
    )
    return len(reasons) > 0, reasons


def _pool_course_score_anket_only(anket):
    """
    Mufredat disi dersler icin kesinlesme puani. TOPSIS'e girmez.
    score = 50 + (anket - 0.5) * 2 * 10  => anket 0.5 -> 50, 1.0 -> 60, 0.0 -> 40.
    None/bos/gecersiz -> anket 0.5 (50). Dis aralik [0,1] disina clamp.
    """
    if anket is None:
        ratio = 0.5
    else:
        try:
            ratio = float(anket)
            if math.isnan(ratio) or math.isinf(ratio):
                ratio = 0.5
        except (TypeError, ValueError):
            ratio = 0.5
    ratio = max(0.0, min(1.0, ratio))
    return POOL_DEFAULT_SCORE + (ratio - 0.5) * 2.0 * POOL_ANKET_SCORE_SPREAD


def get_faculty_year_topsis_results(
    cur,
    fakulte_id,
    akademik_yil,
    donem="G",
    include_course_ids=None,
    strict_ahp: bool = False,
):
    """
    Bir fakulte+yil icin tum adaylarin TOPSIS skorlarini hesaplar.

    UYARI — Skor anlamlari farklilik gosterir:
      * Mufredattaki dersler **TOPSIS pipeline'ina girer** (AHP agirliklarinin
        uygulandigi tam algoritma). Donen `score_methods[id] == "topsis"`.
      * Mufredat **disi** (havuz) dersleri TOPSIS'e girmez; yalnizca anket
        bazli sabit puan alir (~50+-10). Donen `score_methods[id] ==
        "pool_anket_only"`. Bu skor TOPSIS gibi yorumlanmamali.

    AHP cozumu:
      * `strict_ahp=False` (varsayilan): aktif profil cozumlenemezse Saaty
        legacy matrisine **uyari logu** ile dusulur. `ahp_fallback_used=True`
        donus dict'inde bildirilir; caller bunu UI'da gosterip kullaniciyi
        uyarmali.
      * `strict_ahp=True`: aktif tutarli profil yoksa `RuntimeError` firlatir.
        Karar Merkezi'nden tetiklenen calistirmalarda bunu True yapin ki karar
        kullanicinin secmedigi agirliklarla uretilmesin.
    """
    fakulte_id = int(fakulte_id)
    akademik_yil = int(akademik_yil)
    donem = str(donem or "G")
    include_course_ids = {int(d) for d in (include_course_ids or [])}

    cur.execute("PRAGMA table_info(ders)")
    ders_cols = {str(r[1]) for r in cur.fetchall()}
    has_fakulte_col = "fakulte_id" in ders_cols
    has_bolum_col = "bolum_id" in ders_cols
    has_bolum_table = _table_exists(cur, "bolum")

    elective_predicate = build_elective_predicate(cur=cur, alias="d")
    has_elective_filter = elective_predicate != "0=1"

    def _elective_filter(course_ids):
        normalized = {int(d) for d in (course_ids or []) if d is not None}
        if not normalized:
            return set()
        return filter_elective_course_ids(cur, normalized) if has_elective_filter else normalized

    curriculum_ids = _get_curriculum_course_ids(cur, fakulte_id, akademik_yil, donem)
    curriculum_ids = _elective_filter(curriculum_ids)

    aday_dersler = set(curriculum_ids)
    candidate_predicate = elective_predicate if has_elective_filter else "1=1"

    if candidate_predicate:
        if has_fakulte_col and has_bolum_col and has_bolum_table:
            cur.execute(
                f"""
                SELECT DISTINCT d.ders_id
                FROM ders d
                WHERE (
                    d.fakulte_id = ?
                    OR EXISTS (
                        SELECT 1
                        FROM bolum b
                        WHERE b.bolum_id = d.bolum_id AND b.fakulte_id = ?
                    )
                )
                  AND {candidate_predicate}
                """,
                (fakulte_id, fakulte_id),
            )
        elif has_fakulte_col:
            cur.execute(
                f"""
                SELECT DISTINCT d.ders_id
                FROM ders d
                WHERE d.fakulte_id = ?
                  AND {candidate_predicate}
                """,
                (fakulte_id,),
            )
        elif has_bolum_col and has_bolum_table:
            cur.execute(
                f"""
                SELECT DISTINCT d.ders_id
                FROM ders d
                JOIN bolum b ON d.bolum_id = b.bolum_id
                WHERE b.fakulte_id = ?
                  AND {candidate_predicate}
                """,
                (fakulte_id,),
            )
        else:
            cur.execute(
                f"""
                SELECT DISTINCT d.ders_id
                FROM ders d
                WHERE {candidate_predicate}
                """
            )
        aday_dersler.update(int(r[0]) for r in cur.fetchall() if r and r[0] is not None)

    havuz_query = """
        SELECT DISTINCT CAST(h.ders_id AS INTEGER)
        FROM havuz h
        WHERE h.fakulte_id = ? AND h.yil = ?
    """
    havuz_params: list[Any] = [fakulte_id, akademik_yil]
    if _havuz_has_donem_col(cur):
        havuz_query += " AND LOWER(SUBSTR(TRIM(COALESCE(h.donem, '')), 1, 1)) = ?"
        havuz_params.append(_normalize_term_key(donem))
    cur.execute(havuz_query, tuple(havuz_params))
    aday_dersler.update(int(r[0]) for r in cur.fetchall() if r and r[0] is not None)

    aday_dersler.update(_elective_filter(include_course_ids))
    aday_dersler = _elective_filter(aday_dersler)

    if not aday_dersler:
        return {
            "ok": False,
            "error": "Aday ders bulunamadi (fakulte ve yil icin TOPSIS evreni bos).",
            "scores": {},
            "metric_map": {},
            "ders_meta": {},
        }

    ders_meta = {}
    meta_ids = sorted(int(d) for d in aday_dersler)
    if meta_ids:
        chunk_size = 900  # SQLite degisken limitine takilmamak icin.
        for i in range(0, len(meta_ids), chunk_size):
            chunk = meta_ids[i : i + chunk_size]
            placeholders = ",".join("?" for _ in chunk)
            cur.execute(
                f"""
                SELECT ders_id, {'bolum_id' if has_bolum_col else 'NULL as bolum_id'}, ad
                FROM ders
                WHERE ders_id IN ({placeholders})
                """,
                tuple(chunk),
            )
            for r in cur.fetchall():
                d_id = int(r[0])
                ders_meta[d_id] = {
                    "bolum_id": int(r[1]) if r[1] is not None else None,
                    "ad": str(r[2] or ""),
                }

    motor = KararMotoru()
    ahp_profile = None
    ahp_fallback_used = False
    ahp_fallback_reason: str | None = None
    try:
        from app.services.ahp_profile_service import (
            DEFAULT_CRITERIA_KEYS,
            resolve_ahp_profile,
        )
        from app.services.criteria_definition_service import criteria_direction_map

        ahp_profile = resolve_ahp_profile(
            cur.connection,
            faculty_id=fakulte_id,
            department_id=None,
            year=akademik_yil,
        )
        benefit_map = criteria_direction_map(cur.connection)
        profile_weights = ahp_profile.get("weights", {})
        profile_keys = [key for key in ahp_profile.get("criteria_keys", DEFAULT_CRITERIA_KEYS) if key in DEFAULT_CRITERIA_KEYS]
        if set(profile_keys) >= {"basari", "trend", "populerlik", "anket"}:
            agirliklar = [float(profile_weights.get(key, 0.0)) for key in ["basari", "trend", "populerlik", "anket"]]
        else:
            ahp_fallback_used = True
            ahp_fallback_reason = "Profil kriter anahtarlari beklenen 4 kriteri kapsamiyor."
            agirliklar = motor.ahp_calistir()
        # Strict modda tutarsiz profili kabul etme (kullanici aksini istemediyse).
        if strict_ahp and ahp_profile and not bool(ahp_profile.get("is_consistent", True)):
            raise RuntimeError(
                "Aktif AHP profili tutarsiz (CR > 0.10). Strict modda karar uretilemez."
            )
    except Exception as ahp_exc:
        ahp_fallback_used = True
        ahp_fallback_reason = str(ahp_exc)
        if strict_ahp:
            # Karar Merkezi'nden gelen cagri: legacy agirliklara sessizce dusmek
            # akademik karar acisindan tehlikeli. Acik hata firlat.
            raise RuntimeError(
                f"Aktif AHP profili cozumlenemedi (strict_ahp=True): {ahp_exc}"
            ) from ahp_exc
        logger.warning(
            "AHP profili cozumlenemedi, legacy Saaty agirliklari kullaniliyor "
            "(strict_ahp=False): %s", ahp_exc,
        )
        agirliklar = motor.ahp_calistir()
        ahp_profile = None
        benefit_map = {"basari": True, "trend": True, "populerlik": True, "anket": True}
    metric_map = {}
    for ders_id in sorted(aday_dersler):
        m = _read_course_metrics(cur, ders_id, akademik_yil, donem, motor)
        m["ders"] = ders_meta.get(ders_id, {}).get("ad", str(ders_id))
        metric_map[ders_id] = m

    curriculum_course_ids = _get_curriculum_course_ids(
        cur=cur, fakulte_id=fakulte_id, akademik_yil=akademik_yil, donem=donem
    )
    curriculum_course_ids = _elective_filter(curriculum_course_ids)

    curriculum_courses = sorted(d for d in aday_dersler if d in curriculum_course_ids)
    pool_courses = sorted(d for d in aday_dersler if d not in curriculum_course_ids)

    skor_map = {}
    # score_methods: hangi dersin skoru hangi yontemle uretildi (audit/UI icin).
    # Onceki surumde curriculum/pool skorlari ayni `topsis_score` kolonuna yaziliyordu
    # ve UI'da ayni gibi gosteriliyordu; bu kullaniciyi yaniltiyordu.
    score_methods: dict[int, str] = {}
    df_sonuc = pd.DataFrame()
    meta = {}

    # Mufredattaki dersler: sadece bunlar TOPSIS pipeline'ina girer.
    if curriculum_courses:
        df_cur = pd.DataFrame([metric_map[cid] for cid in curriculum_courses])
        if not df_cur.empty:
            df_sonuc, meta = motor.topsis_calistir(
                df_cur,
                agirliklar,
                criteria_keys=["basari", "trend", "populerlik", "anket"],
                benefit_map=benefit_map,
            )
            if ahp_profile:
                meta["ahp_profile_id"] = ahp_profile.get("id")
                meta["ahp_profile_version"] = ahp_profile.get("version")
            if not df_sonuc.empty:
                for _, r in df_sonuc.iterrows():
                    d_id = int(r.get("ders_id", 0) or 0)
                    if d_id <= 0:
                        continue
                    kp = r.get("Kesinlesme_Puani")
                    if kp is None or (isinstance(kp, float) and math.isnan(kp)):
                        kp = _safe_float2(r.get("AHP_TOPSIS_Skor"), 0.0) * 100.0
                    skor_map[d_id] = round(_safe_float2(kp, 0.0), 2)
                    score_methods[d_id] = "topsis"
    else:
        # Fallback: bu fakulte+yil icin mufredatta hic aday ders yok; TOPSIS calismaz,
        # tum adaylar havuz mantigi (anket-only) ile puanlanir.
        logger.debug(
            "get_faculty_year_topsis_results: TOPSIS evreni bos (mufredatta aday yok); "
            "fakulte_id=%s yil=%s, pool_only=%s ders",
            fakulte_id,
            akademik_yil,
            len(pool_courses),
        )

    # Mufredat disi: TOPSIS'e hic girmez; yalnizca anket ile 50+-10.
    for d_id in pool_courses:
        anket_val = (metric_map.get(d_id) or {}).get("anket")
        skor_map[d_id] = round(_pool_course_score_anket_only(anket_val), 2)
        score_methods[d_id] = "pool_anket_only"

    logger.debug(
        "get_faculty_year_topsis_results: TOPSIS=%s ders, pool_anket=%s ders (fakulte_id=%s yil=%s)",
        len(curriculum_courses),
        len(pool_courses),
        fakulte_id,
        akademik_yil,
    )

    if not skor_map:
        return {
            "ok": False,
            "error": "Hicbir ders icin skor uretilemedi.",
            "scores": {},
            "metric_map": metric_map,
            "ders_meta": ders_meta,
        }

    return {
        "ok": True,
        "scores": skor_map,
        "score_methods": score_methods,  # {ders_id: "topsis"|"pool_anket_only"}
        "metric_map": metric_map,
        "ders_meta": ders_meta,
        "df_sonuc": df_sonuc,
        "meta": meta,
        "ahp_profile": ahp_profile,
        "ahp_fallback_used": ahp_fallback_used,
        "ahp_fallback_reason": ahp_fallback_reason,
        "topsis_course_count": len(curriculum_courses),
        "pool_only_course_count": len(pool_courses),
    }

def _get_curriculum_course_ids(cur, fakulte_id, akademik_yil, donem="G"):
    """
    Fakulte + yil (+ donem ilk harf) icin mufredatta bulunan ders_id kumesini dondurur.
    Once bolum uzerinden (canonical); basarisizsa mufredat.fakulte_id (legacy sema).
    """
    fakulte_id = int(fakulte_id)
    akademik_yil = int(akademik_yil)
    donem = str(donem or "G")

    def _fetch_via_bolum(with_donem: bool):
        if with_donem:
            cur.execute(
                """
                SELECT DISTINCT md.ders_id
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
                WHERE b.fakulte_id = ? AND m.akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                """,
                (fakulte_id, akademik_yil, donem),
            )
        else:
            cur.execute(
                """
                SELECT DISTINCT md.ders_id
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
                WHERE b.fakulte_id = ? AND m.akademik_yil = ?
                """,
                (fakulte_id, akademik_yil),
            )
        return {int(r[0]) for r in cur.fetchall() if r and r[0] is not None}

    def _fetch_via_mufredat_fakulte(with_donem: bool):
        if with_donem:
            cur.execute(
                """
                SELECT DISTINCT md.ders_id
                FROM mufredat m
                JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
                WHERE m.fakulte_id = ? AND m.akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                """,
                (fakulte_id, akademik_yil, donem),
            )
        else:
            cur.execute(
                """
                SELECT DISTINCT md.ders_id
                FROM mufredat m
                JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
                WHERE m.fakulte_id = ? AND m.akademik_yil = ?
                """,
                (fakulte_id, akademik_yil),
            )
        return {int(r[0]) for r in cur.fetchall() if r and r[0] is not None}

    try:
        return _fetch_via_bolum(True)
    except Exception:
        try:
            return _fetch_via_bolum(False)
        except Exception:
            try:
                return _fetch_via_mufredat_fakulte(True)
            except Exception:
                try:
                    return _fetch_via_mufredat_fakulte(False)
                except Exception:
                    logger.debug(
                        "_get_curriculum_course_ids: mufredat sorgusu basarisiz fakulte_id=%s yil=%s",
                        fakulte_id,
                        akademik_yil,
                    )
                    return set()


def persist_faculty_year_topsis_scores(cur, fakulte_id, akademik_yil, skor_map, ders_meta, donem="G"):
    """
    Hesaplanan TOPSIS skorlarini havuz tablosuna yazar. Mevcut kayit varsa UPDATE, yoksa INSERT yapar.
    """
    fakulte_id = int(fakulte_id)
    akademik_yil = int(akademik_yil)
    term_key = _normalize_term_key(donem)
    havuz_has_donem = _havuz_has_donem_col(cur)
    havuz_term_scoped = havuz_has_donem and _havuz_unique_includes_donem(cur)
    active_curriculum_ids = _get_curriculum_course_ids(
        cur=cur,
        fakulte_id=fakulte_id,
        akademik_yil=akademik_yil,
        donem=donem,
    )
    active_curriculum_ids = filter_elective_course_ids(cur, active_curriculum_ids)
    elective_ids = filter_elective_course_ids(cur, skor_map.keys())
    elective_predicate = build_elective_predicate(cur=cur, alias="d")

    clear_sql = """
        UPDATE havuz
        SET skor = NULL
        WHERE fakulte_id = ? AND yil = ?
          AND EXISTS (
              SELECT 1
              FROM ders d
              WHERE d.ders_id = CAST(havuz.ders_id AS INTEGER)
                AND {elective_predicate}
          )
    """.format(elective_predicate=elective_predicate)
    clear_params: list[Any] = [fakulte_id, akademik_yil]
    if havuz_term_scoped:
        clear_sql += " AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = ?"
        clear_params.append(term_key)
    cur.execute(clear_sql, tuple(clear_params))

    upsert_count = 0
    for ders_id in sorted(elective_ids):
        score = skor_map.get(int(ders_id))
        meta = ders_meta.get(int(ders_id), {})
        bolum_id = meta.get("bolum_id")
        ders_adi = str(meta.get("ad") or "")
        score_val = round(_safe_float2(score, 0.0), 2)

        update_sql = """
            UPDATE havuz
            SET bolum_id = COALESCE(?, bolum_id),
                ders_adi = CASE WHEN ? <> '' THEN ? ELSE ders_adi END,
                skor = ?
            WHERE ders_id = ? AND fakulte_id = ? AND yil = ?
        """
        update_params = [bolum_id, ders_adi, ders_adi, score_val, str(ders_id), fakulte_id, akademik_yil]
        if havuz_term_scoped:
            update_sql += " AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = ?"
            update_params.append(term_key)
        cur.execute(update_sql, tuple(update_params))
        if cur.rowcount == 0:
            init_statu = 1 if int(ders_id) in active_curriculum_ids else 0
            if havuz_has_donem:
                cur.execute(
                    """
                    INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, donem, statu, sayac, skor, ders_adi)
                    VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
                    """,
                    (
                        str(ders_id),
                        akademik_yil,
                        fakulte_id,
                        bolum_id,
                        "Bahar" if term_key == "b" else "Guz",
                        init_statu,
                        score_val,
                        ders_adi,
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, statu, sayac, skor, ders_adi)
                    VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                    """,
                    (str(ders_id), akademik_yil, fakulte_id, bolum_id, init_statu, score_val, ders_adi),
                )
        upsert_count += 1
    return upsert_count


def ensure_pool_visibility_for_curriculum(cur, fakulte_id, akademik_yil, donem="G"):
    """
    Havuz ekraninda gorunurluk ve kural tutarliligi icin:
    - Mufredatta bulunan dersler havuzda mutlaka satira sahip olur.
    - Mufredatta olan derslerin statu degeri 1'e hizalanir.
    """
    fakulte_id = int(fakulte_id)
    akademik_yil = int(akademik_yil)
    term_key = _normalize_term_key(donem)
    havuz_has_donem = _havuz_has_donem_col(cur)
    havuz_term_scoped = havuz_has_donem and _havuz_unique_includes_donem(cur)
    curriculum_ids = sorted(
        filter_elective_course_ids(
            cur,
            _get_curriculum_course_ids(
                cur=cur,
                fakulte_id=fakulte_id,
                akademik_yil=akademik_yil,
                donem=donem,
            ),
        )
    )
    if not curriculum_ids:
        return {"updated": 0, "inserted": 0, "curriculum_count": 0}

    updated = 0
    inserted = 0
    chunk_size = 900
    for i in range(0, len(curriculum_ids), chunk_size):
        chunk = curriculum_ids[i : i + chunk_size]
        placeholders = ",".join("?" for _ in chunk)

        update_sql = f"""
            UPDATE havuz
            SET statu = 1
            WHERE fakulte_id = ? AND yil = ?
              AND CAST(ders_id AS INTEGER) IN ({placeholders})
        """
        update_params: list[Any] = [fakulte_id, akademik_yil, *chunk]
        if havuz_term_scoped:
            update_sql += " AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = ?"
            update_params.append(term_key)
        cur.execute(update_sql, tuple(update_params))
        updated += int(cur.rowcount or 0)

        missing_sql = f"""
            SELECT d.ders_id, d.bolum_id, d.ad
            FROM ders d
            WHERE d.ders_id IN ({placeholders})
              AND NOT EXISTS (
                    SELECT 1
                    FROM havuz h
                    WHERE h.fakulte_id = ? AND h.yil = ?
                      AND CAST(h.ders_id AS INTEGER) = d.ders_id
        """
        missing_params: list[Any] = [*chunk, fakulte_id, akademik_yil]
        if havuz_term_scoped:
            missing_sql += " AND LOWER(SUBSTR(TRIM(COALESCE(h.donem, '')), 1, 1)) = ?"
            missing_params.append(term_key)
        missing_sql += "\n              )"
        cur.execute(missing_sql, tuple(missing_params))
        eksikler = cur.fetchall()
        for r in eksikler:
            if not r or r[0] is None:
                continue
            if havuz_has_donem:
                cur.execute(
                    """
                    INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, donem, statu, sayac, skor, ders_adi)
                    VALUES (?, ?, ?, ?, ?, 1, 0, NULL, ?)
                    """,
                    (
                        str(int(r[0])),
                        akademik_yil,
                        fakulte_id,
                        int(r[1]) if r[1] is not None else None,
                        "Bahar" if term_key == "b" else "Guz",
                        str(r[2] or ""),
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO havuz (ders_id, yil, fakulte_id, bolum_id, statu, sayac, skor, ders_adi)
                    VALUES (?, ?, ?, ?, 1, 0, NULL, ?)
                    """,
                    (
                        str(int(r[0])),
                        akademik_yil,
                        fakulte_id,
                        int(r[1]) if r[1] is not None else None,
                        str(r[2] or ""),
                    ),
                )
            inserted += 1

    return {
        "updated": updated,
        "inserted": inserted,
        "curriculum_count": len(curriculum_ids),
    }


def generate_next_year_curricula(
    db_path=None,
    fakulte_id=None,
    akademik_yil=None,
    donem="G",
    drop_score_threshold=DROP_SCORE_THRESHOLD,
    drop_average_grade_threshold=DROP_AVERAGE_GRADE_THRESHOLD,
    require_decision_governance: bool = False,
):
    """
    Faculty + year + term icin bolum bazli sonraki yil mufredati olusturur.
    - Validasyon: Sadece mufredatta olan derslerin zorunlu kriterleri; anket zorunlu degil.
    - Havuz / mufredat disi dersler validasyonu bloklamaz.
    - Dusen dersler (skor baraj altinda veya ortalama not baraji altinda)
      yerine kesinlesme puani en yuksek adaylar eklenir.
    - Duser yoksa mufredat aynen bir sonraki yila tasinir.
    - Havuz statu/sayac guncellemesi calculate_next_status ile yapilir.

    Args:
        require_decision_governance: True ise decision_run kaydi basarisiz olursa
            ana sonuc `ok=False` doner ve transaction rollback edilir. Karar
            Merkezi'nden tetiklenen calistirmada kullanin — kullanici "yeni
            karar calistir" derken sessiz governance hatasi gormesin. Otomatik
            arka plan uretiminde False kalmasi guvenli (default).
    """
    if fakulte_id is None or akademik_yil is None:
        return {
            "ok": False,
            "error": "fakulte_id ve akademik_yil zorunludur.",
        }

    fakulte_id = int(fakulte_id)
    akademik_yil = int(akademik_yil)
    sonraki_yil = akademik_yil + 1
    donem = str(donem or "G")
    term_key = _normalize_term_key(donem)
    resolved_db_path = resolve_sqlite_db_path(db_path)

    conn = None
    try:
        if not resolved_db_path.exists():
            return {"ok": False, "error": f"DB bulunamadi: {resolved_db_path}"}

        conn = get_raw_connection(str(resolved_db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        ensure_pool_state_governance_schema(conn, commit=False)
        decision_policy = None
        try:
            from app.db.schema_compat import ensure_decision_governance_schema
            from app.services.decision_policy_service import resolve_decision_policy

            ensure_decision_governance_schema(conn, commit=False)
            decision_policy = resolve_decision_policy(
                conn,
                faculty_id=fakulte_id,
                department_id=None,
                year=akademik_yil,
            )
            if float(drop_score_threshold) == float(DROP_SCORE_THRESHOLD):
                drop_score_threshold = float(decision_policy.get("rest_threshold", DROP_SCORE_THRESHOLD))
        except Exception as policy_exc:
            logger.warning("Karar politikasi cozumlenemedi, legacy esikler kullaniliyor: %s", policy_exc)
        havuz_has_donem = _havuz_has_donem_col(cur)
        # Legacy donemsiz UNIQUE index'i (orn. ux_havuz_ders_fak_yil) burada da
        # temizle: bu index term-scoping'i (Guz/Bahar ayrimini) sessizce kapatip
        # sayac/donem hatalarina yol aciyordu. Idempotent; baslangic migration'i
        # gecikse bile uretim dogru calissin diye uretim hattinda da uygulanir.
        if havuz_has_donem:
            try:
                _drop_legacy_havuz_term_agnostic_unique(cur)
            except Exception as drop_exc:
                logger.warning("Legacy havuz unique index temizlenemedi: %s", drop_exc)
        havuz_term_scoped = havuz_has_donem and _havuz_unique_includes_donem(cur)
        normalized_rows = _normalize_mufredat_faculty_ids(cur)

        cur.execute("SELECT ad FROM fakulte WHERE fakulte_id = ?", (fakulte_id,))
        fak = cur.fetchone()
        if not fak:
            return {"ok": False, "error": f"Fakulte bulunamadi: {fakulte_id}"}

        try:
            from app.services.criteria_completion_service import can_run_algorithm

            # CIFT-DONEM KRITER KAPISI (kullanici kurali):
            # "2 doneminde kriterleri girilmeden mufredat olusturma yapilamasin."
            # Fakultenin o yil mufredatinda Guz + Bahar arasinda hangileri varsa
            # her biri icin kapiyi calistir; uretilecek donemin kapisini her
            # durumda kontrol et. Yalnizca tum kapilar gecerse uretim baslar.
            cur.execute(
                """
                SELECT DISTINCT TRIM(COALESCE(m.donem, ''))
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                WHERE b.fakulte_id = ? AND m.akademik_yil = ?
                  AND COALESCE(TRIM(m.donem), '') <> ''
                """,
                (int(fakulte_id), int(akademik_yil)),
            )
            terms_to_check: set[str] = {_normalize_term_key(donem)}
            for row in cur.fetchall():
                key = _normalize_term_key(str(row[0]) if row and row[0] else "")
                if key in ("g", "b"):
                    terms_to_check.add(key)

            term_gates: dict[str, dict[str, Any]] = {}
            gate_failures: list[tuple[str, dict[str, Any]]] = []
            for term_key in sorted(terms_to_check):
                term_label = "Güz" if term_key == "g" else "Bahar"
                gate_for_term = can_run_algorithm(
                    conn,
                    year=akademik_yil,
                    faculty_id=fakulte_id,
                    semester=term_label,
                    scope_type="faculty",
                )
                term_gates[term_label] = gate_for_term
                if not gate_for_term.get("can_run"):
                    gate_failures.append((term_label, gate_for_term))

            current_label = "Güz" if _normalize_term_key(donem) == "g" else "Bahar"
            criteria_gate = term_gates.get(current_label, {})

            if gate_failures:
                # Once uretilecek donemi onceliklendir.
                primary_label, primary_gate = next(
                    (item for item in gate_failures if item[0] == current_label),
                    gate_failures[0],
                )
                gate_summary = primary_gate.get("summary") or {}
                missing_matrix = [
                    {
                        "ders_id": row.get("course_id"),
                        "ders": row.get("course_name"),
                        "criterion_key": row.get("criterion_key"),
                        "missing_reason": row.get("missing_reason"),
                        "invalid_reason": row.get("invalid_reason"),
                        "donem": primary_label,
                    }
                    for row in (gate_summary.get("matrix") or [])
                    if row.get("is_required") and (not row.get("is_present") or not row.get("is_valid"))
                ]
                blocked_terms = ", ".join(label for label, _ in gate_failures)
                reason = (
                    f"Cift-donem kriter kapisi: {blocked_terms} doneminin kriter "
                    "girisleri tamamlanmadan yeni yil mufredati uretilemez."
                )
                return {
                    "ok": False,
                    "error": reason,
                    "missing_criteria": missing_matrix,
                    "blocked_terms": [label for label, _ in gate_failures],
                    "criteria_completion": {
                        "completion_ratio": primary_gate.get("completion_ratio"),
                        "completion_level": primary_gate.get("completion_level"),
                        "required_completion_ratio": primary_gate.get("required_completion_ratio"),
                        "override_active": primary_gate.get("override_active"),
                        "risk": primary_gate.get("risk"),
                        "by_term": {
                            label: {
                                "can_run": bool(gate.get("can_run")),
                                "completion_ratio": gate.get("completion_ratio"),
                                "blocking_reason": gate.get("blocking_reason"),
                            }
                            for label, gate in term_gates.items()
                        },
                    },
                }
            if not criteria_gate.get("can_run"):
                gate_summary = criteria_gate.get("summary") or {}
                missing_matrix = [
                    {
                        "ders_id": row.get("course_id"),
                        "ders": row.get("course_name"),
                        "criterion_key": row.get("criterion_key"),
                        "missing_reason": row.get("missing_reason"),
                        "invalid_reason": row.get("invalid_reason"),
                    }
                    for row in (gate_summary.get("matrix") or [])
                    if row.get("is_required") and (not row.get("is_present") or not row.get("is_valid"))
                ]
                return {
                    "ok": False,
                    "error": criteria_gate.get("blocking_reason")
                    or "Kriter tamlık kontrolü algoritma çalıştırmayı engelledi.",
                    "missing_criteria": missing_matrix,
                    "criteria_completion": {
                        "completion_ratio": criteria_gate.get("completion_ratio"),
                        "completion_level": criteria_gate.get("completion_level"),
                        "required_completion_ratio": criteria_gate.get("required_completion_ratio"),
                        "override_active": criteria_gate.get("override_active"),
                        "risk": criteria_gate.get("risk"),
                    },
                }
        except Exception as criteria_gate_exc:
            logger.warning("Gelismis kriter tamlik kapisi uygulanamadi: %s", criteria_gate_exc)

        cur.execute(
            "SELECT bolum_id, ad FROM bolum WHERE fakulte_id = ? ORDER BY bolum_id",
            (fakulte_id,),
        )
        bolumler = [(int(r[0]), str(r[1] or "")) for r in cur.fetchall()]
        if not bolumler:
            return {"ok": False, "error": "Fakulteye ait bolum bulunamadi."}

        mevcut_mufredatlar = {}
        eksik_mufredat = []

        for bolum_id, bolum_adi in bolumler:
            cur.execute(
                """
                SELECT m.mufredat_id
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                WHERE b.fakulte_id = ? AND m.bolum_id = ? AND m.akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                ORDER BY COALESCE(m.versiyon, 0) DESC, m.mufredat_id DESC
                LIMIT 1
                """,
                (fakulte_id, bolum_id, akademik_yil, donem),
            )
            row = cur.fetchone()
            if not row:
                eksik_mufredat.append({"bolum_id": bolum_id, "bolum": bolum_adi})
                continue

            mufredat_id = int(row[0])
            cur.execute(
                """
                SELECT d.ders_id
                FROM mufredat_ders md
                JOIN ders d ON d.ders_id = md.ders_id
                WHERE md.mufredat_id = ?
                ORDER BY md.ders_id
                """,
                (mufredat_id,),
            )
            dersler = [int(r[0]) for r in cur.fetchall() if r and r[0] is not None]
            dersler = sorted(filter_elective_course_ids(cur, dersler))
            if not dersler:
                eksik_mufredat.append({"bolum_id": bolum_id, "bolum": bolum_adi})
                continue
            mevcut_mufredatlar[bolum_id] = dersler

        if eksik_mufredat:
            return {
                "ok": False,
                "error": "Bazi bolumlerde secilen yil/donem icin mufredat bulunamadi.",
                "missing_curricula": eksik_mufredat,
            }

        prev_havuz_sql = """
            SELECT CAST(ders_id AS INTEGER) as d_id, statu, sayac
            FROM havuz
            WHERE yil = ? AND fakulte_id = ?
        """
        prev_havuz_params: list[Any] = [akademik_yil, fakulte_id]
        if havuz_term_scoped:
            prev_havuz_sql += " AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = ?"
            prev_havuz_params.append(term_key)
        cur.execute(prev_havuz_sql, tuple(prev_havuz_params))
        prev_havuz = {
            int(r[0]): {"statu": int(r[1] or 0), "sayac": int(r[2] or 0)}
            for r in cur.fetchall()
            if r[0] is not None
        }
        prev_curriculum_ids = set()
        for dersler in mevcut_mufredatlar.values():
            prev_curriculum_ids.update(int(d) for d in dersler)

        def _effective_prev_state(ders_id: int):
            raw = prev_havuz.get(int(ders_id))
            raw_statu = int(raw.get("statu", 0)) if raw else None
            raw_sayac = int(raw.get("sayac", 0)) if raw else 0

            # Kaynak yil mufredatinda olan ders "aktif" kabul edilir.
            # Legacy/veri kaymasi nedeniyle havuzda 0/-1 gÃ¶rÃ¼nse bile kurala hizalar.
            if int(ders_id) in prev_curriculum_ids and raw_statu != 1:
                return 1, raw_sayac
            if raw_statu is None:
                return 0, 0
            return raw_statu, raw_sayac

        eksik_kriter = []
        for bolum_id, dersler in mevcut_mufredatlar.items():
            bolum_adi = next((b[1] for b in bolumler if b[0] == bolum_id), str(bolum_id))
            for ders_id in dersler:
                prev_statu, _ = _effective_prev_state(ders_id)
                if prev_statu != 1:
                    continue
                if not _has_full_criteria(cur, ders_id, akademik_yil, donem):
                    cur.execute("SELECT ad FROM ders WHERE ders_id = ?", (ders_id,))
                    dr = cur.fetchone()
                    ders_adi = str(dr[0]) if dr else str(ders_id)
                    eksik_kriter.append(
                        {
                            "bolum_id": bolum_id,
                            "bolum": bolum_adi,
                            "ders_id": ders_id,
                            "ders": ders_adi,
                        }
                    )

        if eksik_kriter:
            logger.warning(
                "generate_next_year_curricula: %d ders icin kriter eksik (fakulte_id=%s yil=%s). "
                "Bu dersler varsayilan degerlerle hesaplanacak.",
                len(eksik_kriter), fakulte_id, akademik_yil,
            )

        score_pack = get_faculty_year_topsis_results(
            cur=cur,
            fakulte_id=fakulte_id,
            akademik_yil=akademik_yil,
            donem=donem,
        )
        if not score_pack.get("ok"):
            return {
                "ok": False,
                "error": score_pack.get("error", "TOPSIS skorlari olusturulamadi."),
            }

        skor_map = dict(score_pack.get("scores", {}))
        metric_map = dict(score_pack.get("metric_map", {}))
        ders_meta = dict(score_pack.get("ders_meta", {}))
        aday_dersler = set(int(d) for d in metric_map.keys())

        # DONEM AYRIMI (Guz/Bahar karismasini onler):
        # Diger donemin KAYNAK YIL aktif mufredatindaki dersler, bu donemin sonraki
        # yil adayi OLAMAZ. Ornegin Bahar 2022 mufredatindaki bir ders dogrudan
        # Guz 2023 mufredatina eklenemez. (Havuza dusup dinlenen dersler bu kisitin
        # disindadir; burada yalnizca aktif/secili karsi-donem dersleri haric tutulur.)
        # DONEM AYRIMI — fakulte geneli (kaynak yil VE hedef yil):
        # Kaynak yilin diger doneminde aktif olan dersler ve hedef yilin diger
        # doneminde herhangi bir bolumde halihazirda secili dersler, bu donemin
        # aday havuzundan tamamen cikarilir. Boylece "kesinleşme puanlariyla
        # ekleme yapilirken" bile bir Bahar dersi Guz mufredatina (veya tersi)
        # eklenemez. Havuza dusup dinlenen dersler bu kisitin disindadir.
        other_term_source_map = _fetch_other_term_curriculum_map(
            cur=cur, fakulte_id=fakulte_id, akademik_yil=akademik_yil, current_term=donem,
        )
        other_term_target_map = _fetch_other_term_curriculum_map(
            cur=cur, fakulte_id=fakulte_id, akademik_yil=sonraki_yil, current_term=donem,
        )
        other_term_blocked_ids: set[int] = set()
        for _ids in other_term_source_map.values():
            other_term_blocked_ids.update(int(d) for d in _ids)
        for _ids in other_term_target_map.values():
            other_term_blocked_ids.update(int(d) for d in _ids)
        if other_term_blocked_ids:
            aday_dersler -= other_term_blocked_ids

        if not aday_dersler:
            return {"ok": False, "error": "Skor hesaplamak icin aday ders bulunamadi."}

        year_score_upserts = persist_faculty_year_topsis_scores(
            cur=cur,
            fakulte_id=fakulte_id,
            akademik_yil=akademik_yil,
            skor_map=skor_map,
            ders_meta=ders_meta,
            donem=donem,
        )

        bolum_ad_map = {int(b_id): str(b_name or "") for b_id, b_name in bolumler}
        other_term_next_year = _fetch_other_term_curriculum_map(
            cur=cur,
            fakulte_id=fakulte_id,
            akademik_yil=sonraki_yil,
            current_term=donem,
        )

        bolum_sonuc = []
        yeni_mufredatlar = {}

        def _sort_key(d_id):
            sc = _safe_float2(skor_map.get(d_id), 0.0)
            bas = _safe_float2(metric_map.get(d_id, {}).get("basari"), 0.0)
            dol = _safe_float2(metric_map.get(d_id, {}).get("populerlik"), 0.0)
            return (sc, bas, dol, -int(d_id))

        tum_aday_sirali = sorted(list(aday_dersler), key=_sort_key, reverse=True)

        def _is_cross_department_course(course_id: int, target_department_id: int) -> bool:
            kaynak_bolum_id = ders_meta.get(int(course_id), {}).get("bolum_id")
            if kaynak_bolum_id is None:
                return False
            return int(kaynak_bolum_id) != int(target_department_id)

        def _cross_department_count(course_ids: list[int], target_department_id: int) -> int:
            return sum(
                1
                for c_id in course_ids
                if _is_cross_department_course(int(c_id), int(target_department_id))
            )

        def _enforce_cross_department_limit(
            course_ids: list[int],
            target_department_id: int,
            limit: int = MAX_CROSS_DEPARTMENT_COURSES,
        ) -> list[int]:
            if limit < 0:
                return list(course_ids)
            externals = [
                int(c_id)
                for c_id in course_ids
                if _is_cross_department_course(int(c_id), int(target_department_id))
            ]
            if len(externals) <= limit:
                return list(course_ids)
            keep_external = set(sorted(externals, key=_sort_key, reverse=True)[:limit])
            return [
                int(c_id)
                for c_id in course_ids
                if not _is_cross_department_course(int(c_id), int(target_department_id))
                or int(c_id) in keep_external
            ]

        for bolum_id, bolum_adi in bolumler:
            mevcut = list(mevcut_mufredatlar.get(bolum_id, []))
            hedef_adet = len(mevcut)
            blocked_other_term = set(other_term_next_year.get(int(bolum_id), set()))

            dusenler = []
            kalanlar = []
            drop_reason_map = {}
            drop_avg_map = {}

            for d_id in mevcut:
                score = _safe_float2(skor_map.get(d_id), 0.0)
                ortalama_not = _safe_float2(metric_map.get(d_id, {}).get("ortalama_not"), 0.0)
                prev_statu, _ = _effective_prev_state(d_id)
                drop_reasons = evaluate_drop_reasons(
                    score_100=score,
                    average_grade=ortalama_not,
                    score_threshold=drop_score_threshold,
                    average_grade_threshold=drop_average_grade_threshold,
                )
                if int(d_id) not in aday_dersler:
                    drop_reasons = ["Ders secmeli havuz adaylari disinda"] + drop_reasons
                if int(d_id) in blocked_other_term:
                    drop_reasons = ["Ayni akademik yilin diger doneminde secili"] + drop_reasons
                if prev_statu in (-1, -2):
                    drop_reasons = ["Gecmis statu nedeniyle secilemez"] + drop_reasons
                if prev_statu in (-1, -2) or drop_reasons:
                    dusenler.append(d_id)
                    drop_reason_map[d_id] = drop_reasons
                    drop_avg_map[d_id] = ortalama_not
                else:
                    kalanlar.append(d_id)

            ekleme_nedenleri = {}
            if not dusenler:
                yeni = list(mevcut)
            else:
                yeni = list(kalanlar)
                blok = set(yeni) | set(dusenler)

                bolum_ici = [
                    d_id
                    for d_id in tum_aday_sirali
                    if d_id not in blok
                    and d_id not in blocked_other_term
                    and _effective_prev_state(d_id)[0] not in (-1, -2)
                    and ders_meta.get(d_id, {}).get("bolum_id") == bolum_id
                ]
                fakulte_geneli = [
                    d_id
                    for d_id in tum_aday_sirali
                    if d_id not in blok
                    and d_id not in bolum_ici
                    and d_id not in blocked_other_term
                    and _effective_prev_state(d_id)[0] not in (-1, -2)
                ]

                dis_bolum_sayisi = _cross_department_count(yeni, bolum_id)
                for d_id in bolum_ici + fakulte_geneli:
                    if len(yeni) >= hedef_adet:
                        break
                    if d_id in yeni:
                        continue
                    if _is_cross_department_course(d_id, bolum_id) and dis_bolum_sayisi >= MAX_CROSS_DEPARTMENT_COURSES:
                        continue
                    yeni.append(d_id)
                    if _is_cross_department_course(d_id, bolum_id):
                        dis_bolum_sayisi += 1
                    if d_id in bolum_ici:
                        ekleme_nedenleri[d_id] = ["Ayni bolum secmeli adayi"]
                    else:
                        kaynak_bolum_id = ders_meta.get(d_id, {}).get("bolum_id")
                        kaynak_bolum = (
                            bolum_ad_map.get(int(kaynak_bolum_id), f"Bolum-{kaynak_bolum_id}")
                            if kaynak_bolum_id is not None
                            else "Belirsiz"
                        )
                        ekleme_nedenleri[d_id] = [f"Fakulte ortak havuzu adayi (Kaynak: {kaynak_bolum})"]

                if len(yeni) < hedef_adet:
                    for d_id in sorted(dusenler, key=_sort_key, reverse=True):
                        if len(yeni) >= hedef_adet:
                            break
                        if d_id in yeni or d_id not in aday_dersler or d_id in blocked_other_term:
                            continue
                        if _is_cross_department_course(d_id, bolum_id) and dis_bolum_sayisi >= MAX_CROSS_DEPARTMENT_COURSES:
                            continue
                        yeni.append(d_id)
                        if _is_cross_department_course(d_id, bolum_id):
                            dis_bolum_sayisi += 1
                        ekleme_nedenleri[d_id] = ["Kontenjan korunumu icin geri eklendi"]

            yeni_unique = []
            seen = set()
            for d_id in yeni:
                if d_id not in seen:
                    seen.add(d_id)
                    yeni_unique.append(d_id)
            yeni_unique = yeni_unique[:hedef_adet]

            if len(yeni_unique) < hedef_adet:
                for d_id in mevcut:
                    if len(yeni_unique) >= hedef_adet:
                        break
                    if d_id in yeni_unique or d_id not in aday_dersler or d_id in blocked_other_term:
                        continue
                    if _is_cross_department_course(d_id, bolum_id) and _cross_department_count(
                        yeni_unique, bolum_id
                    ) >= MAX_CROSS_DEPARTMENT_COURSES:
                        continue
                    yeni_unique.append(d_id)

            if blocked_other_term:
                yeni_unique = [d_id for d_id in yeni_unique if d_id not in blocked_other_term]
                if len(yeni_unique) < hedef_adet:
                    for d_id in tum_aday_sirali:
                        if len(yeni_unique) >= hedef_adet:
                            break
                        if d_id in yeni_unique or d_id in blocked_other_term:
                            continue
                        if _effective_prev_state(d_id)[0] in (-1, -2):
                            continue
                        if _is_cross_department_course(d_id, bolum_id) and _cross_department_count(
                            yeni_unique, bolum_id
                        ) >= MAX_CROSS_DEPARTMENT_COURSES:
                            continue
                        yeni_unique.append(d_id)
                        if d_id not in ekleme_nedenleri:
                            kaynak_bolum_id = ders_meta.get(d_id, {}).get("bolum_id")
                            kaynak_bolum = (
                                bolum_ad_map.get(int(kaynak_bolum_id), f"Bolum-{kaynak_bolum_id}")
                                if kaynak_bolum_id is not None
                                else "Belirsiz"
                            )
                            ekleme_nedenleri[d_id] = [f"Diger donem cakismasi nedeniyle eklendi (Kaynak: {kaynak_bolum})"]

            yeni_unique = _enforce_cross_department_limit(
                course_ids=yeni_unique,
                target_department_id=bolum_id,
                limit=MAX_CROSS_DEPARTMENT_COURSES,
            )

            if len(yeni_unique) < hedef_adet:
                for d_id in tum_aday_sirali:
                    if len(yeni_unique) >= hedef_adet:
                        break
                    if d_id in yeni_unique or d_id in blocked_other_term:
                        continue
                    if _effective_prev_state(d_id)[0] in (-1, -2):
                        continue
                    if _is_cross_department_course(d_id, bolum_id):
                        continue
                    yeni_unique.append(d_id)
                    if d_id not in ekleme_nedenleri:
                        ekleme_nedenleri[d_id] = ["Ayni bolum adayi ile tamamlandi"]

            eklenenler = [d for d in yeni_unique if d not in mevcut]

            yeni_mufredatlar[bolum_id] = yeni_unique
            bolum_sonuc.append(
                {
                    "bolum_id": bolum_id,
                    "bolum": bolum_adi,
                    "mevcut_adet": len(mevcut),
                    "dusenler": [
                        {
                            "ders_id": d,
                            "ders": ders_meta.get(d, {}).get("ad", str(d)),
                            "score": _safe_float2(skor_map.get(d), 0.0),
                            "average_grade": _safe_float2(drop_avg_map.get(d), 0.0),
                            "reasons": drop_reason_map.get(d, []),
                        }
                        for d in dusenler
                    ],
                    "eklenenler": [
                        {
                            "ders_id": d,
                            "ders": ders_meta.get(d, {}).get("ad", str(d)),
                            "score": _safe_float2(skor_map.get(d), 0.0),
                            "kaynak_bolum_id": ders_meta.get(d, {}).get("bolum_id"),
                            "kaynak_bolum": (
                                bolum_ad_map.get(int(ders_meta.get(d, {}).get("bolum_id")))
                                if ders_meta.get(d, {}).get("bolum_id") is not None
                                else None
                            ),
                            "reasons": ekleme_nedenleri.get(d, ["Yuksek kesinlesme puani"]),
                        }
                        for d in eklenenler
                    ],
                    "tasindi_mi": len(dusenler) == 0,
                    "dis_bolum_ders_sayisi": _cross_department_count(yeni_unique, bolum_id),
                }
            )

        for bolum_id, bolum_adi in bolumler:
            dersler = yeni_mufredatlar.get(bolum_id, [])
            cur.execute(
                """
                SELECT m.mufredat_id
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                WHERE b.fakulte_id = ? AND m.bolum_id = ? AND m.akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                ORDER BY COALESCE(m.versiyon, 0) DESC, m.mufredat_id DESC
                LIMIT 1
                """,
                (fakulte_id, bolum_id, sonraki_yil, donem),
            )
            existing = cur.fetchone()
            if existing:
                hedef_muf_id = int(existing[0])
                cur.execute("DELETE FROM mufredat_ders WHERE mufredat_id = ?", (hedef_muf_id,))
                cur.execute(
                    "UPDATE mufredat SET durum = ? WHERE mufredat_id = ?",
                    ("Otomatik", hedef_muf_id),
                )
            else:
                cur.execute(
                    "SELECT COALESCE(MAX(versiyon), 0) FROM mufredat WHERE bolum_id = ?",
                    (bolum_id,),
                )
                max_ver = int(cur.fetchone()[0] or 0)
                cur.execute(
                    """
                    INSERT INTO mufredat (fakulte_id, bolum_id, akademik_yil, donem, durum, versiyon)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (fakulte_id, bolum_id, sonraki_yil, donem, "Otomatik", max_ver + 1),
                )
                hedef_muf_id = int(cur.lastrowid or 0)

            for d_id in dersler:
                cur.execute(
                    "INSERT INTO mufredat_ders (mufredat_id, ders_id) VALUES (?, ?) ON CONFLICT DO NOTHING",
                    (hedef_muf_id, int(d_id)),
                )

            dis_bolum_ders_sayisi = _cross_department_count(dersler, bolum_id)
            try:
                record_cross_department_usage(
                    conn=conn,
                    fakulte_id=fakulte_id,
                    bolum_id=bolum_id,
                    source_year=akademik_yil,
                    generated_year=sonraki_yil,
                    dis_bolum_ders_sayisi=dis_bolum_ders_sayisi,
                )
            except Exception as audit_exc:
                logger.warning(
                    "generate_next_year_curricula: cross-department audit yazilamadi "
                    "(fakulte=%s bolum=%s yil=%s->%s): %s",
                    fakulte_id,
                    bolum_id,
                    akademik_yil,
                    sonraki_yil,
                    audit_exc,
                )

        secilenler = set()
        for dersler in yeni_mufredatlar.values():
            secilenler.update(int(d) for d in dersler)

        gerekli_idler = (
            set(int(k) for k in prev_havuz.keys())
            | set(int(k) for k in secilenler)
            | set(int(k) for k in prev_curriculum_ids)
            | set(int(k) for k in aday_dersler)
        )
        gerekli_idler = filter_elective_course_ids(cur, gerekli_idler)

        tum_ders_map = {}
        if gerekli_idler:
            chunk_size = 900  # SQLite degisken limitine takilmamak icin.
            gerekli_sorted = sorted(int(d) for d in gerekli_idler)
            for i in range(0, len(gerekli_sorted), chunk_size):
                chunk = gerekli_sorted[i : i + chunk_size]
                placeholders = ",".join("?" for _ in chunk)
                cur.execute(
                    f"""
                    SELECT ders_id, bolum_id, ad
                    FROM ders
                    WHERE ders_id IN ({placeholders})
                    """,
                    tuple(chunk),
                )
                for r in cur.fetchall():
                    if not r or r[0] is None:
                        continue
                    tum_ders_map[int(r[0])] = (
                        int(r[1]) if r[1] is not None else None,
                        str(r[2] or ""),
                    )

        tum_dersler = [
            (int(d_id), meta[0], meta[1])
            for d_id, meta in sorted(tum_ders_map.items(), key=lambda x: x[0])
        ]

        elective_predicate = build_elective_predicate(cur=cur, alias="d")
        cleanup_sql = """
            DELETE FROM havuz
            WHERE fakulte_id = ? AND yil = ?
              AND NOT EXISTS (
                  SELECT 1
                  FROM ders d
                  WHERE d.ders_id = CAST(havuz.ders_id AS INTEGER)
                    AND {elective_predicate}
              )
        """.format(elective_predicate=elective_predicate)
        cleanup_params: list[Any] = [fakulte_id, sonraki_yil]
        if havuz_term_scoped:
            cleanup_sql += " AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = ?"
            cleanup_params.append(term_key)
        cur.execute(cleanup_sql, tuple(cleanup_params))

        # Donem-disi kirlilik temizligi: term-scoped semada, bu donemin hedef yil
        # havuzunda bu uretimin universum'una (gerekli_idler) ait OLMAYAN secmeli
        # satirlari sil. Boylece yanlis donemde (orn. Bahar dersi Guz havuzunda)
        # kalmis eski/hatali satirlar regenerasyonda temizlenir. Dinlenen/aday dersler
        # gerekli_idler icinde oldugu icin korunur.
        if havuz_term_scoped:
            cur.execute(
                """
                SELECT CAST(ders_id AS INTEGER)
                FROM havuz
                WHERE fakulte_id = ? AND yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = ?
                """,
                (fakulte_id, sonraki_yil, term_key),
            )
            existing_term_ids = {int(r[0]) for r in cur.fetchall() if r and r[0] is not None}
            stale_ids = sorted(existing_term_ids - {int(d) for d in gerekli_idler})
            stale_chunk = 900
            for i in range(0, len(stale_ids), stale_chunk):
                chunk = stale_ids[i : i + stale_chunk]
                placeholders = ",".join("?" for _ in chunk)
                cur.execute(
                    f"""
                    DELETE FROM havuz
                    WHERE fakulte_id = ? AND yil = ?
                      AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = ?
                      AND CAST(ders_id AS INTEGER) IN ({placeholders})
                    """,
                    tuple([fakulte_id, sonraki_yil, term_key, *chunk]),
                )

        upsert_count = 0
        pool_transition_count = 0
        pool_policy_cache: dict[tuple[int, int | None, str], dict] = {}

        def _pool_policy_for_course(target_bolum_id):
            cache_key = (int(fakulte_id), int(target_bolum_id) if target_bolum_id is not None else None, term_key)
            if cache_key not in pool_policy_cache:
                pool_policy_cache[cache_key] = resolve_pool_state_policy(
                    conn,
                    year=sonraki_yil,
                    faculty_id=fakulte_id,
                    department_id=int(target_bolum_id) if target_bolum_id is not None else None,
                    semester=donem,
                )
            return pool_policy_cache[cache_key]

        for ders_id, bolum_id, ders_adi in tum_dersler:
            eff_statu, eff_sayac = _effective_prev_state(ders_id)
            legacy_statu, legacy_sayac = calculate_next_status(
                int(eff_statu),
                int(eff_sayac),
                ders_id in secilenler,
            )
            yeni_statu, yeni_sayac = legacy_statu, legacy_sayac
            transition_score_val = _safe_float2(skor_map.get(int(ders_id)), 0.0) if int(ders_id) in skor_map else None
            skor_val = None
            lifecycle_payload = {
                "recommended_status": legacy_statu,
                "final_status": legacy_statu,
                "lifecycle_label": None,
                "approval_required": 0,
                "approval_status": "not_required",
                "transition_id": None,
                "explanation": None,
                "policy_id": None,
            }

            try:
                pool_policy = _pool_policy_for_course(bolum_id)
                trend = analyze_course_trend(cur, int(ders_id), akademik_yil)
                confidence = calculate_course_data_confidence(
                    cur=cur,
                    course_id=int(ders_id),
                    year=akademik_yil,
                    semester=donem,
                    policy=pool_policy,
                )
                confidence_score = confidence.get("score")
                if (
                    float(confidence_score or 0.0) <= 0.0
                    and not confidence.get("has_recent_data")
                    and not confidence.get("has_trend_data")
                ):
                    confidence_score = None
                flags = get_governance_flags(conn, int(ders_id))
                course_type = (ders_meta.get(int(ders_id), {}) or {}).get("tip")
                transition = evaluate_course_state_transition(
                    conn,
                    {
                        "course_id": int(ders_id),
                        "year": sonraki_yil,
                        "semester": donem,
                        "faculty_id": fakulte_id,
                        "department_id": bolum_id,
                        "current_status": eff_statu,
                        "counter_before": eff_sayac,
                        "years_in_pool": eff_sayac if int(eff_statu) == 0 else 0,
                        "years_in_rest": eff_sayac if int(eff_statu) == -1 else 0,
                        "topsis_score": transition_score_val,
                        "trend_score": trend.get("trend_score"),
                        "trend_label": trend.get("trend_label"),
                        "data_confidence_score": confidence_score,
                        "data_confidence_level": confidence.get("level"),
                        "course_type": course_type,
                        "governance_flags": flags,
                        "policy": pool_policy,
                        "in_mufredat_this_year": int(ders_id) in secilenler,
                        "legacy_recommended_status": legacy_statu,
                        "legacy_counter_after": legacy_sayac,
                    },
                )
                transition_id = save_state_transition(conn, transition)
                yeni_statu = int(transition.get("final_status", legacy_statu))
                yeni_sayac = int(transition.get("counter_after", legacy_sayac))
                lifecycle_payload = {
                    "recommended_status": int(transition.get("recommended_status", legacy_statu)),
                    "final_status": yeni_statu,
                    "lifecycle_label": transition.get("lifecycle_label"),
                    "approval_required": 1 if transition.get("approval_required") else 0,
                    "approval_status": transition.get("approval_status"),
                    "transition_id": transition_id,
                    "explanation": transition.get("explanation"),
                    "policy_id": transition.get("policy_id"),
                }
                pool_transition_count += 1
            except Exception as pool_exc:
                logger.warning(
                    "generate_next_year_curricula: havuz lifecycle kaydi yazilamadi "
                    "(ders=%s yil=%s): %s",
                    ders_id,
                    sonraki_yil,
                    pool_exc,
                )

            update_sql = """
                UPDATE havuz
                SET bolum_id=?, statu=?, sayac=?, skor=?, ders_adi=?,
                    recommended_status=?, final_status=?, lifecycle_label=?,
                    approval_required=?, approval_status=?, transition_id=?,
                    explanation=?, policy_id=?
                WHERE ders_id=? AND fakulte_id=? AND yil=?
            """
            update_params = [
                bolum_id,
                yeni_statu,
                yeni_sayac,
                skor_val,
                ders_adi or "",
                lifecycle_payload["recommended_status"],
                lifecycle_payload["final_status"],
                lifecycle_payload["lifecycle_label"],
                lifecycle_payload["approval_required"],
                lifecycle_payload["approval_status"],
                lifecycle_payload["transition_id"],
                lifecycle_payload["explanation"],
                lifecycle_payload["policy_id"],
                str(ders_id),
                fakulte_id,
                sonraki_yil,
            ]
            if havuz_term_scoped:
                update_sql += " AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = ?"
                update_params.append(term_key)
            cur.execute(update_sql, tuple(update_params))
            if cur.rowcount == 0:
                if havuz_has_donem:
                    cur.execute(
                        """
                        INSERT INTO havuz (
                            ders_id, yil, fakulte_id, bolum_id, donem, statu, sayac, skor, ders_adi,
                            recommended_status, final_status, lifecycle_label, approval_required,
                            approval_status, transition_id, explanation, policy_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(ders_id),
                            sonraki_yil,
                            fakulte_id,
                            bolum_id,
                            "Bahar" if term_key == "b" else "Guz",
                            yeni_statu,
                            yeni_sayac,
                            skor_val,
                            ders_adi or "",
                            lifecycle_payload["recommended_status"],
                            lifecycle_payload["final_status"],
                            lifecycle_payload["lifecycle_label"],
                            lifecycle_payload["approval_required"],
                            lifecycle_payload["approval_status"],
                            lifecycle_payload["transition_id"],
                            lifecycle_payload["explanation"],
                            lifecycle_payload["policy_id"],
                        ),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO havuz (
                            ders_id, yil, fakulte_id, bolum_id, statu, sayac, skor, ders_adi,
                            recommended_status, final_status, lifecycle_label, approval_required,
                            approval_status, transition_id, explanation, policy_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(ders_id),
                            sonraki_yil,
                            fakulte_id,
                            bolum_id,
                            yeni_statu,
                            yeni_sayac,
                            skor_val,
                            ders_adi or "",
                            lifecycle_payload["recommended_status"],
                            lifecycle_payload["final_status"],
                            lifecycle_payload["lifecycle_label"],
                            lifecycle_payload["approval_required"],
                            lifecycle_payload["approval_status"],
                            lifecycle_payload["transition_id"],
                            lifecycle_payload["explanation"],
                            lifecycle_payload["policy_id"],
                        ),
                    )
            upsert_count += 1

        decision_governance_result = {}
        try:
            from app.services.decision_run_service import safe_record_decision_run

            decision_governance_result = safe_record_decision_run(
                conn=conn,
                year=akademik_yil,
                faculty_id=fakulte_id,
                semester=donem,
                generation_result={
                    "fakulte_id": fakulte_id,
                    "year_from": akademik_yil,
                    "year_to": sonraki_yil,
                    "donem": donem,
                    "department_count": len(bolum_sonuc),
                    "pool_rows_upserted": upsert_count,
                    "pool_state_transitions": pool_transition_count,
                },
            )
        except Exception as governance_exc:
            decision_governance_result = {"ok": False, "error": str(governance_exc)}
            logger.warning(
                "generate_next_year_curricula: decision governance kaydi yazilamadi "
                "(fakulte=%s yil=%s): %s",
                fakulte_id,
                akademik_yil,
                governance_exc,
            )

        # Karar Merkezi'nden tetiklendigimizde governance hatasini sessizce
        # yutmayalim — kullanici "karar calistirildi" sanip Ders Kararlari'ni
        # bos bulmasin. require_decision_governance=False (default) ise eski
        # gevsek davranis korunur.
        if require_decision_governance and not decision_governance_result.get("ok"):
            conn.rollback()
            return {
                "ok": False,
                "error": (
                    decision_governance_result.get("error")
                    or "Karar governance kaydi olusturulamadi."
                ),
                "decision_governance": decision_governance_result,
            }

        conn.commit()

        return {
            "ok": True,
            "fakulte_id": fakulte_id,
            "fakulte": str(fak[0]),
            "year_from": akademik_yil,
            "year_to": sonraki_yil,
            "donem": donem,
            "departments": bolum_sonuc,
            "missing_curricula": eksik_mufredat,
            "pool_rows_upserted": upsert_count,
            "pool_state_transitions": pool_transition_count,
            "year_score_upserted": year_score_upserts,
            "normalized_curricula": normalized_rows,
            "decision_governance": decision_governance_result,
        }

    except Exception as exc:
        if conn:
            conn.rollback()
        return {
            "ok": False,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        if conn:
            conn.close()


def run_all_algorithms_for_year(
    yil: int,
    db_path: str | None = None,
    donem: str = "G",
    fakulte_id: int | None = None,
) -> dict:
    """
    Algoritma kontrol merkezi icin yil bazli manuel calistirma.

    Not (isim netligi): Bu fonksiyon Tk arayuzundeki MOCK/Trend/AHP/LR/RF/DT
    dugmelerini tek tek calistirmaz; uretim hattini `generate_next_year_curricula`
    uzerinden yurutur (icinde TOPSIS/skor ve mufredat uretimi vardir).

    Kurallar:
    - Sadece kriter girisi tamamlanmis fakulteler islenir.
    - Eksik fakulteler raporlanir, hesaplanmaz.
    - Basarili fakulteler icin (yil -> yil+1) mufredat uretilir.
    - Workflow durum tablolarinda algoritma calisti bilgisi islenir.

    Parametreler:
    - yil: Kaynak yıl (bu yıldan sonraki yıla müfredat üretilir)
    - db_path: Veritabanı dosyası yolu
    - donem: Dönem kodu ("G"=Güz, "B"=Bahar)
    - fakulte_id: Belirli bir fakülte için çalıştır (None=tüm fakülteler)
    """
    yil = int(yil)
    summary = {
        "ok": True,
        "year": yil,
        "processed": [],
        "skipped": [],
        "errors": [],
        "messages": [],
    }
    resolved_db_path = resolve_sqlite_db_path(db_path)

    if not resolved_db_path.exists():
        return {
            "ok": False,
            "year": yil,
            "processed": [],
            "skipped": [],
            "errors": [{"error": f"DB bulunamadi: {resolved_db_path}"}],
            "messages": [f"Veritabani bulunamadi: {resolved_db_path}"],
        }

    db_path = str(resolved_db_path)
    conn = get_raw_connection(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    ensure_yearly_workflow_schema(conn)

    # fakulte_id belirtildiyse sadece o fakülteyi işle, yoksa hepsini al
    if fakulte_id is not None:
        cur.execute("SELECT fakulte_id, ad FROM fakulte WHERE fakulte_id = ?", (int(fakulte_id),))
    else:
        cur.execute("SELECT fakulte_id, ad FROM fakulte ORDER BY fakulte_id")
    faculties = [(int(r[0]), str(r[1] or "")) for r in cur.fetchall()]
    conn.close()

    for fakulte_id_iter, fakulte_adi in faculties:
        status_conn = get_raw_connection(db_path)
        status_conn.row_factory = sqlite3.Row
        try:
            ensure_yearly_workflow_schema(status_conn)
            try:
                from app.services.criteria_completion_service import can_run_algorithm

                gate = can_run_algorithm(
                    status_conn,
                    year=yil,
                    faculty_id=fakulte_id_iter,
                    semester=donem,
                    scope_type="faculty",
                )
                complete = bool(gate.get("can_run"))
            except Exception as gate_exc:
                logger.warning("Gelismis kriter tamlik kapisi kullanilamadi: %s", gate_exc)
                gate = {}
                complete = is_faculty_criteria_complete(
                    status_conn,
                    yil=yil,
                    fakulte_id=fakulte_id_iter,
                    refresh=True,
                )
            faculty_status = get_faculty_year_status(
                status_conn,
                fakulte_id=fakulte_id_iter,
                yil=yil,
                refresh=False,
            )
            if not complete:
                gate_summary = gate.get("summary") or {}
                if gate_summary.get("matrix"):
                    missing = [
                        {
                            "ders_id": row.get("course_id"),
                            "ders": row.get("course_name"),
                            "criterion_key": row.get("criterion_key"),
                            "missing_reason": row.get("missing_reason"),
                            "invalid_reason": row.get("invalid_reason"),
                        }
                        for row in gate_summary.get("matrix", [])
                        if row.get("is_required") and (not row.get("is_present") or not row.get("is_valid"))
                    ]
                else:
                    missing = get_missing_criteria(
                        status_conn,
                        yil=yil,
                        fakulte_id=fakulte_id_iter,
                    )
                legacy_skip = (
                    f"{fakulte_adi} fakultesi icin {yil} yili kriter girisi eksik oldugundan hesaplama yapilmadi."
                )
                skip_msg = legacy_skip
                if gate.get("blocking_reason"):
                    skip_msg = f"{legacy_skip} {gate.get('blocking_reason')}"
                summary["skipped"].append(
                    {
                        "fakulte_id": fakulte_id_iter,
                        "fakulte": fakulte_adi,
                        "year": yil,
                        "reason": skip_msg,
                        "criteria_status": faculty_status.get("criteria_status", "not_started"),
                        "completion_ratio": gate.get("completion_ratio"),
                        "completion_level": gate.get("completion_level"),
                        "override_active": gate.get("override_active"),
                        "missing_criteria": missing,
                    }
                )
                summary["messages"].append(skip_msg)
                continue
        finally:
            status_conn.close()

        result = generate_next_year_curricula(
            db_path=db_path,
            fakulte_id=fakulte_id_iter,
            akademik_yil=yil,
            donem=donem,
        )

        status_conn = get_raw_connection(db_path)
        status_conn.row_factory = sqlite3.Row
        try:
            if result.get("ok"):
                mark_algorithm_run(
                    conn=status_conn,
                    fakulte_id=fakulte_id_iter,
                    source_year=yil,
                    generated_year=yil + 1,
                    success=True,
                )
                ok_msg = (
                    f"{fakulte_adi} fakultesi {yil} yili verileri islendi, {yil + 1} yili mufredati olusturuldu."
                )
                summary["processed"].append({**result, "message": ok_msg})
                summary["messages"].append(ok_msg)
            else:
                mark_algorithm_run(
                    conn=status_conn,
                    fakulte_id=fakulte_id_iter,
                    source_year=yil,
                    generated_year=None,
                    success=False,
                )
                err_msg = result.get("error", "Bilinmeyen hata")
                try:
                    from app.services.decision_run_service import (
                        record_failed_decision_run,
                    )

                    record_failed_decision_run(
                        db_path=db_path,
                        year=yil,
                        faculty_id=fakulte_id_iter,
                        semester=donem,
                        error_message=err_msg,
                    )
                except Exception as governance_exc:
                    logger.warning(
                        "run_all_algorithms_for_year: failed decision_run yazilamadi "
                        "(fakulte=%s yil=%s): %s",
                        fakulte_id_iter,
                        yil,
                        governance_exc,
                    )
                summary["ok"] = False
                summary["errors"].append(
                    {
                        "fakulte_id": fakulte_id_iter,
                        "fakulte": fakulte_adi,
                        "year": yil,
                        "error": err_msg,
                    }
                )
                summary["messages"].append(
                    f"{fakulte_adi} fakultesi icin {yil} yili hesaplama hatasi: {err_msg}"
                )
        finally:
            status_conn.close()

    if not summary["processed"] and not summary["errors"]:
        summary["messages"].append("Calistirilacak uygun fakulte bulunamadi.")
    return summary


def auto_generate_next_year_curricula(db_path=None, donem="G"):
    """
    Tum fakulteler icin otomatik sonraki yil mufredat uretimini tetikler. Her fakultenin en son mufredatli yilini bulur ve bir sonraki yili uretir.
    """
    summary = {
        "ok": True,
        "generated": [],
        "skipped": [],
        "errors": [],
    }
    resolved_db_path = resolve_sqlite_db_path(db_path)
    if not resolved_db_path.exists():
        summary["ok"] = False
        summary["errors"].append({"error": f"DB bulunamadi: {resolved_db_path}"})
        return summary

    db_path = str(resolved_db_path)
    conn = get_raw_connection(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    _normalize_mufredat_faculty_ids(cur)
    conn.commit()
    cur.execute("SELECT fakulte_id, ad FROM fakulte ORDER BY fakulte_id")
    faculties = [(int(r[0]), str(r[1] or "")) for r in cur.fetchall()]
    conn.close()

    def _find_candidate_year(cur, fakulte_id, donem):
        cur.execute(
            """
            SELECT DISTINCT m.akademik_yil
            FROM mufredat m
            JOIN bolum b ON b.bolum_id = m.bolum_id
            WHERE b.fakulte_id = ?
            ORDER BY m.akademik_yil DESC
            """,
            (fakulte_id,),
        )
        years = [int(r[0]) for r in cur.fetchall()]
        if not years:
            return None, "Mufredat yili yok"

        for yil in years:
            cur.execute(
                """
                SELECT COUNT(DISTINCT m.bolum_id)
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                WHERE b.fakulte_id = ? AND m.akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                """,
                (fakulte_id, yil, donem),
            )
            mevcut_bolum_adet = int(cur.fetchone()[0] or 0)
            cur.execute(
                """
                SELECT COUNT(DISTINCT m.bolum_id)
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                WHERE b.fakulte_id = ? AND m.akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                """,
                (fakulte_id, yil + 1, donem),
            )
            sonraki_bolum_adet = int(cur.fetchone()[0] or 0)

            # Kaynak yil ile bir sonraki yilin kapsamÄ±nÄ± karsilastir.
            # Fakultedeki tum bolum sayisini zorlamak, legacy/eksik bolum verisinde
            # ayni yilin tekrar tekrar uretilmesine sebep olabiliyor.
            hedef_bolum_adet = mevcut_bolum_adet
            if mevcut_bolum_adet > 0 and sonraki_bolum_adet < hedef_bolum_adet:
                return yil, None

        return None, "Sonraki yil zaten mevcut"

    for fakulte_id, fakulte_adi in faculties:
        conn = get_raw_connection(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        _normalize_mufredat_faculty_ids(cur)
        conn.commit()
        aday_yil, reason = _find_candidate_year(
            cur=cur,
            fakulte_id=fakulte_id,
            donem=donem,
        )
        conn.close()

        if aday_yil is None:
            summary["skipped"].append(
                {"fakulte_id": fakulte_id, "fakulte": fakulte_adi, "reason": reason}
            )
            continue

        result = generate_next_year_curricula(
            db_path=db_path,
            fakulte_id=fakulte_id,
            akademik_yil=aday_yil,
            donem=donem,
        )

        if result.get("ok"):
            summary["generated"].append(result)
        elif result.get("missing_criteria") or result.get("missing_curricula"):
            summary["skipped"].append(
                {
                    "fakulte_id": fakulte_id,
                    "fakulte": fakulte_adi,
                    "year": aday_yil,
                    "reason": result.get("error", "Kriterler hazir degil"),
                    "missing_criteria": result.get("missing_criteria", []) or [],
                    "missing_curricula": result.get("missing_curricula", []) or [],
                }
            )
        else:
            summary["ok"] = False
            summary["errors"].append(
                {
                    "fakulte_id": fakulte_id,
                    "fakulte": fakulte_adi,
                    "year": aday_yil,
                    "error": result.get("error", "Bilinmeyen hata"),
                }
            )
    return summary


def reset_future_curricula(db_path=None, base_year=2022):
    """
    Sadece base_year ve onceki yillari birakir.
    base_year sonrasi mufredat + havuz verilerini temizler.
    """
    result = {
        "ok": True,
        "base_year": int(base_year),
        "deleted_mufredat": 0,
        "deleted_mufredat_ders": 0,
        "deleted_havuz": 0,
        "normalized_curricula": 0,
    }

    resolved_db_path = resolve_sqlite_db_path(db_path)
    if not resolved_db_path.exists():
        result["ok"] = False
        result["error"] = f"DB bulunamadi: {resolved_db_path}"
        return result

    db_path = str(resolved_db_path)
    conn = None
    try:
        conn = get_raw_connection(db_path)
        cur = conn.cursor()
        result["normalized_curricula"] = _normalize_mufredat_faculty_ids(cur)

        cur.execute(
            "SELECT mufredat_id FROM mufredat WHERE akademik_yil > ?",
            (int(base_year),),
        )
        mids = [int(r[0]) for r in cur.fetchall() if r and r[0] is not None]

        if mids:
            placeholders = ",".join("?" for _ in mids)
            cur.execute(
                f"DELETE FROM mufredat_ders WHERE mufredat_id IN ({placeholders})",
                tuple(mids),
            )
            result["deleted_mufredat_ders"] = int(cur.rowcount or 0)

        cur.execute("DELETE FROM mufredat WHERE akademik_yil > ?", (int(base_year),))
        result["deleted_mufredat"] = int(cur.rowcount or 0)

        cur.execute("DELETE FROM havuz WHERE yil > ?", (int(base_year),))
        result["deleted_havuz"] = int(cur.rowcount or 0)

        conn.commit()
        return result
    except Exception as exc:
        if conn:
            conn.rollback()
        result["ok"] = False
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc()
        return result
    finally:
        if conn:
            conn.close()


def _ensure_curriculum_log_table(cur):
    """Mufredat uretim log tablosu yoksa olusturur."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS curriculum_generation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            generated_count INTEGER NOT NULL DEFAULT 0,
            skipped_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            rounds INTEGER NOT NULL DEFAULT 0,
            summary_text TEXT
        )
    """)


def _write_curriculum_generation_log(db_path, overall):
    """
    Pipeline sonucu ozetini kalici log tablosuna yazar.
    overall: generate_curricula_until_stable donus degeri (generated, skipped, errors, rounds).
    """
    resolved_db_path = resolve_sqlite_db_path(db_path)
    if not resolved_db_path.exists():
        return
    conn = None
    try:
        from datetime import datetime, timezone
        conn = get_raw_connection(str(resolved_db_path))
        cur = conn.cursor()
        _ensure_curriculum_log_table(cur)
        generated = overall.get("generated", []) or []
        skipped = overall.get("skipped", []) or []
        errors = overall.get("errors", []) or []
        rounds = len(overall.get("rounds", []) or [])
        summary_parts = []
        for g in generated[:20]:
            summary_parts.append(
                f"{g.get('fakulte', '?')} {g.get('year_from')}->{g.get('year_to')}"
            )
        for s in skipped[:10]:
            summary_parts.append(f"[Atlanan] {s.get('fakulte', '?')} {s.get('reason', '')}")
        for e in errors[:10]:
            summary_parts.append(f"[Hata] {e.get('fakulte', '?')} {e.get('error', '')}")
        summary_text = "\n".join(summary_parts) if summary_parts else "Yeni uretim yok."
        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            """
            INSERT INTO curriculum_generation_log
                (created_at, generated_count, skipped_count, error_count, rounds, summary_text)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (created_at, len(generated), len(skipped), len(errors), rounds, summary_text),
        )
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def generate_curricula_until_stable(db_path=None, donem="G", max_rounds=8):
    """
    Otomatik uretimi birden fazla tur calistirir.
    Ayni (fakulte, yil_from, yil_to) ciftleri tekrar etmeye basladiginda durur.
    """
    overall = {
        "ok": True,
        "rounds": [],
        "generated": [],
        "skipped": [],
        "errors": [],
    }
    seen_pairs = set()
    seen_skip_keys = set()
    seen_error_keys = set()

    for idx in range(int(max_rounds)):
        summary = auto_generate_next_year_curricula(db_path=db_path, donem=donem)
        overall["rounds"].append({"round": idx + 1, "summary": summary})

        gen_list = summary.get("generated", []) or []
        round_pairs = {
            (
                int(g.get("fakulte_id")),
                int(g.get("year_from")),
                int(g.get("year_to")),
            )
            for g in gen_list
            if g.get("fakulte_id") is not None and g.get("year_from") is not None and g.get("year_to") is not None
        }
        new_pairs = round_pairs - seen_pairs

        if not summary.get("ok"):
            overall["ok"] = False
        for err in (summary.get("errors", []) or []):
            key = (
                err.get("fakulte_id"),
                err.get("year"),
                err.get("error"),
            )
            if key not in seen_error_keys:
                seen_error_keys.add(key)
                overall["errors"].append(err)

        for sk in (summary.get("skipped", []) or []):
            key = (
                sk.get("fakulte_id"),
                sk.get("year"),
                sk.get("reason"),
            )
            if key not in seen_skip_keys:
                seen_skip_keys.add(key)
                overall["skipped"].append(sk)

        if gen_list:
            if new_pairs:
                for g in gen_list:
                    if g.get("fakulte_id") is None or g.get("year_from") is None or g.get("year_to") is None:
                        continue
                    pair = (
                        int(g.get("fakulte_id")),
                        int(g.get("year_from")),
                        int(g.get("year_to")),
                    )
                    if pair in new_pairs:
                        overall["generated"].append(g)
            else:
                # Ayni yil ciftleri tekrar olusuyorsa sonsuz donguyu engelle.
                break

        seen_pairs.update(round_pairs)

        # Yeni uretim yoksa dengeye ulasildi.
        if not gen_list:
            break

    _write_curriculum_generation_log(db_path, overall)
    return overall


def rebuild_school_curricula(db_path=None, base_year=2022, donem="G", max_rounds=8):
    """
    1) base_year sonrasi mufredatlari sifirlar
    2) kriterleri hazir olan yillari zincirleme otomatik yeniden uretir
    """
    reset = reset_future_curricula(db_path=db_path, base_year=base_year)
    if not reset.get("ok"):
        return {"ok": False, "reset": reset, "generation": None}

    generation = generate_curricula_until_stable(
        db_path=db_path,
        donem=donem,
        max_rounds=max_rounds,
    )
    return {
        "ok": bool(reset.get("ok")) and bool(generation.get("ok", True)),
        "reset": reset,
        "generation": generation,
    }


def rebuild_school_curricula_dual_semester(
    db_path=None,
    base_year=2022,
    max_rounds=8,
    block_size=4,
):
    """
    Production-grade dual semester wrapper.

    Ayrik Guz/Bahar pipeline'larini calistirir, ardindan 4+4 blok
    dengesini ve cross-semester kurallarini uygular.
    """
    from app.services.dual_semester import (
        rebuild_school_curricula_dual_semester as _impl,
    )

    return _impl(
        db_path=db_path,
        base_year=base_year,
        max_rounds=max_rounds,
        block_size=block_size,
    )


if __name__ == "__main__":
    run_automatic_scoring()
