"""Run sample benchmark scenarios on bundled example data."""

from __future__ import annotations

import json
from pathlib import Path

from app.services.experiment_service import ExperimentService


def main() -> None:
    service = ExperimentService()
    dataset = service.build_dataset(
        source_type="csv",
        source_path="data/benchmark/raw_real",
        dataset_name="sample_benchmark_dataset",
        synth_noise_std=0.03,
        synth_class_imbalance_alpha=0.2,
        synth_capacity_scale=1.0,
    )

    runs = []
    for scenario in ("real_mcdm_recommendation", "real_ml_prediction", "allocation_fairness", "clustering_exploration"):
        run = service.run_scenario(dataset=dataset, scenario_name=scenario)
        runs.append(
            {
                "scenario": scenario,
                "run_id": run["run"]["run_id"],
                "stored_at": run["stored_at"],
                "algorithms": list(run["results"].keys()),
            }
        )

    recommendation = service.recommend_algorithm(
        problem_type="prediction",
        data_size=5000,
        explainability_priority=True,
        use_history=True,
    )
    out = {"runs": runs, "recommendation": recommendation}

    out_path = Path("reports/benchmark_runs/sample_experiment_summary.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()

