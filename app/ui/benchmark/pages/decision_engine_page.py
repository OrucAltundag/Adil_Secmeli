from __future__ import annotations

import re
import tkinter as tk
from tkinter import ttk
from typing import Any

from app.ui.benchmark.widgets import (
    COLORS,
    DataTable,
    ErrorBanner,
    JsonPreviewWidget,
    MetricCard,
    PageInfoBox,
    SectionHeader,
    SourceBadge,
    run_async,
)

ALGORITHM_KEY_MAP = {
    "ahp": "ahp",
    "topsis": "topsis",
    "vikor": "vikor",
    "prometheeii": "promethee_ii",
    "promethee_ii": "promethee_ii",
    "randomforest": "random_forest",
    "random_forest": "random_forest",
    "logisticregression": "logistic_regression",
    "logistic_regression": "logistic_regression",
    "naivebayes": "naive_bayes",
    "naive_bayes": "naive_bayes",
    "xgboostlike": "xgboost",
    "xgboost": "xgboost",
    "galeshapley": "gale_shapley",
    "gale_shapley": "gale_shapley",
    "greedyallocation": "greedy_allocation",
    "minimumregretallocation": "minimum_regret",
    "kmeans": "kmeans",
    "dbscan": "dbscan",
    "hierarchicalclustering": "hierarchical_clustering",
}


def canonical_algorithm_key(name: str | None) -> str:
    normalized = re.sub(r"[^a-z0-9_]", "", str(name or "").replace("-", "_").lower())
    return ALGORITHM_KEY_MAP.get(normalized, normalized)


