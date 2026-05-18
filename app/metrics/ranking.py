"""Recommendation and ranking metrics."""

from __future__ import annotations

import math


def hit_at_k(actual_items: list[set], predicted_rankings: list[list], k: int = 5) -> float:
    hits = 0
    for truth, ranking in zip(actual_items, predicted_rankings):
        if set(ranking[:k]).intersection(truth):
            hits += 1
    return float(hits / max(len(actual_items), 1))


def ndcg_at_k(actual_items: list[set], predicted_rankings: list[list], k: int = 5) -> float:
    ndcg_values = []
    for truth, ranking in zip(actual_items, predicted_rankings):
        dcg = 0.0
        for i, item in enumerate(ranking[:k], start=1):
            rel = 1.0 if item in truth else 0.0
            dcg += rel / math.log2(i + 1)
        ideal_hits = min(len(truth), k)
        idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
        ndcg_values.append(dcg / idcg if idcg > 0 else 0.0)
    return float(sum(ndcg_values) / max(len(ndcg_values), 1))


def map_at_k(actual_items: list[set], predicted_rankings: list[list], k: int = 5) -> float:
    avg_precisions = []
    for truth, ranking in zip(actual_items, predicted_rankings):
        if not truth:
            avg_precisions.append(0.0)
            continue
        hits = 0
        precision_sum = 0.0
        for i, item in enumerate(ranking[:k], start=1):
            if item in truth:
                hits += 1
                precision_sum += hits / i
        avg_precisions.append(precision_sum / min(len(truth), k))
    return float(sum(avg_precisions) / max(len(avg_precisions), 1))


def coverage(predicted_rankings: list[list], catalog_items: set) -> float:
    recommended = set()
    for ranking in predicted_rankings:
        recommended.update(ranking)
    return float(len(recommended) / max(len(catalog_items), 1))


def diversity(predicted_rankings: list[list]) -> float:
    if not predicted_rankings:
        return 0.0
    all_items = [set(r) for r in predicted_rankings]
    pairwise = []
    for i in range(len(all_items)):
        for j in range(i + 1, len(all_items)):
            union = all_items[i] | all_items[j]
            inter = all_items[i] & all_items[j]
            dissimilarity = 1.0 - (len(inter) / len(union) if union else 0.0)
            pairwise.append(dissimilarity)
    if not pairwise:
        return 0.0
    return float(sum(pairwise) / len(pairwise))
