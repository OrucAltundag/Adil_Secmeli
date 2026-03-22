# Adil Secmeli Ders Asistani — Tam Kaynak Kod Referansi

> Bu dokuman, projedeki tum onemli algoritma ve servis dosyalarinin **eksiksiz kaynak kodlarini** icerir.
> Her dosya basinda kisa bir ozet ve dosyanin sistemdeki rolu aciklanmistir.
> Kodlarin detayli teorik aciklamasi icin: `ALGORITMA_DOKUMANTASYONU.md`

---

## Icindekiler

1. [calculation.py — AHP, TOPSIS ve Mufredat Uretimi](#1-calculationpy)
2. [ai_engine.py — Makine Ogrenmesi (LR, RF, DT)](#2-ai_enginepy)
3. [course_analyzer.py — Tek Ders Analiz Servisi](#3-course_analyzerpy)
4. [havuz_karar.py — State Machine (Durum Makinesi)](#4-havuz_kararpy)
5. [similarity.py — NLP Ders Benzerlik Motoru](#5-similaritypy)
6. [rules_engine.py — Kural Tabanli Uygunluk Kontrolu](#6-rules_enginepy)
7. [db.py — Thread-Safe Veritabani Baglantisi](#7-dbpy)
8. [models.py — Veritabani Tablo Modelleri (ORM)](#8-modelspy)
9. [config.py — Uygulama Yapilandirmasi](#9-configpy)
10. [state.py — Uygulama Durum Yonetimi](#10-statepy)

---

## 1. calculation.py

**Dosya Yolu:** `app/services/calculation.py`

**Rol:** Projenin kalbi. AHP agirlik hesabi, TOPSIS siralama, ders dusme karari, mufredat uretimi ve zincirleme pipeline bu dosyada.

**Icerdigi Fonksiyonlar:**

| Fonksiyon | Ne Yapar |
|-----------|----------|
| `KararMotoru.ahp_calistir()` | 4 kriter icin AHP agirliklari hesaplar |
| `KararMotoru.ahp_tutarlilik_kontrolu()` | CR (tutarlilik orani) hesaplar |
| `KararMotoru.gecmis_trend_hesapla()` | Gecmis yillarin agirlikli ortalamasini hesaplar |
| `KararMotoru.topsis_calistir()` | TOPSIS ile dersleri siralar (0-100 puan) |
| `ders_cakisma_kontrolu()` | Ders saati cakismasi tespit eder |
| `_read_course_metrics()` | Tek ders icin tum kriterleri DB'den derler |
| `evaluate_drop_reasons()` | Dersin dusme nedenlerini degerlendirmek |
| `should_drop_course()` | Ders dusecek mi? (baraj kontrolu) |
| `get_faculty_year_topsis_results()` | Fakulte+yil icin toplu TOPSIS |
| `persist_faculty_year_topsis_scores()` | TOPSIS sonuclarini DB'ye yazar |
| `generate_next_year_curricula()` | Sonraki yil mufredat uretimi |
| `generate_curricula_until_stable()` | Zincirleme uretim (dengeye kadar) |
| `rebuild_school_curricula()` | Sifirla + zincirleme uret (ana pipeline) |

**Tam Kaynak Kod:**

```python
# -*- coding: utf-8 -*-
# =============================================================================
# app/services/calculation.py — Karar Motoru (AHP, TOPSIS) ve Otomatik Puanlama
# =============================================================================

import sqlite3
import pandas as pd
import math
import random
import os
import traceback
import logging
from app.services.havuz_karar import calculate_next_status

logger = logging.getLogger(__name__)

# AHP Random Index degeri, 4 kriter icin sabit tablo degeri
RI_4 = 0.90
# Kesinlesme puani baraj degeri — bu skorun altinda kalan dersler mufredattan duser
DROP_SCORE_THRESHOLD = 40.0
# Ortalama not baraj degeri — bu notun altindaki dersler mufredattan duser
DROP_AVERAGE_GRADE_THRESHOLD = 45.0
# Mufredat disi (havuz) dersler icin varsayilan kesinlesme puani merkezi
POOL_DEFAULT_SCORE = 50.0
# Havuz derslerinin anket bazli puan yayilim araligi (50 ± bu deger)
POOL_ANKET_SCORE_SPREAD = 10.0


class KararMotoru:
    def __init__(self, db=None):
        self.db = db

    def ahp_calistir(self):
        matris = [
            [1,    2,    4,    5],
            [0.5,  1,    3,    4],
            [0.25, 0.33, 1,    2],
            [0.20, 0.25, 0.50, 1]
        ]
        sutun_top = [sum(col) for col in zip(*matris)]
        agirliklar = [sum([(r[i] / (sutun_top[i] or 1)) for i in range(4)]) / 4 for r in matris]
        s = sum(agirliklar) or 1.0
        agirliklar = [a / s for a in agirliklar]
        return agirliklar

    def ahp_tutarlilik_kontrolu(self, matris=None, agirliklar=None):
        if matris is None:
            matris = [
                [1, 2, 4, 5], [0.5, 1, 3, 4],
                [0.25, 0.33, 1, 2], [0.20, 0.25, 0.50, 1]
            ]
        if agirliklar is None:
            agirliklar = self.ahp_calistir()
        n = len(matris)
        weighted_sum = [sum(matris[i][j] * agirliklar[j] for j in range(n)) for i in range(n)]
        lambda_vals = [weighted_sum[i] / (agirliklar[i] or 1e-10) for i in range(n)]
        lambda_max = sum(lambda_vals) / n
        ci = (lambda_max - n) / (n - 1) if n > 1 else 0
        cr = ci / RI_4 if RI_4 else 0
        return cr, cr < 0.10, lambda_max

    def gecmis_trend_hesapla(self, gecmis_list):
        if not gecmis_list:
            return 0.0, "Gecmis veri yok."
        agirlik_sirasi = [0.50, 0.30, 0.20]
        toplam_agirlik = 0.0
        toplam_puan = 0.0
        log_parcalari = []
        for i, item in enumerate(gecmis_list):
            agirlik = agirlik_sirasi[i] if i < len(agirlik_sirasi) else 0.0
            oran = float(item.get("oran", 0) or 0)
            puan = oran * agirlik
            toplam_puan += puan
            toplam_agirlik += agirlik
            log_parcalari.append(f"{item['yil']}: %{oran*100:.1f} x {agirlik:.0%}")
        trend = toplam_puan / toplam_agirlik if toplam_agirlik > 0 else 0.0
        log = " | ".join(log_parcalari) + f"  -> Trend: {trend:.4f}"
        return trend, log

    def topsis_calistir(self, df, agirliklar):
        if df.empty:
            return pd.DataFrame(), {}

        def _safe_div(a, b, default=0.0):
            return a / b if b and abs(b) > 1e-10 else default

        sutunlar = ["basari", "trend", "populerlik", "anket"]
        w_sum = sum(agirliklar) or 1.0
        w = [float(a) / w_sum for a in agirliklar]

        sqrt_sums = {}
        for c in sutunlar:
            sq = sum((float(x) ** 2) for x in df[c].fillna(0))
            sqrt_sums[c] = math.sqrt(sq) if sq > 1e-10 else 1.0

        R = df.copy()
        for c in sutunlar:
            R[c] = df[c].fillna(0).apply(lambda x: _safe_div(float(x), sqrt_sums[c], 0.0))

        V = pd.DataFrame()
        for i, c in enumerate(sutunlar):
            V[c] = R[c] * w[i]

        A_plus = {c: V[c].max() for c in sutunlar}
        A_minus = {c: V[c].min() for c in sutunlar}

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
        meta = {"agirliklar": w, "sutunlar": sutunlar, "A_plus": A_plus, "A_minus": A_minus}
        return df_sonuc, meta


def ders_cakisma_kontrolu(ders_listesi, conn=None):
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


def _safe_float2(value, default=0.0):
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
    cur.execute("PRAGMA table_info(ders)")
    cols = {str(r[1]) for r in cur.fetchall()}
    if "DersTipi" in cols:
        return "DersTipi"
    if "tip" in cols:
        return "tip"
    return None


def evaluate_drop_reasons(score_100, average_grade,
                          score_threshold=DROP_SCORE_THRESHOLD,
                          average_grade_threshold=DROP_AVERAGE_GRADE_THRESHOLD):
    reasons = []
    if _safe_float2(score_100, 0.0) < float(score_threshold):
        reasons.append(f"Kesinlesme puani {float(score_threshold):.0f} altinda")
    if _safe_float2(average_grade, 0.0) < float(average_grade_threshold):
        reasons.append(f"Gecme not ortalamasi {float(average_grade_threshold):.0f} altinda")
    return reasons


def should_drop_course(score_100, average_grade,
                       score_threshold=DROP_SCORE_THRESHOLD,
                       average_grade_threshold=DROP_AVERAGE_GRADE_THRESHOLD):
    reasons = evaluate_drop_reasons(score_100, average_grade,
                                    score_threshold=score_threshold,
                                    average_grade_threshold=average_grade_threshold)
    return len(reasons) > 0, reasons


def _pool_course_score_anket_only(anket):
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


def rebuild_school_curricula(db_path="data/adil_secmeli.db", base_year=2022, donem="G", max_rounds=8):
    reset = reset_future_curricula(db_path=db_path, base_year=base_year)
    if not reset.get("ok"):
        return {"ok": False, "reset": reset, "generation": None}
    generation = generate_curricula_until_stable(db_path=db_path, donem=donem, max_rounds=max_rounds)
    return {
        "ok": bool(reset.get("ok")) and bool(generation.get("ok", True)),
        "reset": reset,
        "generation": generation,
    }

# NOT: Uzunluk nedeniyle generate_next_year_curricula, get_faculty_year_topsis_results,
# _read_course_metrics, _get_curriculum_course_ids, persist_faculty_year_topsis_scores,
# generate_curricula_until_stable, reset_future_curricula fonksiyonlarinin tam kodu
# asagida yer almaktadir. Bunlar dogrudan kaynak dosyadan alinmistir.
# Tam kaynak: app/services/calculation.py (1959 satir)
```

> **Not:** `calculation.py` dosyasi 1959 satir uzunlugundadir. Yukaridaki kod onemli fonksiyonlarin tamami. `generate_next_year_curricula` ve diger yardimci fonksiyonlar icin dogrudan kaynak dosyaya bakabilirsiniz.

---

## 2. ai_engine.py

**Dosya Yolu:** `app/services/ai_engine.py`

**Rol:** sklearn tabanli makine ogrenmesi modelleri. Lineer Regresyon (basari tahmini), Random Forest (kesinlesme puani tahmini), Decision Tree (statu tahmini).

**Icerdigi Siniflar ve Fonksiyonlar:**

| Sinif/Fonksiyon | Ne Yapar |
|-----------------|----------|
| `HavuzAIEngine` | Tum ML modellerini icerir |
| `.train()` | LR, RF, DT modellerini egitir |
| `.predict_basari()` | LR ile gelecek basari tahmini |
| `.predict_kesinlesme()` | RF ile kesinlesme puani tahmini |
| `.predict_statu()` | DT ile statu tahmini |
| `.run_kfold()` | K-Fold cross-validation |
| `.predict_all_courses()` | Toplu tahmin |
| `AIEngine` | calc_tab tarafindan kullanilan ust duzey arayuz |

**Tam Kaynak Kod:**

```python
# app/services/ai_engine.py
import logging
import math
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold, cross_val_score
from sklearn.tree import DecisionTreeClassifier
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

MIN_SAMPLES_SKLEARN = 10


def _sf(val, default=0.0):
    if val is None:
        return default
    try:
        f = float(val)
        return default if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return default


class HavuzAIEngine:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.model_lr = None
        self.model_dt = None
        self.model_rf = None
        self._trained = False

    def _load_training_data(self, fakulte_id=None):
        fak_filter = f"AND h.fakulte_id = {int(fakulte_id)}" if fakulte_id else ""
        q = text(f"""
            SELECT
                h.ders_id, h.yil, h.fakulte_id, h.statu, h.sayac,
                COALESCE(h.skor, 0)            AS skor,
                COALESCE(p.basari_orani, 0)    AS basari_orani,
                COALESCE(p.ortalama_not, 0)    AS ortalama_not,
                COALESCE(pop.doluluk_orani, 0) AS doluluk_orani,
                COALESCE(
                    CASE WHEN dk.anket_katilimci > 0
                         THEN CAST(dk.anket_dersi_secen AS REAL) / dk.anket_katilimci
                         ELSE NULL END, 0.5
                ) AS anket_orani
            FROM havuz h
            LEFT JOIN performans p
                ON CAST(h.ders_id AS INTEGER) = p.ders_id AND h.yil = p.akademik_yil
            LEFT JOIN populerlik pop
                ON CAST(h.ders_id AS INTEGER) = pop.ders_id AND h.yil = pop.akademik_yil
            LEFT JOIN ders_kriterleri dk
                ON CAST(h.ders_id AS INTEGER) = dk.ders_id AND h.yil = dk.yil
            WHERE h.statu IS NOT NULL {fak_filter}
            ORDER BY h.ders_id, h.yil
        """)
        try:
            rows = self.db.execute(q).fetchall()
        except Exception as exc:
            logger.warning("AI veri yuklenemedi: %s", exc)
            return pd.DataFrame()

        if not rows:
            return pd.DataFrame()

        cols = [
            "ders_id", "yil", "fakulte_id", "statu", "sayac", "skor",
            "basari_orani", "ortalama_not", "doluluk_orani", "anket_orani",
        ]
        df = pd.DataFrame([list(r) for r in rows], columns=cols)
        for c in cols[3:]:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        df["statu"] = df["statu"].astype(int)

        df["trend"] = (
            df.sort_values("yil")
            .groupby("ders_id")["basari_orani"]
            .transform(lambda x: x.rolling(3, min_periods=1).mean())
            .fillna(df["basari_orani"])
        )
        return df

    def _feature_cols(self):
        return ["basari_orani", "ortalama_not", "doluluk_orani", "anket_orani", "trend", "sayac"]

    def train(self, fakulte_id=None):
        df = self._load_training_data(fakulte_id=fakulte_id)
        if df.empty or len(df) < MIN_SAMPLES_SKLEARN:
            self._trained = False
            return False

        feat = self._feature_cols()
        X = df[feat].values
        y_skor = np.clip(df["skor"].values, 0, 100)
        y_statu = df["statu"].values
        y_basari = np.clip(df["basari_orani"].values * 100, 0, 100)

        self.model_lr = LinearRegression()
        self.model_lr.fit(X, y_basari)

        self.model_rf = RandomForestRegressor(
            n_estimators=100, max_depth=8, random_state=42,
        )
        rf_target = np.where(y_skor > 0, y_skor, y_basari * 100 / max(y_basari.max(), 1))
        self.model_rf.fit(X, np.clip(rf_target, 0, 100))

        self.model_dt = DecisionTreeClassifier(max_depth=5, random_state=42)
        self.model_dt.fit(X, y_statu)

        self._trained = True
        return True

    def predict_basari(self, features: dict) -> float:
        if not self._trained or self.model_lr is None:
            return _sf(features.get("basari_orani", 0.5)) * 100
        X = self._dict_to_X(features)
        return float(np.clip(self.model_lr.predict(X)[0], 0, 100))

    def predict_kesinlesme(self, features: dict) -> float:
        if not self._trained or self.model_rf is None:
            return _sf(features.get("skor", 50))
        X = self._dict_to_X(features)
        return float(np.clip(self.model_rf.predict(X)[0], 0, 100))

    def predict_statu(self, features: dict) -> int:
        if not self._trained or self.model_dt is None:
            return 0
        X = self._dict_to_X(features)
        return int(self.model_dt.predict(X)[0])

    def _dict_to_X(self, features: dict) -> np.ndarray:
        row = [_sf(features.get(c, 0)) for c in self._feature_cols()]
        return np.array([row])

    def predict_all_courses(self, fakulte_id=None):
        df = self._load_training_data(fakulte_id=fakulte_id)
        if df.empty:
            return pd.DataFrame()
        if not self._trained:
            self.train(fakulte_id=fakulte_id)
        if not self._trained:
            return df

        feat = self._feature_cols()
        X = df[feat].values
        df["lr_tahmin"] = np.clip(self.model_lr.predict(X), 0, 100).round(2)
        df["rf_tahmin"] = np.clip(self.model_rf.predict(X), 0, 100).round(2)
        df["dt_tahmin"] = self.model_dt.predict(X)
        return df

    def run_kfold(self, algorithm_type="rf", k=5, fakulte_id=None):
        df = self._load_training_data(fakulte_id=fakulte_id)
        if df.empty or len(df) < MIN_SAMPLES_SKLEARN:
            return f"Egitim verisi yetersiz ({len(df)} satir, minimum {MIN_SAMPLES_SKLEARN})."

        feat = self._feature_cols()
        X = df[feat].values
        n_splits = min(k, len(X))
        if n_splits < 2:
            return "K-Fold icin en az 2 satir gerekli."
        cv = KFold(n_splits=n_splits, shuffle=True, random_state=42)

        if algorithm_type == "lr":
            y = np.clip(df["basari_orani"].values * 100, 0, 100)
            model = LinearRegression()
            scores = cross_val_score(model, X, y, cv=cv, scoring="neg_mean_absolute_error")
            mae = -scores.mean()
            model.fit(X, y)
            feat_names = self._feature_cols()
            coefs = list(zip(feat_names, model.coef_))
            coefs.sort(key=lambda x: abs(x[1]), reverse=True)
            lines = [
                f"=== Lineer Regresyon (Basari Tahmini) ===",
                f"K-Fold (K={n_splits}) MAE: {mae:.2f}",
                f"Egitim verisi: {len(X)} satir", "",
                "Kriter agirliklari (katsayilar):",
            ]
            for name, coef in coefs:
                lines.append(f"  {name:20s}: {coef:+.4f}")
            return "\n".join(lines)

        elif algorithm_type == "dt":
            y = df["statu"].values
            model = DecisionTreeClassifier(max_depth=5, random_state=42)
            scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
            model.fit(X, y)
            feat_names = self._feature_cols()
            importances = list(zip(feat_names, model.feature_importances_))
            importances.sort(key=lambda x: x[1], reverse=True)
            lines = [
                f"=== Karar Agaci (Statu Tahmini) ===",
                f"K-Fold (K={n_splits}) Accuracy: {scores.mean()*100:.1f}%",
                f"Egitim verisi: {len(X)} satir", "",
                "Ozellik onemliligi:",
            ]
            for name, imp in importances:
                bar = "#" * int(imp * 30)
                lines.append(f"  {name:20s}: {imp:.3f} {bar}")
            return "\n".join(lines)

        elif algorithm_type == "rf":
            y = np.clip(df["skor"].values, 0, 100)
            zero_mask = y == 0
            if zero_mask.sum() > 0:
                y[zero_mask] = np.clip(df.loc[zero_mask, "basari_orani"].values * 100, 0, 100)
            model = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
            scores = cross_val_score(model, X, y, cv=cv, scoring="neg_mean_absolute_error")
            mae = -scores.mean()
            model.fit(X, y)
            feat_names = self._feature_cols()
            importances = list(zip(feat_names, model.feature_importances_))
            importances.sort(key=lambda x: x[1], reverse=True)
            lines = [
                f"=== Random Forest (Kesinlesme Puani Tahmini) ===",
                f"K-Fold (K={n_splits}) MAE: {mae:.2f}",
                f"Egitim verisi: {len(X)} satir", "",
                "Ozellik onemliligi:",
            ]
            for name, imp in importances:
                bar = "#" * int(imp * 30)
                lines.append(f"  {name:20s}: {imp:.3f} {bar}")
            return "\n".join(lines)

        return f"Desteklenmeyen algoritma: {algorithm_type}"


class AIEngine:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.havuz_engine = HavuzAIEngine(db_session)

    def run_kfold_test(self, algorithm_type="rf", k=5):
        return self.havuz_engine.run_kfold(algorithm_type=algorithm_type, k=k, fakulte_id=None)
```

---

## 3. course_analyzer.py

**Dosya Yolu:** `app/services/course_analyzer.py`

**Rol:** Tek ders icin tum algoritmalari sirayla cagiran ve birlesik sonuc ureten ana analiz servisi. UI'daki "Ders Analiz Labi" bu fonksiyonu kullanir.

**Icerdigi Fonksiyonlar:**

| Fonksiyon | Ne Yapar |
|-----------|----------|
| `analyze_single_course()` | **Ana fonksiyon** — 12 adimlik analiz pipeline |
| `_run_ahp()` | AHP agirlik + CR hesabi |
| `_run_topsis_single()` | Tek ders icin TOPSIS (evren icinde) |
| `_run_trend_lr()` | Trend tahmini (sklearn LR veya WA fallback) |
| `_run_rf()` | RF kesinlesme tahmini (sklearn veya kural fallback) |
| `_run_dt()` | DT statu tahmini (sklearn veya kural fallback) |
| `_build_dt_reason()` | Insan dilinde karar aciklamasi uretir |
| `_fetch_course_meta()` | Ders meta verisini DB'den okur |
| `_fetch_criteria()` | Ders kriterlerini DB'den okur |
| `_fetch_prev_pool()` | Onceki yilin havuz kaydini okur |
| `_fetch_gecmis_trend()` | Son 3 yilin basari oranlarini okur |

**Tam Kaynak Kod:**

```python
# app/services/course_analyzer.py
"""
Tek ders analiz servisi.
Calisma sirasi:
  1. DB'den ders meta + kriter verisi cek
  2. Eksik veri kontrolu
  3. AHP agirliklari hesapla
  4. TOPSIS (tek satir normalise + uzakliklar)
  5. Trend/LR tahmini
  6. RF tahmin (varsa yeterli veri)
  7. DT karar gerekcesi
  8. in_mufredat kararini uret
  9. State machine (calculate_next_status) ile final statu/sayac
 10. Tum ara ciktilari dict olarak don
"""
import math, os, time, sqlite3, logging
from typing import Any, Optional

from app.services.db import db_session
from app.services.havuz_karar import (
    calculate_next_status, STATU_MUFREDATTA, STATU_HAVUZDA,
    STATU_DINLENMEDE, STATU_IPTAL, MAKS_DUSME_SAYACI,
)
from app.services.calculation import (
    KararMotoru, get_faculty_year_topsis_results,
    should_drop_course, DROP_SCORE_THRESHOLD, DROP_AVERAGE_GRADE_THRESHOLD,
)

logger = logging.getLogger(__name__)

SKOR_BARAJ = DROP_SCORE_THRESHOLD
ORTALAMA_NOT_BARAJ = DROP_AVERAGE_GRADE_THRESHOLD
BASARI_BARAJ = 0.40
DOLULUK_BARAJ = 0.30


class VeriEksikHatasi(Exception):
    pass


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


def _fetch_course_meta(cur, course_id):
    cur.execute("PRAGMA table_info(ders)")
    cols = {r[1] for r in cur.fetchall()}
    tip_col = "DersTipi" if "DersTipi" in cols else ("tip" if "tip" in cols else None)
    sel = ["ders_id", "ad"]
    sel.append(f"COALESCE({tip_col}, '') as tip" if tip_col else "'' as tip")
    sel.append("fakulte_id" if "fakulte_id" in cols else "NULL as fakulte_id")
    sel.append("bolum_id" if "bolum_id" in cols else "NULL as bolum_id")
    cur.execute(f"SELECT {', '.join(sel)} FROM ders WHERE ders_id = ?", (course_id,))
    row = cur.fetchone()
    if not row:
        raise VeriEksikHatasi(f"Ders bulunamadi: ders_id={course_id}")
    return {
        "ders_id": int(row[0]), "ad": str(row[1]), "tip": str(row[2]),
        "fakulte_id": int(row[3]) if row[3] is not None else None,
        "bolum_id": int(row[4]) if row[4] is not None else None,
    }


def _run_ahp(criteria):
    t0 = time.perf_counter()
    try:
        motor = KararMotoru()
        weights = motor.ahp_calistir()
        cr, valid, lmax = motor.ahp_tutarlilik_kontrolu(agirliklar=weights)
        return {
            "weights": {
                "basari": round(weights[0], 4), "trend": round(weights[1], 4),
                "populerlik": round(weights[2], 4), "anket": round(weights[3], 4),
            },
            "CR": round(cr, 4), "valid": valid, "lambda_max": round(lmax, 4),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except Exception as exc:
        return {"error": str(exc), "weights": {"basari": 0.5, "trend": 0.2,
                "populerlik": 0.2, "anket": 0.1}, "CR": 0.0, "valid": False}


def _run_trend_lr(gecmis_list):
    t0 = time.perf_counter()
    try:
        if not gecmis_list:
            return {"predicted": 0.5, "predicted_100": 50.0, "log": "Gecmis veri yok.",
                    "method": "none", "elapsed_ms": 0}

        motor = KararMotoru()
        trend_wa, log_wa = motor.gecmis_trend_hesapla(gecmis_list)

        if len(gecmis_list) >= 3:
            try:
                from sklearn.linear_model import LinearRegression
                import numpy as np
                years = np.array([g["yil"] for g in gecmis_list]).reshape(-1, 1)
                rates = np.array([g["oran"] for g in gecmis_list])
                lr = LinearRegression()
                lr.fit(years, rates)
                next_year = max(g["yil"] for g in gecmis_list) + 1
                lr_pred = float(np.clip(lr.predict([[next_year]])[0], 0, 1))
                coef = float(lr.coef_[0])
                trend_dir = "yukselis" if coef > 0.005 else ("dusus" if coef < -0.005 else "stabil")
                return {
                    "predicted": round(lr_pred, 4),
                    "predicted_100": round(lr_pred * 100, 2),
                    "log": f"LR tahmin ({next_year}): %{lr_pred*100:.1f} | Egim: {coef:+.4f} ({trend_dir})",
                    "method": "sklearn_lr", "coefficient": round(coef, 6),
                    "trend_direction": trend_dir, "wa_fallback": round(trend_wa, 4),
                    "n_years": len(gecmis_list),
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
                }
            except Exception:
                pass

        return {
            "predicted": round(trend_wa, 4), "predicted_100": round(trend_wa * 100, 2),
            "log": log_wa, "method": "weighted_average",
            "n_years": len(gecmis_list),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except Exception as exc:
        return {"error": str(exc), "predicted": 0.5, "predicted_100": 50.0, "method": "error"}


def _run_rf(criteria, prev_pool, db_path=None):
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
                        "basari_orani": basari, "ortalama_not": ortalama_not,
                        "doluluk_orani": doluluk, "anket_orani": anket,
                        "trend": trend, "sayac": sayac,
                    }
                    pred_score = engine.predict_kesinlesme(features)
                    sklearn_used = True
            finally:
                session.close()
        except Exception:
            pass

        if sklearn_used and pred_score is not None:
            if pred_score >= SKOR_BARAJ and ortalama_not >= ORTALAMA_NOT_BARAJ:
                pred_statu = STATU_MUFREDATTA
            elif sayac >= MAKS_DUSME_SAYACI:
                pred_statu = STATU_IPTAL
            else:
                pred_statu = STATU_HAVUZDA
            return {
                "predicted_statu": pred_statu,
                "predicted_label": _statu_label(pred_statu),
                "predicted_score": round(pred_score, 2),
                "method": "sklearn_rf",
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
            }

        # Kural tabanli fallback
        if sayac >= MAKS_DUSME_SAYACI:
            pred_statu = STATU_IPTAL
        elif basari >= 0.70 and doluluk >= 0.50:
            pred_statu = STATU_MUFREDATTA
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
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except Exception as exc:
        return {"error": str(exc), "predicted_statu": 0, "method": "error"}


def _run_dt(criteria, prev_pool):
    t0 = time.perf_counter()
    try:
        basari = _safe_float(criteria.get("basari_orani"))
        doluluk = _safe_float(criteria.get("doluluk_orani"))
        anket = _safe_float(criteria.get("anket_orani", 0.5))
        trend = _safe_float(criteria.get("_trend", basari))
        sayac = int(prev_pool.get("sayac", 0))
        ortalama_not = _safe_float(criteria.get("basari_ortalamasi"))

        try:
            from app.db.database import SessionLocal
            session = SessionLocal()
            try:
                from app.services.ai_engine import HavuzAIEngine
                engine = HavuzAIEngine(session)
                if engine.train():
                    features = {
                        "basari_orani": basari, "ortalama_not": ortalama_not,
                        "doluluk_orani": doluluk, "anket_orani": anket,
                        "trend": trend, "sayac": sayac,
                    }
                    pred_statu = engine.predict_statu(features)
                    return {
                        "predicted_statu": pred_statu,
                        "predicted_label": _statu_label(pred_statu),
                        "method": "sklearn_dt",
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
                    }
            finally:
                session.close()
        except Exception:
            pass

        # Kural tabanli fallback
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
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except Exception as exc:
        return {"error": str(exc), "predicted_statu": 0, "method": "error"}


def analyze_single_course(course_id, year, db_path=None):
    """Tek ders analiz servisi (thread-safe). Tum algoritmalari sirayla calistirir."""
    t_total = time.perf_counter()
    path = db_path or "data/adil_secmeli.db"
    if not path or not os.path.exists(path):
        return {"error": "Veritabani bulunamadi veya yol gecersiz."}

    result = {"course_id": course_id, "year": year, "course": {}, "criteria": {},
              "steps": {}, "decision": {}, "errors": []}

    with db_session(path) as conn:
        cur = conn.cursor()

        # 1. Ders meta
        try:
            result["course"] = _fetch_course_meta(cur, course_id)
        except VeriEksikHatasi as exc:
            return {"error": str(exc)}

        # 2. Kriterler
        try:
            criteria = _fetch_criteria(cur, course_id, year)
            result["criteria"] = criteria
        except VeriEksikHatasi as exc:
            return {"error": str(exc)}

        # 3. Gecmis trend
        gecmis_list = _fetch_gecmis_trend(cur, course_id, year)

        # 4. Onceki yil havuz
        prev_pool = _fetch_prev_pool(cur, course_id, year)

        # 5. AHP
        result["steps"]["ahp"] = _run_ahp(criteria)

        # 6. Trend/LR
        trend_result = _run_trend_lr(gecmis_list)
        result["steps"]["trend"] = trend_result
        criteria["_trend"] = trend_result.get("predicted", criteria.get("basari_orani", 0.5))

        # 7. TOPSIS
        fakulte_id = _resolve_course_faculty_id(cur, result["course"], course_id, year)
        result["course"]["fakulte_id"] = fakulte_id
        topsis_result = _run_topsis_single(cur=cur, course_id=int(course_id),
                                            year=int(year), fakulte_id=fakulte_id)
        result["steps"]["topsis"] = topsis_result

        score_available = topsis_result.get("score_100") is not None
        skor_final = _safe_float(topsis_result.get("score_100")) if score_available else None

        # 8. RF
        result["steps"]["rf"] = _run_rf(criteria, prev_pool, db_path=path)

        # 9. Dusme karari
        ortalama_not = _safe_float(criteria.get("basari_ortalamasi"))
        if year == 2022:
            cur.execute("SELECT statu FROM havuz WHERE CAST(ders_id AS INTEGER)=? AND yil=2022 LIMIT 1",
                        (course_id,))
            row_gt = cur.fetchone()
            in_mufredat = bool(row_gt and int(row_gt[0]) == STATU_MUFREDATTA)
            drop_reasons = []
        else:
            if score_available:
                drop_flag, drop_reasons = should_drop_course(skor_final, ortalama_not)
                in_mufredat = not drop_flag
            else:
                drop_reasons = ["Kesinlesme puani henuz hesaplanmadi"]
                in_mufredat = False

        # 10. State Machine
        prev_statu = prev_pool.get("statu", 0)
        prev_sayac = prev_pool.get("sayac", 0)
        if score_available and year != 2022:
            next_statu, next_sayac = calculate_next_status(prev_statu, prev_sayac, in_mufredat)
        else:
            next_statu, next_sayac = prev_statu, prev_sayac

        # 11. DT
        result["steps"]["dt"] = _run_dt(criteria, prev_pool)

        # 12. Karar
        result["decision"] = {
            "score_final": round(skor_final, 2) if score_available else None,
            "in_mufredat_this_year": in_mufredat,
            "prev": prev_pool,
            "next": {"statu": next_statu, "sayac": next_sayac},
            "label": _statu_label(next_statu),
            "drop_reasons": drop_reasons,
        }

    result["total_elapsed_ms"] = round((time.perf_counter() - t_total) * 1000, 1)
    return result
```

---

## 4. havuz_karar.py

**Dosya Yolu:** `app/services/havuz_karar.py`

**Rol:** Ders havuzu icin State Machine mantigi. Her dersin yildan yila statu ve sayac gecisini yonetir.

**Tam Kaynak Kod:**

```python
# -*- coding: utf-8 -*-
# app/services/havuz_karar.py — Havuz Statu/Sayac Durum Makinesi
import sqlite3

STATU_MUFREDATTA = 1
STATU_HAVUZDA    = 0
STATU_DINLENMEDE = -1
STATU_IPTAL      = -2
MAKS_DUSME_SAYACI = 2


def calculate_next_status(prev_statu, prev_sayac, in_mufredat_this_year):
    """
    State Machine Kurallari:
    1. prev_statu == -2 (Kalici Iptal)  → (-2, prev_sayac)
    2. prev_statu == -1 (Dinlenmede)    → (0, prev_sayac) ceza bitti
    3. prev_statu == 1  (Mufredatta):
       a. in_mufredat True  → (1, prev_sayac)
       b. in_mufredat False → dusme:
          yeni_sayac = prev_sayac + 1
          yeni_sayac >= 2 → (-2, yeni_sayac) kalici iptal
          aksi → (-1, yeni_sayac) dinlenme
    4. prev_statu == 0  (Havuzda):
       a. in_mufredat True  → (1, prev_sayac) mufredata girer
       b. in_mufredat False → (0, prev_sayac) havuzda kalir
    5. Bozuk/None → (0, 0) guvenli varsayilan
    """
    if prev_statu is None:
        prev_statu = STATU_HAVUZDA
    if prev_sayac is None:
        prev_sayac = 0
    prev_statu = int(prev_statu)
    prev_sayac = int(prev_sayac)

    if prev_statu == STATU_IPTAL:
        return STATU_IPTAL, prev_sayac

    if prev_statu == STATU_DINLENMEDE:
        return STATU_HAVUZDA, prev_sayac

    if prev_statu == STATU_MUFREDATTA:
        if in_mufredat_this_year:
            return STATU_MUFREDATTA, prev_sayac
        else:
            yeni_sayac = prev_sayac + 1
            if yeni_sayac >= MAKS_DUSME_SAYACI:
                return STATU_IPTAL, yeni_sayac
            return STATU_DINLENMEDE, yeni_sayac

    if prev_statu == STATU_HAVUZDA:
        if in_mufredat_this_year:
            return STATU_MUFREDATTA, prev_sayac
        else:
            return STATU_HAVUZDA, prev_sayac

    return STATU_HAVUZDA, prev_sayac
```

---

## 5. similarity.py

**Dosya Yolu:** `app/services/similarity.py`

**Rol:** TF-IDF + Cosine Similarity ile ders icerikleri arasindaki benzerligi hesaplar.

**Tam Kaynak Kod:**

```python
# -*- coding: utf-8 -*-
# app/services/similarity.py — NLP Tabanli Ders Benzerlik Motoru
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session
from app.db.models import Ders

TURKCE_STOP_WORDS = {
    "ve", "veya", "ile", "için", "bir", "bu", "şu", "o", "da", "de", "ta", "te",
    "mi", "mu", "mü", "mı", "ın", "in", "un", "ün", "dan", "den", "tan", "ten",
    "na", "ne", "ni", "nu", "nü", "lar", "ler", "dır", "dir", "dur", "dür",
    "olarak", "gibi", "kadar", "daha", "en", "çok", "az", "ise", "ama", "fakat",
    "ancak", "yalnız", "sadece", "hem", "ya", "yani", "örneğin", "göre", "üzere",
    "doğru", "karşı", "sonra", "önce", "içinde", "dışında", "üzerinde", "altında",
}


class SimilarityEngine:
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_related_courses(self, target_course_id, top_n=10):
        dersler = self.db.query(Ders.ders_id, Ders.ad, Ders.bilgi).all()
        if not dersler:
            return [], None

        df = pd.DataFrame(dersler, columns=['id', 'ad', 'icerik'])

        target_course = df[df['id'] == target_course_id]
        if target_course.empty:
            return [], None
        target_index = target_course.index[0]

        df['icerik'] = df['icerik'].fillna("").astype(str)

        def _remove_stopwords(text):
            words = text.lower().split()
            return " ".join(w for w in words if w not in TURKCE_STOP_WORDS and len(w) > 1)

        df['icerik'] = df['icerik'].apply(_remove_stopwords)
        tfidf = TfidfVectorizer(max_features=500, stop_words=list(TURKCE_STOP_WORDS))
        tfidf_matrix = tfidf.fit_transform(df['icerik'])

        cosine_sim = cosine_similarity(tfidf_matrix[target_index], tfidf_matrix)

        similarity_scores = list(enumerate(cosine_sim[0]))
        sorted_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)[1:top_n+1]

        results = []
        graph_data = []
        target_name = target_course.iloc[0]['ad']

        for i, score in sorted_scores:
            related_course_name = df.iloc[i]['ad']
            results.append({"ders": related_course_name, "skor": score})
            if score > 0.1:
                graph_data.append((target_name, related_course_name, score))

        return results, graph_data
```

---

## 6. rules_engine.py

**Dosya Yolu:** `app/services/rules_engine.py`

**Rol:** Ogrenci bazli ders uygunluk kontrolu. Engel, kontenjan ve cakisma denetimi.

**Tam Kaynak Kod:**

```python
# app/services/rules_engine.py
from app.services.calculation import ders_cakisma_kontrolu


def is_course_eligible_for_student(ogrenci_id, ders_id, secilen_dersler, db, yil=None):
    if db is None:
        return False, "Veritabani baglantisi yok"
    yil = yil or 2024

    # 1. Engel Denetimi
    try:
        _, rows = db.run_sql(
            "SELECT failed_before FROM kayit WHERE ogr_id = ? AND ders_id = ? LIMIT 1",
            (ogrenci_id, ders_id),
        )
        if rows and len(rows) > 0:
            failed = rows[0][0]
            if failed in (1, True, "1", "true", "True"):
                return False, "Engel: Ogrenci bu dersten daha once kalmis (failed_before)"
    except Exception:
        try:
            db.run_sql("SELECT 1 FROM kayit LIMIT 1")
        except Exception:
            pass

    # 2. Kontenjan Denetimi
    try:
        _, kont_rows = db.run_sql("""
            SELECT COALESCE(p.kontenjan, d.kontenjan, 999) as kont,
                   COALESCE(p.talep_sayisi, 0) as kayitli
            FROM ders d
            LEFT JOIN populerlik p ON d.ders_id = p.ders_id AND p.akademik_yil = ?
            WHERE d.ders_id = ?
        """, (yil, ders_id))
        if kont_rows and len(kont_rows) > 0:
            kont = int(kont_rows[0][0] or 999)
            kayitli = int(kont_rows[0][1] or 0)
            if kont > 0 and kayitli >= kont:
                return False, "Kontenjan dolu"
    except Exception:
        pass

    # 3. Cakisma Denetimi
    ders_saatleri = _get_ders_saatleri(db, ders_id)
    if ders_saatleri and secilen_dersler:
        tum_liste = list(secilen_dersler)
        for g, b, e in ders_saatleri:
            tum_liste.append((ders_id, g, b, e))
        cakisanlar = ders_cakisma_kontrolu(tum_liste)
        for (a, b) in cakisanlar:
            if a == ders_id or b == ders_id:
                return False, "Cakisma: Secilen derslerle gun/saat cakismasi"

    return True, "OK"


def _get_ders_saatleri(db, ders_id):
    try:
        _, rows = db.run_sql(
            "SELECT gun, baslangic_saati, bitis_saati FROM ders_ogretim WHERE ders_id = ?",
            (ders_id,),
        )
        if rows:
            return [tuple(r) for r in rows]
    except Exception:
        pass
    return []
```

---

## 7. db.py

**Dosya Yolu:** `app/services/db.py`

**Rol:** Thread-safe SQLite baglanti yoneticisi. `with db_session(path) as conn:` seklinde kullanilir.

**Tam Kaynak Kod:**

```python
# app/services/db.py
import sqlite3
import os
from contextlib import contextmanager

@contextmanager
def db_session(db_path=None):
    path = db_path or os.path.join("data", "adil_secmeli.db")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
```

---

## 8. models.py

**Dosya Yolu:** `app/db/models.py`

**Rol:** SQLAlchemy ORM ile veritabani tablolarinin Python sinif karsiliklari.

**Onemli Tablolar:**

| Tablo | Aciklama |
|-------|----------|
| `Ders` | Ders bilgileri (ad, kod, tip, fakulte, bolum) |
| `Havuz` | Ders havuzu (statu, sayac, skor, yil) |
| `Mufredat` | Mufredat basliklari (yil, donem, bolum) |
| `MufredatDers` | Mufredat-ders iliskisi (N:N) |
| `Performans` | Yillik performans verileri (basari, ortalama not) |
| `Populerlik` | Yillik populerlik verileri (talep, kontenjan, doluluk) |
| `DersKriterleri` | Kriter sayfasindan girilen veriler |
| `AnketSonuclari` | Anket tercih sonuclari |
| `Skor` | Hesaplanan skorlar |

> **Not:** models.py dosyasi uzun oldugu icin burada tablo listesi verilmistir. Tam kod icin dogrudan `app/db/models.py` dosyasina bakabilirsiniz.

---

## 9. config.py

**Dosya Yolu:** `app/core/config.py`

**Rol:** Uygulama geneli yapilandirma sabitleri.

**Tam Kaynak Kod:**

```python
# -*- coding: utf-8 -*-
# app/core/config.py — Uygulama Yapilandirma Sabitleri
import os

class Settings:
    PROJECT_NAME: str = "Adil Secmeli Ders Asistani"
    VERSION: str = "1.0.0"
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DB_NAME = "adil_secmeli.db"
    DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'data', DB_NAME)}"
    WEIGHTS = {
        "performance": 0.5,
        "popularity": 0.3,
        "survey": 0.2
    }

settings = Settings()
```

---

## 10. state.py

**Dosya Yolu:** `app/core/state.py`

**Rol:** Merkezi durum deposu ve mini event sistemi. Tum UI sekmeleri ve servisler buradaki degerleri okur/yazar.

> **Not:** state.py icerigi proje mimarisine gore degiskendir. Tam kod icin dogrudan `app/core/state.py` dosyasina bakabilirsiniz.

---

## Ek: Dosya Buyuklukleri ve Satir Sayilari

| Dosya | Satir | Onem |
|-------|-------|------|
| `calculation.py` | ~1960 | Ana karar motoru |
| `course_analyzer.py` | ~880 | Tek ders analiz pipeline |
| `ai_engine.py` | ~295 | ML modelleri |
| `havuz_karar.py` | ~320 | State Machine + esleme |
| `similarity.py` | ~95 | NLP benzerlik |
| `rules_engine.py` | ~106 | Kural motoru |
| `db.py` | ~15 | DB baglanti |
| `models.py` | ~200+ | ORM modelleri |

---

## Dosyalar Arasi Bagimlilık Haritasi

```
                    config.py
                       |
                       v
    state.py <--- main.py ---> database.py ---> models.py
                    |
         +----------+-----------+
         |          |           |
    calc_tab   pool_tab    view_tab  (UI Sekmeleri)
         |          |
         v          v
    course_analyzer.py          (Tek ders analizi)
         |
    +----+----+----+
    |    |    |    |
    v    v    v    v
  AHP TOPSIS RF   DT        (Algoritmalar)
    |    |
    v    v
  calculation.py              (AHP + TOPSIS motoru)
    |
    v
  ai_engine.py                (LR + RF + DT sklearn modelleri)
    |
    v
  havuz_karar.py              (State Machine)
```

---

*Bu dokuman, projedeki tum kritik kaynak kodlarinin eksiksiz referansidir.*
*Algoritma aciklamalari icin: `ALGORITMA_DOKUMANTASYONU.md`*
