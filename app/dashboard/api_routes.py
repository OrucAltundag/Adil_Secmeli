"""REST API routes for benchmark dashboard workflows."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.dashboard.serializers import build_comparison_table, summarize_run
from app.services.experiment_service import ExperimentService

router = APIRouter()
service = ExperimentService()
_STATE: dict[str, Any] = {"dataset": None}


class DatasetLoadRequest(BaseModel):
    source_type: Literal["sqlite", "csv"] = "sqlite"
    source_path: str = "data/adil_secmeli.db"
    dataset_name: str = "benchmark_dataset"
    synth_noise_std: float = Field(default=0.02, ge=0.0, le=1.0)
    synth_class_imbalance_alpha: float = Field(default=0.0, ge=0.0, le=1.0)
    synth_capacity_scale: float = Field(default=1.0, ge=0.1, le=10.0)


class ScenarioRunRequest(BaseModel):
    scenario_name: str
    algorithm_names: list[str] | None = None
    synthetic_tier: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=100)


class CompareRequest(BaseModel):
    scenario_name: str
    algorithm_names: list[str]
    synthetic_tier: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=100)


class RecommendationRequest(BaseModel):
    problem_type: Literal["prediction", "ranking", "allocation", "clustering"]
    data_size: int = Field(ge=1)
    explainability_priority: bool = False
    use_history: bool = True


@router.get("/scenarios")
def list_scenarios():
    return {"scenarios": service.list_scenarios()}


@router.get("/algorithms")
def list_algorithms(group: str | None = None):
    return {"algorithms": service.list_algorithms(group=group)}


@router.post("/datasets/load")
def load_dataset(request: DatasetLoadRequest):
    dataset = service.build_dataset(
        source_type=request.source_type,
        source_path=request.source_path,
        dataset_name=request.dataset_name,
        synth_noise_std=request.synth_noise_std,
        synth_class_imbalance_alpha=request.synth_class_imbalance_alpha,
        synth_capacity_scale=request.synth_capacity_scale,
    )
    _STATE["dataset"] = dataset
    return {
        "dataset_name": dataset.dataset_name,
        "raw_real_tables": sorted(dataset.raw_real.keys()),
        "derived_tables": sorted(dataset.derived.keys()),
        "synthetic_tiers": sorted(dataset.synthetic.keys()),
        "metadata": dataset.metadata,
    }


@router.post("/runs/execute")
def run_scenario(request: ScenarioRunRequest):
    dataset = _STATE.get("dataset")
    if dataset is None:
        raise HTTPException(status_code=400, detail="No dataset loaded. Call /datasets/load first.")
    run_payload = service.run_scenario(
        dataset=dataset,
        scenario_name=request.scenario_name,
        algorithm_names=request.algorithm_names,
        synthetic_tier=request.synthetic_tier,
        top_k=request.top_k,
    )
    return {
        "summary": summarize_run(run_payload),
        "comparison_table": build_comparison_table(run_payload),
        "details": run_payload,
    }


@router.post("/runs/compare")
def compare_algorithms(request: CompareRequest):
    dataset = _STATE.get("dataset")
    if dataset is None:
        raise HTTPException(status_code=400, detail="No dataset loaded. Call /datasets/load first.")
    run_payload = service.compare_algorithms(
        dataset=dataset,
        scenario_name=request.scenario_name,
        algorithm_names=request.algorithm_names,
        synthetic_tier=request.synthetic_tier,
        top_k=request.top_k,
    )
    return {
        "summary": summarize_run(run_payload),
        "comparison_table": build_comparison_table(run_payload),
        "details": run_payload,
    }


@router.post("/recommendation")
def recommend_algorithm(request: RecommendationRequest):
    return service.recommend_algorithm(
        problem_type=request.problem_type,
        data_size=request.data_size,
        explainability_priority=request.explainability_priority,
        use_history=request.use_history,
    )


@router.get("/runs")
def list_runs(limit: int = 20):
    limit = max(1, min(limit, 200))
    runs = service.result_store.list_runs(limit=limit)
    return {"runs": [summarize_run({"run": run_blob.get("run", {}), "results": run_blob.get("payload", {}).get("results", {})}) for run_blob in runs]}


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    try:
        payload = service.result_store.load_run(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Run not found")
    run_payload = {"run": payload.get("run", {}), "results": payload.get("payload", {}).get("results", {})}
    return {
        "summary": summarize_run(run_payload),
        "comparison_table": build_comparison_table(run_payload),
        "details": payload,
    }
