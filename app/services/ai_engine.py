# app/services/ai_engine.py
# Makine öğrenmesi: Havuz tablosu (ders_id, yil, fakulte, alan, statu, sayac, skor) üzerinde
# LR: Skor tahmini | DT: Statü kararı | RF: Kesinleşme Puanı (0-100)

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def _check_skor_debug(val, label="skor"):
    """Kesinleşme puanı None/NaN ise debug loga yazar."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        logger.debug("Kesinlesme_Puani %s: None veya NaN tespit edildi", label)
from sklearn.model_selection import cross_val_score, KFold, train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder
from sqlalchemy.orm import Session
from sqlalchemy import text
import random


def _safe_predict(model, X, default=0.5):
    """Tahmin yaparken hata durumunda güvenli varsayılan döner."""
    try:
        pred = model.predict(X)
        return np.clip(np.asarray(pred).flatten(), 0, 100)
    except Exception:
        return np.full(X.shape[0] if hasattr(X, "shape") else 1, default)


class HavuzAIEngine:
    """
    Havuz tablosu üzerinde makine öğrenmesi.
    - LR: sayac + geçmiş skor -> gelecek skor tahmini
    - DT: alan, fakulte_id, sayac -> statu (1/0/-1)
    - RF: tüm özellikler -> Kesinleşme Puanı (0-100)
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.model_lr = None
        self.model_dt = None
        self.model_rf = None
        self.enc_alan = LabelEncoder()
        self.enc_fakulte = LabelEncoder()
        self._trained = False

    def get_havuz_data(self, fakulte_id: int = None, yillar: list = None):
        """
        Havuz tablosundan veriyi çeker.
        Kolonlar: ders_id, yil, fakulte_id, alan (varsa), statu, sayac, skor
        """
        yillar = yillar or [2022, 2023, 2024, 2025]
        wh = " AND h.yil IN ({})".format(",".join(str(y) for y in yillar)) if yillar else ""
        if fakulte_id is not None:
            wh += f" AND h.fakulte_id = {int(fakulte_id)}"

        # alan sütunu bazı veritabanlarında yok; güvenli sorgu
        q = text(f"""
            SELECT h.ders_id, h.yil, h.fakulte_id, 'Genel' as alan,
                   h.statu, h.sayac, COALESCE(h.skor, 0) as skor
            FROM havuz h
            JOIN ders d ON d.ders_id = h.ders_id
            WHERE 1=1 {wh}
            ORDER BY h.ders_id, h.yil
        """)
        try:
            rows = self.db.execute(q).fetchall()
        except Exception:
            rows = []

        if not rows:
            return pd.DataFrame()

        cols = ["ders_id", "yil", "fakulte_id", "alan", "statu", "sayac", "skor"]
        df = pd.DataFrame([list(r) for r in rows], columns=cols)
        df["skor"] = pd.to_numeric(df["skor"], errors="coerce").fillna(0)
        df["sayac"] = pd.to_numeric(df["sayac"], errors="coerce").fillna(0)
        df["statu"] = pd.to_numeric(df["statu"], errors="coerce").fillna(0).astype(int)
        return df

    def _prepare_features(self, df: pd.DataFrame):
        """Havuz verisinden özellik matrisi ve hedefleri hazırla."""
        if df.empty or len(df) < 3:
            return None, None, None, None, None

        # Alan ve fakulte kategorik -> sayısal
        df = df.copy()
        df["alan_cat"] = df["alan"].astype(str).fillna("Genel")
        df["fakulte_cat"] = df["fakulte_id"].astype(str)
        try:
            df["alan_enc"] = self.enc_alan.fit_transform(df["alan_cat"])
        except Exception:
            df["alan_enc"] = 0
        try:
            df["fakulte_enc"] = self.enc_fakulte.fit_transform(df["fakulte_cat"])
        except Exception:
            df["fakulte_enc"] = 0

        # LR için: sayac + geçmiş skor ortalama -> gelecek skor
        # Geçmiş yıl verisi: ders bazlı ortalama skor
        skor_ort = df.groupby("ders_id")["skor"].transform("mean").fillna(50)
        X_lr = df[["sayac", "skor"]].copy()
        X_lr["skor_gecmis"] = skor_ort
        X_lr = X_lr.fillna(0)

        # DT için: alan, fakulte, sayac -> statu (1=mufredatta, 0=havuzda, -1=dinlenmede)
        X_dt = df[["alan_enc", "fakulte_enc", "sayac"]].values
        y_dt = df["statu"].values

        # RF için: tüm özellikler -> Kesinleşme Puanı (0-100)
        X_rf = df[["alan_enc", "fakulte_enc", "sayac", "skor", "yil"]].copy()
        X_rf["skor_gecmis"] = skor_ort
        X_rf = X_rf.fillna(0).values
        y_rf = np.clip(df["skor"].values, 0, 100)

        y_lr = df["skor"].values
        return X_lr, y_lr, X_dt, y_dt, X_rf, y_rf, df

    def train(self, fakulte_id: int = None):
        """Üç modeli eğitir: LR, DT, RF."""
        df = self.get_havuz_data(fakulte_id=fakulte_id)
        prep = self._prepare_features(df)
        if prep is None:
            self._trained = False
            return False

        X_lr, y_lr, X_dt, y_dt, X_rf, y_rf, _ = prep
        self.model_lr = LinearRegression()
        self.model_lr.fit(X_lr, y_lr)

        self.model_dt = DecisionTreeClassifier(max_depth=5, random_state=42)
        self.model_dt.fit(X_dt, y_dt)

        self.model_rf = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
        self.model_rf.fit(X_rf, y_rf)

        self._trained = True
        return True

    def predict_skor(self, sayac: float, skor_gecmis: float, skor_mevcut: float = None) -> float:
        """LR ile gelecek skor tahmini."""
        if not self._trained or self.model_lr is None:
            return float(skor_gecmis) if skor_gecmis else 50.0
        X = np.array([[sayac, skor_mevcut or skor_gecmis, skor_gecmis]])
        return float(np.clip(self.model_lr.predict(X)[0], 0, 100))

    def predict_statu(self, alan: str, fakulte_id: int, sayac: int) -> int:
        """DT ile ders bu dönem açılacak mı (1/0/-1)."""
        if not self._trained or self.model_dt is None:
            return 0
        try:
            a_enc = self.enc_alan.transform([str(alan or "Genel")])[0]
        except Exception:
            a_enc = 0
        try:
            f_enc = self.enc_fakulte.transform([str(fakulte_id)])[0]
        except Exception:
            f_enc = 0
        X = np.array([[a_enc, f_enc, sayac]])
        return int(self.model_dt.predict(X)[0])

    def predict_kesinlesme_puani(self, row: dict) -> float:
        """
        RF ile Kesinleşme Puanı (0-100).
        row: {alan, fakulte_id, sayac, skor, yil, skor_gecmis}
        """
        if not self._trained or self.model_rf is None:
            return float(row.get("skor", 50))
        try:
            a_enc = self.enc_alan.transform([str(row.get("alan") or "Genel")])[0]
        except Exception:
            a_enc = 0
        try:
            f_enc = self.enc_fakulte.transform([str(row.get("fakulte_id", 0))])[0]
        except Exception:
            f_enc = 0
        X = np.array([[
            a_enc,
            f_enc,
            float(row.get("sayac", 0)),
            float(row.get("skor", 50)),
            int(row.get("yil", 2024)),
            float(row.get("skor_gecmis", row.get("skor", 50))),
        ]])
        p = self.model_rf.predict(X)[0]
        _check_skor_debug(p, "RF.predict_kesinlesme_puani")
        return float(np.clip(p if p is not None and not np.isnan(p) else 50.0, 0, 100))

    def run_kfold_havuz(self, algorithm_type: str = "rf", k: int = 5, fakulte_id: int = None) -> str:
        """Havuz verisi üzerinde K-Fold doğrulama."""
        df = self.get_havuz_data(fakulte_id=fakulte_id)
        prep = self._prepare_features(df)
        if prep is None:
            return "Havuz verisi yetersiz. Önce havuzu doldurun."

        X_lr, y_lr, X_dt, y_dt, X_rf, y_rf, _ = prep

        if algorithm_type == "lr":
            model = LinearRegression()
            cv = KFold(n_splits=min(k, len(X_lr)), shuffle=True, random_state=42)
            scores = cross_val_score(model, X_lr, y_lr, cv=cv, scoring="neg_mean_absolute_error")
            mae = -scores.mean()
            return f"LR (Skor Tahmini) | MAE: {mae:.2f} | K={k}"
        elif algorithm_type == "dt":
            model = DecisionTreeClassifier(max_depth=5, random_state=42)
            cv = KFold(n_splits=min(k, len(X_dt)), shuffle=True, random_state=42)
            scores = cross_val_score(model, X_dt, y_dt, cv=cv, scoring="accuracy")
            return f"DT (Statü Tahmini) | Accuracy: {scores.mean()*100:.1f}% | K={k}"
        elif algorithm_type == "rf":
            model = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
            cv = KFold(n_splits=min(k, len(X_rf)), shuffle=True, random_state=42)
            scores = cross_val_score(model, X_rf, y_rf, cv=cv, scoring="neg_mean_absolute_error")
            mae = -scores.mean()
            return f"RF (Kesinleşme Puanı) | MAE: {mae:.2f} | K={k}"
        return "Desteklenmeyen algoritma."


