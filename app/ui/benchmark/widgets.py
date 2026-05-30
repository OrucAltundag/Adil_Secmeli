"""Reusable Tkinter widgets for the Benchmark Platform pages."""

from __future__ import annotations

import json
import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

COLORS = {
    "navy": "#0F172A",
    "blue": "#1D4ED8",
    "cyan": "#0891B2",
    "green": "#16A34A",
    "orange": "#F97316",
    "red": "#DC2626",
    "bg": "#F8FAFC",
    "card": "#FFFFFF",
    "border": "#E2E8F0",
    "muted": "#64748B",
    "text": "#111827",
}


def run_async(root: tk.Misc, worker: Callable[[], Any], on_success: Callable[[Any], None], on_error: Callable[[Exception], None] | None = None) -> None:
    def _schedule(callback: Callable[[], None]) -> None:
        try:
            if root.winfo_exists():
                root.after(0, callback)
        except (RuntimeError, tk.TclError):
            return

    def _target() -> None:
        try:
            result = worker()
            _schedule(lambda result=result: on_success(result))
        except Exception as exc:
            if on_error:
                _schedule(lambda exc=exc: on_error(exc))

    threading.Thread(target=_target, daemon=True).start()


class SectionHeader(ttk.Frame):
    def __init__(self, parent, title: str, description: str | None = None):
        super().__init__(parent)
        ttk.Label(self, text=title, font=("Segoe UI", 16, "bold"), foreground=COLORS["navy"]).pack(anchor="w")
        if description:
            ttk.Label(self, text=description, font=("Segoe UI", 10), foreground=COLORS["muted"]).pack(anchor="w", pady=(2, 0))


