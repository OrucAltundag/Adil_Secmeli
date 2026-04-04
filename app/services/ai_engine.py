# app/services/ai_engine.py
# Makine ogrenmesi: performans + populerlik + havuz verileri uzerinde
# LR: Gelecek yil basari tahmini
# RF: Kesinlesme Puani tahmini (0-100)
# DT: Statu karari (mufredatta / havuzda / dinlenmede)

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

# sklearn modelleri icin minimum egitim verisi satir sayisi
MIN_SAMPLES_SKLEARN = 10


def _sf(val, default=0.0):
    """
    Guvenli float donusumu. None/NaN/Inf icin varsayilan deger doner.
    """
    if val is None:
        return default
    try:
        f = float(val)
        return default if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return default


class HavuzAIEngine:
    """
    Havuz + performans + populerlik verileri uzerinde ML modelleri.

    LR:  basari_orani, doluluk_orani, ortalama_not -> gelecek yil basari tahmini
    RF:  basari, doluluk, ortalama_not, trend, anket, sayac -> kesinlesme puani (0-100)
    DT:  ayni ozellikler -> statu tahmini (1 / 0 / -1)
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.model_lr = None
        self.model_dt = None
        self.model_rf = None
        self._trained = False
        self._last_training_meta = {}

    def _load_training_data(self, fakulte_id=None, yil=None, curriculum_only: bool = False):
        """
        performans + populerlik + havuz + ders_kriterleri tablolarindan
        birlestirmis egitim verisi olusturur.
        """
        filters = ["h.statu IS NOT NULL"]
        params = {}
        if fakulte_id is not None:
            filters.append("h.fakulte_id = :fakulte_id")
            params["fakulte_id"] = int(fakulte_id)
        if yil is not None:
            filters.append("h.yil = :yil")
            params["yil"] = int(yil)
        if curriculum_only:
            filters.append(
                """
                EXISTS (
                    SELECT 1
                    FROM mufredat_ders md
                    JOIN mufredat m ON md.mufredat_id = m.mufredat_id
                    JOIN bolum b ON b.bolum_id = m.bolum_id
                    WHERE md.ders_id = CAST(h.ders_id AS INTEGER)
                      AND b.fakulte_id = h.fakulte_id
                      AND m.akademik_yil = h.yil
                )
                """
            )

        q = text(f"""
            SELECT
                h.ders_id,
                h.yil,
                h.fakulte_id,
                h.statu,
                h.sayac,
                COALESCE(h.skor, 0)          AS skor,
                COALESCE(p.basari_orani, 0)  AS basari_orani,
                COALESCE(p.ortalama_not, 0)  AS ortalama_not,
                COALESCE(pop.doluluk_orani, 0) AS doluluk_orani,
                COALESCE(
                    CASE WHEN dk.anket_katilimci > 0
                         THEN CAST(dk.anket_dersi_secen AS REAL) / dk.anket_katilimci
                         ELSE NULL END,
                    0.5
                ) AS anket_orani
            FROM havuz h
            LEFT JOIN performans p
                ON CAST(h.ders_id AS INTEGER) = p.ders_id AND h.yil = p.akademik_yil
            LEFT JOIN populerlik pop
                ON CAST(h.ders_id AS INTEGER) = pop.ders_id AND h.yil = pop.akademik_yil
            LEFT JOIN ders_kriterleri dk
                ON CAST(h.ders_id AS INTEGER) = dk.ders_id AND h.yil = dk.yil
            WHERE {" AND ".join(filters)}
            ORDER BY h.ders_id, h.yil
        """)
        try:
            rows = self.db.execute(q, params).fetchall()
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
        """ML modelleri icin kullanilan ozellik (feature) sutun listesini doner."""
        return ["basari_orani", "ortalama_not", "doluluk_orani", "anket_orani", "trend", "sayac"]

    def _resolve_training_frames(self, fakulte_id=None, yil=None, curriculum_only: bool = False):
        """
        Tahmin gosterimi ve egitim kapsamlarini ayirir.
        UI genelde mufredat dersleri icin tahmin ister; egitim verisi azsa ayni
        fakulte/yilin tum havuz verisine genisletilir.
        """
        target_df = self._load_training_data(
            fakulte_id=fakulte_id,
            yil=yil,
            curriculum_only=curriculum_only,
        )
        fit_df = target_df
        meta = {
            "requested_curriculum_only": bool(curriculum_only),
            "target_rows": len(target_df),
            "fit_rows": len(fit_df),
            "fit_scope": "curriculum" if curriculum_only else "faculty_year",
            "fallback_used": False,
        }

        if curriculum_only and len(target_df) < MIN_SAMPLES_SKLEARN:
            fallback_df = self._load_training_data(
                fakulte_id=fakulte_id,
                yil=yil,
                curriculum_only=False,
            )
            if len(fallback_df) > len(fit_df):
                fit_df = fallback_df
                meta.update(
                    {
                        "fit_rows": len(fit_df),
                        "fit_scope": "faculty_year",
                        "fallback_used": True,
                    }
                )

        self._last_training_meta = dict(meta)
        return target_df, fit_df, meta

    def _train_from_dataframe(self, df: pd.DataFrame) -> bool:
        self.model_lr = None
        self.model_rf = None
        self.model_dt = None
        self._trained = False

        if df.empty or len(df) < MIN_SAMPLES_SKLEARN:
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

    def get_last_training_meta(self) -> dict:
        return dict(self._last_training_meta)

    def train(self, fakulte_id=None, yil=None, curriculum_only: bool = False):
        """
        LR, RF ve DT modellerini havuz verisi uzerinde egitir. Basarili ise True, veri yetersizse False doner.
        """
        _, fit_df, meta = self._resolve_training_frames(
            fakulte_id=fakulte_id,
            yil=yil,
            curriculum_only=curriculum_only,
        )
        if meta.get("fallback_used"):
            logger.info(
                "AI egitimi fakulte/yil geneline genisletildi: target=%s fit=%s fakulte_id=%s yil=%s",
                meta.get("target_rows"),
                meta.get("fit_rows"),
                fakulte_id,
                yil,
            )
        return self._train_from_dataframe(fit_df)

    def predict_basari(self, features: dict) -> float:
        """LR: gelecek yil basari orani tahmini (0-100)."""
        if not self._trained or self.model_lr is None:
            return _sf(features.get("basari_orani", 0.5)) * 100
        X = self._dict_to_X(features)
        return float(np.clip(self.model_lr.predict(X)[0], 0, 100))

    def predict_kesinlesme(self, features: dict) -> float:
        """RF: kesinlesme puani tahmini (0-100)."""
        if not self._trained or self.model_rf is None:
            return _sf(features.get("skor", 50))
        X = self._dict_to_X(features)
        return float(np.clip(self.model_rf.predict(X)[0], 0, 100))

    def predict_statu(self, features: dict) -> int:
        """DT: statu tahmini (1/0/-1/-2)."""
        if not self._trained or self.model_dt is None:
            return 0
        X = self._dict_to_X(features)
        return int(self.model_dt.predict(X)[0])

    def _dict_to_X(self, features: dict) -> np.ndarray:
        """Feature dictionary'yi numpy array'e cevirir (sklearn uyumlu)."""
        row = [_sf(features.get(c, 0)) for c in self._feature_cols()]
        return np.array([row])

    def predict_all_courses(self, fakulte_id=None, yil=None, curriculum_only: bool = False):
        """Tum dersler icin toplu tahmin yapar; DataFrame doner."""
        target_df, fit_df, meta = self._resolve_training_frames(
            fakulte_id=fakulte_id,
            yil=yil,
            curriculum_only=curriculum_only,
        )
        if target_df.empty:
            return pd.DataFrame()

        self._train_from_dataframe(fit_df)
        df = target_df.copy()

        if not self._trained:
            df["lr_tahmin"] = np.clip(df["basari_orani"].values * 100, 0, 100).round(2)
            df["rf_tahmin"] = np.clip(
                np.where(df["skor"].values > 0, df["skor"].values, df["basari_orani"].values * 100),
                0,
                100,
            ).round(2)
            df["dt_tahmin"] = df["statu"].astype(int)
            df["prediction_mode"] = "fallback"
            return df

        feat = self._feature_cols()
        X = df[feat].values

        df["lr_tahmin"] = np.clip(self.model_lr.predict(X), 0, 100).round(2)
        df["rf_tahmin"] = np.clip(self.model_rf.predict(X), 0, 100).round(2)
        df["dt_tahmin"] = self.model_dt.predict(X)
        df["prediction_mode"] = "model"
        if meta.get("fallback_used"):
            df["training_scope"] = meta.get("fit_scope")
        return df

    def run_kfold(self, algorithm_type="rf", k=5, fakulte_id=None, yil=None, curriculum_only: bool = False):
        """K-Fold cross-validation sonucu doner (string)."""
        _, df, meta = self._resolve_training_frames(
            fakulte_id=fakulte_id,
            yil=yil,
            curriculum_only=curriculum_only,
        )
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
                f"Egitim verisi: {len(X)} satir",
            ]
            if meta.get("fallback_used"):
                lines.append(
                    f"Not: Mufredat kapsami {meta.get('target_rows')} satir oldugu icin fakulte geneli {meta.get('fit_rows')} satirla egitim yapildi."
                )
            lines.extend([
                "",
                "Kriter agirliklari (katsayilar):",
            ])
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
                f"Egitim verisi: {len(X)} satir",
            ]
            if meta.get("fallback_used"):
                lines.append(
                    f"Not: Mufredat kapsami {meta.get('target_rows')} satir oldugu icin fakulte geneli {meta.get('fit_rows')} satirla egitim yapildi."
                )
            lines.extend([
                "",
                "Ozellik onemliligi:",
            ])
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
                f"Egitim verisi: {len(X)} satir",
            ]
            if meta.get("fallback_used"):
                lines.append(
                    f"Not: Mufredat kapsami {meta.get('target_rows')} satir oldugu icin fakulte geneli {meta.get('fit_rows')} satirla egitim yapildi."
                )
            lines.extend([
                "",
                "Ozellik onemliligi:",
            ])
            for name, imp in importances:
                bar = "#" * int(imp * 30)
                lines.append(f"  {name:20s}: {imp:.3f} {bar}")
            return "\n".join(lines)

        return f"Desteklenmeyen algoritma: {algorithm_type}"


class AIEngine:
    """
    calc_tab.py tarafindan kullanilan ust duzey arayuz. HavuzAIEngine'i sarar.
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.havuz_engine = HavuzAIEngine(db_session)

    def run_kfold_test(self, algorithm_type="rf", k=5):
        return self.havuz_engine.run_kfold(
            algorithm_type=algorithm_type, k=k, fakulte_id=None,
        )