def build_candidate_rows(
    recommendation: dict[str, Any],
    governance_rows: list[dict[str, Any]],
    readiness_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    recommended_key = canonical_algorithm_key(recommendation.get("algorithm"))
    candidates = recommendation.get("candidates") or [recommendation.get("algorithm")]
    rows = []
    for candidate in candidates:
        key = canonical_algorithm_key(str(candidate))
        governance = _find_algorithm(governance_rows, key)
        readiness = _find_algorithm(readiness_rows, key)
        is_selected = key == recommended_key
        rows.append(
            {
                "Aday": candidate,
                "Durum": "Önerildi" if is_selected else "Elendi",
                "Rol": _role_label(governance.get("usage_role")),
                "Readiness": readiness.get("readiness_level") or ("ML değil" if governance.get("algorithm_family") != "ml" else "Bilinmiyor"),
                "Gerekçe": recommendation.get("reason") if is_selected else _elimination_reason(governance, readiness),
            }
        )
    return rows


class DecisionEnginePage(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=14)
        self.api = api_client
        self.problem_type_map = {
            "Tahmin": "prediction",
            "Sıralama": "ranking",
            "Yerleştirme": "allocation",
            "Kümeleme": "clustering",
        }
        self._build()
        self.request_recommendation()

    def _build(self) -> None:
        SectionHeader(
            self,
            "Algoritma Öneri Motoru",
            "Veri profili, senaryo ve benchmark geçmişine göre uygun algoritma adayı önerir.",
        ).pack(fill=tk.X)
        PageInfoBox(
            self,
            "Problem türü ve veri büyüklüğüne göre hangi algoritmanın denenebileceğini önerir.",
            "Problem tipini, veri boyutunu ve açıklanabilirlik önceliğini seçip Öneri Üret düğmesine basın.",
            "Bu öneri final karar değildir; benchmark ve yönetişim kontrolleriyle birlikte değerlendirilmelidir.",
        ).pack(fill=tk.X, pady=(10, 0))
        self.source_badge = SourceBadge(self)
        self.source_badge.pack(fill=tk.X, pady=(6, 0))
        self.banner = ErrorBanner(self)

        controls = ttk.LabelFrame(self, text="Öneri Girdileri", padding=10)
        controls.pack(fill=tk.X, pady=(12, 10))
        ttk.Label(controls, text="Problem Tipi").grid(row=0, column=0, sticky="w")
        self.problem_cb = ttk.Combobox(controls, state="readonly", values=list(self.problem_type_map.keys()), width=18)
        self.problem_cb.set("Tahmin")
        self.problem_cb.grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(controls, text="Veri Boyutu").grid(row=0, column=2, sticky="w")
        self.size_entry = ttk.Entry(controls, width=12)
        self.size_entry.insert(0, "5000")
        self.size_entry.grid(row=0, column=3, sticky="w", padx=8)
        self.explain_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls, text="Açıklanabilirlik öncelikli", variable=self.explain_var).grid(row=0, column=4, sticky="w", padx=8)
        ttk.Button(controls, text="Öneri Üret", command=self.request_recommendation).grid(row=0, column=5, sticky="e")

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        rec_frame = ttk.LabelFrame(body, text="Sistemin Önerdiği Algoritma", padding=12)
        rec_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        self.algorithm_card = MetricCard(rec_frame, "Algoritma", "-", "Gerekçe bekleniyor", accent=COLORS["blue"])
        self.algorithm_card.pack(fill=tk.X)
        self.confidence_card = MetricCard(rec_frame, "Güven Skoru", "-", "0-1 arası", accent=COLORS["green"])
        self.confidence_card.pack(fill=tk.X, pady=(8, 0))
        self.reason_label = ttk.Label(rec_frame, text="-", wraplength=520, foreground=COLORS["muted"])
        self.reason_label.pack(fill=tk.X, pady=(8, 0))

        guard_frame = ttk.LabelFrame(body, text="Governance / Readiness Kontrolü", padding=8)
        guard_frame.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        self.role_card = MetricCard(guard_frame, "Yönetişim Rolü", "-", "Registry bilgisi", accent=COLORS["orange"])
        self.readiness_card = MetricCard(guard_frame, "Readiness", "-", "ML sample guard", accent=COLORS["blue"])
        self.final_card = MetricCard(guard_frame, "Final Karar mı?", "Hayır", "Bu öneri tek başına nihai karar değildir.", accent=COLORS["red"])
        self.history_card = MetricCard(guard_frame, "Geçmiş Kapsamı", "-", "Kullanılan run sayısı", accent=COLORS["cyan"])
        for idx, card in enumerate([self.role_card, self.readiness_card, self.final_card, self.history_card]):
            card.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=4, pady=4)
            guard_frame.columnconfigure(idx % 2, weight=1)

        candidate_frame = ttk.LabelFrame(body, text="Aday Algoritmalar ve Eleme Gerekçeleri", padding=8)
        candidate_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        self.candidate_table = DataTable(candidate_frame, ["Aday", "Durum", "Rol", "Readiness", "Gerekçe"], height=8)
        self.candidate_table.pack(fill=tk.BOTH, expand=True)

        json_frame = ttk.LabelFrame(body, text="Öneri Detayı (JSON)", padding=8)
        json_frame.grid(row=1, column=1, sticky="nsew")
        self.json_preview = JsonPreviewWidget(json_frame, height=10)
        self.json_preview.pack(fill=tk.BOTH, expand=True)

    def request_recommendation(self) -> None:
        try:
            size = int(self.size_entry.get() or "5000")
        except ValueError:
            size = 5000
        payload = {
            "problem_type": self.problem_type_map.get(self.problem_cb.get(), "prediction"),
            "data_size": size,
            "explainability_priority": self.explain_var.get(),
            "use_history": True,
        }

        def worker():
            return {
                "recommendation": self.api.get_recommendation(payload),
                "governance": self.api.get_algorithm_governance(),
                "readiness": self.api.get_ml_readiness(),
                "runs": self.api.get_runs(),
            }

        def success(result):
            recommendation_result = result["recommendation"]
            self.source_badge.set_source(any(item.used_mock for item in result.values()))
            data = recommendation_result.data
            governance_rows = _extract_rows(result["governance"].data)
            readiness_rows = _extract_rows(result["readiness"].data)
            run_rows = _extract_runs(result["runs"].data)
            self._apply_recommendation(data, governance_rows, readiness_rows, run_rows)

        def error(exc):
            self.banner.show(f"Algoritma önerisi alınamadı: {exc}")

        self._run_api_action(worker, success, error)

    def _apply_recommendation(self, data: dict[str, Any], governance_rows: list[dict[str, Any]], readiness_rows: list[dict[str, Any]], run_rows: list[dict[str, Any]]) -> None:
        algorithm = data.get("algorithm", "-")
        algorithm_key = canonical_algorithm_key(algorithm)
        governance = _find_algorithm(governance_rows, algorithm_key)
        readiness = _find_algorithm(readiness_rows, algorithm_key)
        source = data.get("source", "-")
        coverage = data.get("data_coverage") or {}
        used_run_count = data.get("used_run_count")
        if used_run_count in {None, ""}:
            used_run_count = coverage.get("used_run_count")
        if used_run_count in {None, ""}:
            used_run_count = _count_runs_for_algorithm(run_rows, algorithm)

        self.algorithm_card.set_value(algorithm, _source_label(source))
        self.confidence_card.set_value(data.get("confidence", "-"))
        self.reason_label.configure(text=data.get("reason", "-"))
        self.role_card.set_value(_role_label(governance.get("usage_role")), governance.get("user_facing_warning") or "Registry kaydı")
        self.readiness_card.set_value(readiness.get("readiness_level") or ("ML değil" if governance.get("algorithm_family") != "ml" else "Bilinmiyor"))
        self.final_card.set_value("Hayır", "Bu öneri final karar değildir.")
        self.history_card.set_value(f"{used_run_count or 0} run", coverage.get("coverage_note") or _source_label(source))
        self.candidate_table.set_rows(build_candidate_rows(data, governance_rows, readiness_rows))
        self.json_preview.set_json({**data, "governance": governance, "readiness": readiness, "used_run_count": used_run_count})

        if governance.get("usage_role") == "benchmark_only":
            self.banner.show(
                f"{algorithm} registry'de benchmark_only rolünde. Bu öneri yalnızca deneysel karşılaştırma olarak ele alınmalı.",
                level="warning",
            )
        else:
            self.banner.show("Bu öneri final karar değildir; yönetişim ve readiness kontrolleriyle birlikte değerlendirin.", level="warning")

    def _run_api_action(self, worker, success, error) -> None:
        if self.api.__class__.__name__ != "BenchmarkApiClient":
            try:
                success(worker())
            except Exception as exc:
                error(exc)
            return
        run_async(self, worker, success, error)


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return data
        for key in ("algorithms", "algorithm_readiness", "runs"):
            if isinstance(payload.get(key), list):
                return payload[key]
    return payload if isinstance(payload, list) else []


