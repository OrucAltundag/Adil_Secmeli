# -*- coding: utf-8 -*-
"""ELECTRE TRI-B sonuclarini bagimsiz Decision Tree ile dogrular.

DT, ELECTRE etiketlerini yeniden ogrenmez. Hedef yildan once tamamlanmis karar
calistirmalarindaki ham kriterler ve akademik olarak uygulanmis ``final_status``
etiketleriyle egitilir. Boylece DT sonucu, ELECTRE kararinin yerine gecmeyen
bagimsiz ve okunabilir bir ikinci gorus olarak kullanilir.
"""

from __future__ import annotations

import json
import math
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from sklearn.metrics import balanced_accuracy_score
from sklearn.tree import DecisionTreeClassifier

from app.services.lr_trend_prediction_service import predict_next_year_trend


FEATURE_NAMES = (
    "basari",
    "trend",
    "lr_trend_forecast",
    "populerlik",
    "anket",
    "topsis_score",
    "data_confidence",
    "old_status",
)

FEATURE_LABELS = {
    "basari": "Başarı",
    "trend": "Trend",
    "lr_trend_forecast": "LR sonraki yıl tahmini",
    "populerlik": "Doluluk / talep",
    "anket": "Anket / tercih",
    "topsis_score": "TOPSIS",
    "data_confidence": "Veri güveni",
    "old_status": "Önceki statü",
}

STATUS_LABELS = {
    1: "Müfredat",
    0: "Havuz",
    -1: "Dinlenme",
    -2: "İptal adayı",
}

MIN_TRAINING_SAMPLES = 100
MIN_SAMPLES_PER_CLASS = 10


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    return result if math.isfinite(result) else float(default)


def _bounded(value: Any) -> float:
    return max(0.0, min(1.0, _finite(value)))


def _normalize_semester(value: str | None) -> str:
    text = str(value or "").strip().lower()
    if text.startswith("b") or text.startswith("s"):
        return "Bahar"
    return "Guz"


def _status_label(value: int | None) -> str:
    if value is None:
        return "Üretilemedi"
    return STATUS_LABELS.get(int(value), str(value))


@dataclass
class DTValidationContext:
    available: bool
    reason: str
    target_year: int
    training_scope: str
    sample_count: int = 0
    class_counts: dict[int, int] = field(default_factory=dict)
    validation_score: float | None = None
    model: DecisionTreeClassifier | None = None

    def summary(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "reason": self.reason,
            "target_year": self.target_year,
            "training_scope": self.training_scope,
            "sample_count": self.sample_count,
            "class_counts": {str(key): value for key, value in self.class_counts.items()},
            "validation_score": self.validation_score,
            "feature_names": list(FEATURE_NAMES),
            "advisory_only": True,
            "should_influence_decision": False,
        }


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    ).fetchone()
    return bool(row)


