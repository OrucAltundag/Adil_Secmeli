"""Feature engineering for derived benchmark-ready datasets."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from app.datasets.entities import DatasetBundle


@dataclass(slots=True)
class FeatureConfig:
    categorical_columns: list[str]
    numeric_columns: list[str]
    composite_weights: dict[str, float]
    # Normalize yontemi: "minmax" (varsayilan, geriye uyumlu) | "zscore" | "none"
    normalize_method: str = "minmax"
    # Eksik veri doldurma: "median" (varsayilan) | "mean" | "knn"
    impute_strategy: str = "median"
    knn_neighbors: int = 5


DEFAULT_FEATURE_CONFIG = FeatureConfig(
    categorical_columns=[
        "faculty_id",
        "department_id",
        "gender",
        "term",
        "course_faculty_id",
        "course_department_id",
    ],
    numeric_columns=[
        "gpa",
        "capacity",
        "difficulty_score",
        "instructor_effect_score",
        "preference_rank",
        "preference_score",
        "satisfaction",
        "contribution",
        "general_sentiment",
    ],
    composite_weights={
        "academic_preparedness": 0.30,
        "preference_strength": 0.25,
        "satisfaction_signal": 0.25,
        "course_capacity_signal": 0.20,
    },
)


class FeatureEngineer:
    """Transforms raw tables into model-ready derived features."""

    def __init__(self, config: FeatureConfig | None = None) -> None:
        self.config = config or DEFAULT_FEATURE_CONFIG

    def generate(self, bundle: DatasetBundle) -> DatasetBundle:
        students = bundle.raw_real["students"].copy()
        courses = bundle.raw_real["courses"].copy()
        preferences = bundle.raw_real["preferences"].copy()
        survey = bundle.raw_real.get("survey_responses", pd.DataFrame()).copy()

        joint = self._build_student_course_matrix(students, courses, preferences, survey)
        normalized = self._normalize_numeric(joint)
        with_scores = self._add_composite_scores(normalized)
        encoded = self._one_hot_encode(with_scores)

        derived = dict(bundle.derived)
        derived["student_course_features"] = encoded
        derived["student_course_features_unencoded"] = with_scores

        return DatasetBundle(
            dataset_name=bundle.dataset_name,
            raw_real=dict(bundle.raw_real),
            derived=derived,
            synthetic=dict(bundle.synthetic),
            metadata=dict(bundle.metadata),
        )

    def _build_student_course_matrix(
        self,
        students: pd.DataFrame,
        courses: pd.DataFrame,
        preferences: pd.DataFrame,
        survey: pd.DataFrame,
    ) -> pd.DataFrame:
        students = students.rename(columns={"faculty_id": "student_faculty_id", "department_id": "student_department_id"})
        courses = courses.rename(columns={"faculty_id": "course_faculty_id", "department_id": "course_department_id"})
        preferences = preferences.rename(columns={"rank": "preference_rank"})

        merged = preferences.merge(students, on="student_id", how="left")
        merged = merged.merge(courses, on="course_id", how="left")
        if not survey.empty:
            merged = merged.merge(
                survey[["student_id", "course_id", "satisfaction", "contribution", "general_sentiment"]],
                on=["student_id", "course_id"],
                how="left",
            )
        else:
            merged["satisfaction"] = np.nan
            merged["contribution"] = np.nan
            merged["general_sentiment"] = np.nan

        merged["faculty_id"] = merged["student_faculty_id"].combine_first(merged["course_faculty_id"])
        merged["department_id"] = merged["student_department_id"].combine_first(merged["course_department_id"])
        return merged

    def _normalize_numeric(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        numeric_cols = [c for c in self.config.numeric_columns if c in out.columns]
        if not numeric_cols:
            return out

        for column in numeric_cols:
            out[column] = pd.to_numeric(out[column], errors="coerce")

        # preference rank: lower is better, invert before normalization.
        if "preference_rank" in out.columns:
            max_rank = np.nanmax(out["preference_rank"].to_numpy()) if len(out) else 1.0
            if np.isnan(max_rank) or max_rank <= 0:
                max_rank = 1.0
            out["preference_rank"] = (max_rank + 1.0) - out["preference_rank"]

        filled = self._impute(out[numeric_cols])
        out[numeric_cols] = self._scale(filled)
        return out

    def _impute(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Eksik degerleri secilen stratejiye gore doldur."""
        strategy = getattr(self.config, "impute_strategy", "median")
        if frame.empty:
            return frame
        try:
            if strategy == "knn":
                k = max(1, int(getattr(self.config, "knn_neighbors", 5)))
                imputer = KNNImputer(n_neighbors=k)
            elif strategy == "mean":
                imputer = SimpleImputer(strategy="mean")
            else:  # "median" — varsayilan, geriye uyumlu
                imputer = SimpleImputer(strategy="median")
            arr = imputer.fit_transform(frame)
            # Tum sutun NaN ise imputer sutunu dusurebilir; guvenli fallback
            if arr.shape[1] != frame.shape[1]:
                return frame.fillna(frame.median(numeric_only=True)).fillna(0.0)
            return pd.DataFrame(arr, columns=frame.columns, index=frame.index).fillna(0.0)
        except Exception:
            return frame.fillna(frame.median(numeric_only=True)).fillna(0.0)

    def _scale(self, frame: pd.DataFrame) -> np.ndarray | pd.DataFrame:
        """Secilen yonteme gore olcekle: minmax | zscore | none."""
        method = getattr(self.config, "normalize_method", "minmax")
        if frame.empty or method == "none":
            return frame
        scaler = StandardScaler() if method == "zscore" else MinMaxScaler()
        return scaler.fit_transform(frame)

    def _add_composite_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()

        out["academic_preparedness"] = out.get("gpa", 0.0).fillna(0.0)
        out["preference_strength"] = (
            0.6 * out.get("preference_rank", 0.0).fillna(0.0) + 0.4 * out.get("preference_score", 0.0).fillna(0.0)
        )
        out["satisfaction_signal"] = (
            out.get("satisfaction", 0.0).fillna(0.0)
            + out.get("contribution", 0.0).fillna(0.0)
            + out.get("general_sentiment", 0.0).fillna(0.0)
        ) / 3.0
        out["course_capacity_signal"] = out.get("capacity", 0.0).fillna(0.0)

        weights = self.config.composite_weights
        out["composite_score"] = (
            out["academic_preparedness"] * weights["academic_preparedness"]
            + out["preference_strength"] * weights["preference_strength"]
            + out["satisfaction_signal"] * weights["satisfaction_signal"]
            + out["course_capacity_signal"] * weights["course_capacity_signal"]
        )
        return out

    def _one_hot_encode(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        cats = [c for c in self.config.categorical_columns if c in out.columns]
        if not cats:
            return out
        return pd.get_dummies(out, columns=cats, dummy_na=True, dtype=float)


def split_features_and_target(
    features_df: pd.DataFrame,
    *,
    target_column: str,
    drop_columns: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    if target_column not in features_df.columns:
        raise KeyError(f"target_column '{target_column}' missing from dataframe")
    drop_cols = set(drop_columns or [])
    drop_cols.add(target_column)
    X = features_df.drop(columns=[c for c in drop_cols if c in features_df.columns], errors="ignore")
    y = features_df[target_column]
    return X, y
