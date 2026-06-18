# -*- coding: utf-8 -*-
"""Guz ve Bahar TOPSIS hesaplarini adim adim gosteren karar sayfasi."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from app.services.calculation import get_faculty_year_topsis_results
from app.services.topsis_explainability_service import calculate_topsis_breakdowns


class TopsisDecisionPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self._faculty_map: dict[str, int] = {}
        self._department_map: dict[str, int | None] = {"Tümü": None}
        self._details: dict[str, dict[str, Any]] = {}
        self._build()

    def _conn(self):
        conn = getattr(self.db, "conn", None)
        if conn is None:
            raise RuntimeError("Veritabanı bağlantısı bulunamadı.")
        return conn

    def _build(self):
        filters = ttk.LabelFrame(self, text="TOPSIS Kapsamı", padding=8)
        filters.pack(fill=tk.X, padx=8, pady=8)
        ttk.Label(filters, text="Yıl").pack(side=tk.LEFT)
        self.cb_year = ttk.Combobox(filters, state="readonly", width=9)
        self.cb_year.pack(side=tk.LEFT, padx=(4, 12))
        ttk.Label(filters, text="Fakülte").pack(side=tk.LEFT)
        self.cb_faculty = ttk.Combobox(filters, state="readonly", width=28)
        self.cb_faculty.pack(side=tk.LEFT, padx=(4, 12))
        self.cb_faculty.bind("<<ComboboxSelected>>", self._faculty_changed)
        ttk.Label(filters, text="Bölüm").pack(side=tk.LEFT)
        self.cb_department = ttk.Combobox(filters, state="readonly", width=28)
        self.cb_department.pack(side=tk.LEFT, padx=(4, 12))
        ttk.Button(filters, text="Hesapla", command=self.calculate).pack(side=tk.LEFT)
        self.lbl_profile = ttk.Label(filters, text="")
        self.lbl_profile.pack(side=tk.RIGHT)

        paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self.fall_tree = self._term_panel(paned, "Güz Dönemi")
        ttk.Separator(paned, orient=tk.HORIZONTAL)
        self.spring_tree = self._term_panel(paned, "Bahar Dönemi")

        detail = ttk.LabelFrame(self, text="Seçili Dersin TOPSIS Formül Dökümü", padding=8)
        detail.pack(fill=tk.BOTH, expand=False, padx=8, pady=(0, 8))
        self.txt_detail = tk.Text(detail, height=14, wrap=tk.WORD)
        self.txt_detail.pack(fill=tk.BOTH, expand=True)

    def _term_panel(self, parent, title):
        frame = ttk.LabelFrame(parent, text=title, padding=6)
        parent.add(frame, weight=2)
        columns = (
            "kod", "ders", "başarı", "trend", "doluluk", "anket",
            "ağırlıklı vektör", "S+", "S-", "C*", "kesinleşme puanı",
        )
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=8)
        ybar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        xbar = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        tree.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        for column in columns:
            tree.heading(column, text=column.title())
            tree.column(column, width=125, anchor=tk.W)
        tree.column("ders", width=240)
        tree.column("ağırlıklı vektör", width=330)
        tree.bind("<<TreeviewSelect>>", self._show_detail)
        return tree

    def refresh(self):
        try:
            conn = self._conn()
            cur = conn.cursor()
            previous_year = self.cb_year.get()
            cur.execute("SELECT DISTINCT akademik_yil FROM mufredat WHERE akademik_yil IS NOT NULL ORDER BY akademik_yil")
            years = [str(int(row[0])) for row in cur.fetchall()]
            self.cb_year["values"] = years
            self.cb_year.set(previous_year if previous_year in years else (years[-1] if years else ""))

            previous_faculty = self.cb_faculty.get()
            cur.execute("SELECT fakulte_id, ad FROM fakulte ORDER BY ad")
            self._faculty_map = {str(row[1]): int(row[0]) for row in cur.fetchall()}
            names = list(self._faculty_map)
            self.cb_faculty["values"] = names
            self.cb_faculty.set(previous_faculty if previous_faculty in names else (names[0] if names else ""))
            self._load_departments()
        except Exception:
            return

    def _faculty_changed(self, _event=None):
        self._load_departments()

    def _load_departments(self):
        faculty_id = self._faculty_map.get(self.cb_faculty.get())
        self._department_map = {"Tümü": None}
        if faculty_id is not None:
            cur = self._conn().cursor()
            cur.execute("SELECT bolum_id, ad FROM bolum WHERE fakulte_id=? ORDER BY ad", (int(faculty_id),))
            self._department_map.update({str(row[1]): int(row[0]) for row in cur.fetchall()})
        values = list(self._department_map)
        self.cb_department["values"] = values
        if self.cb_department.get() not in values:
            self.cb_department.set("Tümü")

    @staticmethod
    def _clear(tree):
        tree.delete(*tree.get_children())

    def calculate(self):
        self._clear(self.fall_tree)
        self._clear(self.spring_tree)
        self._details.clear()
        self.txt_detail.delete("1.0", tk.END)
        if not self.cb_year.get() or self.cb_faculty.get() not in self._faculty_map:
            messagebox.showwarning("TOPSIS", "Yıl ve fakülte seçin.")
            return
        year = int(self.cb_year.get())
        faculty_id = self._faculty_map[self.cb_faculty.get()]
        department_id = self._department_map.get(self.cb_department.get())
        profiles: list[str] = []
        errors: list[str] = []
        for term, tree in (("Guz", self.fall_tree), ("Bahar", self.spring_tree)):
            try:
                pack = get_faculty_year_topsis_results(
                    self._conn().cursor(), faculty_id, year, term, strict_ahp=True
                )
                if not pack.get("ok"):
                    errors.append(f"{term}: {pack.get('error')}")
                    continue
                profile = pack.get("ahp_profile") or {}
                profiles.append(f"{profile.get('name') or 'AHP'} #{profile.get('id') or '-'}")
                weights = dict(profile.get("weights") or {})
                methods = {int(k): v for k, v in dict(pack.get("score_methods") or {}).items()}
                meta = {int(k): v for k, v in dict(pack.get("ders_meta") or {}).items()}
                metrics = {int(k): v for k, v in dict(pack.get("metric_map") or {}).items()}
                course_rows = []
                for course_id, values in metrics.items():
                    course_meta = meta.get(course_id, {})
                    if methods.get(course_id) != "topsis":
                        continue
                    if department_id is not None and course_meta.get("bolum_id") != department_id:
                        continue
                    course_rows.append({"course_id": course_id, "ders_id": course_id, **values})
                breakdowns = calculate_topsis_breakdowns(course_rows, weights)
                for course_id, breakdown in sorted(
                    breakdowns.items(), key=lambda item: float(item[1].get("final_score") or 0), reverse=True
                ):
                    course_meta = meta.get(course_id, {})
                    raw = breakdown["raw_values"]
                    weighted = breakdown["weighted_values"]
                    iid = f"{term}:{course_id}"
                    self._details[iid] = {"term": term, "meta": course_meta, **breakdown}
                    tree.insert(
                        "", tk.END, iid=iid,
                        values=(
                            course_meta.get("kod") or "", course_meta.get("ad") or course_id,
                            f"{raw.get('basari', 0):.6f}", f"{raw.get('trend', 0):.6f}",
                            f"{raw.get('populerlik', 0):.6f}", f"{raw.get('anket', 0):.6f}",
                            " | ".join(f"{key}={value:.6f}" for key, value in weighted.items()),
                            f"{breakdown['positive_distance']:.6f}",
                            f"{breakdown['negative_distance']:.6f}",
                            f"{breakdown['closeness_coefficient']:.6f}",
                            f"{breakdown['final_score']:.6f}",
                        ),
                    )
            except Exception as exc:
                errors.append(f"{term}: {exc}")
        self.lbl_profile.config(text="Aktif AHP: " + (" / ".join(dict.fromkeys(profiles)) or "bulunamadı"))
        if errors:
            self.txt_detail.insert(tk.END, "\n".join(errors))

    def _show_detail(self, event):
        tree = event.widget
        selected = tree.selection()
        if not selected:
            return
        detail = self._details.get(str(selected[0]))
        if not detail:
            return
        self.txt_detail.delete("1.0", tk.END)
        meta = detail.get("meta") or {}
        lines = [
            f"{meta.get('kod') or ''} {meta.get('ad') or ''} — {detail.get('term')}",
            "",
            "1. Ham karar matrisi: " + ", ".join(f"{k}={v:.6f}" for k, v in detail["raw_values"].items()),
            "2. Vektör paydaları: " + ", ".join(f"sqrt(sum({k}²))={v:.6f}" for k, v in detail["normalization_denominators"].items()),
            "3. Normalize değerler: " + ", ".join(f"{k}={v:.6f}" for k, v in detail["normalized_values"].items()),
            "4. AHP ağırlıkları: " + ", ".join(f"{k}={v:.6f}" for k, v in detail["weights"].items()),
            "5. Ağırlıklı normalize değerler: " + ", ".join(f"{k}={v:.6f}" for k, v in detail["weighted_values"].items()),
            "6. Pozitif ideal A+: " + ", ".join(f"{k}={v:.6f}" for k, v in detail["positive_ideal"].items()),
            "7. Negatif ideal A-: " + ", ".join(f"{k}={v:.6f}" for k, v in detail["negative_ideal"].items()),
            f"8. S+ = {detail['positive_distance']:.6f}",
            f"9. S- = {detail['negative_distance']:.6f}",
            f"10. C* = S- / (S+ + S-) = {detail['closeness_coefficient']:.6f}",
            f"11. Kesinleşme puanı = C* × 100 = {detail['final_score']:.6f}",
        ]
        self.txt_detail.insert(tk.END, "\n".join(lines))

