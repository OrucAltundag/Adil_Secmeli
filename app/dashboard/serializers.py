"""Serializer helpers for benchmark API responses."""

from __future__ import annotations

from typing import Any


def summarize_run(run_payload: dict[str, Any]) -> dict[str, Any]:
    run = run_payload.get("run", {})
    results = run_payload.get("results", {})
    return {
        "run_id": run.get("run_id"),
        "scenario_name": run.get("scenario_name"),
        "dataset_name": run.get("dataset_name"),
        "status": run.get("status"),
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
        "algorithms": list(results.keys()),
    }


def build_comparison_table(run_payload: dict[str, Any]) -> list[dict[str, Any]]:
    table = []
    results = run_payload.get("results", {})
    for algorithm_name, payload in results.items():
        metrics = payload.get("metrics", {})
        flat_metrics = {}
        for group_name, metric_values in metrics.items():
            for metric_name, metric_value in metric_values.items():
                flat_metrics[f"{group_name}.{metric_name}"] = metric_value
        table.append({"algorithm": algorithm_name, **flat_metrics})
    return table
