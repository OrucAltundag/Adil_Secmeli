# -*- coding: utf-8 -*-
"""Algoritma yönetişimi ve governed benchmark raporlama servisi."""

from __future__ import annotations

import csv
import io
import json
import sqlite3
from typing import Any

from app.services.algorithm_governance_service import list_algorithm_governance, list_task_mappings
from app.services.governed_benchmark_service import get_governed_run_report


def generate_algorithm_role_report(conn: sqlite3.Connection) -> dict[str, Any]:
    algorithms = list_algorithm_governance(conn)
    tasks = list_task_mappings(conn)
    role_counts: dict[str, int] = {}
    for row in algorithms:
        role_counts[row["usage_role"]] = role_counts.get(row["usage_role"], 0) + 1
    return {
        "algorithms": algorithms,
        "task_mappings": tasks,
        "role_counts": role_counts,
        "summary_text": (
            "Algoritmalar aynı karar seviyesinde kullanılmaz. Nihai karar AHP + TOPSIS + kural motoru + state machine hattıyla verilir; "
            "ML, clustering ve benchmark algoritmaları rol etiketlerine göre sınırlandırılır."
        ),
    }


def generate_benchmark_statistical_report(conn: sqlite3.Connection, benchmark_run_id: int) -> dict[str, Any]:
    report = get_governed_run_report(conn, benchmark_run_id)
    stats = report.get("statistics") or []
    return {"benchmark_run_id": benchmark_run_id, "statistics": stats, "summary_text": stats[0].get("summary_text") if stats else "İstatistiksel karşılaştırma bulunamadı."}


def generate_algorithm_data_guard_report(conn: sqlite3.Connection, benchmark_run_id: int) -> dict[str, Any]:
    metrics = get_governed_run_report(conn, benchmark_run_id).get("metrics") or []
    guards = []
    for row in metrics:
        metrics_json = row.get("metrics") or {}
        if isinstance(metrics_json, str):
            try:
                metrics_json = json.loads(metrics_json)
            except Exception:
                metrics_json = {}
        guards.append({"algorithm_key": row.get("algorithm_key"), "warnings": row.get("warnings") or row.get("warnings_json"), "metrics": metrics_json})
    return {"benchmark_run_id": benchmark_run_id, "data_guard": guards}


def generate_clustering_report(conn: sqlite3.Connection, benchmark_run_id: int) -> dict[str, Any]:
    clustering = get_governed_run_report(conn, benchmark_run_id).get("clustering") or []
    return {
        "benchmark_run_id": benchmark_run_id,
        "clustering": clustering,
        "summary_text": "Clustering sonuçları keşifsel analizdir; nihai müfredat kararı üretmez.",
    }


def export_benchmark_report(conn: sqlite3.Connection, benchmark_run_id: int, format: str = "json") -> str:
    report = get_governed_run_report(conn, benchmark_run_id)
    if format == "csv":
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=["algorithm_key", "task_type", "primary_metric_name", "primary_metric_value"])
        writer.writeheader()
        for row in report.get("metrics") or []:
            writer.writerow(
                {
                    "algorithm_key": row.get("algorithm_key"),
                    "task_type": row.get("task_type"),
                    "primary_metric_name": row.get("primary_metric_name"),
                    "primary_metric_value": row.get("primary_metric_value"),
                }
            )
        return buffer.getvalue()
    return json.dumps(report, ensure_ascii=False, indent=2)


def export_algorithm_governance_matrix(conn: sqlite3.Connection, format: str = "json") -> str:
    report = generate_algorithm_role_report(conn)
    if format == "csv":
        buffer = io.StringIO()
        rows = report["algorithms"]
        writer = csv.DictWriter(buffer, fieldnames=["algorithm_key", "display_name", "algorithm_family", "task_type", "usage_role", "can_affect_final_decision", "minimum_sample_count"])
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in writer.fieldnames})
        return buffer.getvalue()
    return json.dumps(report, ensure_ascii=False, indent=2)
