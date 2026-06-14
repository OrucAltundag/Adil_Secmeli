"""REST API routes for benchmark dashboard workflows."""

from __future__ import annotations

import math
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.dashboard.serializers import build_comparison_table, summarize_run
from app.services.experiment_service import ExperimentService

router = APIRouter()
service = ExperimentService()
_STATE: dict[str, Any] = {"dataset": None}


def _default_db_path() -> str:
    """Otomatik dataset üretimi için yapılandırılmış veritabanı yolu."""
    try:
        from app.core.config import load_app_config

        return load_app_config().sqlite_db_path
    except Exception:
        return "data/adil_secmeli.db"


def _ensure_dataset():
    """State'te dataset yoksa varsayılan veritabanından otomatik üretir.

    "Dataset Eksik" durumunu giderir: kullanıcı manuel yükleme yapmasa bile
    benchmark çalıştırılabilir. Üretilen dataset state'e cache'lenir.
    """
    dataset = _STATE.get("dataset")
    if dataset is not None:
        return dataset
    dataset = service.build_dataset(
        source_type="sqlite",
        source_path=_default_db_path(),
        dataset_name="adil_real",
    )
    _STATE["dataset"] = dataset
    return dataset


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
    allocation_parameters: dict[str, Any] | None = None


class CompareRequest(BaseModel):
    scenario_name: str
    algorithm_names: list[str]
    synthetic_tier: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=100)
    allocation_parameters: dict[str, Any] | None = None


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
        "layer_counts": _layer_counts(dataset),
        "preview": _dataset_preview(dataset),
        "quality_summary": _quality_summary(dataset),
    }


@router.get("/datasets/status")
def dataset_status():
    """Yüklü dataset durumunu döndürür; yoksa varsayılan DB'den otomatik üretir."""
    dataset = _ensure_dataset()
    return {
        "loaded": True,
        "auto_built": True,
        "dataset_name": dataset.dataset_name,
        "raw_real_tables": sorted(dataset.raw_real.keys()),
        "derived_tables": sorted(dataset.derived.keys()),
        "synthetic_tiers": sorted(dataset.synthetic.keys()),
        "layer_counts": _layer_counts(dataset),
    }


@router.post("/runs/execute")
def run_scenario(request: ScenarioRunRequest):
    # Dataset yüklü değilse varsayılan veritabanından otomatik üret.
    dataset = _ensure_dataset()
    run_payload = service.run_scenario(
        dataset=dataset,
        scenario_name=request.scenario_name,
        algorithm_names=request.algorithm_names,
        synthetic_tier=request.synthetic_tier,
        top_k=request.top_k,
    )
    if request.allocation_parameters is not None:
        run_payload["request_parameters"] = {"allocation": request.allocation_parameters}
    return {
        "summary": summarize_run(run_payload),
        "comparison_table": build_comparison_table(run_payload),
        "details": run_payload,
        "request_parameters": run_payload.get("request_parameters"),
    }


@router.post("/runs/compare")
def compare_algorithms(request: CompareRequest):
    # Dataset yüklü değilse varsayılan veritabanından otomatik üret.
    dataset = _ensure_dataset()
    run_payload = service.compare_algorithms(
        dataset=dataset,
        scenario_name=request.scenario_name,
        algorithm_names=request.algorithm_names,
        synthetic_tier=request.synthetic_tier,
        top_k=request.top_k,
    )
    if request.allocation_parameters is not None:
        run_payload["request_parameters"] = {"allocation": request.allocation_parameters}
    return {
        "summary": summarize_run(run_payload),
        "comparison_table": build_comparison_table(run_payload),
        "details": run_payload,
        "request_parameters": run_payload.get("request_parameters"),
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


def _layer_counts(dataset) -> dict[str, dict[str, int]]:
    return {
        "raw_real": {name: int(len(table)) for name, table in dataset.raw_real.items()},
        "derived": {name: int(len(table)) for name, table in dataset.derived.items()},
        "synthetic": {name: int(len(table)) for name, table in dataset.synthetic.items()},
    }


def _dataset_preview(dataset, limit: int = 25) -> dict[str, Any]:
    table_name = "student_course_features"
    layer_name = "derived"
    table = dataset.derived.get(table_name)
    if table is None or table.empty:
        table_name = "student_course_features_unencoded"
        table = dataset.derived.get(table_name)
    if table is None or table.empty:
        layer_name = "raw_real"
        if dataset.raw_real:
            table_name = sorted(dataset.raw_real.keys())[0]
            table = dataset.raw_real[table_name]
    if table is None:
        return {"layer": layer_name, "table": table_name, "columns": [], "rows": []}
    rows = []
    cleaned = table.head(limit).where(table.head(limit).notna(), None)
    for row in cleaned.to_dict(orient="records"):
        rows.append({str(key): _json_safe(value) for key, value in row.items()})
    return {
        "layer": layer_name,
        "table": table_name,
        "columns": [str(column) for column in table.columns.tolist()],
        "rows": rows,
    }


def _quality_summary(dataset, target_column: str = "course_id") -> dict[str, Any]:
    table = dataset.derived.get("student_course_features")
    if table is None or table.empty:
        table = dataset.derived.get("student_course_features_unencoded")
    if table is None or table.empty:
        table = next(iter(dataset.raw_real.values()), None) if dataset.raw_real else None
    if table is None:
        return {
            "row_count": 0,
            "column_count": 0,
            "missing_ratio": 0.0,
            "target_column": target_column,
            "target_present": False,
            "class_distribution": {},
        }
    total_cells = max(1, int(table.shape[0] * table.shape[1]))
    missing_ratio = float(table.isna().sum().sum() / total_cells)
    target_present = target_column in table.columns
    class_distribution = {}
    if target_present:
        counts = table[target_column].value_counts(dropna=False).head(10)
        class_distribution = {str(key): int(value) for key, value in counts.to_dict().items()}
    return {
        "row_count": int(len(table)),
        "column_count": int(len(table.columns)),
        "missing_ratio": missing_ratio,
        "target_column": target_column,
        "target_present": bool(target_present),
        "class_distribution": class_distribution,
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    item_fn = getattr(value, "item", None)
    if callable(item_fn):
        try:
            return item_fn()
        except Exception:
            pass
    iso_fn = getattr(value, "isoformat", None)
    if callable(iso_fn):
        try:
            return iso_fn()
        except Exception:
            pass
    return value
