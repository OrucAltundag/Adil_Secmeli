"""Core supervised ML models for benchmarking."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.naive_bayes import GaussianNB

from app.algorithms.base import AlgorithmOutput, IPredictor


def _build_lr_estimator():
    from sklearn.linear_model import LogisticRegression

    return LogisticRegression(max_iter=2000, n_jobs=None)


class SklearnPredictorBase(IPredictor):
    def __init__(self, name: str, estimator: Any, *, task_type: str = "prediction", parameters: dict[str, Any] | None = None) -> None:
        super().__init__(name=name, task_type=task_type, parameters=parameters or {})
        self.estimator = estimator
        self.classes_: list[Any] = []
        self.feature_names_: list[str] = []
        self._is_fit = False

    def fit(self, X: pd.DataFrame, y: pd.Series | np.ndarray | list[Any] | None = None) -> "SklearnPredictorBase":
        if y is None:
            raise ValueError(f"{self.name} requires target labels in fit().")
        X_df = self._as_dataframe(X)
        y_series = pd.Series(y)
        self.feature_names_ = X_df.columns.tolist()
        self.estimator.fit(X_df, y_series)
        self.classes_ = list(getattr(self.estimator, "classes_", sorted(y_series.unique().tolist())))
        self._is_fit = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> list[list[float]]:
        X_df = self._as_dataframe(X)
        if not self._is_fit:
            raise ValueError("Model not fitted.")
        if hasattr(self.estimator, "predict_proba"):
            return self.estimator.predict_proba(X_df).tolist()
        preds = self.estimator.predict(X_df)
        # deterministic pseudo-probability for estimators without predict_proba
        probs = []
        class_index = {c: i for i, c in enumerate(self.classes_)}
        for label in preds:
            row = [0.0] * len(self.classes_)
            row[class_index[label]] = 1.0
            probs.append(row)
        return probs

    def predict(self, X: pd.DataFrame) -> AlgorithmOutput:
        started = self._start_timer()
        X_df = self._as_dataframe(X)
        if not self._is_fit:
            raise ValueError("Model not fitted.")

        preds = self.estimator.predict(X_df).tolist()
        probas = np.array(self.predict_proba(X_df), dtype=float)
        confidence = float(np.mean(np.max(probas, axis=1))) if len(probas) else 0.0
        return self._build_output(
            started,
            predictions=preds,
            confidence=confidence,
            explanation=self.explain(X_df),
            artifacts={"classes": self.classes_, "feature_importance": self._feature_importance()},
        )

    def recommend(self, X: pd.DataFrame, top_k: int = 5) -> AlgorithmOutput:
        started = self._start_timer()
        X_df = self._as_dataframe(X)
        probas = np.array(self.predict_proba(X_df), dtype=float)
        if probas.size == 0:
            return self._build_output(started, recommendations=[], confidence=0.0, explanation="No probabilities generated")
        top_k = max(1, min(top_k, len(self.classes_)))
        recs = []
        for idx, row in enumerate(probas):
            sorted_idx = np.argsort(row)[::-1][:top_k]
            recs.append(
                {
                    "entity_id": idx,
                    "items": [{"label": self.classes_[i], "score": float(row[i])} for i in sorted_idx],
                }
            )
        confidence = float(np.mean(np.max(probas, axis=1)))
        return self._build_output(
            started,
            recommendations=recs,
            confidence=confidence,
            explanation=self.explain(X_df),
            artifacts={"classes": self.classes_, "feature_importance": self._feature_importance()},
        )

    def score(self, X: pd.DataFrame, y: pd.Series | None = None) -> float:
        if y is None:
            return 0.0
        X_df = self._as_dataframe(X)
        return float(self.estimator.score(X_df, y))

    def explain(self, X: pd.DataFrame | None = None) -> str:
        feature_importance = self._feature_importance()
        if not feature_importance:
            return f"{self.name} explanation unavailable for this estimator."
        top = sorted(feature_importance.items(), key=lambda t: abs(t[1]), reverse=True)[:5]
        top_str = ", ".join([f"{k}={v:.4f}" for k, v in top])
        return f"{self.name} important features: {top_str}"

    def _feature_importance(self) -> dict[str, float]:
        if hasattr(self.estimator, "coef_"):
            coef = np.asarray(getattr(self.estimator, "coef_"))
            if coef.ndim == 2:
                coef = np.mean(np.abs(coef), axis=0)
            return {name: float(val) for name, val in zip(self.feature_names_, coef.tolist())}
        if hasattr(self.estimator, "feature_importances_"):
            fi = np.asarray(getattr(self.estimator, "feature_importances_"), dtype=float)
            return {name: float(val) for name, val in zip(self.feature_names_, fi.tolist())}
        return {}

    def _as_dataframe(self, X: Any) -> pd.DataFrame:
        if isinstance(X, pd.DataFrame):
            out = X.copy()
        else:
            out = pd.DataFrame(X)
        if not out.columns.tolist():
            out.columns = [f"f{i}" for i in range(out.shape[1])]
        return out.fillna(0.0)


class NaiveBayesPredictor(SklearnPredictorBase):
    def __init__(self) -> None:
        super().__init__(name="NaiveBayes", estimator=GaussianNB())


class LogisticRegressionPredictor(SklearnPredictorBase):
    def __init__(self) -> None:
        super().__init__(name="LogisticRegression", estimator=_build_lr_estimator())


class RandomForestPredictor(SklearnPredictorBase):
    def __init__(self, n_estimators: int = 300, random_seed: int = 42) -> None:
        super().__init__(
            name="RandomForest",
            estimator=RandomForestClassifier(
                n_estimators=n_estimators,
                random_state=random_seed,
                n_jobs=-1,
                class_weight="balanced_subsample",
            ),
            parameters={"n_estimators": n_estimators, "random_seed": random_seed},
        )


class XGBoostLikePredictor(SklearnPredictorBase):
    """Uses XGBoost when available, otherwise GradientBoosting fallback."""

    def __init__(self, random_seed: int = 42) -> None:
        estimator: Any
        model_name = "XGBoostFallback"
        try:
            from xgboost import XGBClassifier  # type: ignore

            estimator = XGBClassifier(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=random_seed,
                eval_metric="mlogloss",
            )
            model_name = "XGBoost"
        except Exception:
            estimator = GradientBoostingClassifier(random_state=random_seed)

        super().__init__(name=model_name, estimator=estimator, parameters={"random_seed": random_seed})
