"""Small REST client for the desktop Benchmark Platform UI."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from app.ui.benchmark import mock_data

DEFAULT_BASE_URL = os.environ.get("ADIL_BENCHMARK_API_URL", "http://127.0.0.1:8000")


@dataclass(slots=True)
class ApiResult:
    ok: bool
    data: Any
    error: str | None = None
    used_mock: bool = False


class BenchmarkApiClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 6.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self.last_dataset: dict[str, Any] | None = None
        self.last_dataset_name: str | None = None
        self.last_dataset_used_mock = False
        self.selected_run_ids_for_comparison: list[str] = []

    def get_scenarios(self) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", "/api/v1/benchmark/scenarios"), mock_data.get_mock_scenarios)

    def get_algorithms(self) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", "/api/v1/benchmark/algorithms"), mock_data.get_mock_algorithms)

    def load_dataset(self, payload: dict[str, Any] | None = None) -> ApiResult:
        body = payload or {"source_type": "csv", "source_path": "data/benchmark/raw_real", "dataset_name": "desktop_benchmark_dataset"}
        result = self._with_mock(lambda: self._request("POST", "/api/v1/benchmark/datasets/load", body), mock_data.get_mock_dataset_load_result)
        if isinstance(result.data, dict):
            self.last_dataset = result.data
            self.last_dataset_name = result.data.get("dataset_name")
            self.last_dataset_used_mock = bool(result.used_mock)
        return result

    def execute_run(self, payload: dict[str, Any]) -> ApiResult:
        body = self._normalize_run_payload(payload)
        return self._with_mock(lambda: self._request("POST", "/api/v1/benchmark/runs/execute", body), lambda: mock_data.get_mock_execute_run(body))

    def compare_runs(self, payload: dict[str, Any]) -> ApiResult:
        body = self._normalize_run_payload(payload)
        return self._with_mock(lambda: self._request("POST", "/api/v1/benchmark/runs/compare", body), lambda: mock_data.get_mock_execute_run(body))

    def get_recommendation(self, payload: dict[str, Any]) -> ApiResult:
        body = {
            "problem_type": payload.get("problem_type") or payload.get("scenario") or "prediction",
            "data_size": int(payload.get("data_size") or 5000),
            "explainability_priority": bool(payload.get("explainability_priority", False)),
            "use_history": bool(payload.get("use_history", True)),
        }
        return self._with_mock(
            lambda: self._request("POST", "/api/v1/benchmark/recommendation", body),
            lambda: mock_data.get_mock_recommendation(body),
        )

    def get_runs(self) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", "/api/v1/benchmark/runs"), mock_data.get_mock_runs)

    def get_run_detail(self, run_id: str) -> ApiResult:
        safe_id = urllib.parse.quote(str(run_id), safe="")
        return self._with_mock(lambda: self._request("GET", f"/api/v1/benchmark/runs/{safe_id}"), lambda: mock_data.get_mock_run_detail(run_id))

    def get_ml_readiness(self) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", "/api/v1/ml/readiness"), mock_data.get_mock_ml_readiness)

    def get_ml_model_runs(self) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", "/api/v1/ml/model-runs"), mock_data.get_mock_ml_model_runs)

    def get_ml_predictions(self) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", "/api/v1/ml/predictions"), mock_data.get_mock_ml_predictions)

    def get_ml_feature_summary(self) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", "/api/v1/ml/features/summary"), mock_data.get_mock_ml_feature_summary)

    def build_ml_feature_snapshot(self, payload: dict[str, Any] | None = None) -> ApiResult:
        body = payload or {"save_snapshot": True}
        return self._with_mock(lambda: self._request("POST", "/api/v1/ml/features/build-snapshot", body), lambda: mock_data.get_mock_ml_feature_snapshot(body))

    def train_ml_model(self, payload: dict[str, Any]) -> ApiResult:
        return self._with_mock(lambda: self._request("POST", "/api/v1/ml/model-runs/train", payload), lambda: mock_data.get_mock_ml_train(payload))

    def create_ml_readiness_report(self, payload: dict[str, Any] | None = None) -> ApiResult:
        body = payload or {"save": True}
        return self._with_mock(lambda: self._request("POST", "/api/v1/ml/readiness/report", body), lambda: mock_data.get_mock_ml_readiness_report(body))

    def get_ml_readiness_reports(self) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", "/api/v1/ml/readiness-reports"), mock_data.get_mock_ml_readiness_reports)

    def get_algorithm_governance(self) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", "/api/v1/algorithms/governance"), mock_data.get_mock_algorithm_governance)

    def set_algorithm_active(self, algorithm_key: str, is_active: bool) -> ApiResult:
        """Algoritmayı aktif/pasif yapar (mock fallback yok; gerçek API gerektirir)."""
        return self._with_mock(
            lambda: self._request(
                "PATCH",
                f"/api/v1/algorithms/governance/{algorithm_key}/active",
                {"is_active": bool(is_active)},
            ),
            lambda: {"data": {"algorithm_key": algorithm_key, "is_active": bool(is_active)}},
        )

    def get_algorithm_tasks(self) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", "/api/v1/algorithms/tasks"), mock_data.get_mock_algorithm_tasks)

    def get_governed_runs(self) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", "/api/v1/benchmark/governed-runs"), mock_data.get_mock_governed_runs)

    def execute_governed_run(self, payload: dict[str, Any]) -> ApiResult:
        return self._with_mock(
            lambda: self._request("POST", "/api/v1/benchmark/governed-runs/execute", payload),
            lambda: mock_data.get_mock_execute_governed_run(payload),
        )

    def get_governed_run_metrics(self, run_id: int | str) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", f"/api/v1/benchmark/governed-runs/{run_id}/metrics"), mock_data.get_mock_governed_run_metrics)

    def get_governed_run_validation(self, run_id: int | str) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", f"/api/v1/benchmark/governed-runs/{run_id}/validation"), mock_data.get_mock_governed_run_validation)

    def get_governed_run_statistics(self, run_id: int | str) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", f"/api/v1/benchmark/governed-runs/{run_id}/statistics"), mock_data.get_mock_governed_run_statistics)

    def get_governed_run_diagnostics(self, run_id: int | str) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", f"/api/v1/benchmark/governed-runs/{run_id}/diagnostics"), mock_data.get_mock_governed_run_diagnostics)

    def get_governed_run_leakage(self, run_id: int | str) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", f"/api/v1/benchmark/governed-runs/{run_id}/leakage"), mock_data.get_mock_governed_run_leakage)

    def get_governed_run_clustering(self, run_id: int | str) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", f"/api/v1/benchmark/governed-runs/{run_id}/clustering"), mock_data.get_mock_governed_run_clustering)

    def _normalize_run_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        algorithms = payload.get("algorithm_names") or payload.get("algorithms") or []
        body = {
            "scenario_name": payload.get("scenario_name") or payload.get("scenario") or "real_mcdm_recommendation",
            "algorithm_names": algorithms,
            "synthetic_tier": payload.get("synthetic_tier"),
            "top_k": payload.get("top_k") or payload.get("k") or 10,
        }
        if payload.get("allocation_parameters") is not None:
            body["allocation_parameters"] = payload["allocation_parameters"]
        return body

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url=url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}

    def _with_mock(self, call, fallback) -> ApiResult:
        try:
            return ApiResult(ok=True, data=call(), used_mock=False)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError, ValueError) as exc:
            return ApiResult(ok=False, data=fallback(), error=str(exc), used_mock=True)
