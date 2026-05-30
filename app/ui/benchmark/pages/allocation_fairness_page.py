from __future__ import annotations

import tkinter as tk
from collections import defaultdict
from tkinter import ttk
from typing import Any

from app.ui.benchmark import mock_data
from app.ui.benchmark.widgets import (
    COLORS,
    BarChart,
    DataTable,
    ErrorBanner,
    MetricCard,
    PageInfoBox,
    SectionHeader,
    SourceBadge,
    run_async,
)

ALLOCATION_ALGORITHMS = ["GaleShapley", "RandomAllocation", "GreedyAllocation", "MinimumRegretAllocation"]
PRIORITY_RULES = {
    "GPA önceliği": "gpa_priority",
    "Tercih sırası": "preference_rank",
    "Rastgele baseline": "random_baseline",
}
DEPARTMENT_RULES = {
    "Bölüm kontenjanını koru": "department_quota",
    "Fakülte geneli": "faculty_pool",
    "Esnek": "flexible",
}


def normalize_allocation_result(payload: dict[str, Any], top_k: int = 3) -> dict[str, Any]:
    details = payload.get("details", {}) if isinstance(payload, dict) else {}
    results = details.get("results", {}) if isinstance(details, dict) else {}
    comparison = payload.get("comparison_table", []) if isinstance(payload, dict) else []
    comparison_by_algorithm = {
        str(row.get("algorithm")): row for row in comparison if isinstance(row, dict) and row.get("algorithm")
    }

    fairness_rows: list[dict[str, Any]] = []
    assignment_rows: list[dict[str, Any]] = []
    if isinstance(results, dict):
        for algorithm, result in results.items():
            if not isinstance(result, dict):
                continue
            output = result.get("output") or {}
            metrics = (result.get("metrics") or {}).get("fairness") or {}
            raw_assignments = output.get("assignments") or []
            normalized_assignments = [
                _normalize_assignment_row(row, str(algorithm), top_k)
                for row in raw_assignments
                if isinstance(row, dict)
            ]
            assignment_rows.extend(normalized_assignments)
            fairness_rows.append(
                _build_fairness_row(
                    str(algorithm),
                    metrics,
                    normalized_assignments,
                    comparison_by_algorithm.get(str(algorithm), {}),
                    top_k,
                )
            )

    if not fairness_rows:
        fairness_rows = [_build_fairness_row(str(row.get("algorithm")), {}, [], row, top_k) for row in comparison_by_algorithm.values()]
    if not fairness_rows:
        fairness_rows = [dict(row) for row in mock_data.FAIRNESS_ROWS]
    if not assignment_rows:
        assignment_rows = [_normalize_assignment_row(row, str(row.get("algorithm") or "GaleShapley"), top_k) for row in mock_data.ALLOCATION_ROWS]

    issue_rows = _build_issue_rows(assignment_rows)
    return {
        "fairness_rows": fairness_rows,
        "assignment_rows": assignment_rows,
        "breakdown_rows": _build_breakdown_rows(assignment_rows),
        "issue_rows": issue_rows,
        "transfer": _transfer_status(fairness_rows, issue_rows),
    }


