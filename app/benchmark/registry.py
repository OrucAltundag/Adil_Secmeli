"""Algorithm registry/factory for benchmark experiments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.algorithms.allocation import (
    FCFSAllocator,
    GaleShapleyAllocator,
    GreedyAllocator,
    MinimumRegretAllocator,
    RandomAllocator,
)
from app.algorithms.base import IAlgorithm
from app.algorithms.clustering import (
    DBSCANClusterer,
    HierarchicalClusterer,
    KMeansClusterer,
)
from app.algorithms.mcdm import AHPRanker, PROMETHEERanker, TOPSISRanker, VIKORRanker
from app.algorithms.ml import (
    LogisticRegressionPredictor,
    MajorityClassPredictor,
    NaiveBayesPredictor,
    PopularityRecommender,
    RandomForestPredictor,
    RandomPredictor,
    XGBoostLikePredictor,
)


@dataclass(slots=True)
class RegistryEntry:
    name: str
    group: str
    factory: Callable[[], IAlgorithm]
    usage_role: str = "benchmark_only"
    role_label: str = "Sadece benchmark"


class AlgorithmRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, RegistryEntry] = {}
        self._register_defaults()

    def register(
        self,
        name: str,
        group: str,
        factory: Callable[[], IAlgorithm],
        *,
        usage_role: str = "benchmark_only",
        role_label: str = "Sadece benchmark",
    ) -> None:
        self._entries[name] = RegistryEntry(name=name, group=group, factory=factory, usage_role=usage_role, role_label=role_label)

    def create(self, name: str) -> IAlgorithm:
        try:
            return self._entries[name].factory()
        except KeyError as exc:
            available = ", ".join(sorted(self._entries.keys()))
            raise KeyError(f"Algorithm '{name}' not found. Available: {available}") from exc

    def list_algorithms(self, group: str | None = None) -> list[dict[str, str]]:
        entries = self._entries.values()
        if group is not None:
            entries = [entry for entry in entries if entry.group == group]
        return [
            {"name": entry.name, "group": entry.group, "usage_role": entry.usage_role, "role_label": entry.role_label}
            for entry in sorted(entries, key=lambda e: (e.group, e.name))
        ]

    def _register_defaults(self) -> None:
        # MCDM
        self.register("AHP", "mcdm", lambda: AHPRanker(), usage_role="production_decision", role_label="Ana karar motoru")
        self.register("TOPSIS", "mcdm", lambda: TOPSISRanker(), usage_role="production_decision", role_label="Ana karar motoru")
        self.register("VIKOR", "mcdm", lambda: VIKORRanker(), usage_role="benchmark_only", role_label="Sadece benchmark")
        self.register("PROMETHEE_II", "mcdm", lambda: PROMETHEERanker(), usage_role="benchmark_only", role_label="Sadece benchmark")

        # ML baseline/core/advanced
        self.register("RandomPredictor", "ml_baseline", lambda: RandomPredictor(classes=[]), usage_role="benchmark_only", role_label="Sadece benchmark")
        self.register("MajorityClassPredictor", "ml_baseline", lambda: MajorityClassPredictor(), usage_role="benchmark_only", role_label="Sadece benchmark")
        self.register("PopularityRecommender", "ml_baseline", lambda: PopularityRecommender(), usage_role="benchmark_only", role_label="Sadece benchmark")
        self.register("NaiveBayes", "ml", lambda: NaiveBayesPredictor(), usage_role="benchmark_only", role_label="Sadece benchmark")
        self.register("LogisticRegression", "ml", lambda: LogisticRegressionPredictor(), usage_role="benchmark_only", role_label="Sadece benchmark")
        self.register("RandomForest", "ml", lambda: RandomForestPredictor(), usage_role="advisory_ml", role_label="Destekleyici ML")
        self.register("XGBoostLike", "ml_advanced", lambda: XGBoostLikePredictor(), usage_role="benchmark_only", role_label="Sadece benchmark")

        # Clustering
        self.register("KMeans", "clustering", lambda: KMeansClusterer())
        self.register("HierarchicalClustering", "clustering", lambda: HierarchicalClusterer())
        self.register("DBSCAN", "clustering", lambda: DBSCANClusterer())

        # Allocation
        self.register("GaleShapley", "allocation", lambda: GaleShapleyAllocator())
        self.register("RandomAllocation", "allocation", lambda: RandomAllocator())
        self.register("GreedyAllocation", "allocation", lambda: GreedyAllocator())
        self.register("FirstComeFirstServed", "allocation", lambda: FCFSAllocator())
        self.register("MinimumRegretAllocation", "allocation", lambda: MinimumRegretAllocator())
