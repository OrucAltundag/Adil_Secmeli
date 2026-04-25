# -*- coding: utf-8 -*-
"""Benchmark ve algoritma yönetişimi için düşük seviyeli repository."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.base import fetch_all_dicts


class BenchmarkRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_algorithm_governance(self) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT algorithm_key, display_name, algorithm_family, task_type, usage_role,
                   can_affect_final_decision, minimum_sample_count, recommended_metrics_json
            FROM algorithm_governance_registry
            ORDER BY algorithm_family, algorithm_key
            """
        )
        return fetch_all_dicts(cur)

    def list_benchmark_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, run_name, task_type, dataset_name, sample_count, feature_count,
                   algorithms_json, validation_strategy, primary_metric_name, status,
                   started_at, completed_at
            FROM algorithm_benchmark_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        return fetch_all_dicts(cur)

    def get_benchmark_run(self, run_id: int) -> dict[str, Any] | None:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM algorithm_benchmark_runs WHERE id = ?", (int(run_id),))
        rows = fetch_all_dicts(cur)
        return rows[0] if rows else None
