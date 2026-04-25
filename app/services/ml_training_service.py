# -*- coding: utf-8 -*-
"""ML model eğitim orkestrasyonu; yetersiz veride güvenli skip üretir."""

from __future__ import annotations

from datetime import datetime
import sqlite3

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier

from app.services.ml_algorithm_registry_service import get_algorithm_config
from app.services.ml_evaluation_service import evaluate_classification_model, evaluate_regression_model
from app.services.ml_feature_pipeline import build_course_feature_dataset
from app.services.ml_model_registry_service import create_model_run, mark_failed, mark_skipped, mark_trained
from app.services.ml_readiness_service import check_model_readiness


def train_model_run(
    conn: sqlite3.Connection,
    *,
    algorithm_key: str,
    year: int | None = None,
    faculty_id: int | None = None,
    department_id: int | None = None,
    created_by: str | None = None,
) -> dict:
    cfg = get_algorithm_config(conn, algorithm_key)
    dataset = build_course_feature_dataset(conn, year=year, faculty_id=faculty_id, department_id=department_id, save_snapshot=True)
    readiness = check_model_readiness(conn, cfg.algorithm_key, dataset, target_column="target_status")
    run_id = create_model_run(
        conn,
        algorithm_key=cfg.algorithm_key,
        model_name=cfg.display_name,
        model_type=cfg.algorithm_type,
        usage_role=cfg.usage_role,
        model_version=f"{cfg.algorithm_key}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        feature_schema_version=dataset.feature_schema_version,
        training_sample_count=dataset.sample_count,
        target_column="target_status" if cfg.algorithm_type != "regression" else "previous_topsis_score",
        training_scope={"year": year, "faculty_id": faculty_id, "department_id": department_id},
        class_distribution=readiness.samples_per_class,
        parameters={"source": "ml_training_service", "advisory_only": cfg.usage_role != "production_decision"},
        readiness_level=readiness.readiness_level,
        readiness_warnings=readiness.warnings + readiness.blocking_reasons,
        created_by=created_by,
    )
    if not readiness.is_ready:
        reason = "; ".join(readiness.blocking_reasons or ["Readiness koşulu sağlanmadı."])
        return mark_skipped(conn, run_id, reason) | {"readiness": readiness.as_dict()}
    try:
        model = _build_model(cfg.algorithm_key)
        if cfg.algorithm_type == "regression":
            y = dataset.X["previous_topsis_score"].astype(float)
            if len(pd.Series(y).dropna()) < 2:
                raise ValueError("Regresyon hedef verisi yetersiz.")
            evaluation = evaluate_regression_model(model, dataset.X, y)
        else:
            if dataset.y is None or pd.Series(dataset.y).nunique() < 2:
                raise ValueError("Sınıflandırma hedef verisi yetersiz.")
            evaluation = evaluate_classification_model(model, dataset.X, dataset.y)
        result = mark_trained(
            conn,
            run_id,
            train_metrics=evaluation.train_metrics,
            validation_metrics=evaluation.validation_metrics,
            cross_validation=evaluation.cross_validation,
            overfitting_report=evaluation.overfitting_report,
        )
        result["readiness"] = readiness.as_dict()
        result["warnings"] = evaluation.warnings
        return result
    except Exception as exc:
        return mark_failed(conn, run_id, str(exc)) | {"readiness": readiness.as_dict()}


def _build_model(algorithm_key: str):
    if algorithm_key == "linear_regression":
        return LinearRegression()
    if algorithm_key == "decision_tree":
        return DecisionTreeClassifier(max_depth=5, random_state=42)
    if algorithm_key == "random_forest":
        return RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, class_weight="balanced_subsample")
    if algorithm_key == "logistic_regression":
        return LogisticRegression(max_iter=2000)
    if algorithm_key == "naive_bayes":
        return GaussianNB()
    if algorithm_key in {"xgboost", "gradient_boosting"}:
        from sklearn.ensemble import GradientBoostingClassifier

        return GradientBoostingClassifier(random_state=42)
    return DecisionTreeClassifier(max_depth=3, random_state=42)
