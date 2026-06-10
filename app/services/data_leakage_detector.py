# -*- coding: utf-8 -*-
"""ML/benchmark veri sızıntısı kontrol servisi."""

from __future__ import annotations

from typing import Any, Iterable


def detect_target_leakage(feature_names: Iterable[str], target_name: str | None) -> dict[str, Any]:
    features = {_norm(f) for f in feature_names}
    target = _norm(target_name or "")
    if target and target in features:
        return _report(True, "critical", [f"Hedef değişken feature listesinde yer alıyor: {target_name}."], True)
    return _report(False, "none", [], False)


def detect_future_leakage(dataset_meta: dict[str, Any] | None) -> dict[str, Any]:
    meta = dataset_meta or {}
    train_years = set(int(y) for y in meta.get("train_years", []) if str(y).isdigit())
    test_years = set(int(y) for y in meta.get("test_years", []) if str(y).isdigit())
    if train_years and test_years and max(train_years) > min(test_years):
        return _report(True, "high", ["Gelecek yıl verisi eğitim setine karışmış görünüyor."], True)
    return _report(False, "none", [], False)


def detect_duplicate_entity_leakage(entity_ids: dict[str, Iterable[Any]] | Iterable[Any], splits: dict[str, Iterable[Any]] | None = None) -> dict[str, Any]:
    if isinstance(entity_ids, dict):
        train = set(entity_ids.get("train") or [])
        test = set(entity_ids.get("test") or [])
    else:
        split_map = splits or {}
        ids = list(entity_ids)
        train_idx = set(split_map.get("train_idx") or [])
        test_idx = set(split_map.get("test_idx") or [])
        train = {ids[i] for i in train_idx if i < len(ids)}
        test = {ids[i] for i in test_idx if i < len(ids)}
    overlap = train & test
    if overlap:
        return _report(True, "medium", [f"Aynı entity train/test içinde tekrar ediyor: {len(overlap)} kayıt."], False, {"overlap_count": len(overlap)})
    return _report(False, "none", [], False)


def detect_score_leakage(feature_names: Iterable[str]) -> dict[str, Any]:
    risky_tokens = {"topsis", "skor_top", "final_status", "recommended_status", "nihai_karar", "decision"}
    risky = [f for f in feature_names if any(token in _norm(f) for token in risky_tokens)]
    if risky:
        return _report(True, "high", [f"Karar/skor çıktısı feature olarak kullanılmış olabilir: {risky}."], True, {"risky_features": risky})
    return _report(False, "none", [], False)


def detect_mcdm_output_as_feature(feature_names: Iterable[str]) -> dict[str, Any]:
    risky = [f for f in feature_names if any(token in _norm(f) for token in ("topsis", "ahp", "vikor", "promethee", "closeness"))]
    if risky:
        return _report(True, "high", [f"MCDM çıktısı feature setinde görünüyor: {risky}."], True, {"risky_features": risky})
    return _report(False, "none", [], False)


def generate_leakage_report(
    *,
    feature_names: Iterable[str],
    target_name: str | None = None,
    dataset_meta: dict[str, Any] | None = None,
    entity_ids: dict[str, Iterable[Any]] | None = None,
) -> dict[str, Any]:
    reports = [
        detect_target_leakage(feature_names, target_name),
        detect_score_leakage(feature_names),
        detect_mcdm_output_as_feature(feature_names),
        detect_future_leakage(dataset_meta),
    ]
    if entity_ids is not None:
        reports.append(detect_duplicate_entity_leakage(entity_ids))
    warnings = []
    blocked = False
    level_order = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    max_level = "none"
    for report in reports:
        warnings.extend(report.get("warnings", []))
        blocked = blocked or bool(report.get("blocked"))
        if level_order.get(str(report.get("leakage_level") or ""), 0) > level_order[max_level]:
            max_level = report["leakage_level"]
    detected = bool(warnings)
    summary = (
        "Kritik veri sızıntısı tespit edildi; sonuçlar geçersiz sayılmalıdır."
        if blocked
        else ("Veri sızıntısı riski tespit edildi; raporda uyarılı gösterilmelidir." if detected else "Veri sızıntısı tespit edilmedi.")
    )
    return {
        "leakage_detected": detected,
        "leakage_level": max_level,
        "warnings": warnings,
        "blocked": blocked,
        "summary_text": summary,
    }


def _report(detected: bool, level: str, warnings: list[str], blocked: bool, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "leakage_detected": detected,
        "leakage_level": level,
        "warnings": warnings,
        "blocked": blocked,
        "details": details or {},
        "summary_text": "Veri sızıntısı uyarısı var." if detected else "Veri sızıntısı yok.",
    }


def _norm(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
