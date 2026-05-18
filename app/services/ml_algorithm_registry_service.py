# -*- coding: utf-8 -*-
"""ML algoritma registry ve kullanım rolü yönetimi."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime

from app.db.schema_compat import ensure_ml_governance_schema

PRODUCTION_DECISION = "production_decision"
ADVISORY_ML = "advisory_ml"
BENCHMARK_ONLY = "benchmark_only"
EXPERIMENTAL = "experimental"


@dataclass(frozen=True)
class MLAlgorithmConfig:
    algorithm_key: str
    display_name: str
    algorithm_type: str
    usage_role: str
    default_enabled: bool
    min_training_samples: int
    min_samples_per_class: int | None
    requires_validation: bool
    supports_confidence: bool
    supports_explainability: bool
    notes: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


DEFAULT_ALGORITHMS: list[MLAlgorithmConfig] = [
    MLAlgorithmConfig("linear_regression", "Linear Regression", "regression", ADVISORY_ML, True, 50, None, True, True, True, "Destekleyici başarı/skor tahmini."),
    MLAlgorithmConfig("decision_tree", "Decision Tree", "classification", ADVISORY_ML, True, 100, 10, True, True, True, "Destekleyici statü sınıflandırması; küçük veride overfit riski yüksektir."),
    MLAlgorithmConfig("random_forest", "Random Forest", "classification", ADVISORY_ML, True, 200, 10, True, True, True, "Destekleyici topluluk modeli; üretim kararı için yüksek veri gerektirir."),
    MLAlgorithmConfig("logistic_regression", "Logistic Regression", "classification", BENCHMARK_ONLY, True, 100, 10, True, True, True, "Sadece benchmark ve deneysel karşılaştırma."),
    MLAlgorithmConfig("naive_bayes", "Naive Bayes", "classification", BENCHMARK_ONLY, True, 100, 10, True, True, False, "Sadece benchmark ve hızlı baseline."),
    MLAlgorithmConfig("xgboost", "XGBoost", "classification", BENCHMARK_ONLY, False, 500, 20, True, True, True, "Kuruluysa benchmark; aksi halde GradientBoosting fallback kullanılabilir."),
    MLAlgorithmConfig("gradient_boosting", "Gradient Boosting", "classification", BENCHMARK_ONLY, True, 500, 20, True, True, True, "XGBoost yoksa benchmark fallback."),
    MLAlgorithmConfig("clustering", "Clustering", "clustering", BENCHMARK_ONLY, True, 100, None, True, False, False, "KMeans/DBSCAN gibi desen analizi modelleri."),
    MLAlgorithmConfig("baseline_historical_average", "Historical Average Baseline", "baseline", ADVISORY_ML, True, 10, None, False, True, False, "Az veride güvenli, açıklanabilir destek tahmini."),
]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _bool(value) -> bool:
    return bool(int(value)) if isinstance(value, (int, str)) and str(value).isdigit() else bool(value)


def _row_to_config(row: sqlite3.Row | tuple) -> MLAlgorithmConfig:
    if isinstance(row, sqlite3.Row):
        data = {key: row[key] for key in row.keys()}
    else:
        keys = [
            "algorithm_key", "display_name", "algorithm_type", "usage_role", "default_enabled",
            "min_training_samples", "min_samples_per_class", "requires_validation",
            "supports_confidence", "supports_explainability", "notes",
        ]
        data = dict(zip(keys, row))
    return MLAlgorithmConfig(
        algorithm_key=str(data["algorithm_key"]),
        display_name=str(data["display_name"]),
        algorithm_type=str(data["algorithm_type"]),
        usage_role=str(data["usage_role"]),
        default_enabled=_bool(data.get("default_enabled")),
        min_training_samples=int(data.get("min_training_samples") or 0),
        min_samples_per_class=int(data["min_samples_per_class"]) if data.get("min_samples_per_class") is not None else None,
        requires_validation=_bool(data.get("requires_validation")),
        supports_confidence=_bool(data.get("supports_confidence")),
        supports_explainability=_bool(data.get("supports_explainability")),
        notes=data.get("notes"),
    )


def seed_default_algorithm_registry(conn: sqlite3.Connection) -> list[dict]:
    """Varsayılan ML algoritma konumlandırmasını idempotent şekilde oluşturur."""
    ensure_ml_governance_schema(conn, commit=False)
    cur = conn.cursor()
    for cfg in DEFAULT_ALGORITHMS:
        cur.execute(
            """
            INSERT INTO ml_algorithm_registry (
                algorithm_key, display_name, algorithm_type, usage_role, default_enabled,
                min_training_samples, min_samples_per_class, requires_validation,
                supports_confidence, supports_explainability, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(algorithm_key) DO UPDATE SET
                display_name = excluded.display_name,
                algorithm_type = excluded.algorithm_type,
                min_training_samples = excluded.min_training_samples,
                min_samples_per_class = excluded.min_samples_per_class,
                requires_validation = excluded.requires_validation,
                supports_confidence = excluded.supports_confidence,
                supports_explainability = excluded.supports_explainability,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (
                cfg.algorithm_key,
                cfg.display_name,
                cfg.algorithm_type,
                cfg.usage_role,
                1 if cfg.default_enabled else 0,
                cfg.min_training_samples,
                cfg.min_samples_per_class,
                1 if cfg.requires_validation else 0,
                1 if cfg.supports_confidence else 0,
                1 if cfg.supports_explainability else 0,
                cfg.notes,
                _now(),
                _now(),
            ),
        )
    return list_algorithm_registry(conn)


