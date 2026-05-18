# -*- coding: utf-8 -*-
"""ML destekleyici tahmin, fallback ve tahmin log servisi."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier

from app.db.schema_compat import ensure_ml_governance_schema
from app.services.ml_algorithm_registry_service import get_algorithm_config
from app.services.ml_confidence_service import estimate_prediction_confidence
from app.services.ml_evaluation_service import (
    evaluate_classification_model,
    evaluate_regression_model,
)
from app.services.ml_explainability_service import (
    explain_model_prediction,
    save_prediction_explanation,
)
from app.services.ml_feature_pipeline import (
    build_course_feature_dataset,
    extract_features_for_course,
)
from app.services.ml_model_registry_service import (
    create_model_run,
    mark_failed,
    mark_skipped,
    mark_trained,
)
from app.services.ml_readiness_service import check_model_readiness


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False, sort_keys=True)


def predict_course(
    conn: sqlite3.Connection,
    *,
    algorithm_key: str,
    course_id: int,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    prediction_type: str = "status",
) -> dict:
    """Tek ders için destekleyici ML tahmini üretir ve ml_predictions tablosuna yazar."""
    ensure_ml_governance_schema(conn, commit=False)
    cfg = get_algorithm_config(conn, algorithm_key)
    dataset = build_course_feature_dataset(conn, year=year, faculty_id=faculty_id, department_id=department_id)
    readiness = check_model_readiness(conn, cfg.algorithm_key, dataset, target_column="target_status")
    model_run_id = create_model_run(
        conn,
        algorithm_key=cfg.algorithm_key,
        model_name=cfg.display_name,
        model_type=cfg.algorithm_type,
        usage_role=cfg.usage_role,
        model_version=f"{cfg.algorithm_key}-{_now()}",
        feature_schema_version=dataset.feature_schema_version,
        training_sample_count=dataset.sample_count,
        target_column="target_status",
        training_scope={"year": year, "faculty_id": faculty_id, "department_id": department_id},
        class_distribution=readiness.samples_per_class,
        parameters={"advisory_only": True},
        readiness_level=readiness.readiness_level,
        readiness_warnings=readiness.warnings + readiness.blocking_reasons,
    )

    if not readiness.is_ready or not readiness.can_train:
        reason = "; ".join(readiness.blocking_reasons or readiness.warnings or ["Model readiness koşulları sağlanmadı."])
        mark_skipped(conn, model_run_id, reason)
        return fallback_prediction(
            conn,
            algorithm_key=cfg.algorithm_key,
            course_id=course_id,
            year=year,
            faculty_id=faculty_id,
            department_id=department_id,
            prediction_type=prediction_type,
            fallback_method="rule_based_status_estimator" if prediction_type == "status" else "historical_average",
            fallback_reason=reason,
        )

    try:
        X = dataset.X
        y = dataset.y
        course_features = extract_features_for_course(conn, int(course_id), int(year))
        if not course_features:
            reason = "Seçili ders için feature satırı bulunamadı."
            mark_skipped(conn, model_run_id, reason)
            return fallback_prediction(
                conn,
                algorithm_key=cfg.algorithm_key,
                course_id=course_id,
                year=year,
                faculty_id=faculty_id,
                department_id=department_id,
                prediction_type=prediction_type,
                fallback_method="no_prediction",
                fallback_reason=reason,
            )
        X_row = pd.DataFrame([course_features], columns=dataset.feature_names).fillna(0.0)
        model = _build_model(cfg.algorithm_key)
        if cfg.algorithm_type == "regression":
            target = X["previous_topsis_score"].astype(float) if "previous_topsis_score" in X.columns else dataset.y
            if target is None or len(pd.Series(target).dropna()) < 2:
                raise ValueError("Regresyon hedef değişkeni yetersiz.")
            evaluation = evaluate_regression_model(model, X, target)
            model.fit(X, target)
            predicted_numeric = float(model.predict(X_row)[0])
            predicted_text = f"{predicted_numeric:.2f}"
        else:
            if y is None or pd.Series(y).nunique() < 2:
                raise ValueError("Sınıflandırma hedef değişkeni yetersiz.")
            evaluation = evaluate_classification_model(model, X, y)
            model.fit(X, y)
            pred = model.predict(X_row)[0]
            predicted_numeric = float(pred) if str(pred).lstrip("-").isdigit() else None
            predicted_text = str(pred)

        marked = mark_trained(
            conn,
            model_run_id,
            train_metrics=evaluation.train_metrics,
            validation_metrics=evaluation.validation_metrics,
            cross_validation=evaluation.cross_validation,
            overfitting_report=evaluation.overfitting_report,
        )
        confidence = estimate_prediction_confidence(
            model,
            predicted_text,
            X_row,
            {
                "sample_count": dataset.sample_count,
                "required_min_samples": cfg.min_training_samples,
                "validation_metrics": evaluation.validation_metrics,
                "model_type": cfg.algorithm_type,
                "readiness_level": readiness.readiness_level,
                "overfitting_report": evaluation.overfitting_report,
                "missing_feature_ratio": _dataset_missing_ratio(dataset),
            },
        )
        # Registry rolü production_decision değilse tahmin karara etki edemez.
        should_influence = confidence.should_influence_decision and cfg.usage_role == "production_decision"
        explanation = (
            f"{cfg.display_name} destekleyici tahmini: {predicted_text}. "
            f"Güven: {confidence.confidence_score:.2f} / {confidence.confidence_level}. "
            "Bu tahmin nihai karara etki etmemiştir; nihai karar AHP/TOPSIS + kurallar + state machine ile verilir."
        )
        prediction_id = save_prediction(
            conn,
            model_run_id=model_run_id,
            algorithm_key=cfg.algorithm_key,
            course_id=course_id,
            year=year,
            faculty_id=faculty_id,
            department_id=department_id,
            prediction_type=prediction_type,
            predicted_value_text=predicted_text,
            predicted_value_numeric=predicted_numeric,
            confidence_score=confidence.confidence_score,
            confidence_level=confidence.confidence_level,
            uncertainty_reasons=confidence.uncertainty_reasons,
            fallback_used=False,
            advisory_only=True,
            should_influence_decision=should_influence,
            explanation=explanation,
        )
        ml_explanation = explain_model_prediction(
            model,
            X_row,
            dataset.feature_names,
            cfg.algorithm_key,
            readiness_level=readiness.readiness_level,
            sample_count=dataset.sample_count,
        )
        save_prediction_explanation(conn, prediction_id, ml_explanation)
        return get_prediction(conn, prediction_id) | {"model_run": marked, "readiness": readiness.as_dict(), "ml_explanation": ml_explanation.as_dict()}
    except Exception as exc:
        mark_failed(conn, model_run_id, str(exc))
        return fallback_prediction(
            conn,
            algorithm_key=cfg.algorithm_key,
            course_id=course_id,
            year=year,
            faculty_id=faculty_id,
            department_id=department_id,
            prediction_type=prediction_type,
            fallback_method="no_prediction",
            fallback_reason=f"Model tahmini çalışmadı: {exc}",
        )


def predict_batch(
    conn: sqlite3.Connection,
    *,
    algorithm_key: str,
    course_ids: list[int],
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
) -> list[dict]:
    return [
        predict_course(
            conn,
            algorithm_key=algorithm_key,
            course_id=int(course_id),
            year=int(year),
            faculty_id=faculty_id,
            department_id=department_id,
        )
        for course_id in course_ids
    ]


def fallback_prediction(
    conn: sqlite3.Connection,
    *,
    algorithm_key: str,
    course_id: int,
    year: int,
    faculty_id: int | None = None,
    department_id: int | None = None,
    prediction_type: str = "status",
    fallback_method: str = "no_prediction",
    fallback_reason: str = "Model readiness koşulları sağlanmadı.",
) -> dict:
    predicted_text, predicted_numeric = _fallback_value(conn, course_id, year, fallback_method)
    explanation = (
        f"{algorithm_key} modeli kullanılmadı. Sebep: {fallback_reason} "
        f"Fallback yöntemi: {fallback_method}. Bu çıktı destekleyicidir ve nihai karara etki etmez."
    )
    prediction_id = save_prediction(
        conn,
        model_run_id=None,
        algorithm_key=algorithm_key,
        course_id=course_id,
        year=year,
        faculty_id=faculty_id,
        department_id=department_id,
        prediction_type=prediction_type,
        predicted_value_text=predicted_text,
        predicted_value_numeric=predicted_numeric,
        confidence_score=0.20,
        confidence_level="low",
        uncertainty_reasons=[fallback_reason],
        fallback_used=True,
        fallback_method=fallback_method,
        fallback_reason=fallback_reason,
        advisory_only=True,
        should_influence_decision=False,
        explanation=explanation,
    )
    return get_prediction(conn, prediction_id)


def save_prediction(
    conn: sqlite3.Connection,
    *,
    model_run_id: int | None,
    algorithm_key: str,
    course_id: int,
    year: int,
    faculty_id: int | None,
    department_id: int | None,
    prediction_type: str,
    predicted_value_text: str | None,
    predicted_value_numeric: float | None,
    confidence_score: float | None,
    confidence_level: str | None,
    uncertainty_reasons: list[str] | None,
    fallback_used: bool,
    fallback_method: str | None = None,
    fallback_reason: str | None = None,
    advisory_only: bool = True,
    should_influence_decision: bool = False,
    explanation: str | None = None,
) -> int:
    ensure_ml_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ml_predictions (
            model_run_id, algorithm_key, course_id, year, faculty_id, department_id,
            prediction_type, predicted_value_text, predicted_value_numeric,
            confidence_score, confidence_level, uncertainty_reasons_json,
            fallback_used, fallback_method, fallback_reason, advisory_only,
            should_influence_decision, explanation, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            model_run_id,
            algorithm_key,
            int(course_id),
            int(year),
            faculty_id,
            department_id,
            prediction_type,
            predicted_value_text,
            predicted_value_numeric,
            confidence_score,
            confidence_level,
            _json(uncertainty_reasons or []),
            1 if fallback_used else 0,
            fallback_method,
            fallback_reason,
            1 if advisory_only else 0,
            1 if should_influence_decision else 0,
            explanation,
            _now(),
        ),
    )
    return int(cur.lastrowid)


def get_prediction(conn: sqlite3.Connection, prediction_id: int) -> dict:
    cur = conn.cursor()
    cur.execute("SELECT * FROM ml_predictions WHERE id = ? LIMIT 1", (int(prediction_id),))
    row = cur.fetchone()
    if not row:
        return {}
    return _prediction_row(row, [d[0] for d in cur.description])


def list_predictions(
    conn: sqlite3.Connection,
    *,
    course_id: int | None = None,
    algorithm_key: str | None = None,
    limit: int = 100,
) -> list[dict]:
    ensure_ml_governance_schema(conn, commit=False)
    sql = "SELECT * FROM ml_predictions WHERE 1=1"
    params: list[Any] = []
    if course_id is not None:
        sql += " AND course_id = ?"
        params.append(int(course_id))
    if algorithm_key:
        sql += " AND algorithm_key = ?"
        params.append(algorithm_key)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(max(1, min(int(limit), 500)))
    cur = conn.cursor()
    cur.execute(sql, tuple(params))
    keys = [d[0] for d in cur.description]
    return [_prediction_row(row, keys) for row in cur.fetchall()]


def get_predictions_for_course(conn: sqlite3.Connection, course_id: int, year: int | None = None) -> list[dict]:
    sql = "SELECT * FROM ml_predictions WHERE course_id = ?"
    params: list[Any] = [int(course_id)]
    if year is not None:
        sql += " AND year = ?"
        params.append(int(year))
    sql += " ORDER BY id DESC"
    cur = conn.cursor()
    cur.execute(sql, tuple(params))
    keys = [d[0] for d in cur.description]
    return [_prediction_row(row, keys) for row in cur.fetchall()]


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


def _dataset_missing_ratio(dataset) -> float:
    summary = dataset.missing_features_summary or {}
    if not summary:
        return 0.0
    ratios = [float(item.get("missing_ratio") or 0.0) for item in summary.values() if isinstance(item, dict)]
    return sum(ratios) / max(len(ratios), 1)


def _fallback_value(conn: sqlite3.Connection, course_id: int, year: int, method: str) -> tuple[str | None, float | None]:
    cur = conn.cursor()
    if method == "historical_average":
        try:
            cur.execute(
                """
                SELECT AVG(skor_top)
                FROM skor
                WHERE ders_id=? AND akademik_yil <= ? AND skor_top IS NOT NULL
                """,
                (int(course_id), int(year)),
            )
            value = cur.fetchone()[0]
            if value is not None:
                return f"{float(value):.2f}", float(value)
        except Exception:
            pass
    if method == "rule_based_status_estimator":
        try:
            cur.execute(
                """
                SELECT statu
                FROM havuz
                WHERE CAST(ders_id AS INTEGER)=? AND yil <= ?
                ORDER BY yil DESC, id DESC
                LIMIT 1
                """,
                (int(course_id), int(year)),
            )
            row = cur.fetchone()
            if row:
                return str(int(row[0])), float(row[0])
        except Exception:
            pass
    return "tahmin_yok", None


def _prediction_row(row: sqlite3.Row | tuple, keys: list[str]) -> dict:
    data = {key: row[key] for key in row.keys()} if isinstance(row, sqlite3.Row) else dict(zip(keys, row))
    try:
        data["uncertainty_reasons"] = json.loads(data.get("uncertainty_reasons_json") or "[]")
    except Exception:
        data["uncertainty_reasons"] = []
    data["fallback_used"] = bool(data.get("fallback_used"))
    data["advisory_only"] = bool(data.get("advisory_only"))
    data["should_influence_decision"] = bool(data.get("should_influence_decision"))
    return data
