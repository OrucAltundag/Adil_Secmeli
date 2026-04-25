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

    def get_scenarios(self) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", "/api/v1/benchmark/scenarios"), mock_data.get_mock_scenarios)

    def get_algorithms(self) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", "/api/v1/benchmark/algorithms"), mock_data.get_mock_algorithms)

    def load_dataset(self, payload: dict[str, Any] | None = None) -> ApiResult:
        body = payload or {"source_type": "csv", "source_path": "data/benchmark/raw_real", "dataset_name": "desktop_benchmark_dataset"}
        return self._with_mock(lambda: self._request("POST", "/api/v1/benchmark/datasets/load", body), mock_data.get_mock_dataset_load_result)

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
            lambda: mock_data.get_mock_recommendation(body["problem_type"]),
        )

    def get_runs(self) -> ApiResult:
        return self._with_mock(lambda: self._request("GET", "/api/v1/benchmark/runs"), mock_data.get_mock_runs)

    def get_run_detail(self, run_id: str) -> ApiResult:
        safe_id = urllib.parse.quote(str(run_id), safe="")
        return self._with_mock(lambda: self._request("GET", f"/api/v1/benchmark/runs/{safe_id}"), lambda: mock_data.get_mock_run_detail(run_id))

    def _normalize_run_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        algorithms = payload.get("algorithm_names") or payload.get("algorithms") or []
        return {
            "scenario_name": payload.get("scenario_name") or payload.get("scenario") or "real_mcdm_recommendation",
            "algorithm_names": algorithms,
            "synthetic_tier": payload.get("synthetic_tier"),
            "top_k": payload.get("top_k") or payload.get("k") or 10,
        }

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
