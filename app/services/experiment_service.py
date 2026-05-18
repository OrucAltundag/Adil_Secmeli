"""High-level orchestration service for benchmark scenarios."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.benchmark import (
    DEFAULT_SCENARIOS,
    AlgorithmRegistry,
    ExperimentRunner,
    ResultStore,
)
from app.datasets import DataPipeline, PipelineConfig
from app.services.algorithm_manager import AlgorithmManager


class ExperimentService:
    def __init__(
        self,
        data_pipeline: DataPipeline | None = None,
        registry: AlgorithmRegistry | None = None,
        result_store: ResultStore | None = None,
    ) -> None:
        self.data_pipeline = data_pipeline or DataPipeline()
        self.registry = registry or AlgorithmRegistry()
        self.result_store = result_store or ResultStore()
        self.runner = ExperimentRunner(registry=self.registry, result_store=self.result_store)
        self.algorithm_manager = AlgorithmManager(result_store=self.result_store)

    def list_scenarios(self) -> list[dict[str, Any]]:
        return [
            {
                "name": scenario.name,
                "description": scenario.description,
                "problem_type": scenario.problem_type,
                "default_algorithms": scenario.algorithm_names,
            }
            for scenario in DEFAULT_SCENARIOS.values()
        ]

    def list_algorithms(self, group: str | None = None) -> list[dict[str, str]]:
        return self.registry.list_algorithms(group=group)

    def build_dataset(
        self,
        *,
        source_type: str,
        source_path: str,
        dataset_name: str = "benchmark_dataset",
        synth_noise_std: float = 0.02,
        synth_class_imbalance_alpha: float = 0.0,
        synth_capacity_scale: float = 1.0,
    ):
        config = PipelineConfig(
            dataset_name=dataset_name,
            source_type="csv" if source_type == "csv" else "sqlite",
            source_path=source_path,
            synth_noise_std=synth_noise_std,
            synth_class_imbalance_alpha=synth_class_imbalance_alpha,
            synth_capacity_scale=synth_capacity_scale,
        )
        return self.data_pipeline.run(config)

    def run_scenario(
        self,
        dataset,
        scenario_name: str,
        *,
        algorithm_names: list[str] | None = None,
        synthetic_tier: str | None = None,
        top_k: int | None = None,
    ) -> dict:
        if scenario_name not in DEFAULT_SCENARIOS:
            available = ", ".join(sorted(DEFAULT_SCENARIOS.keys()))
            raise KeyError(f"Unknown scenario '{scenario_name}'. Available: {available}")
        scenario = DEFAULT_SCENARIOS[scenario_name]
        scenario = replace(
            scenario,
            use_synthetic_tier=synthetic_tier if synthetic_tier is not None else scenario.use_synthetic_tier,
            top_k=int(top_k) if top_k is not None else scenario.top_k,
        )
        return self.runner.run(dataset=dataset, scenario=scenario, algorithm_names=algorithm_names)

    def compare_algorithms(
        self,
        dataset,
        *,
        scenario_name: str,
        algorithm_names: list[str],
        synthetic_tier: str | None = None,
        top_k: int | None = None,
    ) -> dict:
        if not algorithm_names:
            raise ValueError("compare_algorithms requires a non-empty algorithm list.")
        return self.run_scenario(
            dataset=dataset,
            scenario_name=scenario_name,
            algorithm_names=algorithm_names,
            synthetic_tier=synthetic_tier,
            top_k=top_k,
        )

    def recommend_algorithm(
        self,
        *,
        problem_type: str,
        data_size: int,
        explainability_priority: bool = False,
        use_history: bool = True,
    ) -> dict[str, Any]:
        recommendation = self.algorithm_manager.recommend(
            problem_type=problem_type,
            data_size=data_size,
            explainability_priority=explainability_priority,
            use_history=use_history,
        )
        return recommendation.as_dict()
