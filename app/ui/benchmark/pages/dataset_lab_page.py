from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk

from app.ui.benchmark import mock_data
from app.ui.benchmark.widgets import (
    COLORS,
    DataTable,
    ErrorBanner,
    MetricCard,
    SectionHeader,
    run_async,
)


class DatasetLabPage(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=14)
        self.api = api_client
        self.selected_file = tk.StringVar(value="")
        self.source_type = tk.StringVar(value="csv")
        self._build()

    def _build(self) -> None:
        SectionHeader(self, "Dataset Lab", "Veri katmanlarini, yukleme akislarini ve sentetik veri ayarlarini yonetin.").pack(fill=tk.X)
        self.banner = ErrorBanner(self)

        layer_frame = ttk.LabelFrame(self, text="Veri Katmanlari", padding=10)
        layer_frame.pack(fill=tk.X, pady=(12, 10))
        for idx, item in enumerate(mock_data.DATASET_LAYER_CARDS):
            card = MetricCard(layer_frame, item["name"], item["count"], f"{item['source']} - {item['description']}", accent=COLORS["cyan"])
            card.grid(row=0, column=idx, sticky="nsew", padx=6)
            layer_frame.columnconfigure(idx, weight=1)

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        load_frame = ttk.LabelFrame(body, text="Veri Yukleme", padding=10)
        load_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        ttk.Radiobutton(load_frame, text="CSV klasoru", variable=self.source_type, value="csv").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(load_frame, text="SQLite dosyasi", variable=self.source_type, value="sqlite").grid(row=0, column=1, sticky="w")
        ttk.Entry(load_frame, textvariable=self.selected_file).grid(row=1, column=0, columnspan=3, sticky="ew", pady=8)
        load_frame.columnconfigure(0, weight=1)
        ttk.Button(load_frame, text="Dosya Sec", command=self.pick_file).grid(row=2, column=0, sticky="w")
        ttk.Button(load_frame, text="Yukle", command=self.load_dataset).grid(row=2, column=1, sticky="w", padx=6)
        ttk.Button(load_frame, text="Onizle", command=self.preview_data).grid(row=2, column=2, sticky="w")

        process_frame = ttk.LabelFrame(body, text="Veri Isleme ve Sentetik Veri", padding=10)
        process_frame.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        self.options = {}
        for idx, label in enumerate(["One-hot encoding", "0-1 normalization", "Composite score", "Bootstrap synthetic generation", "Noise injection", "Class imbalance", "Capacity constraint"]):
            var = tk.BooleanVar(value=idx < 3)
            self.options[label] = var
            ttk.Checkbutton(process_frame, text=label, variable=var).grid(row=idx, column=0, sticky="w", pady=2)
        ttk.Label(process_frame, text="Olcek").grid(row=0, column=1, sticky="w", padx=(18, 4))
        self.scale_cb = ttk.Combobox(process_frame, state="readonly", values=["5k", "10k", "50k", "100k", "250k"], width=10)
        self.scale_cb.set("100k")
        self.scale_cb.grid(row=0, column=2, sticky="ew")
        ttk.Label(process_frame, text="Seed").grid(row=1, column=1, sticky="w", padx=(18, 4))
        self.seed_entry = ttk.Entry(process_frame, width=10)
        self.seed_entry.insert(0, "42")
        self.seed_entry.grid(row=1, column=2, sticky="ew")
        ttk.Label(process_frame, text="Noise").grid(row=2, column=1, sticky="w", padx=(18, 4))
        self.noise_entry = ttk.Entry(process_frame, width=10)
        self.noise_entry.insert(0, "0.03")
        self.noise_entry.grid(row=2, column=2, sticky="ew")
        ttk.Label(process_frame, text="Imbalance").grid(row=3, column=1, sticky="w", padx=(18, 4))
        self.imbalance_entry = ttk.Entry(process_frame, width=10)
        self.imbalance_entry.insert(0, "0.20")
        self.imbalance_entry.grid(row=3, column=2, sticky="ew")
        ttk.Button(process_frame, text="Sentetik Veri Uret", command=self.generate_synthetic).grid(row=7, column=1, columnspan=2, sticky="ew", pady=(8, 0), padx=(18, 0))

        preview_frame = ttk.LabelFrame(body, text="Veri Onizleme", padding=8)
        preview_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        self.preview_table = DataTable(preview_frame, ["student_id", "age", "gender", "gpa", "faculty", "pref_count", "avg_rank", "score_composite"], height=8)
        self.preview_table.pack(fill=tk.BOTH, expand=True)
        self.preview_table.set_rows(mock_data.DATA_PREVIEW_ROWS)

        refs_frame = ttk.LabelFrame(body, text="Veri Modeli Referanslari", padding=8)
        refs_frame.grid(row=1, column=1, sticky="nsew")
        self.refs_table = DataTable(refs_frame, ["Model", "Aciklama"], height=8)
        self.refs_table.pack(fill=tk.BOTH, expand=True)
        self.refs_table.set_rows([{"Model": name, "Aciklama": desc} for name, desc in mock_data.MODEL_REFERENCES])

    def pick_file(self) -> None:
        if self.source_type.get() == "sqlite":
            path = filedialog.askopenfilename(title="SQLite dosyasi sec", filetypes=[("SQLite", "*.db *.sqlite"), ("Tum dosyalar", "*.*")])
        else:
            path = filedialog.askdirectory(title="CSV klasoru sec")
        if path:
            self.selected_file.set(path)

    def load_dataset(self) -> None:
        path = self.selected_file.get().strip() or "data/benchmark/raw_real"
        payload = {"source_type": self.source_type.get(), "source_path": path, "dataset_name": "desktop_benchmark_dataset"}

        def worker():
            return self.api.load_dataset(payload)

        def success(result):
            if result.used_mock:
                self.banner.show("Backend API erisilemiyor, ornek veri gosteriliyor.", level="warning")
            else:
                self.banner.show("Dataset basariyla yuklendi.", level="warning")
            self.preview_data()

        run_async(self, worker, success)

    def preview_data(self) -> None:
        self.preview_table.set_rows(mock_data.DATA_PREVIEW_ROWS)

    def generate_synthetic(self) -> None:
        self.banner.show(f"Sentetik veri ayari hazirlandi: olcek={self.scale_cb.get()}, seed={self.seed_entry.get()}. API yoksa mock onizleme kullaniliyor.", level="warning")
