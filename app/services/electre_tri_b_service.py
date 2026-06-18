# -*- coding: utf-8 -*-
"""Kriter bazli ELECTRE TRI-B ders siniflandirma servisi.

TOPSIS genel performans puanini uretir; bu modul ise dersin ham kriterlerini
referans profillerle karsilastirarak sirali akademik karar kategorisine atar.
Varsayilan atama kurali, ust kategoriye gecis icin yeterli kanit isteyen
``pessimistic`` yaklasimdir.
"""

from __future__ import annotations

import math
from typing import Any

from app.services.havuz_karar import (
    STATU_DINLENMEDE,
    STATU_HAVUZDA,
    STATU_IPTAL,
    STATU_MUFREDATTA,
)

CRITERIA = ("basari", "trend", "populerlik", "anket")
CRITERION_LABELS = {
    "basari": "Basari",
    "trend": "Trend",
    "populerlik": "Doluluk / talep",
    "anket": "Anket / tercih",
}

DEFAULT_Q = {key: 0.05 for key in CRITERIA}
DEFAULT_P = {key: 0.15 for key in CRITERIA}
DEFAULT_VETO = {
    "basari": 0.25,
    "trend": None,
    "populerlik": None,
    "anket": None,
}


def _finite(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)
    return result if math.isfinite(result) else float(default)


def _bounded(value: Any) -> float:
    return max(0.0, min(1.0, _finite(value)))


def _normalized_weights(weights: dict[str, Any]) -> dict[str, float]:
    clean = {key: max(0.0, _finite(weights.get(key))) for key in CRITERIA}
    total = sum(clean.values())
    if total <= 1e-12:
        raise ValueError("ELECTRE TRI-B icin AHP agirliklari bos veya gecersiz.")
    return {key: value / total for key, value in clean.items()}


def _threshold_map(raw: Any, defaults: dict[str, Any]) -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    result: dict[str, Any] = {}
    for key in CRITERIA:
        value = source.get(key, defaults.get(key))
        result[key] = None if value is None else _bounded(value)
    return result


def _profile_values(policy: dict[str, Any]) -> list[dict[str, Any]]:
    """Politika esiklerini kriter bazli sinir profillerine donusturur.

    ``electre_profiles`` verilirse kriter bazli ozel degerler kullanilir.
    Aksi halde mevcut 70/50/40 politika esikleri tum kriterlere uygulanir.
    30 esigi ayri bir kategori yaratmaz; iptal adayi aciklamasinda kritik alt
    sinir olarak korunur.
    """
    custom = policy.get("electre_profiles")
    if isinstance(custom, list) and custom:
        profiles: list[dict[str, Any]] = []
        for item in custom:
            if not isinstance(item, dict):
                continue
            status = int(item.get("status"))
            values = item.get("values") or {}
            profiles.append(
                {
                    "name": str(item.get("name") or status),
                    "status": status,
                    "values": {key: _bounded(values.get(key)) for key in CRITERIA},
                }
            )
        if profiles:
            return profiles

    boundaries = (
        ("Mufredat", STATU_MUFREDATTA, _finite(policy.get("curriculum_keep_threshold"), 70.0) / 100.0),
        ("Havuz", STATU_HAVUZDA, _finite(policy.get("pool_threshold"), 50.0) / 100.0),
        ("Dinlenme", STATU_DINLENMEDE, _finite(policy.get("rest_threshold"), 40.0) / 100.0),
    )
    return [
        {
            "name": name,
            "status": status,
            "values": {key: _bounded(boundary) for key in CRITERIA},
        }
        for name, status, boundary in boundaries
    ]


def partial_concordance(alternative: float, profile: float, q: float, p: float) -> float:
    """Fayda yonlu bir kriter icin c_j(a, b_h)."""
    if p <= q:
        raise ValueError("ELECTRE tercih esigi p, kayitsizlik esigi q'dan buyuk olmalidir.")
    difference = float(alternative) - float(profile)
    if difference >= -q:
        return 1.0
    if difference <= -p:
        return 0.0
    value = (difference + p) / (p - q)
    if value <= 1e-12:
        return 0.0
    if value >= 1.0 - 1e-12:
        return 1.0
    return round(value, 15)


def partial_discordance(
    alternative: float,
    profile: float,
    p: float,
    veto: float | None,
) -> float:
    """Profil lehine fark buyudukce veto derecesini 0-1 araliginda uretir."""
    if veto is None:
        return 0.0
    if veto <= p:
        raise ValueError("ELECTRE veto esigi v, tercih esigi p'den buyuk olmalidir.")
    deficit = float(profile) - float(alternative)
    if deficit <= p:
        return 0.0
    if deficit >= veto:
        return 1.0
    return (deficit - p) / (veto - p)


