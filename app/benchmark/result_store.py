"""Persistence layer for benchmark runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.datasets.entities import BenchmarkRun

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None


def _json_default(value: Any):
    if np is not None:
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, np.ndarray):
            return value.tolist()
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    if isinstance(value, set):
        return list(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class ResultStore:
    def __init__(self, root_dir: str = "reports/benchmark_runs") -> None:
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_run(self, run: BenchmarkRun, payload: dict[str, Any]) -> Path:
        path = self.root / f"{run.run_id}.json"
        data = {
            "run": run.as_dict(),
            "payload": payload,
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
        return path

    def load_run(self, run_id: str) -> dict[str, Any]:
        path = self.root / f"{run_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Run not found: {run_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def list_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        files = sorted(self.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
        runs = []
        for path in files:
            try:
                runs.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
        return runs