class AllocationFairnessPage(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=14)
        self.api = api_client
        self.metric_cards: dict[str, MetricCard] = {}
        self.last_payload: dict[str, Any] | None = None
        self._build()
        self._apply_view(normalize_allocation_result({"comparison_table": mock_data.FAIRNESS_ROWS}, top_k=3))

    def _build(self) -> None:
        SectionHeader(
            self,
            "Yerleştirme Adaleti",
            "Yerleştirme algoritmalarını tercih memnuniyeti ve kontenjan adaletiyle izleyin.",
        ).pack(fill=tk.X)
        PageInfoBox(
            self,
            "Öğrenci-ders yerleştirme algoritmalarını adalet, memnuniyet ve kontenjan kullanımı açısından karşılaştırır.",
            "Yerleştirme benchmark'ını çalıştırıp algoritma tablosundan ortalama tercih sırası, top-k memnuniyet ve atanmayan öğrenci sayılarını inceleyin.",
            "Bu ekran dönem planlama kararını destekler; kesin planı tek başına üretmez.",
        ).pack(fill=tk.X, pady=(10, 0))
        self.source_badge = SourceBadge(self)
        self.source_badge.set_source(True)
        self.source_badge.pack(fill=tk.X, pady=(6, 0))
        self.banner = ErrorBanner(self)

        controls = ttk.LabelFrame(self, text="Çalıştırma Parametreleri", padding=8)
        controls.pack(fill=tk.X, pady=(8, 4))
        self.top_k_var = tk.IntVar(value=3)
        self.capacity_scale_var = tk.DoubleVar(value=1.0)
        self.priority_var = tk.StringVar(value="GPA önceliği")
        self.department_rule_var = tk.StringVar(value="Bölüm kontenjanını koru")

        ttk.Label(controls, text="Top-K").pack(side=tk.LEFT)
        tk.Spinbox(controls, from_=1, to=10, width=5, textvariable=self.top_k_var).pack(side=tk.LEFT, padx=(4, 12))
        ttk.Label(controls, text="Kontenjan katsayısı").pack(side=tk.LEFT)
        tk.Spinbox(controls, from_=0.5, to=2.0, increment=0.1, width=6, textvariable=self.capacity_scale_var).pack(side=tk.LEFT, padx=(4, 12))
        ttk.Label(controls, text="Öncelik").pack(side=tk.LEFT)
        ttk.Combobox(controls, textvariable=self.priority_var, values=list(PRIORITY_RULES), state="readonly", width=18).pack(side=tk.LEFT, padx=(4, 12))
        ttk.Label(controls, text="Bölüm kuralı").pack(side=tk.LEFT)
        ttk.Combobox(controls, textvariable=self.department_rule_var, values=list(DEPARTMENT_RULES), state="readonly", width=22).pack(side=tk.LEFT, padx=(4, 12))
        ttk.Button(controls, text="Yerleştirme Benchmark Çalıştır", command=self.run_allocation).pack(side=tk.RIGHT)

        metric_frame = ttk.Frame(self)
        metric_frame.pack(fill=tk.X, pady=(6, 10))
        card_defs = [
            ("average_rank", "Ortalama Tercih", COLORS["blue"]),
            ("top_k_satisfaction", "Top-K Memnuniyet", COLORS["green"]),
            ("envy_score", "Envy Skoru", COLORS["orange"]),
            ("seat_fill_rate", "Koltuk Doluluk", COLORS["cyan"]),
            ("capacity_violations", "Kontenjan İhlali", COLORS["red"]),
            ("unassigned", "Atanmayan", COLORS["red"]),
            ("transfer", "Planlamaya Aktarım", COLORS["orange"]),
        ]
        for idx, (key, title, color) in enumerate(card_defs):
            card = MetricCard(metric_frame, title, "-", accent=color)
            card.grid(row=idx // 4, column=idx % 4, sticky="nsew", padx=4, pady=3)
            metric_frame.columnconfigure(idx % 4, weight=1)
            self.metric_cards[key] = card

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        comp_frame = ttk.LabelFrame(body, text="Algoritma Karşılaştırması", padding=8)
        comp_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.fairness_table = DataTable(
            comp_frame,
            ["algorithm", "average_rank", "top_k_satisfaction", "envy_score", "seat_fill_rate", "assigned", "unassigned", "capacity_violations"],
            height=5,
            column_labels={
                "algorithm": "Algoritma",
                "average_rank": "Ortalama Sıra",
                "top_k_satisfaction": "Top-K Memnuniyet",
                "envy_score": "Envy Skoru",
                "seat_fill_rate": "Koltuk Doluluk",
                "assigned": "Atanan",
                "unassigned": "Atanmayan",
                "capacity_violations": "Kontenjan İhlali",
            },
        )
        self.fairness_table.pack(fill=tk.X)

        assign_frame = ttk.LabelFrame(body, text="Öğrenci - Atama Tablosu", padding=8)
        assign_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        self.assignment_table = DataTable(
            assign_frame,
            ["student_id", "student_name", "assigned_course", "assigned_course_id", "preference_rank_received", "satisfaction_score", "algorithm", "capacity_status"],
            height=8,
            column_labels={
                "student_id": "Öğrenci ID",
                "student_name": "Öğrenci",
                "assigned_course": "Atanan Ders",
                "assigned_course_id": "Ders ID",
                "preference_rank_received": "Tercih Sırası",
                "satisfaction_score": "Memnuniyet",
                "algorithm": "Algoritma",
                "capacity_status": "Kontenjan Durumu",
            },
        )
        self.assignment_table.pack(fill=tk.BOTH, expand=True)

        right_tabs = ttk.Notebook(body)
        right_tabs.grid(row=1, column=1, sticky="nsew")
        chart_frame = ttk.Frame(right_tabs, padding=8)
        breakdown_frame = ttk.Frame(right_tabs, padding=8)
        issues_frame = ttk.Frame(right_tabs, padding=8)
        right_tabs.add(chart_frame, text="Grafik")
        right_tabs.add(breakdown_frame, text="Fakülte/Bölüm")
        right_tabs.add(issues_frame, text="İhlal ve Nedenler")

        self.chart = BarChart(chart_frame, height=220)
        self.chart.pack(fill=tk.BOTH, expand=True)
        self.breakdown_table = DataTable(
            breakdown_frame,
            ["scope", "group", "assigned", "unassigned", "avg_satisfaction", "avg_rank"],
            height=8,
            column_labels={
                "scope": "Kırılım",
                "group": "Grup",
                "assigned": "Atanan",
                "unassigned": "Atanmayan",
                "avg_satisfaction": "Ort. Memnuniyet",
                "avg_rank": "Ort. Tercih",
            },
        )
        self.breakdown_table.pack(fill=tk.BOTH, expand=True)
        self.issue_table = DataTable(
            issues_frame,
            ["type", "algorithm", "group", "affected", "reason"],
            height=8,
            column_labels={"type": "Tür", "algorithm": "Algoritma", "group": "Grup/Ders", "affected": "Etkilenen", "reason": "Neden"},
        )
        self.issue_table.pack(fill=tk.BOTH, expand=True)

    def run_allocation(self) -> None:
        parameters = self._allocation_parameters()
        payload = {
            "scenario": "allocation_fairness",
            "algorithms": ALLOCATION_ALGORITHMS,
            "top_k": parameters["top_k"],
            "allocation_parameters": parameters,
        }
        self.last_payload = payload

        def worker():
            return self.api.execute_run(payload)

        def success(result):
            self.source_badge.set_source(result.used_mock)
            if result.used_mock:
                self.banner.show("Backend API erişilemiyor; örnek yerleştirme sonuçları gösteriliyor.", level="warning")
            else:
                self.banner.show("Yerleştirme benchmark sonucu gerçek run çıktısından güncellendi.", level="warning")
            self._apply_view(normalize_allocation_result(result.data, top_k=parameters["top_k"]))

        def error(exc):
            self.banner.show(f"Yerleştirme benchmark çalıştırılamadı: {exc}")

        self._run_api_action(worker, success, error)

    def _allocation_parameters(self) -> dict[str, Any]:
        return {
            "top_k": int(self.top_k_var.get() or 3),
            "capacity_scale": float(self.capacity_scale_var.get() or 1.0),
            "priority_rule": PRIORITY_RULES.get(self.priority_var.get(), "gpa_priority"),
            "department_rule": DEPARTMENT_RULES.get(self.department_rule_var.get(), "department_quota"),
        }

    def _apply_view(self, view: dict[str, Any]) -> None:
        fairness_rows = view["fairness_rows"]
        assignment_rows = view["assignment_rows"]
        best = _best_fairness_row(fairness_rows)
        self.fairness_table.set_rows(fairness_rows)
        self.assignment_table.set_rows(assignment_rows[:200])
        self.breakdown_table.set_rows(view["breakdown_rows"])
        self.issue_table.set_rows(view["issue_rows"])
        self.chart.plot(fairness_rows, "algorithm", "seat_fill_rate", color=COLORS["green"])

        self.metric_cards["average_rank"].set_value(best.get("average_rank", "—"))
        self.metric_cards["top_k_satisfaction"].set_value(best.get("top_k_satisfaction", "—"))
        self.metric_cards["envy_score"].set_value(best.get("envy_score", "—"))
        self.metric_cards["seat_fill_rate"].set_value(best.get("seat_fill_rate", "—"))
        self.metric_cards["capacity_violations"].set_value(best.get("capacity_violations", 0))
        self.metric_cards["unassigned"].set_value(best.get("unassigned", 0))
        transfer = view["transfer"]
        self.metric_cards["transfer"].set_value(transfer["status"], transfer["reason"])
        self.metric_cards["transfer"].set_accent(COLORS["green"] if transfer["status"] == "Aktarılabilir" else COLORS["orange"])

    def _run_api_action(self, worker, success, error) -> None:
        if self.api.__class__.__name__ != "BenchmarkApiClient":
            try:
                success(worker())
            except Exception as exc:
                error(exc)
            return
        run_async(self, worker, success, error)


def _normalize_assignment_row(row: dict[str, Any], algorithm: str, top_k: int) -> dict[str, Any]:
    course_id = row.get("assigned_course_id", row.get("course_id"))
    allocated = _as_bool(row.get("allocated"), default=course_id not in {None, "", "—"})
    rank = row.get("preference_rank_received", row.get("rank_received", row.get("rank")))
    rank_value = _as_float(rank, 0.0)
    satisfaction = row.get("satisfaction_score")
    if satisfaction is None or satisfaction == "":
        satisfaction = max(0.0, 1.0 - ((rank_value - 1.0) / max(float(top_k), 1.0))) if allocated and rank_value else 0.0
    return {
        **row,
        "student_id": row.get("student_id", "—"),
        "student_name": row.get("student_name") or f"Anonim-{row.get('student_id', '—')}",
        "assigned_course": row.get("assigned_course") or row.get("course_name") or (course_id if allocated else "Atanmadı"),
        "assigned_course_id": course_id if allocated else "—",
        "preference_rank_received": rank if allocated else "—",
        "satisfaction_score": round(_as_float(satisfaction), 3),
        "algorithm": row.get("algorithm") or algorithm,
        "capacity_status": row.get("capacity_status") or ("Atandı" if allocated else "Atanmadı"),
        "allocated": allocated,
        "faculty": row.get("faculty") or row.get("faculty_id") or "Bilinmiyor",
        "department": row.get("department") or row.get("department_id") or "Bilinmiyor",
        "course_capacity": row.get("course_capacity") or row.get("capacity"),
        "unassigned_reason": row.get("unassigned_reason") or ("—" if allocated else "Tercih edilen derslerde kontenjan kalmadı veya uygun tercih yok."),
    }


def _build_fairness_row(algorithm: str, metrics: dict[str, Any], assignments: list[dict[str, Any]], comparison_row: dict[str, Any], top_k: int) -> dict[str, Any]:
    assigned = len([row for row in assignments if row.get("allocated")])
    total = len(assignments)
    ranks = [_as_float(row.get("preference_rank_received"), 0.0) for row in assignments if row.get("allocated") and row.get("preference_rank_received") != "—"]
    top_k_satisfaction = len([rank for rank in ranks if rank <= top_k]) / max(1, len(ranks)) if ranks else None
    average_rank = _first_number(metrics, comparison_row, "average_rank", "average_assigned_rank")
    top_k_value = _first_number(metrics, comparison_row, "top_k_satisfaction", f"top_{top_k}_satisfaction", "top_3_satisfaction")
    envy_value = _first_number(metrics, comparison_row, "envy_score")
    fill_value = _first_number(metrics, comparison_row, "seat_fill_rate")
    return {
        "algorithm": algorithm,
        "average_rank": average_rank if average_rank is not None else (sum(ranks) / max(1, len(ranks)) if ranks else "—"),
        "top_k_satisfaction": top_k_value if top_k_value is not None else (top_k_satisfaction if top_k_satisfaction is not None else "—"),
        "envy_score": envy_value if envy_value is not None else "—",
        "seat_fill_rate": fill_value if fill_value is not None else (assigned / max(1, total)),
        "assigned": assigned if total else comparison_row.get("assigned", "—"),
        "unassigned": (total - assigned) if total else comparison_row.get("unassigned", "—"),
        "capacity_violations": _capacity_violation_count(assignments),
    }


def _build_breakdown_rows(assignments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for scope, key in [("Fakülte", "faculty"), ("Bölüm", "department")]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in assignments:
            groups[str(row.get(key) or "Bilinmiyor")].append(row)
        for group, items in sorted(groups.items()):
            assigned_items = [item for item in items if item.get("allocated")]
            ranks = [_as_float(item.get("preference_rank_received"), 0.0) for item in assigned_items if item.get("preference_rank_received") != "—"]
            rows.append(
                {
                    "scope": scope,
                    "group": group,
                    "assigned": len(assigned_items),
                    "unassigned": len(items) - len(assigned_items),
                    "avg_satisfaction": round(sum(_as_float(item.get("satisfaction_score")) for item in assigned_items) / max(1, len(assigned_items)), 3),
                    "avg_rank": round(sum(ranks) / max(1, len(ranks)), 3) if ranks else "—",
                }
            )
    return rows or [{"scope": "—", "group": "Kayıt yok", "assigned": 0, "unassigned": 0, "avg_satisfaction": "—", "avg_rank": "—"}]


def _build_issue_rows(assignments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues = []
    for row in assignments:
        if not row.get("allocated"):
            issues.append(
                {
                    "type": "Atanmayan",
                    "algorithm": row.get("algorithm"),
                    "group": row.get("department"),
                    "affected": row.get("student_id"),
                    "reason": row.get("unassigned_reason"),
                }
            )
    by_course: dict[tuple[str, Any], list[dict[str, Any]]] = defaultdict(list)
    for row in assignments:
        if row.get("allocated") and row.get("assigned_course_id") not in {None, "", "—"}:
            by_course[(str(row.get("algorithm")), row.get("assigned_course_id"))].append(row)
    for (algorithm, course_id), rows in by_course.items():
        capacity = rows[0].get("course_capacity")
        if capacity is None or capacity == "" or capacity == "—":
            continue
        cap = int(_as_float(capacity, 0.0))
        if cap > 0 and len(rows) > cap:
            issues.append(
                {
                    "type": "Kontenjan İhlali",
                    "algorithm": algorithm,
                    "group": course_id,
                    "affected": len(rows) - cap,
                    "reason": f"{len(rows)} atama / {cap} kontenjan",
                }
            )
    return issues or [{"type": "Sorun yok", "algorithm": "—", "group": "—", "affected": 0, "reason": "Kontenjan ihlali veya atanmayan kayıt görünmüyor."}]


def _transfer_status(fairness_rows: list[dict[str, Any]], issue_rows: list[dict[str, Any]]) -> dict[str, str]:
    blocking_issues = [row for row in issue_rows if row.get("type") != "Sorun yok"]
    best = _best_fairness_row(fairness_rows)
    if blocking_issues:
        return {"status": "İnceleme gerekli", "reason": "Atanmayan veya kontenjan ihlali var."}
    if _as_float(best.get("seat_fill_rate")) >= 0.95 and _as_float(best.get("envy_score"), 1.0) <= 0.25:
        return {"status": "Aktarılabilir", "reason": "Doluluk ve envy eşikleri sağlandı."}
    return {"status": "İnceleme gerekli", "reason": "Doluluk veya envy eşiği sağlanmadı."}


def _best_fairness_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    return max(rows, key=lambda row: (_as_float(row.get("seat_fill_rate")), _as_float(row.get("top_k_satisfaction")), -_as_float(row.get("envy_score"), 1.0)))


def _capacity_violation_count(assignments: list[dict[str, Any]]) -> int:
    issues = [row for row in _build_issue_rows(assignments) if row.get("type") == "Kontenjan İhlali"]
    return sum(int(_as_float(row.get("affected"), 0.0)) for row in issues)


def _first_number(metrics: dict[str, Any], comparison_row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        for source_key in [key, f"fairness.{key}"]:
            value = metrics.get(source_key) if source_key in metrics else comparison_row.get(source_key)
            if value not in {None, ""}:
                return value
    return None


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str) and value in {"", "—"}:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "evet", "yes", "atandı"}
    return bool(value)
