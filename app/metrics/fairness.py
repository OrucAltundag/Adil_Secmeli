"""Fairness metrics for allocation and recommendation outputs."""

from __future__ import annotations

import pandas as pd


def average_rank(assignments: pd.DataFrame) -> float:
    if "rank_received" not in assignments.columns:
        return 0.0
    valid = pd.to_numeric(assignments["rank_received"], errors="coerce").dropna()
    return float(valid.mean()) if not valid.empty else 0.0


def top_k_satisfaction(assignments: pd.DataFrame, k: int = 3) -> float:
    if "rank_received" not in assignments.columns:
        return 0.0
    valid = pd.to_numeric(assignments["rank_received"], errors="coerce")
    sat = (valid <= k).fillna(False)
    return float(sat.mean()) if len(sat) else 0.0


def envy_score(assignments: pd.DataFrame) -> float:
    """
    Proxy envy:
    If students with worse preference rank receive assignment while better-ranked students stay unassigned,
    that indicates envy potential.
    """
    if assignments.empty or "allocated" not in assignments.columns:
        return 0.0
    ranked = assignments.copy()
    ranked["rank_received"] = pd.to_numeric(ranked.get("rank_received"), errors="coerce")
    unassigned = ranked[~ranked["allocated"]]
    assigned = ranked[ranked["allocated"]]
    if assigned.empty or unassigned.empty:
        return 0.0
    assigned_rank = assigned["rank_received"].dropna()
    if assigned_rank.empty:
        return 0.0
    threshold = float(assigned_rank.median())
    envy_cases = (unassigned["rank_received"].fillna(threshold + 1) < threshold).sum()
    return float(envy_cases / max(len(ranked), 1))


def seat_fill_rate(assignments: pd.DataFrame, courses: pd.DataFrame) -> float:
    if assignments.empty or courses.empty:
        return 0.0
    assigned_counts = assignments[assignments["allocated"]].groupby("course_id").size()
    capacities = courses.set_index("course_id")["capacity"] if "capacity" in courses.columns else pd.Series(dtype=float)
    capacities = pd.to_numeric(capacities, errors="coerce").fillna(0.0)
    if capacities.empty:
        return 0.0
    fill = 0.0
    total_capacity = capacities.sum()
    for cid, cap in capacities.items():
        fill += min(float(assigned_counts.get(cid, 0)), float(cap))
    return float(fill / max(total_capacity, 1.0))


def allocation_fairness_metrics(assignments: pd.DataFrame, courses: pd.DataFrame, top_k: int = 3) -> dict[str, float]:
    return {
        "average_rank": average_rank(assignments),
        "top_k_satisfaction": top_k_satisfaction(assignments, k=top_k),
        "envy_score": envy_score(assignments),
        "seat_fill_rate": seat_fill_rate(assignments, courses),
    }