# =========================================================
# ESKİ AIEngine (kayit/performans tabanlı) - Geriye uyumluluk
# =========================================================
class AIEngine:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.havuz_engine = HavuzAIEngine(db_session)

    def get_training_data(self):
        sorgu = text("""
            SELECT k.ogr_id, k.ders_id, k.durum,
                   p.basari_orani as ders_zorlugu, 50 as ogr_basari
            FROM kayit k
            JOIN performans p ON k.ders_id = p.ders_id
            WHERE k.durum IN ('Geçti', 'Kaldı')
            LIMIT 2000;
        """)
        veritabani_sonucu = self.db.execute(sorgu).fetchall()
        if not veritabani_sonucu:
            return None, None, None

        veri_tablosu = pd.DataFrame(
            veritabani_sonucu,
            columns=["ogr_id", "ders_id", "durum", "ders_zorlugu", "ogr_basari"],
        )
        veri_tablosu["y_sinif"] = veri_tablosu["durum"].apply(lambda x: 1 if x == "Geçti" else 0)
        veri_tablosu["y_not"] = veri_tablosu["durum"].apply(
            lambda x: random.randint(50, 100) if x == "Geçti" else random.randint(0, 49)
        )
        veri_tablosu["ogr_basari"] = np.random.randint(40, 90, veri_tablosu.shape[0])

        X = veri_tablosu[["ders_zorlugu", "ogr_basari"]].values
        y_sinif = veri_tablosu["y_sinif"].values
        y_not = veri_tablosu["y_not"].values
        return X, y_sinif, y_not

    def run_kfold_test(self, algorithm_type: str = "rf", k: int = 5):
        # Önce Havuz verisi var mı dene
        sonuc_havuz = self.havuz_engine.run_kfold_havuz(
            algorithm_type=algorithm_type, k=k, fakulte_id=None
        )
        if "yetersiz" not in sonuc_havuz.lower():
            return f"=== Havuz Tabanlı {sonuc_havuz} ==="

        # Havuz yoksa eski kayit/performans tabanlı test
        X, y_sinif, y_not = self.get_training_data()
        if X is None:
            return "Veri bulunamadı. Lütfen önce MOCK veri üretin veya havuzu doldurun."

        model = None
        hedef_y = None
        puanlama_metriki = ""
        gorev_adi = ""

        if algorithm_type == "lr":
            model = LinearRegression()
            hedef_y = y_not
            puanlama_metriki = "neg_mean_absolute_error"
            gorev_adi = "Lineer Regresyon (Not Tahmini)"
        elif algorithm_type == "dt":
            model = DecisionTreeClassifier(max_depth=5)
            hedef_y = y_sinif
            puanlama_metriki = "accuracy"
            gorev_adi = "Karar Ağacı (Geçme/Kalma)"
        elif algorithm_type == "rf":
            model = RandomForestClassifier(n_estimators=100, max_depth=5)
            hedef_y = y_sinif
            puanlama_metriki = "accuracy"
            gorev_adi = "Random Forest (Geçme/Kalma)"

        if model is None:
            return f"Desteklenmeyen: {algorithm_type}"

        try:
            cv = KFold(n_splits=k, shuffle=True, random_state=42)
            skorlar = cross_val_score(model, X, hedef_y, cv=cv, scoring=puanlama_metriki)
            sonuc = f"=== {gorev_adi} (Kayıt/Performans) ===\nK={k}\n"
            if puanlama_metriki == "neg_mean_absolute_error":
                sonuc += f"MAE: {-skorlar.mean():.2f}\n"
            else:
                sonuc += f"Accuracy: {skorlar.mean()*100:.1f}%\n"
            return sonuc
        except Exception as e:
            return f"Hata: {e}"
