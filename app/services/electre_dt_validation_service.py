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
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from statistics import median
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
    "topsis_peer_percentile",
    "topsis_delta_median",
    "basari_delta_median",
    "trend_delta_median",
    "populerlik_delta_median",
    "anket_delta_median",
    "topsis_distance_to_peer_max",
    "topsis_distance_to_peer_min",
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
    "topsis_peer_percentile": "Akran TOPSIS yüzdeliği",
    "topsis_delta_median": "Akran TOPSIS medyan farkı",
    "basari_delta_median": "Akran başarı medyan farkı",
    "trend_delta_median": "Akran trend medyan farkı",
    "populerlik_delta_median": "Akran doluluk medyan farkı",
    "anket_delta_median": "Akran anket medyan farkı",
    "topsis_distance_to_peer_max": "Akran en yükseğe uzaklık",
    "topsis_distance_to_peer_min": "Akran en düşüğe uzaklık",
}

PEER_FEATURE_DEFAULTS = {
    "peer_count": 0.0,
    "topsis_peer_percentile": 0.5,
    "topsis_delta_median": 0.0,
    "basari_delta_median": 0.0,
    "trend_delta_median": 0.0,
    "populerlik_delta_median": 0.0,
    "anket_delta_median": 0.0,
    "topsis_distance_to_peer_max": 0.0,
    "topsis_distance_to_peer_min": 0.0,
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


def _signed_unit(value: Any) -> float:
    return max(-1.0, min(1.0, _finite(value)))


def build_peer_comparison_features(
    rows: list[dict[str, Any]],
) -> dict[int, dict[str, float]]:
    """Her dersi ayni kapsamdaki diger derslerle karsilastiran ozellikleri uretir.

    ``rows`` icinde ``course_id``, ``topsis_score`` ve ``raw_values`` beklenir.
    Hedef ders kendi medyan/yuzdelik hesabina katilmaz (leave-one-out akran
    baglami). Bu fonksiyon etiket kullanmaz; ELECTRE/DT ciktilarindan veri sizmaz.
    """

    result: dict[int, dict[str, float]] = {}
    for row in rows:
        course_id = int(row.get("course_id") or row.get("ders_id") or 0)
        peers = [item for item in rows if item is not row]
        if course_id <= 0 or not peers:
            result[course_id] = dict(PEER_FEATURE_DEFAULTS)
            continue

        own_score = max(0.0, min(100.0, _finite(row.get("topsis_score"))))
        peer_scores = [max(0.0, min(100.0, _finite(item.get("topsis_score")))) for item in peers]
        less = sum(1 for value in peer_scores if value < own_score - 1e-12)
        equal = sum(1 for value in peer_scores if abs(value - own_score) <= 1e-12)
        percentile = (less + 0.5 * equal) / len(peer_scores)

        features = dict(PEER_FEATURE_DEFAULTS)
        features.update(
            {
                "peer_count": float(len(peers)),
                "topsis_peer_percentile": max(0.0, min(1.0, percentile)),
                "topsis_delta_median": _signed_unit((own_score - median(peer_scores)) / 100.0),
                "topsis_distance_to_peer_max": min(1.0, abs(max(peer_scores) - own_score) / 100.0),
                "topsis_distance_to_peer_min": min(1.0, abs(own_score - min(peer_scores)) / 100.0),
            }
        )
        own_raw = dict(row.get("raw_values") or {})
        for criterion in ("basari", "trend", "populerlik", "anket"):
            peer_values = [
                _bounded(dict(item.get("raw_values") or {}).get(criterion))
                for item in peers
            ]
            features[f"{criterion}_delta_median"] = _signed_unit(
                _bounded(own_raw.get(criterion)) - median(peer_values)
            )
        result[course_id] = features
    return result


def peer_assessment(peer_features: dict[str, Any] | None) -> dict[str, Any]:
    """DT hazir olmasa da gosterilebilen seffaf akran tutarlilik ozeti."""

    features = {**PEER_FEATURE_DEFAULTS, **dict(peer_features or {})}
    peer_count = int(max(0.0, _finite(features.get("peer_count"))))
    percentile = max(0.0, min(1.0, _finite(features.get("topsis_peer_percentile"), 0.5)))
    deltas = [
        _signed_unit(features.get(f"{key}_delta_median", 0.0))
        for key in ("basari", "trend", "populerlik", "anket")
    ]
    positive = sum(1 for value in deltas if value > 0.05)
    negative = sum(1 for value in deltas if value < -0.05)
    if peer_count <= 0:
        level = "unavailable"
        label = "Akran karşılaştırması için ders yetersiz"
    elif percentile >= 0.70 and positive >= negative:
        level = "strong"
        label = "Akranlarına göre güçlü"
    elif percentile <= 0.30 and negative > positive:
        level = "weak"
        label = "Akranlarına göre zayıf"
    else:
        level = "balanced"
        label = "Akranlarına yakın / dengeli"
    return {
        "level": level,
        "label": label,
        "peer_count": peer_count,
        "topsis_percentile": percentile,
        "topsis_percentile_100": percentile * 100.0,
        "topsis_delta_median_100": _signed_unit(features.get("topsis_delta_median")) * 100.0,
        "distance_to_peer_max_100": _bounded(
            features.get("topsis_distance_to_peer_max")
        )
        * 100.0,
        "distance_to_peer_min_100": _bounded(
            features.get("topsis_distance_to_peer_min")
        )
        * 100.0,
        "criterion_delta_medians": {
            key: _signed_unit(features.get(f"{key}_delta_median", 0.0))
            for key in ("basari", "trend", "populerlik", "anket")
        },
        "advisory_only": True,
        "changes_final_decision": False,
    }


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
    required = {
        "decision_runs",
        "course_decisions",
        "course_score_breakdowns",
        "curriculum_decision_reviews",
    }
    if not all(_table_exists(conn, table) for table in required):
        return []

    where = [
        "cd.year < ?",
        "dr.status = 'completed'",
        "COALESCE(dr.stale_flag, 0) = 0",
        """EXISTS (
            SELECT 1
            FROM curriculum_decision_reviews review
            WHERE review.status = 'approved'
              AND review.department_id = cd.department_id
              AND (
                  review.fall_run_id = cd.decision_run_id
                  OR review.spring_run_id = cd.decision_run_id
              )
        )""",
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
        SELECT cd.id, cd.course_id, cd.year, cd.semester,
               cd.final_status AS algorithm_final_status,
               cd.old_status, cd.topsis_score, cd.data_confidence_score,
               cd.faculty_id, cd.department_id, b.raw_values_json,
               (
                   SELECT review.payload_json
                   FROM curriculum_decision_reviews review
                   WHERE review.status = 'approved'
                     AND review.department_id = cd.department_id
                     AND (
                         review.fall_run_id = cd.decision_run_id
                         OR review.spring_run_id = cd.decision_run_id
                     )
                   ORDER BY review.id DESC
                   LIMIT 1
               ) AS approved_review_payload_json
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
        # Egitim etiketi algoritmanin kendi final_status cikisi degildir. Kurulca
        # onaylanmis yeni mufredat onizlemesindeki fiili donem listesinden uretilir:
        # listede ise Mufredat(1), degilse Havuz(0). Manuel takaslar bu nedenle
        # dogrudan gercek etikete yansir; DT, ELECTRE'yi taklit etmez.
        try:
            approved_payload = json.loads(row.get("approved_review_payload_json") or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        term_key = "spring" if _normalize_semester(row.get("semester")) == "Bahar" else "fall"
        if not isinstance(approved_payload, dict) or term_key not in approved_payload:
            continue
        term_payload = dict(approved_payload.get(term_key) or {})
        approved_course_ids = {
            int(item.get("course_id") or 0)
            for item in (term_payload.get("items") or [])
            if isinstance(item, dict)
        }
        row["final_status"] = (
            1 if int(row.get("course_id") or 0) in approved_course_ids else 0
        )
        # DT'nin LR sinyalini egitimde ve tahminde ayni semantikle kullanmasi
        # gerekir. Tarihsel bir karar icin sadece o yildan ONCEKI skorlar
        # kullanilarak ilgili yil tahmin edilir; boylece gelecek veri sizintisi
        # olusmaz. Veri yoksa LR servisi notr 0.50 dondurur.
        lr = predict_next_year_trend(cur, int(row.get("course_id") or 0), int(row.get("year") or 0))
        row["lr_trend_forecast"] = lr.get("trend_score_normalized", 0.5)
        records.append(row)

    # Her tarihsel satir da kendi yil/donem/fakulte/bolumundeki diger derslere
    # gore hesaplanir. Hedef yilda uretilen akran ozellikleriyle egitim
    # ozelliklerinin anlami boylece ayni kalir.
    groups: dict[tuple[int, str, int | None, int | None], list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        key = (
            int(row.get("year") or 0),
            _normalize_semester(row.get("semester")),
            int(row["faculty_id"]) if row.get("faculty_id") is not None else None,
            int(row["department_id"]) if row.get("department_id") is not None else None,
        )
        groups[key].append(row)
    for group_rows in groups.values():
        peer_map = build_peer_comparison_features(group_rows)
        for row in group_rows:
            row["peer_features"] = peer_map.get(
                int(row.get("course_id") or 0), dict(PEER_FEATURE_DEFAULTS)
            )
    return records


def _feature_row(
    raw_values: dict[str, Any],
    *,
    lr_trend_forecast: Any = 0.5,
    peer_features: dict[str, Any] | None = None,
    topsis_score: Any,
    data_confidence: Any,
    old_status: Any,
) -> list[float]:
    peer = {**PEER_FEATURE_DEFAULTS, **dict(peer_features or {})}
    return [
        _bounded(raw_values.get("basari")),
        _bounded(raw_values.get("trend")),
        _bounded(lr_trend_forecast),
        _bounded(raw_values.get("populerlik")),
        _bounded(raw_values.get("anket")),
        _bounded(_finite(topsis_score) / 100.0),
        _bounded(data_confidence),
        _finite(old_status, 0.0),
        _bounded(peer.get("topsis_peer_percentile", 0.5)),
        _signed_unit(peer.get("topsis_delta_median")),
        _signed_unit(peer.get("basari_delta_median")),
        _signed_unit(peer.get("trend_delta_median")),
        _signed_unit(peer.get("populerlik_delta_median")),
        _signed_unit(peer.get("anket_delta_median")),
        _bounded(peer.get("topsis_distance_to_peer_max")),
        _bounded(peer.get("topsis_distance_to_peer_min")),
    ]


def _dataset(records: list[dict[str, Any]]) -> tuple[list[list[float]], list[int]]:
    X: list[list[float]] = []
    y: list[int] = []
    for row in records:
        status = row.get("final_status")
        if status is None:
            continue
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
                peer_features=dict(row.get("peer_features") or {}),
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
            f"DT için onaylanmış geçmiş kurul örneği yetersiz: "
            f"{sample_count}/{min_training_samples}. Hedef yıldan önce kurulca "
            "onaylanmış müfredat kararları bekleniyor."
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
    """Hedef karar calistirmasi icin kurul etiketli bagimsiz DT modeli hazirlar."""

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
    # sklearn Tree.feature / Tree.threshold runtime'da ndarray donduren ozellikler;
    # tip stub'larinda eksik oldugu icin getattr ile erisilir.
    feature_arr = getattr(tree, "feature")
    threshold_arr = getattr(tree, "threshold")
    decision_path = model.decision_path([feature_values])
    node_ids = getattr(decision_path, "indices")
    parts: list[str] = []
    for node_id in node_ids:
        feature_index = int(feature_arr[node_id])
        if feature_index < 0:
            continue
        feature_name = FEATURE_NAMES[feature_index]
        threshold = float(threshold_arr[node_id])
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


def _policy_advisory_prediction(
    *,
    topsis_score: Any,
    old_status: Any,
    electre_status: int,
    peer_result: dict[str, Any],
    policy: dict[str, Any] | None,
) -> tuple[int, float, str]:
    """Model yokken politika esikleri + akran baglamiyla dusuk guvenli oneri."""

    source = dict(policy or {})
    keep = _finite(source.get("curriculum_keep_threshold"), 70.0)
    pool = _finite(source.get("pool_threshold"), 50.0)
    rest = _finite(source.get("rest_threshold"), 40.0)
    score = max(0.0, min(100.0, _finite(topsis_score)))
    peer_level = str(peer_result.get("level") or "")
    try:
        old_status_int = int(old_status)
    except (TypeError, ValueError):
        old_status_int = None

    if score >= keep or (peer_level == "strong" and score >= pool):
        predicted = 1
    elif score >= pool:
        predicted = 0
    elif score >= rest:
        predicted = -1
    else:
        predicted = -2

    if old_status_int == 1 and score >= keep:
        predicted = 1
    elif old_status_int == 1 and predicted < 0 and score >= pool:
        predicted = 0
    elif peer_level == "weak" and predicted == 1 and score < keep:
        predicted = 0

    distance = min(abs(score - keep), abs(score - pool), abs(score - rest))
    confidence = 0.35 + min(0.25, distance / 100.0)
    if predicted == int(electre_status):
        confidence += 0.05
    confidence = max(0.30, min(0.65, confidence))
    reason = (
        f"DT modeli eğitilemediği için politika destekli öneri üretildi "
        f"(TOPSIS {score:.2f}; eşikler {keep:.0f}/{pool:.0f}/{rest:.0f}; "
        f"akran: {peer_result.get('label')})."
    )
    return predicted, confidence, reason


def evaluate_course_with_dt(
    context: DTValidationContext,
    *,
    raw_values: dict[str, Any],
    lr_trend_forecast: Any = 0.5,
    peer_features: dict[str, Any] | None = None,
    topsis_score: Any,
    data_confidence: Any,
    old_status: Any,
    electre_status: int,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bir ders icin DT ikinci gorusunu ve ELECTRE karsilastirmasini uretir."""

    normalized_peer = {**PEER_FEATURE_DEFAULTS, **dict(peer_features or {})}
    peer_result = peer_assessment(normalized_peer)

    if not context.available or context.model is None:
        prediction, confidence, advisory_reason = _policy_advisory_prediction(
            topsis_score=topsis_score,
            old_status=old_status,
            electre_status=int(electre_status),
            peer_result=peer_result,
            policy=policy,
        )
        comparison, comparison_text = _comparison(prediction, int(electre_status))
        return {
            "available": False,
            "predicted_status": prediction,
            "predicted_label": _status_label(prediction),
            "confidence": confidence,
            "comparison": comparison,
            "rule_path": "DT yok; politika eşikleri + akran özeti",
            "explanation": (
                f"{context.reason} {advisory_reason} {comparison_text} "
                "Bu sonuç düşük güvenli destek sinyalidir; nihai kararı değiştirmez."
            ),
            "context": context.summary(),
            "lr_trend_forecast": _bounded(lr_trend_forecast),
            "peer_features": normalized_peer,
            "peer_assessment": peer_result,
            "fallback_advisory": True,
            "advisory_only": True,
            "should_influence_decision": False,
        }

    values = _feature_row(
        raw_values,
        lr_trend_forecast=lr_trend_forecast,
        peer_features=normalized_peer,
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
        f"Akran kontrolü: {peer_result['label']} "
        f"(TOPSIS yüzdeliği %{peer_result['topsis_percentile_100']:.1f}, "
        f"medyan farkı {peer_result['topsis_delta_median_100']:+.2f} puan). "
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
        "lr_trend_forecast": _bounded(lr_trend_forecast),
        "peer_features": normalized_peer,
        "peer_assessment": peer_result,
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
