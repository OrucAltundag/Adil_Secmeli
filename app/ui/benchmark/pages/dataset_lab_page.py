from __future__ import annotations

import csv
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

from app.ui.benchmark import mock_data
from app.ui.benchmark.widgets import (
    COLORS,
    DataTable,
    ErrorBanner,
    MetricCard,
    PageInfoBox,
    SectionHeader,
    SourceBadge,
    run_async,
)


class DatasetLabPage(ttk.Frame):
    def __init__(self, parent, api_client):
        super().__init__(parent, padding=14)
        self.api = api_client
        self.selected_file = tk.StringVar(value="")
        self.source_type = tk.StringVar(value="csv")
        self.loaded_dataset: dict | None = None
        self.layer_cards: dict[str, MetricCard] = {}
        self.quality_cards: dict[str, MetricCard] = {}
        self._build()

    def _build(self) -> None:
        SectionHeader(self, "Veri Seti Laboratuvarı", "Benchmark için kullanılacak veri katmanlarını hazırlayın ve kontrol edin.").pack(fill=tk.X)
        PageInfoBox(
            self,
            "Ham veri, işlenmiş veri ve sentetik test verisini benchmark akışına hazırlar.",
            "CSV klasörü veya SQLite dosyası seçip Yükle düğmesine basın; ardından önizleme ve veri modeli referanslarını kontrol edin.",
            "Sentetik veri stres testi içindir; gerçek akademik karar yerine geçmez.",
        ).pack(fill=tk.X, pady=(10, 0))
        self.source_badge = SourceBadge(self)
        self.source_badge.pack(fill=tk.X, pady=(8, 0))
        self.banner = ErrorBanner(self)

        layer_frame = ttk.LabelFrame(self, text="Veri Katmanları", padding=10)
        layer_frame.pack(fill=tk.X, pady=(12, 10))
        for idx, item in enumerate(mock_data.DATASET_LAYER_CARDS):
            card = MetricCard(layer_frame, item["name"], item["count"], f"{item['source']} - {item['description']}", accent=COLORS["cyan"])
            card.grid(row=0, column=idx, sticky="nsew", padx=6)
            layer_frame.columnconfigure(idx, weight=1)
            self.layer_cards[item["name"]] = card

        quality_frame = ttk.LabelFrame(self, text="Veri Kalite Özeti", padding=10)
        quality_frame.pack(fill=tk.X, pady=(0, 10))
        for idx, (key, title, value, subtitle) in enumerate(
            [
                ("row_count", "Satır", "-", "Yüklenen tablo"),
                ("column_count", "Kolon", "-", "Özellik sayısı"),
                ("missing_ratio", "Eksik Oran", "-", "0-1 arası"),
                ("target_present", "Hedef Kolon", "-", "course_id"),
                ("class_distribution", "Sınıf Dağılımı", "-", "İlk 10 sınıf"),
            ]
        ):
            card = MetricCard(quality_frame, title, value, subtitle, accent=COLORS["blue"])
            card.grid(row=0, column=idx, sticky="nsew", padx=4)
            quality_frame.columnconfigure(idx, weight=1)
            self.quality_cards[key] = card

        body = ttk.Frame(self)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        load_frame = ttk.LabelFrame(body, text="Veri Yükleme", padding=10)
        load_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        ttk.Radiobutton(load_frame, text="CSV klasörü", variable=self.source_type, value="csv").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(load_frame, text="SQLite dosyası", variable=self.source_type, value="sqlite").grid(row=0, column=1, sticky="w")
        ttk.Entry(load_frame, textvariable=self.selected_file).grid(row=1, column=0, columnspan=3, sticky="ew", pady=8)
        load_frame.columnconfigure(0, weight=1)
        ttk.Button(load_frame, text="Dosya Seç", command=self.pick_file).grid(row=2, column=0, sticky="w")
        ttk.Button(load_frame, text="Yükle", command=self.load_dataset).grid(row=2, column=1, sticky="w", padx=6)
        ttk.Button(load_frame, text="Önizle", command=self.preview_data).grid(row=2, column=2, sticky="w")

        process_frame = ttk.LabelFrame(body, text="Veri İşleme ve Sentetik Veri", padding=10)
        process_frame.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        self.options = {}
        for idx, label in enumerate(["One-hot kodlama", "0-1 normalizasyon", "Bileşik skor", "Bootstrap sentetik üretim", "Gürültü ekleme", "Sınıf dengesizliği", "Kontenjan kısıtı"]):
            var = tk.BooleanVar(value=idx < 3)
            self.options[label] = var
            ttk.Checkbutton(process_frame, text=label, variable=var).grid(row=idx, column=0, sticky="w", pady=2)
        ttk.Label(process_frame, text="Ölçek").grid(row=0, column=1, sticky="w", padx=(18, 4))
        self.scale_cb = ttk.Combobox(process_frame, state="readonly", values=["5k", "10k", "50k", "100k", "250k"], width=10)
        self.scale_cb.set("100k")
        self.scale_cb.grid(row=0, column=2, sticky="ew")
        ttk.Label(process_frame, text="Seed").grid(row=1, column=1, sticky="w", padx=(18, 4))
        self.seed_entry = ttk.Entry(process_frame, width=10)
        self.seed_entry.insert(0, "42")
        self.seed_entry.grid(row=1, column=2, sticky="ew")
        ttk.Label(process_frame, text="Gürültü").grid(row=2, column=1, sticky="w", padx=(18, 4))
        self.noise_entry = ttk.Entry(process_frame, width=10)
        self.noise_entry.insert(0, "0.03")
        self.noise_entry.grid(row=2, column=2, sticky="ew")
        ttk.Label(process_frame, text="Dengesizlik").grid(row=3, column=1, sticky="w", padx=(18, 4))
        self.imbalance_entry = ttk.Entry(process_frame, width=10)
        self.imbalance_entry.insert(0, "0.20")
        self.imbalance_entry.grid(row=3, column=2, sticky="ew")
        ttk.Button(process_frame, text="Sentetik Veri Üret", command=self.generate_synthetic).grid(row=7, column=1, columnspan=2, sticky="ew", pady=(8, 0), padx=(18, 0))

        self.preview_frame = ttk.LabelFrame(body, text="Veri Önizleme", padding=8)
        self.preview_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        self.preview_table = None
        self._render_preview_table(
            ["student_id", "age", "gender", "gpa", "faculty", "pref_count", "avg_rank", "score_composite"],
            mock_data.DATA_PREVIEW_ROWS,
        )

        refs_frame = ttk.LabelFrame(body, text="Veri Modeli Referansları", padding=8)
        refs_frame.grid(row=1, column=1, sticky="nsew")
        self.refs_table = DataTable(refs_frame, ["Model", "Aciklama"], height=8, column_labels={"Model": "Model", "Aciklama": "Açıklama"})
        self.refs_table.pack(fill=tk.BOTH, expand=True)
        self.refs_table.set_rows([{"Model": name, "Aciklama": desc} for name, desc in mock_data.MODEL_REFERENCES])

    def pick_file(self) -> None:
        if self.source_type.get() == "sqlite":
            path = filedialog.askopenfilename(title="SQLite dosyası seç", filetypes=[("SQLite", "*.db *.sqlite"), ("Tüm dosyalar", "*.*")])
        else:
            path = filedialog.askdirectory(title="CSV klasörü seç")
        if path:
            self.selected_file.set(path)

    def load_dataset(self) -> None:
        self._load_dataset_from_api("Veri seti başarıyla yüklendi.")

    def preview_data(self) -> None:
        if self.loaded_dataset:
            self._apply_dataset_result(self.loaded_dataset)
            return
        self._render_preview_table(
            ["student_id", "age", "gender", "gpa", "faculty", "pref_count", "avg_rank", "score_composite"],
            mock_data.DATA_PREVIEW_ROWS,
        )

    def generate_synthetic(self) -> None:
        self._load_dataset_from_api(f"Sentetik veri ayarları API'ye gönderildi. Seçili ölçek: {self.scale_cb.get()}.")

    def _load_dataset_from_api(self, success_message: str) -> None:
        path = self.selected_file.get().strip() or "data/benchmark/raw_real"
        ok, message = self._preflight_source(path)
        if not ok:
            self.banner.show(message)
            return
        payload = {
            "source_type": self.source_type.get(),
            "source_path": path,
            "dataset_name": "desktop_benchmark_dataset",
            "synth_noise_std": self._float_from_entry(self.noise_entry, 0.03),
            "synth_class_imbalance_alpha": self._float_from_entry(self.imbalance_entry, 0.20),
            "synth_capacity_scale": 1.0,
            "synthetic_tier": self.scale_cb.get(),
        }

        def worker():
            return self.api.load_dataset(payload)

        def success(result):
            if result.used_mock:
                self.source_badge.set_source(True)
                self.banner.show("Backend API erişilemiyor; örnek veri gösteriliyor.", level="warning")
            else:
                self.source_badge.set_source(False)
                self.banner.show(success_message, level="warning")
            self.loaded_dataset = result.data
            self._apply_dataset_result(result.data)

        def error(exc):
            self.source_badge.set_source(True)
            self.banner.show(f"Veri seti yüklenemedi: {exc}. Kaynak yolunu ve veri formatını kontrol edin.")

        if self.api.__class__.__name__ != "BenchmarkApiClient":
            try:
                success(worker())
            except Exception as exc:
                error(exc)
            return
        run_async(self, worker, success, error)

    def _apply_dataset_result(self, data: dict) -> None:
        self._update_layer_cards(data.get("layer_counts") or {})
        self._update_quality_cards(data.get("quality_summary") or {})
        preview = data.get("preview") or {}
        columns = [str(col) for col in preview.get("columns") or []]
        rows = preview.get("rows") or []
        if not columns and rows:
            columns = list(rows[0].keys())
        if columns:
            visible_columns = columns[:10]
            visible_rows = [{col: row.get(col, "") for col in visible_columns} for row in rows]
            self._render_preview_table(visible_columns, visible_rows)
        else:
            self._render_preview_table(
                ["student_id", "age", "gender", "gpa", "faculty", "pref_count", "avg_rank", "score_composite"],
                mock_data.DATA_PREVIEW_ROWS,
            )

    def _update_layer_cards(self, layer_counts: dict) -> None:
        for layer_name, card in self.layer_cards.items():
            tables = layer_counts.get(layer_name) or {}
            total = sum(int(value or 0) for value in tables.values()) if isinstance(tables, dict) else 0
            table_count = len(tables) if isinstance(tables, dict) else 0
            if total:
                card.set_value(self._format_count(total), f"{table_count} tablo")

    def _update_quality_cards(self, summary: dict) -> None:
        if not summary:
            return
        self.quality_cards["row_count"].set_value(self._format_count(summary.get("row_count", 0)))
        self.quality_cards["column_count"].set_value(summary.get("column_count", "-"))
        missing = summary.get("missing_ratio")
        self.quality_cards["missing_ratio"].set_value(f"{float(missing or 0):.2%}")
        target_present = "Var" if summary.get("target_present") else "Yok"
        target_column = summary.get("target_column") or "course_id"
        self.quality_cards["target_present"].set_value(target_present, str(target_column))
        distribution = summary.get("class_distribution") or {}
        self.quality_cards["class_distribution"].set_value(len(distribution), "Sınıf")

    def _render_preview_table(self, columns: list[str], rows: list[dict]) -> None:
        if self.preview_table is not None:
            self.preview_table.destroy()
        self.preview_table = DataTable(self.preview_frame, columns, height=8, column_labels={col: _column_label(col) for col in columns})
        self.preview_table.pack(fill=tk.BOTH, expand=True)
        self.preview_table.set_rows(rows)

    def _preflight_source(self, path: str) -> tuple[bool, str]:
        source = Path(path)
        if self.source_type.get() == "csv":
            if not source.exists() or not source.is_dir():
                return False, f"CSV klasörü bulunamadı: {path}. Geçerli bir benchmark CSV klasörü seçin."
            required = ["students.csv", "courses.csv", "preferences.csv"]
            missing = [name for name in required if not (source / name).exists()]
            if missing:
                return False, f"CSV klasöründe gerekli dosyalar eksik: {', '.join(missing)}."
            header = self._csv_header(source / "preferences.csv")
            if "course_id" not in header:
                return False, "preferences.csv içinde hedef kolon course_id bulunamadı. Dosya başlığını kontrol edin."
            return True, ""
        if not source.exists() or not source.is_file():
            return False, f"SQLite dosyası bulunamadı: {path}. Geçerli bir .db/.sqlite dosyası seçin."
        return True, ""

    def _csv_header(self, path: Path) -> set[str]:
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                return {str(item).strip() for item in next(reader, [])}
        except OSError:
            return set()

    def _float_from_entry(self, entry: ttk.Entry, default: float) -> float:
        try:
            return float(entry.get())
        except ValueError:
            return default

    def _format_count(self, value: int) -> str:
        value = int(value or 0)
        if value >= 1000:
            return f"{value / 1000:.1f}K"
        return str(value)


def _column_label(column: str) -> str:
    labels = {
        "student_id": "Öğrenci ID",
        "course_id": "Ders ID",
        "age": "Yaş",
        "gender": "Cinsiyet",
        "gpa": "GNO",
        "faculty": "Fakülte",
        "pref_count": "Tercih Sayısı",
        "avg_rank": "Ortalama Sıra",
        "score_composite": "Bileşik Skor",
    }
    return labels.get(column, column)