def list_algorithm_registry(conn: sqlite3.Connection, usage_role: str | None = None) -> list[dict]:
    seed_needed = False
    ensure_ml_governance_schema(conn, commit=False)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM ml_algorithm_registry")
    if int(cur.fetchone()[0] or 0) == 0:
        seed_needed = True
    if seed_needed:
        seed_default_algorithm_registry(conn)

    sql = """
        SELECT algorithm_key, display_name, algorithm_type, usage_role, default_enabled,
               min_training_samples, min_samples_per_class, requires_validation,
               supports_confidence, supports_explainability, notes
        FROM ml_algorithm_registry
    """
    params: list = []
    if usage_role:
        sql += " WHERE usage_role = ?"
        params.append(usage_role)
    sql += " ORDER BY CASE usage_role WHEN 'production_decision' THEN 0 WHEN 'advisory_ml' THEN 1 WHEN 'benchmark_only' THEN 2 ELSE 3 END, display_name"
    cur.execute(sql, tuple(params))
    return [_row_to_config(row).as_dict() for row in cur.fetchall()]


def get_algorithm_config(conn: sqlite3.Connection, algorithm_key: str) -> MLAlgorithmConfig:
    ensure_ml_governance_schema(conn, commit=False)
    if not algorithm_key:
        raise ValueError("algorithm_key zorunludur")
    seed_default_algorithm_registry(conn)
    cur = conn.cursor()
    normalized = _normalize_algorithm_key(algorithm_key)
    cur.execute(
        """
        SELECT algorithm_key, display_name, algorithm_type, usage_role, default_enabled,
               min_training_samples, min_samples_per_class, requires_validation,
               supports_confidence, supports_explainability, notes
        FROM ml_algorithm_registry
        WHERE algorithm_key = ?
        LIMIT 1
        """,
        (normalized,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"ML algoritması bulunamadı: {algorithm_key}")
    return _row_to_config(row)


def update_algorithm_usage_role(
    conn: sqlite3.Connection,
    algorithm_key: str,
    *,
    usage_role: str | None = None,
    default_enabled: bool | None = None,
    min_training_samples: int | None = None,
    min_samples_per_class: int | None = None,
    notes: str | None = None,
) -> dict:
    valid_roles = {PRODUCTION_DECISION, ADVISORY_ML, BENCHMARK_ONLY, EXPERIMENTAL}
    if usage_role is not None and usage_role not in valid_roles:
        raise ValueError(f"Geçersiz kullanım rolü: {usage_role}")
    cfg = get_algorithm_config(conn, algorithm_key)
    updates = {
        "usage_role": usage_role if usage_role is not None else cfg.usage_role,
        "default_enabled": 1 if (default_enabled if default_enabled is not None else cfg.default_enabled) else 0,
        "min_training_samples": int(min_training_samples if min_training_samples is not None else cfg.min_training_samples),
        "min_samples_per_class": min_samples_per_class if min_samples_per_class is not None else cfg.min_samples_per_class,
        "notes": notes if notes is not None else cfg.notes,
        "updated_at": _now(),
        "algorithm_key": cfg.algorithm_key,
    }
    conn.execute(
        """
        UPDATE ml_algorithm_registry
        SET usage_role = :usage_role,
            default_enabled = :default_enabled,
            min_training_samples = :min_training_samples,
            min_samples_per_class = :min_samples_per_class,
            notes = :notes,
            updated_at = :updated_at
        WHERE algorithm_key = :algorithm_key
        """,
        updates,
    )
    return get_algorithm_config(conn, cfg.algorithm_key).as_dict()


def is_algorithm_allowed_for_role(conn: sqlite3.Connection, algorithm_key: str, role: str) -> bool:
    cfg = get_algorithm_config(conn, algorithm_key)
    if role == PRODUCTION_DECISION:
        return cfg.usage_role == PRODUCTION_DECISION
    if role == ADVISORY_ML:
        return cfg.usage_role in {PRODUCTION_DECISION, ADVISORY_ML}
    if role == BENCHMARK_ONLY:
        return cfg.usage_role in {PRODUCTION_DECISION, ADVISORY_ML, BENCHMARK_ONLY, EXPERIMENTAL}
    return cfg.usage_role == role


def _normalize_algorithm_key(value: str) -> str:
    mapping = {
        "lr": "linear_regression",
        "linearregression": "linear_regression",
        "linear_regression": "linear_regression",
        "dt": "decision_tree",
        "decisiontree": "decision_tree",
        "decision_tree": "decision_tree",
        "rf": "random_forest",
        "randomforest": "random_forest",
        "random_forest": "random_forest",
        "logisticregression": "logistic_regression",
        "logistic_regression": "logistic_regression",
        "naivebayes": "naive_bayes",
        "naive_bayes": "naive_bayes",
        "xgboostlike": "xgboost",
        "xgboost": "xgboost",
        "gradientboosting": "gradient_boosting",
        "gradient_boosting": "gradient_boosting",
    }
    key = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    return mapping.get(key, key)
