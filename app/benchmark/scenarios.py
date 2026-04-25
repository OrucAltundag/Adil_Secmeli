"""Scenario definitions for repeatable benchmark runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BenchmarkScenario:
    name: str
    description: str
    problem_type: str  # prediction | ranking | clustering | allocation | mixed
    dataset_layer: str = "derived"
    table_name: str = "student_course_features"
    target_column: str = "course_id"
    top_k: int = 5
    use_synthetic_tier: str | None = None
    algorithm_names: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


DEFAULT_SCENARIOS: dict[str, BenchmarkScenario] = {
    "real_mcdm_recommendation": BenchmarkScenario(
        name="real_mcdm_recommendation",
        description="Real-data ranking benchmark for explainable MCDM methods.",
        problem_type="ranking",
        table_name="student_course_features_unencoded",
        target_column="course_id",
        top_k=5,
        algorithm_names=["AHP", "TOPSIS", "VIKOR", "PROMETHEE_II"],
    ),
    "real_ml_prediction": BenchmarkScenario(
        name="real_ml_prediction",
        description="Real-data supervised prediction benchmark.",
        problem_type="prediction",
        table_name="student_course_features",
        target_column="course_id",
        top_k=5,
        algorithm_names=[
            "RandomPredictor",
            "MajorityClassPredictor",
            "NaiveBayes",
            "LogisticRegression",
            "RandomForest",
            "XGBoostLike",
        ],
    ),
    "allocation_fairness": BenchmarkScenario(
        name="allocation_fairness",
        description="Capacity-constrained allocation and fairness comparison.",
        problem_type="allocation",
        dataset_layer="raw_real",
        table_name="preferences",
        top_k=3,
        algorithm_names=[
            "GaleShapley",
            "RandomAllocation",
            "GreedyAllocation",
            "FirstComeFirstServed",
            "MinimumRegretAllocation",
        ],
    ),
    "clustering_exploration": BenchmarkScenario(
        name="clustering_exploration",
        description="Unsupervised segmentation quality benchmark.",
        problem_type="clustering",
        table_name="student_course_features",
        top_k=5,
        algorithm_names=["KMeans", "HierarchicalClustering", "DBSCAN"],
    ),
}