def compare_to_profile(
    values: dict[str, Any],
    profile: dict[str, Any],
    weights: dict[str, Any],
    *,
    q: dict[str, Any] | None = None,
    p: dict[str, Any] | None = None,
    veto: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_weights = _normalized_weights(weights)
    q_map = _threshold_map(q, DEFAULT_Q)
    p_map = _threshold_map(p, DEFAULT_P)
    veto_map = _threshold_map(veto, DEFAULT_VETO)
    profile_values = dict(profile.get("values") or {})

    partial_c: dict[str, float] = {}
    partial_d: dict[str, float] = {}
    for key in CRITERIA:
        alt = _bounded(values.get(key))
        boundary = _bounded(profile_values.get(key))
        q_value = float(q_map[key])
        p_value = float(p_map[key])
        partial_c[key] = partial_concordance(alt, boundary, q_value, p_value)
        partial_d[key] = partial_discordance(alt, boundary, p_value, veto_map[key])

    concordance = sum(normalized_weights[key] * partial_c[key] for key in CRITERIA)
    credibility = concordance
    if concordance < 1.0 - 1e-12:
        for key in CRITERIA:
            discordance = partial_d[key]
            if discordance > concordance:
                credibility *= (1.0 - discordance) / (1.0 - concordance)
    credibility = max(0.0, min(1.0, credibility))

    strong = [key for key in CRITERIA if partial_c[key] >= 0.999]
    weak = [key for key in CRITERIA if partial_c[key] < 0.5]
    vetoed = [key for key in CRITERIA if partial_d[key] >= 0.999]
    return {
        "profile": str(profile.get("name") or ""),
        "status": int(profile.get("status")),
        "profile_values": {key: _bounded(profile_values.get(key)) for key in CRITERIA},
        "partial_concordance": partial_c,
        "discordance": partial_d,
        "concordance": concordance,
        "credibility": credibility,
        "strong_criteria": strong,
        "weak_criteria": weak,
        "vetoed_criteria": vetoed,
    }


def assign_course_electre_tri_b(
    values: dict[str, Any],
    weights: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Dersi pessimistic ELECTRE TRI-B kuraliyla akademik kategoriye atar."""
    lambda_cut = _finite(policy.get("electre_lambda"), 0.65)
    if not 0.5 <= lambda_cut <= 1.0:
        raise ValueError("ELECTRE lambda degeri 0.50-1.00 araliginda olmalidir.")

    q_map = _threshold_map(policy.get("electre_q"), DEFAULT_Q)
    p_map = _threshold_map(policy.get("electre_p"), DEFAULT_P)
    veto_map = _threshold_map(policy.get("electre_veto"), DEFAULT_VETO)
    profiles = _profile_values(policy)

    comparisons: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None
    for profile in profiles:
        comparison = compare_to_profile(
            values,
            profile,
            weights,
            q=q_map,
            p=p_map,
            veto=veto_map,
        )
        comparison["outranks"] = comparison["credibility"] >= lambda_cut
        comparisons.append(comparison)
        if comparison["outranks"]:
            selected = comparison
            break

    if selected is None:
        status = STATU_IPTAL
        category = "Iptal adayi"
        credibility = comparisons[-1]["credibility"] if comparisons else 0.0
        strong: list[str] = []
        weak = list(CRITERIA)
        vetoed = sorted({key for item in comparisons for key in item["vetoed_criteria"]})
        passed_profile = None
    else:
        status = int(selected["status"])
        category = str(selected["profile"])
        credibility = float(selected["credibility"])
        strong = list(selected["strong_criteria"])
        weak = list(selected["weak_criteria"])
        vetoed = list(selected["vetoed_criteria"])
        passed_profile = str(selected["profile"])

    strong_labels = [CRITERION_LABELS[key] for key in strong]
    weak_labels = [CRITERION_LABELS[key] for key in weak]
    veto_labels = [CRITERION_LABELS[key] for key in vetoed]
    reason_parts = [
        f"ELECTRE TRI-B pessimistic atama: {category}",
        f"credibility={credibility:.4f}, lambda={lambda_cut:.2f}",
    ]
    if strong_labels:
        reason_parts.append("guclu kriterler: " + ", ".join(strong_labels))
    if weak_labels:
        reason_parts.append("zayif kriterler: " + ", ".join(weak_labels))
    if veto_labels:
        reason_parts.append("veto: " + ", ".join(veto_labels))

    return {
        "recommended_status": status,
        "category": category,
        "assignment_rule": "pessimistic",
        "classification_method": "electre_tri_b",
        "lambda": lambda_cut,
        "credibility": credibility,
        "passed_profile": passed_profile,
        "strong_criteria": strong,
        "weak_criteria": weak,
        "vetoed_criteria": vetoed,
        "comparisons": comparisons,
        "q": q_map,
        "p": p_map,
        "veto": veto_map,
        "rule_triggered": f"electre_tri_b:{passed_profile or 'lowest'}",
        "reason": "; ".join(reason_parts) + ".",
        "requires_manual_approval": status == STATU_IPTAL,
        "severity": "critical" if status == STATU_IPTAL else "warning" if status == STATU_DINLENMEDE else "info",
    }
