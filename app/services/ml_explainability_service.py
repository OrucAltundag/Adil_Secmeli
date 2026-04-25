# -*- coding: utf-8 -*-
"""ML tahmin açıklanabilirliği."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime
import json
import sqlite3
from typing import Any

import numpy as np
import pandas as pd

from app.db.schema_compat import ensure_ml_governance_schema


@dataclass
class MLExplanation:
    top_features_json: list[dict[str, Any]] = field(default_factory=list)
    positive_factors_json: list[str] = field(default_factory=list)
    negative_factors_json: list[str] = field(default_factory=list)
    decision_path_json: list[dict[str, Any]] | None = None
    feature_importance_json: dict[str, float] | None = None
    limitations: list[str] = field(default_factory=list)
    human_readable_text: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def get_feature_importance(model, feature_names: list[str]) -> dict[str, float]:
    estimator = getattr(model, "estimator", model)
    if hasattr(estimator, "feature_importances_"):
        values = np.asarray(getattr(estimator, "feature_importances_"), dtype=float)
        return {name: float(value) for name, value in zip(feature_names, values)}
    if hasattr(estimator, "coef_"):
        coef = np.asarray(getattr(estimator, "coef_"), dtype=float)
        if coef.ndim == 2:
            coef = np.mean(np.abs(coef), axis=0)
        return {name: float(value) for name, value in zip(feature_names, coef)}
    if hasattr(model, "_feature_importance"):
        try:
            return {str(k): float(v) for k, v in model._feature_importance().items()}
        except Exception:
            return {}
    return {}


def get_decision_path_if_tree(model, X_row, feature_names: list[str]) -> list[dict[str, Any]] | None:
    estimator = getattr(model, "estimator", model)
    if not hasattr(estimator, "tree_") or not hasattr(estimator, "decision_path"):
        return None
    try:
        X_df = pd.DataFrame(X_row, columns=feature_names) if not isinstance(X_row, pd.DataFrame) else X_row[feature_names]
        node_indicator = estimator.decision_path(X_df)
        tree = estimator.tree_
        path = []
        for node_id in node_indicator.indices[node_indicator.indptr[0] : node_indicator.indptr[1]]:
            if tree.feature[node_id] < 0:
                path.append({"node": int(node_id), "leaf": True})
            else:
                feature = feature_names[int(tree.feature[node_id])]
                threshold = float(tree.threshold[node_id])
                value = float(X_df.iloc[0][feature])
                path.append({
                    "node": int(node_id),
                    "feature": feature,
                    "threshold": threshold,
                    "value": value,
                    "direction": "left" if value <= threshold else "right",
                })
        return path
    except Exception:
        return None


def explain_model_prediction(
    model,
    X_row,
    feature_names: list[str],
    algorithm_key: str,
    *,
    readiness_level: str | None = None,
    sample_count: int | None = None,
) -> MLExplanation:
    importance = get_feature_importance(model, feature_names)
    top = sorted(importance.items(), key=lambda item: abs(item[1]), reverse=True)[:5]
    top_features = [{"feature": name, "importance": float(value)} for name, value in top]
    limitations: list[str] = []
    if not importance:
        limitations.append("Bu model için yerleşik feature importance bilgisi üretilemedi.")
    if readiness_level in {"not_ready", "low"} or (sample_count is not None and sample_count < 50):
        limitations.append("Bu açıklama sınırlı eğitim verisi nedeniyle dikkatli yorumlanmalıdır.")
    decision_path = get_decision_path_if_tree(model, X_row, feature_names)
    if decision_path:
        positive = [f"{item['feature']} karar yolunda etkili oldu." for item in decision_path if "feature" in item][:3]
    else:
        positive = [f"{name} model tahmininde öne çıkan feature." for name, _ in top[:3]]
    text = generate_human_readable_ml_explanation(
        algorithm_key=algorithm_key,
        top_features=top_features,
        limitations=limitations,
    )
    return MLExplanation(
        top_features_json=top_features,
        positive_factors_json=positive,
        negative_factors_json=[],
        decision_path_json=decision_path,
        feature_importance_json=importance,
        limitations=limitations,
        human_readable_text=text,
    )


def generate_human_readable_ml_explanation(
    *,
    algorithm_key: str,
    top_features: list[dict[str, Any]],
    limitations: list[str],
) -> str:
    if top_features:
        feature_text = ", ".join(str(item["feature"]) for item in top_features[:3])
        base = f"{algorithm_key} destekleyici tahmininde en etkili alanlar: {feature_text}."
    else:
        base = f"{algorithm_key} için model içi açıklama sınırlı üretildi."
    if limitations:
        base += " " + " ".join(limitations)
    base += " Bu ML çıktısı nihai karar değildir; nihai karar AHP/TOPSIS + kurallar + state machine ile verilir."
    return base


def save_prediction_explanation(conn: sqlite3.Connection, prediction_id: int, explanation: MLExplanation) -> int:
    ensure_ml_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ml_prediction_explanations (
            prediction_id, top_features_json, feature_importance_json,
            decision_path_json, limitations_json, human_readable_text, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(prediction_id),
            _json(explanation.top_features_json),
            _json(explanation.feature_importance_json or {}),
            _json(explanation.decision_path_json or []),
            _json(explanation.limitations),
            explanation.human_readable_text,
            _now(),
        ),
    )
    return int(cur.lastrowid)


def get_prediction_explanation(conn: sqlite3.Connection, prediction_id: int) -> dict | None:
    ensure_ml_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM ml_prediction_explanations WHERE prediction_id=? ORDER BY id DESC LIMIT 1",
        (int(prediction_id),),
    )
    row = cur.fetchone()
    if not row:
        return None
    if isinstance(row, sqlite3.Row):
        data = {key: row[key] for key in row.keys()}
    else:
        keys = [d[0] for d in cur.description]
        data = dict(zip(keys, row))
    for key in ("top_features_json", "feature_importance_json", "decision_path_json", "limitations_json"):
        try:
            data[key[:-5]] = json.loads(data.get(key) or ("{}" if "importance" in key else "[]"))
        except Exception:
            data[key[:-5]] = {} if "importance" in key else []
    return data
