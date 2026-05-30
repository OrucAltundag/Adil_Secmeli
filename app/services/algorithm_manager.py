"""Algorithm selection engine (rule-based + benchmark-history aware)."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Any

from app.benchmark.result_store import ResultStore


@dataclass(slots=True)
class AlgorithmRecommendation:
    algorithm: str
    confidence: float
    reason: str
    source: str  # rules | history
    candidates: list[str]
    used_run_count: int = 0
    data_coverage: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "confidence": self.confidence,
            "reason": self.reason,
            "source": self.source,
            "candidates": self.candidates,
            "used_run_count": self.used_run_count,
            "data_coverage": self.data_coverage
            or {
                "source": self.source,
                "used_run_count": self.used_run_count,
                "coverage_note": "Kural tabanlı öneri; geçmiş benchmark run kullanılmadı." if self.source == "rules" else "Geçmiş benchmark verisi kullanıldı.",
            },
        }


class AlgorithmManager:
    def __init__(self, result_store: ResultStore | None = None) -> None:
        self.result_store = result_store or ResultStore()

    def recommend(
        self,
        *,
        problem_type: str,
        data_size: int,
        explainability_priority: bool = False,
        use_history: bool = True,
    ) -> AlgorithmRecommendation:
        rule_based = self._rule_based(problem_type=problem_type, data_size=data_size, explainability_priority=explainability_priority)
        if use_history:
            historical = self._history_based(problem_type=problem_type)
            if historical is not None:
                return historical
        return rule_based

    def _rule_based(self, *, problem_type: str, data_size: int, explainability_priority: bool) -> AlgorithmRecommendation:
        problem = (problem_type or "").lower()
        if problem == "allocation":
            return AlgorithmRecommendation(
                algorithm="GaleShapley",
                confidence=0.85,
                reason="Allocation problem with capacity/fairness constraints is best served by stable matching.",
                source="rules",
                candidates=["GaleShapley", "MinimumRegretAllocation", "GreedyAllocation"],
            )
        if problem == "clustering":
            if data_size >= 50_000:
                return AlgorithmRecommendation(
                    algorithm="KMeans",
                    confidence=0.80,
                    reason="Large-scale exploratory segmentation favors scalable centroid-based clustering.",
                    source="rules",
                    candidates=["KMeans", "DBSCAN", "HierarchicalClustering"],
                )
            return AlgorithmRecommendation(
                algorithm="HierarchicalClustering",
                confidence=0.72,
                reason="Smaller exploratory dataset allows richer hierarchical cluster structure inspection.",
                source="rules",
                candidates=["HierarchicalClustering", "KMeans", "DBSCAN"],
            )
        if problem == "ranking":
            if explainability_priority or data_size < 10_000:
                return AlgorithmRecommendation(
                    algorithm="AHP",
                    confidence=0.78,
                    reason="Small/interpretable ranking scenario favors AHP with transparent criterion weighting.",
                    source="rules",
                    candidates=["AHP", "TOPSIS", "VIKOR", "PROMETHEE_II"],
                )
            return AlgorithmRecommendation(
                algorithm="TOPSIS",
                confidence=0.74,
                reason="General ranking scenario favors TOPSIS due to robust ideal-solution distance modeling.",
                source="rules",
                candidates=["TOPSIS", "VIKOR", "PROMETHEE_II", "AHP"],
            )

        # prediction default
        if data_size < 10_000 and explainability_priority:
            return AlgorithmRecommendation(
                algorithm="LogisticRegression",
                confidence=0.79,
                reason="Small dataset with explainability preference favors interpretable linear models.",
                source="rules",
                candidates=["LogisticRegression", "NaiveBayes", "RandomForest"],
            )
        if data_size >= 50_000:
            return AlgorithmRecommendation(
                algorithm="XGBoostLike",
                confidence=0.82,
                reason="Large dataset favors scalable tree ensemble models.",
                source="rules",
                candidates=["XGBoostLike", "RandomForest", "LogisticRegression"],
            )
        return AlgorithmRecommendation(
            algorithm="RandomForest",
            confidence=0.76,
            reason="Balanced default for medium-size predictive workloads.",
            source="rules",
            candidates=["RandomForest", "LogisticRegression", "NaiveBayes"],
        )

    def _history_based(self, *, problem_type: str) -> AlgorithmRecommendation | None:
        runs = self.result_store.list_runs(limit=200)
        if not runs:
            return None
        scores: dict[str, list[float]] = {}
        candidates: dict[str, list[str]] = {}
        for run_blob in runs:
            payload = run_blob.get("payload", {})
            scenario = payload.get("scenario", {})
            if (scenario.get("problem_type") or "").lower() != problem_type.lower():
                continue
            results = payload.get("results", {})
            for algo_name, algo_data in results.items():
                metric_groups = algo_data.get("metrics", {})
                score = self._objective_score(problem_type, metric_groups)
                scores.setdefault(algo_name, []).append(score)
                candidates.setdefault(algo_name, []).append(scenario.get("name", "unknown"))

        if not scores:
            return None
        algo = max(scores.items(), key=lambda item: mean(item[1]))[0]
        avg_score = float(mean(scores[algo]))
        return AlgorithmRecommendation(
            algorithm=algo,
            confidence=max(0.5, min(0.95, avg_score)),
            reason=f"Selected from historical benchmark outcomes across {len(scores[algo])} runs.",
            source="history",
            candidates=sorted(scores.keys()),
            used_run_count=len(scores[algo]),
            data_coverage={
                "problem_type": problem_type,
                "used_run_count": len(scores[algo]),
                "candidate_count": len(scores),
                "scenarios": sorted(set(candidates.get(algo, []))),
            },
        )

    def _objective_score(self, problem_type: str, metric_groups: dict[str, dict[str, float]]) -> float:
        p = problem_type.lower()
        if p == "prediction":
            cls = metric_groups.get("classification", {})
            rec = metric_groups.get("recommendation", {})
            return float(
                0.55 * cls.get("f1", 0.0)
                + 0.20 * cls.get("roc_auc", 0.0)
                + 0.15 * rec.get("ndcg_at_k", 0.0)
                + 0.10 * rec.get("hit_at_k", 0.0)
            )
        if p == "ranking":
            rec = metric_groups.get("recommendation", {})
            academic = metric_groups.get("academic", {})
            return float(
                0.40 * rec.get("ndcg_at_k", 0.0)
                + 0.30 * rec.get("map_at_k", 0.0)
                + 0.20 * rec.get("hit_at_k", 0.0)
                + 0.10 * academic.get("ranking_similarity_ground_truth", 0.0)
            )
        if p == "allocation":
            fair = metric_groups.get("fairness", {})
            avg_rank = fair.get("average_rank", 0.0)
            rank_component = 1.0 / max(avg_rank, 1.0) if avg_rank else 0.0
            return float(
                0.35 * fair.get("top_k_satisfaction", 0.0)
                + 0.25 * fair.get("seat_fill_rate", 0.0)
                + 0.25 * (1.0 - fair.get("envy_score", 0.0))
                + 0.15 * rank_component
            )
        if p == "clustering":
            cl = metric_groups.get("clustering", {})
            db = cl.get("davies_bouldin", 0.0)
            db_component = 1.0 / (1.0 + db) if db != float("inf") else 0.0
            return float(
                0.45 * max(cl.get("silhouette", -1.0), 0.0)
                + 0.35 * db_component
                + 0.20 * min(cl.get("calinski_harabasz", 0.0) / 1000.0, 1.0)
            )
        return 0.0
