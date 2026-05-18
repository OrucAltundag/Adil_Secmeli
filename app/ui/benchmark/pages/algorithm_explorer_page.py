from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.benchmark import mock_data
from app.ui.benchmark.widgets import (
    COLORS,
    DataTable,
    ErrorBanner,
    JsonPreviewWidget,
    MetricCard,
    SectionHeader,
    algorithm_group_color,
    run_async,
)


class AlgorithmExplorerPage(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=14)
        self.api = api_client
        self.algorithms = []
        self._build()
        self.load_algorithms()

    def _build(self) -> None:
        SectionHeader(self, "Algorithm Explorer", "Algoritma registry, ortak kontrat, parametreler ve standart cikti yapisini inceleyin.").pack(fill=tk.X)
        self.banner = ErrorBanner(self)

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.columnconfigure(2, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(body, text="Algoritma Registry", padding=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(left, text="Ara").pack(anchor="w")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.apply_filter())
        ttk.Entry(left, textvariable=self.search_var, width=24).pack(fill=tk.X, pady=(0, 6))
        ttk.Label(left, text="Kategori").pack(anchor="w")
        self.group_cb = ttk.Combobox(left, state="readonly", values=["Tumu", "MCDM", "ML", "Clustering", "Allocation"], width=22)
        self.group_cb.set("Tumu")
        self.group_cb.pack(fill=tk.X, pady=(0, 8))
        self.group_cb.bind("<<ComboboxSelected>>", lambda _e: self.apply_filter())
        self.listbox = tk.Listbox(left, height=22, exportselection=False)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        middle = ttk.Frame(body)
        middle.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        middle.rowconfigure(2, weight=1)
        contract = ttk.LabelFrame(middle, text="Ortak Algoritma Kontrati", padding=8)
        contract.grid(row=0, column=0, sticky="ew")
        for idx, method in enumerate(["fit", "predict", "recommend", "score", "explain"]):
            MetricCard(contract, method, "API", "Standart metot", accent=COLORS["cyan"]).grid(row=0, column=idx, sticky="nsew", padx=3)
            contract.columnconfigure(idx, weight=1)

        detail = ttk.LabelFrame(middle, text="Algoritma Detayi", padding=8)
        detail.grid(row=1, column=0, sticky="ew", pady=8)
        self.detail_labels = {}
        for idx, field in enumerate(["Ad", "Grup", "Kullanım Rolü", "Aciklama", "Kullanim Senaryosu", "Avantajlar", "Dezavantajlar"]):
            ttk.Label(detail, text=field, font=("Segoe UI", 9, "bold")).grid(row=idx, column=0, sticky="nw", pady=2)
            label = ttk.Label(detail, text="-", wraplength=430, foreground=COLORS["muted"])
            label.grid(row=idx, column=1, sticky="w", pady=2)
            self.detail_labels[field] = label

        params = ttk.LabelFrame(middle, text="Parametreler ve Metrikler", padding=8)
        params.grid(row=2, column=0, sticky="nsew")
        self.params_table = DataTable(params, ["Tip", "Deger"], height=7)
        self.params_table.pack(fill=tk.BOTH, expand=True)

        right = ttk.LabelFrame(body, text="Cikti Onizleme", padding=8)
        right.grid(row=0, column=2, sticky="nsew")
        ttk.Button(right, text="Ornek Cikti Uret", command=self.generate_output).pack(anchor="e", pady=(0, 6))
        self.json_preview = JsonPreviewWidget(right, height=24)
        self.json_preview.pack(fill=tk.BOTH, expand=True)

    def load_algorithms(self) -> None:
        def worker():
            return self.api.get_algorithms()

        def success(result):
            if result.used_mock:
                self.banner.show("Backend API erisilemiyor, mock algoritma registry gosteriliyor.", level="warning")
            self.algorithms = result.data.get("algorithms", mock_data.ALGORITHMS)
            self.apply_filter()
            if self.listbox.size():
                self.listbox.selection_set(0)
                self.on_select()

        run_async(self, worker, success)

    def apply_filter(self) -> None:
        query = self.search_var.get().strip().lower()
        group = self.group_cb.get()
        self.listbox.delete(0, tk.END)
        for item in self.algorithms:
            name = item.get("name", "")
            item_group = item.get("group", "")
            if query and query not in name.lower():
                continue
            if group != "Tumu" and item_group != group:
                continue
            self.listbox.insert(tk.END, name)

    def on_select(self, event=None) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        name = self.listbox.get(selection[0])
        item = next((a for a in self.algorithms if a.get("name") == name), {"name": name, "group": "-"})
        detail = mock_data.ALGORITHM_DETAILS.get(name, {})
        self.detail_labels["Ad"].configure(text=name, foreground=algorithm_group_color(item.get("group", "")))
        self.detail_labels["Grup"].configure(text=item.get("group", "-"))
        self.detail_labels["Kullanım Rolü"].configure(text=item.get("role_label") or item.get("usage_role") or "Sadece benchmark")
        self.detail_labels["Aciklama"].configure(text=detail.get("description", "Registry uzerinden gelen algoritma."))
        self.detail_labels["Kullanim Senaryosu"].configure(text=detail.get("use_case", "Benchmark senaryosuna gore kullanilir."))
        self.detail_labels["Avantajlar"].configure(text=detail.get("pros", "-"))
        self.detail_labels["Dezavantajlar"].configure(text=detail.get("cons", "-"))
        rows = [{"Tip": "Parametre", "Deger": p} for p in detail.get("parameters", ["default"])]
        rows += [{"Tip": "Metrik", "Deger": m} for m in detail.get("metrics", ["runtime", "confidence"])]
        self.params_table.set_rows(rows)
        self.generate_output()

    def generate_output(self) -> None:
        name = self.listbox.get(self.listbox.curselection()[0]) if self.listbox.curselection() else "RandomForest"
        self.json_preview.set_json(
            {
                "algorithm_name": name,
                "prediction": "OSD102",
                "recommendation": ["OSD102", "OSD101", "OSD107"],
                "confidence": 0.91,
                "explanation": f"{name} icin ornek aciklama ve karar gerekcesi.",
                "runtime_ms": 52,
                "parameters": {"source": "desktop-preview"},
            }
        )