def _extract_runs(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("runs"), list):
        return payload["runs"]
    return _extract_rows(payload)


def _find_algorithm(rows: list[dict[str, Any]], algorithm_key: str) -> dict[str, Any]:
    for row in rows:
        key = canonical_algorithm_key(row.get("algorithm_key") or row.get("algorithm") or row.get("name") or row.get("display_name"))
        if key == algorithm_key:
            return row
    return {}


def _role_label(role: str | None) -> str:
    return {
        "production_decision": "Final karara dahil",
        "advisory_ml": "Destekleyici ML",
        "benchmark_only": "Sadece benchmark",
    }.get(role or "", role or "Bilinmiyor")


def _source_label(source: str | None) -> str:
    return {"history": "Geçmiş benchmark", "rules": "Kural tabanlı", "mock": "Örnek veri"}.get(source or "", source or "—")


def _elimination_reason(governance: dict[str, Any], readiness: dict[str, Any]) -> str:
    if governance.get("usage_role") == "benchmark_only":
        return "Registry rolü benchmark_only; final karar için kullanılmaz."
    if readiness and not readiness.get("can_train", True):
        reasons = readiness.get("blocking_reasons") or readiness.get("warnings") or []
        return "; ".join(str(item) for item in reasons[:2]) or "Readiness guard yetersiz."
    return "Seçilen problem/veri profili için öneri skorunda geride kaldı."


def _count_runs_for_algorithm(rows: list[dict[str, Any]], algorithm: str) -> int:
    key = canonical_algorithm_key(algorithm)
    count = 0
    for row in rows:
        algorithms = row.get("algorithms") or []
        if isinstance(algorithms, str):
            algorithms = [algorithms]
        if any(canonical_algorithm_key(item) == key for item in algorithms):
            count += 1
    return count