class PageInfoBox(tk.Frame):
    """Compact purpose/usage box shown at the top of benchmark pages."""

    def __init__(self, parent, purpose: str, usage: str, note: str | None = None):
        super().__init__(parent, bg="#EFF6FF", highlightbackground="#BFDBFE", highlightthickness=1, padx=12, pady=10)
        tk.Label(
            self,
            text="Bu sayfa ne işe yarar?",
            bg="#EFF6FF",
            fg=COLORS["blue"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill=tk.X)
        tk.Label(
            self,
            text=f"Amaç: {purpose}",
            bg="#EFF6FF",
            fg=COLORS["text"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=1100,
        ).pack(fill=tk.X, pady=(4, 0))
        tk.Label(
            self,
            text=f"Kullanım: {usage}",
            bg="#EFF6FF",
            fg=COLORS["text"],
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=1100,
        ).pack(fill=tk.X, pady=(2, 0))
        if note:
            tk.Label(
                self,
                text=f"Not: {note}",
                bg="#EFF6FF",
                fg=COLORS["muted"],
                font=("Segoe UI", 9, "italic"),
                anchor="w",
                justify="left",
                wraplength=1100,
            ).pack(fill=tk.X, pady=(2, 0))


class SourceBadge(tk.Frame):
    """Small badge that makes real API vs mock data visible."""

    def __init__(self, parent):
        super().__init__(parent, bg=COLORS["bg"])
        self.label = tk.Label(self, text="", bg="#E0F2FE", fg=COLORS["blue"], font=("Segoe UI", 9, "bold"), padx=8, pady=4)
        self.label.pack(anchor="e")
        self.set_source(False)

    def set_source(self, used_mock: bool, detail: str | None = None) -> None:
        if used_mock:
            self.label.configure(text=detail or "Veri kaynağı: Örnek veri (mock)", bg="#FFF7ED", fg=COLORS["orange"])
        else:
            self.label.configure(text=detail or "Veri kaynağı: Gerçek API", bg="#ECFDF5", fg=COLORS["green"])


class MetricCard(tk.Frame):
    def __init__(self, parent, title: str, value: Any, subtitle: str | None = None, accent: str = COLORS["blue"]):
        super().__init__(parent, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1, padx=12, pady=10)
        self._accent = accent
        tk.Label(self, text=title, bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.value_label = tk.Label(self, text=str(value), bg=COLORS["card"], fg=accent, font=("Segoe UI", 17, "bold"))
        self.value_label.pack(anchor="w", pady=(4, 0))
        self.subtitle_label = tk.Label(self, text=subtitle or "", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 8))
        self.subtitle_label.pack(anchor="w")

    def set_value(self, value: Any, subtitle: str | None = None) -> None:
        self.value_label.configure(text=str(value))
        if subtitle is not None:
            self.subtitle_label.configure(text=subtitle)

    def set_accent(self, accent: str) -> None:
        self._accent = accent
        self.value_label.configure(fg=accent)


class StatusCard(MetricCard):
    STATUS_COLORS = {
        "success": COLORS["green"],
        "warning": COLORS["orange"],
        "error": COLORS["red"],
        "info": COLORS["blue"],
    }

    def __init__(self, parent, title: str, value: Any, status_type: str = "info"):
        super().__init__(parent, title, value, accent=self.STATUS_COLORS.get(status_type, COLORS["blue"]))


class ErrorBanner(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#FEF2F2", highlightbackground="#FECACA", highlightthickness=1, padx=10, pady=8)
        self.label = tk.Label(self, text="", bg="#FEF2F2", fg=COLORS["red"], font=("Segoe UI", 9, "bold"), anchor="w", justify="left")
        self.label.pack(fill=tk.X)

    def show(self, message: str, level: str = "error") -> None:
        if level == "warning":
            self.configure(bg="#FFF7ED", highlightbackground="#FDBA74")
            self.label.configure(bg="#FFF7ED", fg=COLORS["orange"])
        else:
            self.configure(bg="#FEF2F2", highlightbackground="#FECACA")
            self.label.configure(bg="#FEF2F2", fg=COLORS["red"])
        self.label.configure(text=message)
        self.pack(fill=tk.X, pady=(8, 8))

    def clear(self) -> None:
        self.pack_forget()


class EmptyState(ttk.Frame):
    def __init__(self, parent, text: str):
        super().__init__(parent, padding=20)
        ttk.Label(self, text=text, foreground=COLORS["muted"], font=("Segoe UI", 10)).pack()


class DataTable(ttk.Frame):
    def __init__(self, parent, columns: list[str], height: int = 8, column_labels: dict[str, str] | None = None):
        super().__init__(parent)
        self.columns = columns
        self.column_labels = column_labels or {}
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=height)
        ybar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        xbar = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        for col in columns:
            self.tree.heading(col, text=self.column_labels.get(col, col), command=lambda c=col: self.sort_by(c, False))
            self.tree.column(col, width=120, anchor="center", stretch=True)
        self.tree.tag_configure("best", background="#ECFDF5")
        self.tree.tag_configure("error", background="#FEF2F2")

    def set_rows(self, rows: list[dict[str, Any]] | list[list[Any]], best_key: str | None = None) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in rows:
            if isinstance(row, dict):
                values = [self._format(row.get(col, "")) for col in self.columns]
                tags = ("best",) if best_key and str(row.get(best_key, "")).lower() in {"best", "true", "1"} else ()
                if str(row.get("status", "")).lower() in {"error", "failed", "hata"}:
                    tags = ("error",)
            else:
                values = [self._format(v) for v in row]
                tags = ()
            self.tree.insert("", tk.END, values=values, tags=tags)

    def selected_values(self) -> list[Any]:
        selected = self.tree.selection()
        if not selected:
            return []
        return list(self.tree.item(selected[0], "values"))

    def sort_by(self, col: str, descending: bool) -> None:
        self.columns.index(col)
        data = [(self.tree.set(item, col), item) for item in self.tree.get_children("")]

        def _key(item):
            value = item[0]
            try:
                return float(value)
            except (TypeError, ValueError):
                return str(value)

        data.sort(key=_key, reverse=descending)
        for pos, (_, item) in enumerate(data):
            self.tree.move(item, "", pos)
        self.tree.heading(col, command=lambda: self.sort_by(col, not descending))

    def _format(self, value: Any) -> str:
        if isinstance(value, float):
            return f"{value:.3f}"
        return "" if value is None else str(value)


class JsonPreviewWidget(ttk.Frame):
    def __init__(self, parent, height: int = 12):
        super().__init__(parent)
        self.text = tk.Text(self, height=height, wrap="none", font=("Consolas", 9), bg="#F8FAFC", fg=COLORS["text"], relief="solid", bd=1)
        ybar = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        xbar = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def set_json(self, value: Any) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", json.dumps(value, indent=2, ensure_ascii=False))
        self.text.configure(state="disabled")


class BarChart(tk.Canvas):
    def __init__(self, parent, height: int = 180):
        super().__init__(parent, height=height, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightthickness=1)

    def plot(self, rows: list[dict[str, Any]], label_key: str, value_key: str, color: str = COLORS["blue"]) -> None:
        self.delete("all")
        self.update_idletasks()
        width = max(self.winfo_width(), 500)
        height = max(self.winfo_height(), 160)
        margin = 32
        values = []
        for row in rows:
            try:
                values.append(float(row.get(value_key, 0) or 0))
            except (TypeError, ValueError):
                values.append(0.0)
        max_value = max(values) if values else 1.0
        max_value = max(max_value, 1e-6)
        bar_count = max(len(rows), 1)
        slot = (width - margin * 2) / bar_count
        for idx, row in enumerate(rows):
            value = values[idx]
            x0 = margin + idx * slot + 8
            x1 = margin + (idx + 1) * slot - 8
            y1 = height - 34
            y0 = y1 - (height - 72) * (value / max_value)
            self.create_rectangle(x0, y0, x1, y1, fill=color, outline="")
            self.create_text((x0 + x1) / 2, y0 - 10, text=f"{value:.3g}", fill=COLORS["navy"], font=("Segoe UI", 8, "bold"))
            label = str(row.get(label_key, ""))[:14]
            self.create_text((x0 + x1) / 2, height - 17, text=label, fill=COLORS["muted"], font=("Segoe UI", 8))

    def plot_line(self, rows: list[dict[str, Any]], label_key: str, value_key: str, color: str = COLORS["blue"]) -> None:
        self.delete("all")
        self.update_idletasks()
        width = max(self.winfo_width(), 500)
        height = max(self.winfo_height(), 160)
        margin = 36
        values = []
        for row in rows:
            try:
                values.append(float(row.get(value_key, 0) or 0))
            except (TypeError, ValueError):
                values.append(0.0)
        max_value = max(values) if values else 1.0
        max_value = max(max_value, 1e-6)
        if len(rows) == 1:
            rows = [rows[0], rows[0]]
            values = [values[0], values[0]]
        points = []
        for idx, row in enumerate(rows):
            x = margin + idx * ((width - margin * 2) / max(len(rows) - 1, 1))
            y = height - 34 - (height - 72) * (values[idx] / max_value)
            points.append((x, y))
            self.create_oval(x - 4, y - 4, x + 4, y + 4, fill=color, outline="")
            self.create_text(x, y - 12, text=f"{values[idx]:.3g}", fill=COLORS["navy"], font=("Segoe UI", 8, "bold"))
            self.create_text(x, height - 17, text=str(row.get(label_key, ""))[:14], fill=COLORS["muted"], font=("Segoe UI", 8))
        for start, end in zip(points, points[1:]):
            self.create_line(start[0], start[1], end[0], end[1], fill=color, width=2)


def algorithm_group_color(group: str) -> str:
    group = (group or "").lower()
    if "mcdm" in group:
        return COLORS["blue"]
    if "ml" in group:
        return COLORS["cyan"]
    if "cluster" in group:
        return COLORS["orange"]
    if "allocation" in group:
        return "#7C3AED"
    return COLORS["muted"]
