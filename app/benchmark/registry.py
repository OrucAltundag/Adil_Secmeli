"""Algorithm registry/factory for benchmark experiments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.algorithms.base import IAlgorithm
from app.algorithms.allocation import FCFSAllocator, GaleShapleyAllocator, GreedyAllocator, MinimumRegretAllocator, RandomAllocator
from app.algorithms.clustering import DBSCANClusterer, HierarchicalClusterer, KMeansClusterer
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


class AlgorithmRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, RegistryEntry] = {}
        self._register_defaults()

    def register(self, name: str, group: str, factory: Callable[[], IAlgorithm]) -> None:
        self._entries[name] = RegistryEntry(name=name, group=group, factory=factory)

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
        return [{"name": entry.name, "group": entry.group} for entry in sorted(entries, key=lambda e: (e.group, e.name))]

    def _register_defaults(self) -> None:
        # MCDM
        self.register("AHP", "mcdm", lambda: AHPRanker())
        self.register("TOPSIS", "mcdm", lambda: TOPSISRanker())
        self.register("VIKOR", "mcdm", lambda: VIKORRanker())
        self.register("PROMETHEE_II", "mcdm", lambda: PROMETHEERanker())

        # ML baseline/core/advanced
        self.register("RandomPredictor", "ml_baseline", lambda: RandomPredictor(classes=[]))
        self.register("MajorityClassPredictor", "ml_baseline", lambda: MajorityClassPredictor())
        self.register("PopularityRecommender", "ml_baseline", lambda: PopularityRecommender())
        self.register("NaiveBayes", "ml", lambda: NaiveBayesPredictor())
        self.register("LogisticRegression", "ml", lambda: LogisticRegressionPredictor())
        self.register("RandomForest", "ml", lambda: RandomForestPredictor())
        self.register("XGBoostLike", "ml_advanced", lambda: XGBoostLikePredictor())

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

