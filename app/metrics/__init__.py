"""Metrics package."""

from app.metrics.academic import pattern_reproduction_score, ranking_similarity_with_ground_truth
from app.metrics.classification import classification_metrics, top_k_accuracy
from app.metrics.clustering import clustering_metrics
from app.metrics.fairness import allocation_fairness_metrics
from app.metrics.performance import PerformanceSnapshot, PerformanceTracker
from app.metrics.ranking import coverage, diversity, hit_at_k, map_at_k, ndcg_at_k

__all__ = [
    "classification_metrics",
    "top_k_accuracy",
    "hit_at_k",
    "ndcg_at_k",
    "map_at_k",
    "coverage",
    "diversity",
    "clustering_metrics",
    "allocation_fairness_metrics",
    "PerformanceTracker",
    "PerformanceSnapshot",
    "ranking_similarity_with_ground_truth",
    "pattern_reproduction_score",
]