def _load_historical_records(
    conn: sqlite3.Connection,
    *,
    target_year: int,
    faculty_id: int | None,
    department_id: int | None,
    semester: str | None,
    global_scope: bool,
) -> list[dict[str, Any]]:
    required = {"decision_runs", "course_decisions", "course_score_breakdowns"}
    if not all(_table_exists(conn, table) for table in required):
        return []

    where = [
        "cd.year < ?",
        "cd.final_status IS NOT NULL",
        "dr.status = 'completed'",
        "COALESCE(dr.stale_flag, 0) = 0",
    ]
    params: list[Any] = [int(target_year)]
    if not global_scope and faculty_id is not None:
        where.append("cd.faculty_id = ?")
        params.append(int(faculty_id))
    if not global_scope and department_id is not None:
        where.append("cd.department_id = ?")
        params.append(int(department_id))
    if semester:
        where.append("LOWER(SUBSTR(TRIM(COALESCE(cd.semester, '')), 1, 1)) = ?")
        params.append(_normalize_semester(semester)[0].lower())

    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT cd.id, cd.course_id, cd.year, cd.semester, cd.final_status,
               cd.old_status, cd.topsis_score, cd.data_confidence_score,
               cd.faculty_id, cd.department_id, b.raw_values_json
        FROM course_decisions cd
        JOIN decision_runs dr ON dr.id = cd.decision_run_id
        LEFT JOIN course_score_breakdowns b
          ON b.decision_run_id = cd.decision_run_id AND b.course_id = cd.course_id
        WHERE {' AND '.join(where)}
        ORDER BY cd.id DESC
        """,
        tuple(params),
    )
    keys = [str(item[0]) for item in cur.description]

    # Ayni ders/yil/donem icin tekrarlanan eski run'lar egitim agirligini
    # yapay olarak artirmasin; en yeni tamamlanmis kaydi kullan.
    seen: set[tuple[int, int, str]] = set()
    records: list[dict[str, Any]] = []
    for raw_row in cur.fetchall():
        row = dict(zip(keys, raw_row))
        dedupe_key = (
            int(row.get("course_id") or 0),
            int(row.get("year") or 0),
            _normalize_semester(row.get("semester")),
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        try:
            raw_values = json.loads(row.get("raw_values_json") or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            raw_values = {}
        if not isinstance(raw_values, dict):
            raw_values = {}
        row["raw_values"] = raw_values
        # DT'nin LR sinyalini egitimde ve tahminde ayni semantikle kullanmasi
        # gerekir. Tarihsel bir karar icin sadece o yildan ONCEKI skorlar
        # kullanilarak ilgili yil tahmin edilir; boylece gelecek veri sizintisi
        # olusmaz. Veri yoksa LR servisi notr 0.50 dondurur.
        lr = predict_next_year_trend(cur, int(row.get("course_id") or 0), int(row.get("year") or 0))
        row["lr_trend_forecast"] = lr.get("trend_score_normalized", 0.5)
        records.append(row)
    return records


def _feature_row(
    raw_values: dict[str, Any],
    *,
    lr_trend_forecast: Any = 0.5,
    topsis_score: Any,
    data_confidence: Any,
    old_status: Any,
) -> list[float]:
    return [
        _bounded(raw_values.get("basari")),
        _bounded(raw_values.get("trend")),
        _bounded(lr_trend_forecast),
        _bounded(raw_values.get("populerlik")),
        _bounded(raw_values.get("anket")),
        _bounded(_finite(topsis_score) / 100.0),
        _bounded(data_confidence),
        _finite(old_status, 0.0),
    ]


def _dataset(records: list[dict[str, Any]]) -> tuple[list[list[float]], list[int]]:
    X: list[list[float]] = []
    y: list[int] = []
    for row in records:
        status = row.get("final_status")
        try:
            status_int = int(status)
        except (TypeError, ValueError):
            continue
        if status_int not in STATUS_LABELS:
            continue
        X.append(
            _feature_row(
                dict(row.get("raw_values") or {}),
                lr_trend_forecast=row.get("lr_trend_forecast", 0.5),
                topsis_score=row.get("topsis_score"),
                data_confidence=row.get("data_confidence_score"),
                old_status=row.get("old_status"),
            )
        )
        y.append(status_int)
    return X, y


def _readiness_reason(
    sample_count: int,
    class_counts: Counter[int],
    min_training_samples: int,
    min_samples_per_class: int,
) -> str | None:
    if sample_count < min_training_samples:
        return (
            f"DT için geçmiş örnek sayısı yetersiz: {sample_count}/{min_training_samples}. "
            "Hedef yıldan önceki tamamlanmış kararlar bekleniyor."
        )
    if len(class_counts) < 2:
        return "DT için en az iki farklı geçmiş final statüsü gerekir."
    weak = {key: value for key, value in class_counts.items() if value < min_samples_per_class}
    if weak:
        readable = ", ".join(f"{_status_label(key)}={value}" for key, value in sorted(weak.items()))
        return (
            f"DT sınıf örnekleri yetersiz ({readable}); her sınıf için en az "
            f"{min_samples_per_class} kayıt gerekir."
        )
    return None


def _temporal_validation(records: list[dict[str, Any]]) -> float | None:
    years = sorted({int(row.get("year") or 0) for row in records if row.get("year") is not None})
    if len(years) < 2:
        return None
    validation_year = years[-1]
    train_rows = [row for row in records if int(row.get("year") or 0) < validation_year]
    test_rows = [row for row in records if int(row.get("year") or 0) == validation_year]
    X_train, y_train = _dataset(train_rows)
    X_test, y_test = _dataset(test_rows)
    if len(set(y_train)) < 2 or not X_test:
        return None
    model = DecisionTreeClassifier(
        max_depth=4,
        min_samples_leaf=max(2, len(X_train) // 40),
        class_weight="balanced",
        random_state=42,
    )
    model.fit(X_train, y_train)
    return float(balanced_accuracy_score(y_test, model.predict(X_test)))


def prepare_dt_validation_context(
    conn: sqlite3.Connection,
    *,
    target_year: int,
    faculty_id: int | None,
    department_id: int | None = None,
    semester: str | None = None,
    min_training_samples: int = MIN_TRAINING_SAMPLES,
    min_samples_per_class: int = MIN_SAMPLES_PER_CLASS,
) -> DTValidationContext:
    """Hedef karar calistirmasi icin tek bir bagimsiz DT modeli hazirlar."""

    attempts = [False]
    if faculty_id is not None or department_id is not None:
        attempts.append(True)

    last_reason = "DT geçmiş verisi bulunamadı."
    last_count = 0
    last_classes: Counter[int] = Counter()
    for global_scope in attempts:
        records = _load_historical_records(
            conn,
            target_year=int(target_year),
            faculty_id=faculty_id,
            department_id=department_id,
            semester=semester,
            global_scope=global_scope,
        )
        X, y = _dataset(records)
        class_counts: Counter[int] = Counter(y)
        reason = _readiness_reason(
            len(X), class_counts, int(min_training_samples), int(min_samples_per_class)
        )
        scope_name = "global_gecmis" if global_scope else "secili_kapsam_gecmisi"
        last_reason = reason or ""
        last_count = len(X)
        last_classes = class_counts
        if reason:
            continue

        validation_score = _temporal_validation(records)
        model = DecisionTreeClassifier(
            max_depth=4,
            min_samples_leaf=max(2, len(X) // 40),
            class_weight="balanced",
            random_state=42,
        )
        model.fit(X, y)
        return DTValidationContext(
            available=True,
            reason="DT geçmiş final kararlarıyla eğitildi; sonuç yalnızca destekleyicidir.",
            target_year=int(target_year),
            training_scope=scope_name,
            sample_count=len(X),
            class_counts=dict(class_counts),
            validation_score=validation_score,
            model=model,
        )

    return DTValidationContext(
        available=False,
        reason=last_reason,
        target_year=int(target_year),
        training_scope="global_gecmis" if len(attempts) > 1 else "secili_kapsam_gecmisi",
        sample_count=last_count,
        class_counts=dict(last_classes),
    )


def _rule_path(model: DecisionTreeClassifier, feature_values: list[float]) -> str:
    tree = model.tree_
    node_ids = model.decision_path([feature_values]).indices
    parts: list[str] = []
    for node_id in node_ids:
        feature_index = int(tree.feature[node_id])
        if feature_index < 0:
            continue
        feature_name = FEATURE_NAMES[feature_index]
        threshold = float(tree.threshold[node_id])
        value = float(feature_values[feature_index])
        operator = "≤" if value <= threshold else ">"
        parts.append(f"{FEATURE_LABELS[feature_name]} {operator} {threshold:.3f}")
    return " → ".join(parts) if parts else "Tek yapraklı DT modeli"


def _comparison(predicted_status: int, electre_status: int) -> tuple[str, str]:
    if predicted_status == electre_status:
        return "agree", "DT, ELECTRE TRI-B önerisini destekliyor."
    if predicted_status > electre_status:
        return (
            "dt_more_positive",
            "DT geçmiş karar örüntülerine göre ELECTRE'den daha olumlu bir statü öneriyor.",
        )
    return (
        "dt_more_cautious",
        "DT geçmiş karar örüntülerine göre ELECTRE'den daha temkinli bir statü öneriyor.",
    )


def evaluate_course_with_dt(
    context: DTValidationContext,
    *,
    raw_values: dict[str, Any],
    lr_trend_forecast: Any = 0.5,
    topsis_score: Any,
    data_confidence: Any,
    old_status: Any,
    electre_status: int,
) -> dict[str, Any]:
    """Bir ders icin DT ikinci gorusunu ve ELECTRE karsilastirmasini uretir."""

    if not context.available or context.model is None:
        return {
            "available": False,
            "predicted_status": None,
            "predicted_label": "Veri yetersiz",
            "confidence": None,
            "comparison": "unavailable",
            "rule_path": "",
            "explanation": context.reason,
            "context": context.summary(),
            "advisory_only": True,
            "should_influence_decision": False,
        }

    values = _feature_row(
        raw_values,
        lr_trend_forecast=lr_trend_forecast,
        topsis_score=topsis_score,
        data_confidence=data_confidence,
        old_status=old_status,
    )
    prediction = int(context.model.predict([values])[0])
    probabilities = context.model.predict_proba([values])[0]
    classes = [int(value) for value in context.model.classes_]
    probability_map = {
        str(status): float(probability) for status, probability in zip(classes, probabilities)
    }
    confidence = float(max(probabilities)) if len(probabilities) else 0.0
    comparison, comparison_text = _comparison(prediction, int(electre_status))
    path = _rule_path(context.model, values)
    explanation = (
        f"DT önerisi: {_status_label(prediction)} (güven {confidence:.2f}). "
        f"ELECTRE önerisi: {_status_label(int(electre_status))}. {comparison_text} "
        "DT nihai kararı değiştirmez; yalnızca kurul incelemesi için ikinci görüş sağlar."
    )
    return {
        "available": True,
        "predicted_status": prediction,
        "predicted_label": _status_label(prediction),
        "confidence": confidence,
        "comparison": comparison,
        "rule_path": path,
        "explanation": explanation,
        "probabilities": probability_map,
        "context": context.summary(),
        "advisory_only": True,
        "should_influence_decision": False,
    }


def comparison_label(value: str | None) -> str:
    return {
        "agree": "Uyumlu",
        "dt_more_positive": "DT daha olumlu",
        "dt_more_cautious": "DT daha temkinli",
        "unavailable": "Veri yetersiz",
    }.get(str(value or ""), "Bilinmiyor")
