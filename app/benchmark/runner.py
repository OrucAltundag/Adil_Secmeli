"""Benchmark experiment runner."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from uuid import uuid4

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from app.algorithms.base import IAllocator, IClusterer, IPredictor, IRanker
from app.benchmark.registry import AlgorithmRegistry
from app.benchmark.result_store import ResultStore
from app.benchmark.scenarios import BenchmarkScenario
from app.datasets.entities import BenchmarkRun, DatasetBundle, MetricResult
from app.metrics.academic import ranking_similarity_with_ground_truth
from app.metrics.classification import classification_metrics, top_k_accuracy
from app.metrics.clustering import clustering_metrics
from app.metrics.fairness import allocation_fairness_metrics
from app.metrics.performance import PerformanceTracker
from app.metrics.ranking import coverage, diversity, hit_at_k, map_at_k, ndcg_at_k


class ExperimentRunner:
    """Executes comparable multi-algorithm experiments on shared scenarios."""

    def __init__(self, registry: AlgorithmRegistry | None = None, result_store: ResultStore | None = None) -> None:
        self.registry = registry or AlgorithmRegistry()
        self.result_store = result_store or ResultStore()

    def run(
        self,
        dataset: DatasetBundle,
        scenario: BenchmarkScenario,
        algorithm_names: list[str] | None = None,
    ) -> dict:
        run_id = f"run_{uuid4().hex[:12]}"
        selected_algorithms = algorithm_names or scenario.algorithm_names
        benchmark_run = BenchmarkRun(
            run_id=run_id,
            scenario_name=scenario.name,
            dataset_name=dataset.dataset_name,
            started_at=datetime.utcnow(),
            algorithms=selected_algorithms,
        )

        results: dict[str, dict] = {}
        for algorithm_name in selected_algorithms:
            algorithm = self.registry.create(algorithm_name)
            algo_result, metrics = self._run_algorithm(dataset, scenario, algorithm)
            results[algorithm_name] = {"output": algo_result.as_dict(), "metrics": metrics}
            for metric_group, metric_payload in metrics.items():
                for metric_name, metric_value in metric_payload.items():
                    benchmark_run.metrics.append(
                        MetricResult(
                            run_id=run_id,
                            algorithm_name=algorithm_name,
                            metric_group=metric_group,
                            metric_name=metric_name,
                            metric_value=float(metric_value),
                        )
                    )

        benchmark_run.status = "completed"
        benchmark_run.finished_at = datetime.utcnow()
        payload = {
            "scenario": asdict(scenario),
            "results": results,
            "metrics": [m.as_dict() for m in benchmark_run.metrics],
        }
        persisted_path = self.result_store.save_run(benchmark_run, payload)
        return {"run": benchmark_run.as_dict(), "results": results, "stored_at": str(persisted_path)}

    def _run_algorithm(self, dataset: DatasetBundle, scenario: BenchmarkScenario, algorithm):
        if scenario.problem_type == "prediction":
            return self._run_prediction(dataset, scenario, algorithm)
        if scenario.problem_type == "ranking":
            return self._run_ranking(dataset, scenario, algorithm)
        if scenario.problem_type == "clustering":
            return self._run_clustering(dataset, scenario, algorithm)
        if scenario.problem_type == "allocation":
            return self._run_allocation(dataset, scenario, algorithm)
        raise ValueError(f"Unsupported problem_type: {scenario.problem_type}")

    def _get_table(self, dataset: DatasetBundle, scenario: BenchmarkScenario) -> pd.DataFrame:
        if scenario.use_synthetic_tier:
            try:
                return dataset.synthetic[scenario.use_synthetic_tier].copy()
            except KeyError as exc:
                available = ", ".join(sorted(dataset.synthetic.keys()))
                raise KeyError(f"Synthetic tier not found: {scenario.use_synthetic_tier}. Available: {available}") from exc
        layer = scenario.dataset_layer
        table_name = scenario.table_name
        return dataset.table(layer, table_name).copy()

    def _run_prediction(self, dataset: DatasetBundle, scenario: BenchmarkScenario, algorithm):
        if not isinstance(algorithm, (IPredictor, IRanker)):
            raise TypeError(f"{algorithm.name} is not compatible with prediction scenario")

        df = self._get_table(dataset, scenario)
        target = scenario.target_column
        if target not in df.columns:
            raise KeyError(f"Target column missing: {target}")

        y = df[target]
        drop_cols = [target, "item_id", "student_id"]
        X = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")
        X = pd.get_dummies(X, dummy_na=True).fillna(0.0)
        stratify = y if y.nunique() > 1 else None
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=stratify)

        with PerformanceTracker(workload_size=len(X_test)) as tracker:
            algorithm.fit(X_train, y_train)
            output = algorithm.predict(X_test)
            ranked_output = algorithm.recommend(X_test, top_k=scenario.top_k)
        perf = tracker.snapshot().as_dict()

        y_pred = output.predictions
        y_proba = np.array(algorithm.predict_proba(X_test), dtype=float) if isinstance(algorithm, IPredictor) else None
        cls_metrics = classification_metrics(y_true=y_test.tolist(), y_pred=y_pred, y_proba=y_proba)
        ranked_labels = []
        for rec in ranked_output.recommendations:
            items = rec.get("items", [])
            labels = []
            for item in items:
                if isinstance(item, dict):
                    labels.append(item.get("label", item.get("item_id", item)))
                else:
                    labels.append(item)
            ranked_labels.append(labels)
        actual_sets = [{actual} for actual in y_test.tolist()]
        rec_metrics = {
            "hit_at_k": hit_at_k(actual_sets, ranked_labels, k=scenario.top_k),
            "ndcg_at_k": ndcg_at_k(actual_sets, ranked_labels, k=scenario.top_k),
            "map_at_k": map_at_k(actual_sets, ranked_labels, k=scenario.top_k),
            "coverage": coverage(ranked_labels, set(y_train.unique().tolist())),
            "diversity": diversity(ranked_labels),
            "top_k_accuracy": top_k_accuracy(y_true=y_test.tolist(), ranked_labels=ranked_labels, k=scenario.top_k),
        }
        return output, {"classification": cls_metrics, "recommendation": rec_metrics, "performance": perf}

    def _run_ranking(self, dataset: DatasetBundle, scenario: BenchmarkScenario, algorithm):
        if not isinstance(algorithm, IRanker):
            raise TypeError(f"{algorithm.name} is not a ranker")
        df = self._get_table(dataset, scenario)
        if "course_id" in df.columns:
            aggregated = df.groupby("course_id").mean(numeric_only=True).reset_index().rename(columns={"course_id": "item_id"})
        else:
            aggregated = df.copy()
            if "item_id" not in aggregated.columns:
                aggregated = aggregated.reset_index().rename(columns={"index": "item_id"})

        # Keep numeric criteria only for MCDM.
        numeric_cols = aggregated.select_dtypes(include=["number"]).columns.tolist()
        numeric_cols = [c for c in numeric_cols if c != "item_id"]
        mcdm_df = aggregated[["item_id", *numeric_cols]].copy()

        with PerformanceTracker(workload_size=len(mcdm_df)) as tracker:
            algorithm.fit(mcdm_df)
            output = algorithm.recommend(mcdm_df, top_k=scenario.top_k)
        perf = tracker.snapshot().as_dict()

        predicted_ranking = [r["item_id"] for r in output.recommendations]
        if "course_id" in df.columns:
            popularity = df["course_id"].value_counts().index.tolist()
        else:
            popularity = predicted_ranking
        gt_top = set(popularity[: scenario.top_k])
        ranked_labels = [predicted_ranking]
        actual_sets = [gt_top]
        rec_metrics = {
            "hit_at_k": hit_at_k(actual_sets, ranked_labels, k=scenario.top_k),
            "ndcg_at_k": ndcg_at_k(actual_sets, ranked_labels, k=scenario.top_k),
            "map_at_k": map_at_k(actual_sets, ranked_labels, k=scenario.top_k),
            "coverage": coverage(ranked_labels, set(popularity)),
            "diversity": diversity(ranked_labels),
        }
        academic = {"ranking_similarity_ground_truth": ranking_similarity_with_ground_truth(predicted_ranking, popularity)}
        return output, {"recommendation": rec_metrics, "academic": academic, "performance": perf}

    def _run_clustering(self, dataset: DatasetBundle, scenario: BenchmarkScenario, algorithm):
        if not isinstance(algorithm, IClusterer):
            raise TypeError(f"{algorithm.name} is not a clusterer")
        df = self._get_table(dataset, scenario)
        drop_cols = ["course_id", "student_id", "item_id", scenario.target_column]
        X = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")
        X = pd.get_dummies(X, dummy_na=True).fillna(0.0)

        with PerformanceTracker(workload_size=len(X)) as tracker:
            output = algorithm.cluster(X)
        perf = tracker.snapshot().as_dict()
        labels = output.predictions
        cl_metrics = clustering_metrics(X, labels)
        academic = {"pattern_reproduction": 0.0}
        if "department_id" in df.columns and len(labels) == len(df):
            tmp = pd.DataFrame({"department_id": df["department_id"].tolist(), "cluster": labels})
            if not tmp.empty:
                purity = tmp.groupby("department_id")["cluster"].agg(lambda s: s.value_counts(normalize=True).iloc[0]).mean()
                academic["pattern_reproduction"] = float(purity)
        return output, {"clustering": cl_metrics, "academic": academic, "performance": perf}

    def _run_allocation(self, dataset: DatasetBundle, scenario: BenchmarkScenario, algorithm):
        if not isinstance(algorithm, IAllocator):
            raise TypeError(f"{algorithm.name} is not an allocator")
        students = dataset.raw_real["students"]
        courses = dataset.raw_real["courses"]
        preferences = dataset.raw_real["preferences"]
        with PerformanceTracker(workload_size=len(students)) as tracker:
            output = algorithm.allocate(students, courses, preferences)
        perf = tracker.snapshot().as_dict()
        assignments_df = pd.DataFrame(output.assignments)
        fairness = allocation_fairness_metrics(assignments_df, courses, top_k=scenario.top_k)
        return output, {"fairness": fairness, "performance": perf}
