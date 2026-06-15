# -*- coding: utf-8 -*-
"""Dönem Planlama Tkinter paneli.

Güz ve baharı **aynı akademik yılın iki parçası** olarak ele alan yeniden
tasarlanmış ekran. Bölümler:

- Üst: kapsam (yıl/fakülte/bölüm), durum, özet kartları
- "Yıllık Görünüm": havuz + güz + bahar derslerini durum etiketleriyle tek
  tabloda birleştirir (filtrelenebilir, renkli)
- "Güz / Bahar": yan yana iki panel; her dersin diğer dönemdeki durumu da görünür
- "Bütünlük Kontrolü": yıllık müfredat çakışma/uyarı raporu
- "Plan Üret": policy tabanlı motor (mevcut müfredatı koruyarak yeni öneri üretir)
- "Rapor" / "Plan Geçmişi"

Tüm veriler gerçek veritabanı kayıtlarından gelir.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from app.repositories.curriculum_repository import (
    get_courses_status_batch,
    get_curriculum_courses_by_year,
    get_period_planning_summary,
    get_pool_courses_with_curriculum_status,
    save_period_planning_result,
)
from app.services.course_curriculum_status_service import FALL, SPRING
from app.services.semester_planning_engine import (
    generate_semester_plan,
    get_plan_run,
    list_plan_runs,
)
from app.services.semester_planning_policy_service import create_policy, resolve_policy, seed_default_policy
from app.services.semester_planning_reporting_service import (
    compare_plan_scenarios,
    export_constraint_violations,
    export_semester_plan,
    generate_human_readable_plan_report,
    get_constraint_violations,
    get_semester_plan_assignments,
)
from app.services.yearly_curriculum_integrity_service import check_yearly_curriculum_integrity

# Durum rengi jetonu -> (arka plan, yazı rengi)
_COLOR_TAGS: dict[str, tuple[str, str]] = {
    "green": ("#DCFCE7", "#166534"),
    "blue": ("#DBEAFE", "#1E40AF"),
    "yellow": ("#FEF9C3", "#854D0E"),
    "red": ("#FEE2E2", "#991B1B"),
    "gray": ("#F1F5F9", "#475569"),
    "purple": ("#EDE9FE", "#5B21B6"),
}

# Yıllık görünüm filtreleri
_FILTERS = [
    "Tümü",
    "Havuzda",
    "Müfredatta",
    "Güzde",
    "Baharda",
    "Çakışma",
    "Yeni öneri",
    "Tekrar eklenemez",
]


class SemesterPlanningPage(ttk.Frame):
    """Yıllık bütünlük odaklı Güz/Bahar dönem planlama ekranı."""

    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.app = app
        self._run_rows: dict[str, int] = {}
        self._faculty_options: dict[str, int | None] = {"Tüm Fakülteler": None}
        self._department_options: dict[str, int | None] = {"Fakülte Geneli": None}
        self._suppress_events = False
        self._last_run_id: int | None = None
        self._last_plan_result: dict[str, Any] | None = None
        self._yearly_rows: list[dict[str, Any]] = []
        self.var_target = tk.StringVar(value="8")
        self.var_fall_min = tk.StringVar(value="4")
        self.var_fall_max = tk.StringVar(value="4")
        self.var_spring_min = tk.StringVar(value="4")
        self.var_spring_max = tk.StringVar(value="4")
        self.var_respect = tk.BooleanVar(value=True)
        self.var_filter = tk.StringVar(value="Tümü")
        self._build_ui()

    # ------------------------------------------------------------------
    # Bağlantı / hata yardımcıları
    # ------------------------------------------------------------------
    def _conn(self):
        conn = getattr(getattr(self.app, "db", None), "conn", None)
        if conn is None:
            raise RuntimeError(self._friendly_backend_error())
        return conn

    @staticmethod
    def _friendly_backend_error() -> str:
        return "Dönem planlama işlemi tamamlanamadı. Veritabanı bağlantısını ve seçili kapsamı kontrol edin."

    # ------------------------------------------------------------------
    # UI kurulum
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=8)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Dönem Planlama", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Button(header, text="Yenile", command=self.refresh).pack(side=tk.RIGHT)
        self.status_var = tk.StringVar(value="Kapsam seçin; yıllık görünüm yüklenecek.")
        ttk.Label(header, textvariable=self.status_var).pack(side=tk.RIGHT, padx=8)

        self._build_scope_bar()
        self._build_summary_cards()

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self._build_yearly_tab()
        self._build_terms_tab()
        self._build_integrity_tab()
        self._build_plan_tab()
        self._build_report_tab()
        self._build_runs_tab()

    def _build_scope_bar(self) -> None:
        bar = ttk.LabelFrame(self, text="Akademik Yıl ve Kapsam", padding=8)
        bar.pack(fill=tk.X, padx=8, pady=(4, 6))

        ttk.Label(bar, text="Yıl").grid(row=0, column=0, sticky=tk.W, padx=(0, 4))
        self.var_year = tk.StringVar(value="2026")
        self.year_combo = ttk.Combobox(bar, textvariable=self.var_year, width=8, state="readonly")
        self.year_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 12))
        self.year_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        ttk.Label(bar, text="Fakülte").grid(row=0, column=2, sticky=tk.W, padx=(0, 4))
        self.faculty_combo = ttk.Combobox(bar, width=30, state="readonly")
        self.faculty_combo.grid(row=0, column=3, sticky=tk.W, padx=(0, 12))
        self.faculty_combo.bind("<<ComboboxSelected>>", self._on_faculty_change)

        ttk.Label(bar, text="Bölüm").grid(row=0, column=4, sticky=tk.W, padx=(0, 4))
        self.department_combo = ttk.Combobox(bar, width=30, state="readonly")
        self.department_combo.grid(row=0, column=5, sticky=tk.W, padx=(0, 12))
        self.department_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        ttk.Label(
            bar,
            text="(Müfredat bölüm bazlı tutulur; en doğru bütünlük kontrolü için bölüm seçin.)",
            foreground="#64748B",
        ).grid(row=1, column=0, columnspan=6, sticky=tk.W, pady=(6, 0))

    def _build_summary_cards(self) -> None:
        wrap = ttk.Frame(self, padding=(8, 0))
        wrap.pack(fill=tk.X)
        self.summary_cards: dict[str, ttk.Label] = {}
        cards = [
            ("fall_count", "Güz Dersi", "#166534"),
            ("spring_count", "Bahar Dersi", "#166534"),
            ("yearly_total", "Yıllık Toplam", "#1E40AF"),
            ("pool_count", "Havuz Dersi", "#1E40AF"),
            ("new_suggestion_count", "Yeni Öneri", "#5B21B6"),
            ("conflict_count", "Çakışma", "#991B1B"),
        ]
        for idx, (key, label, color) in enumerate(cards):
            card = ttk.LabelFrame(wrap, text=label, padding=(10, 4))
            card.grid(row=0, column=idx, sticky=tk.EW, padx=4, pady=4)
            wrap.columnconfigure(idx, weight=1)
            value = ttk.Label(card, text="-", font=("Segoe UI", 16, "bold"), foreground=color)
            value.pack()
            self.summary_cards[key] = value

    def _make_status_tree(self, parent, columns: dict[str, tuple[str, int]]):
        tree = ttk.Treeview(parent, columns=list(columns.keys()), show="headings")
        for col, (text, width) in columns.items():
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor=tk.W)
        for name, (bg, fg) in _COLOR_TAGS.items():
            tree.tag_configure(name, background=bg, foreground=fg)
        return tree

    def _build_yearly_tab(self) -> None:
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Yıllık Görünüm")

        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(toolbar, text="Filtre:").pack(side=tk.LEFT)
        filter_combo = ttk.Combobox(toolbar, textvariable=self.var_filter, values=_FILTERS, width=18, state="readonly")
        filter_combo.pack(side=tk.LEFT, padx=(4, 12))
        filter_combo.bind("<<ComboboxSelected>>", lambda _e: self._render_yearly_table())
        ttk.Label(
            toolbar,
            text="Renkler: yeşil=müfredatta · mavi=havuzda · mor=yeni öneri · kırmızı=çakışma/tekrar eklenemez",
            foreground="#64748B",
        ).pack(side=tk.LEFT)

        columns = {
            "code": ("Ders Kodu", 110),
            "name": ("Ders Adı", 240),
            "score": ("Skor", 70),
            "pool": ("Havuz", 90),
            "fall": ("Güz", 60),
            "spring": ("Bahar", 60),
            "status": ("Yıllık Durum", 230),
            "reco": ("Öneri", 200),
        }
        container = ttk.Frame(frame)
        container.pack(fill=tk.BOTH, expand=True)
        self.yearly_tree = self._make_status_tree(container, columns)
        yscroll = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.yearly_tree.yview)
        self.yearly_tree.configure(yscrollcommand=yscroll.set)
        self.yearly_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_terms_tab(self) -> None:
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Güz / Bahar")
        panes = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True)
        self.fall_status_tree = self._make_term_panel(panes, "Güz Dönemi")
        self.spring_status_tree = self._make_term_panel(panes, "Bahar Dönemi")

    def _make_term_panel(self, parent, title: str):
        box = ttk.LabelFrame(parent, text=title, padding=6)
        parent.add(box, weight=1)
        columns = {
            "code": ("Ders Kodu", 100),
            "name": ("Ders Adı", 200),
            "score": ("Skor", 60),
            "status": ("Durum", 210),
            "reco": ("Öneri", 180),
        }
        tree = self._make_status_tree(box, columns)
        scroll = ttk.Scrollbar(box, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        return tree

    def _build_integrity_tab(self) -> None:
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Bütünlük Kontrolü")
        top = ttk.Frame(frame)
        top.pack(fill=tk.X)
        ttk.Button(top, text="Kontrolü Yenile", command=self._load_integrity).pack(side=tk.LEFT)
        self.integrity_status_var = tk.StringVar(value="Yıllık müfredat bütünlüğü için kapsam seçin.")
        ttk.Label(top, textvariable=self.integrity_status_var, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=10)
        columns = {
            "severity": ("Seviye", 90),
            "type": ("Tür", 200),
            "message": ("Açıklama", 760),
        }
        self.integrity_tree = self._make_status_tree(frame, columns)
        self.integrity_tree.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    def _build_plan_tab(self) -> None:
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Plan Üret")

        controls = ttk.LabelFrame(frame, text="Plan Ayarları ve İşlemler", padding=8)
        controls.pack(fill=tk.X)
        self.policy_var = tk.StringVar(value="Politika bilgisi yükleniyor.")
        ttk.Label(controls, textvariable=self.policy_var, foreground="#334155", wraplength=1100).grid(
            row=0, column=0, columnspan=10, sticky=tk.EW, pady=(0, 6)
        )
        policy_fields = [
            ("Hedef", self.var_target),
            ("Güz Min", self.var_fall_min),
            ("Güz Max", self.var_fall_max),
            ("Bahar Min", self.var_spring_min),
            ("Bahar Max", self.var_spring_max),
        ]
        col = 0
        for label, var in policy_fields:
            ttk.Label(controls, text=label).grid(row=1, column=col, sticky=tk.W, padx=(0, 4), pady=2)
            ttk.Entry(controls, textvariable=var, width=6).grid(row=1, column=col + 1, sticky=tk.W, padx=(0, 10), pady=2)
            col += 2
        ttk.Checkbutton(
            controls,
            text="Mevcut müfredatı koru (yıl içinde çift dönem engeli)",
            variable=self.var_respect,
        ).grid(row=2, column=0, columnspan=6, sticky=tk.W, pady=(4, 2))

        btns = ttk.Frame(controls)
        btns.grid(row=3, column=0, columnspan=10, sticky=tk.W, pady=(6, 0))
        ttk.Button(btns, text="Adayları Kontrol Et", command=self.preview_plan).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Plan Üret", command=self.generate_plan).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Alternatifleri Üret", command=self.generate_alternatives).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Politikayı Kaydet", command=self.save_policy).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Planı Müfredata Kaydet", command=self.save_plan_to_curriculum).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Planı CSV", command=self.export_plan_csv).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="İhlaller CSV", command=self.export_violations_csv).pack(side=tk.LEFT, padx=2)

        plan_nb = ttk.Notebook(frame)
        plan_nb.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        plan_frame = ttk.Frame(plan_nb, padding=6)
        plan_nb.add(plan_frame, text="Güz/Bahar Planı")
        panes = ttk.PanedWindow(plan_frame, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True)
        self.fall_tree = self._make_plan_tree(panes, "Güz", use_paned=True)
        self.spring_tree = self._make_plan_tree(panes, "Bahar", use_paned=True)

        un_frame = ttk.Frame(plan_nb, padding=6)
        plan_nb.add(un_frame, text="Yerleşmeyen")
        self.unassigned_tree = self._make_plan_tree(un_frame, "Plan Dışı Kalanlar", use_paned=False)

        viol_frame = ttk.Frame(plan_nb, padding=6)
        plan_nb.add(viol_frame, text="Kısıt İhlalleri")
        self.violation_tree = ttk.Treeview(
            viol_frame, columns=("type", "course", "severity", "message", "suggestion"), show="headings"
        )
        for col, text, width in (
            ("type", "Kısıt", 140), ("course", "Ders", 130), ("severity", "Seviye", 80),
            ("message", "Mesaj", 430), ("suggestion", "Öneri", 430),
        ):
            self.violation_tree.heading(col, text=text)
            self.violation_tree.column(col, width=width, anchor=tk.W)
        self.violation_tree.pack(fill=tk.BOTH, expand=True)

        scen_frame = ttk.Frame(plan_nb, padding=6)
        plan_nb.add(scen_frame, text="Alternatif Planlar")
        self.scenario_tree = ttk.Treeview(
            scen_frame, columns=("name", "type", "score", "fall", "spring", "violations"), show="headings"
        )
        for col, text in {
            "name": "Senaryo", "type": "Tip", "score": "Plan Skoru",
            "fall": "Güz", "spring": "Bahar", "violations": "İhlal",
        }.items():
            self.scenario_tree.heading(col, text=text)
            self.scenario_tree.column(col, width=150, anchor=tk.W)
        self.scenario_tree.pack(fill=tk.BOTH, expand=True)

        # Plan özeti satırı
        summary = ttk.Frame(frame)
        summary.pack(fill=tk.X, pady=(6, 0))
        self.plan_summary_labels: dict[str, ttk.Label] = {}
        for idx, (label, key) in enumerate(
            [("Seçilen", "selected"), ("Güz", "fall"), ("Bahar", "spring"),
             ("Yerleşmeyen", "unassigned"), ("İhlal", "violations"), ("Plan Skoru", "score")]
        ):
            ttk.Label(summary, text=f"{label}:").grid(row=0, column=idx * 2, sticky=tk.W, padx=(4, 2))
            value = ttk.Label(summary, text="-", foreground="#0B5CAD")
            value.grid(row=0, column=idx * 2 + 1, sticky=tk.W, padx=(0, 16))
            self.plan_summary_labels[key] = value

    def _make_plan_tree(self, parent, title: str, use_paned: bool = True):
        box = ttk.LabelFrame(parent, text=title, padding=6)
        if use_paned:
            parent.add(box, weight=1)
        else:
            box.pack(fill=tk.BOTH, expand=True)
        columns = ("code", "name", "score", "demand", "capacity", "explanation")
        tree = ttk.Treeview(box, columns=columns, show="headings")
        headings = {
            "code": "Ders Kodu", "name": "Ders Adı", "score": "Skor",
            "demand": "Talep", "capacity": "Kontenjan", "explanation": "Açıklama",
        }
        widths = {"code": 110, "name": 220, "score": 70, "demand": 70, "capacity": 80, "explanation": 380}
        for col in columns:
            tree.heading(col, text=headings[col])
            tree.column(col, width=widths[col], anchor=tk.W)
        tree.pack(fill=tk.BOTH, expand=True)
        return tree

    def _build_report_tab(self) -> None:
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Rapor")
        ttk.Button(frame, text="Seçili Plan Raporunu Yenile", command=self.load_report_for_selected_run).pack(anchor=tk.W)
        self.report_text = tk.Text(frame, height=12, wrap=tk.WORD)
        self.report_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.report_text.configure(state=tk.DISABLED)

    def _build_runs_tab(self) -> None:
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Plan Geçmişi")
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(toolbar, text="Geçmişi Yenile", command=self._load_runs).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Seçili Planı Aç", command=self.load_selected_run).pack(side=tk.LEFT, padx=4)
        self.run_tree = ttk.Treeview(
            frame, columns=("id", "year", "faculty", "department", "fall", "spring", "score", "status"), show="headings"
        )
        for col, text in {
            "id": "Run ID", "year": "Yıl", "faculty": "Fakülte", "department": "Bölüm",
            "fall": "Güz", "spring": "Bahar", "score": "Skor", "status": "Durum",
        }.items():
            self.run_tree.heading(col, text=text)
            self.run_tree.column(col, width=100, anchor=tk.W)
        self.run_tree.pack(fill=tk.BOTH, expand=True)
        self.run_tree.bind("<<TreeviewSelect>>", lambda _event: self.load_selected_run())

    # ------------------------------------------------------------------
    # Yenile / kapsam
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        try:
            conn = self._conn()
            seed_default_policy(conn)
            conn.commit()
            self._populate_filters(conn)
            self._load_current_policy()
            self._load_yearly_view()
            self._load_integrity()
            self._load_runs()
            self.status_var.set("Hazır. Yıllık görünüm yüklendi.")
        except Exception:
            messagebox.showerror("Dönem Planlama", self._friendly_backend_error())

    def _populate_filters(self, conn) -> None:
        self._suppress_events = True
        try:
            cur = conn.cursor()
            current_year = self.var_year.get()
            years = self._fetch_years(cur)
            self.year_combo["values"] = [str(item) for item in years]
            if current_year in self.year_combo["values"]:
                self.year_combo.set(current_year)
            elif "2026" in self.year_combo["values"]:
                self.year_combo.set("2026")
            elif years:
                self.year_combo.set(str(years[-1]))

            current_faculty = self.faculty_combo.get()
            self._faculty_options = {"Tüm Fakülteler": None}
            for fac_id, name in self._fetch_faculties(cur):
                self._faculty_options[f"{name} (ID: {fac_id})"] = int(fac_id)
            self.faculty_combo["values"] = list(self._faculty_options.keys())
            self.faculty_combo.set(current_faculty if current_faculty in self._faculty_options else "Tüm Fakülteler")
            self._populate_departments(cur, selected_label=self.department_combo.get())
        finally:
            self._suppress_events = False

    @staticmethod
    def _fetch_years(cur) -> list[int]:
        years: set[int] = {2026}
        for table, column in (("skor", "akademik_yil"), ("mufredat", "akademik_yil"), ("semester_plan_runs", "year")):
            try:
                cur.execute(f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL")
                for row in cur.fetchall():
                    if not row or row[0] is None:
                        continue
                    try:
                        years.add(int(row[0]))
                    except (TypeError, ValueError):
                        continue
            except Exception:
                continue
        return sorted(years)

    @staticmethod
    def _fetch_faculties(cur) -> list[tuple[int, str]]:
        try:
            cur.execute("SELECT fakulte_id, ad FROM fakulte ORDER BY ad")
            return [(int(row[0]), str(row[1])) for row in cur.fetchall()]
        except Exception:
            return []

    def _populate_departments(self, cur, selected_label: str | None = None) -> None:
        faculty_id = self._selected_faculty_id()
        self._department_options = {"Fakülte Geneli": None}
        try:
            if faculty_id is None:
                cur.execute("SELECT bolum_id, ad FROM bolum ORDER BY ad")
            else:
                cur.execute("SELECT bolum_id, ad FROM bolum WHERE fakulte_id = ? ORDER BY ad", (int(faculty_id),))
            for dep_id, name in cur.fetchall():
                self._department_options[f"{name} (ID: {dep_id})"] = int(dep_id)
        except Exception:
            pass
        self.department_combo["values"] = list(self._department_options.keys())
        self.department_combo.set(selected_label if selected_label in self._department_options else "Fakülte Geneli")

    def _on_faculty_change(self, _event: Any = None) -> None:
        if self._suppress_events:
            return
        try:
            cur = self._conn().cursor()
            self._populate_departments(cur)
            self._load_current_policy()
            self._load_yearly_view()
            self._load_integrity()
            self._load_runs()
        except Exception:
            messagebox.showerror("Dönem Planlama", self._friendly_backend_error())

    def _on_filter_change(self, _event: Any = None) -> None:
        if self._suppress_events:
            return
        self._load_current_policy()
        self._load_yearly_view()
        self._load_integrity()
        self._load_runs()

    def _selected_year(self) -> int:
        try:
            return int(self.var_year.get() or 0)
        except ValueError:
            return 0

    def _selected_faculty_id(self) -> int | None:
        return self._faculty_options.get(self.faculty_combo.get())

    def _selected_department_id(self) -> int | None:
        return self._department_options.get(self.department_combo.get())

    # ------------------------------------------------------------------
    # Yıllık görünüm + özet kartları + dönem panelleri
    # ------------------------------------------------------------------
    def _load_yearly_view(self) -> None:
        year = self._selected_year()
        if year <= 0:
            return
        try:
            conn = self._conn()
            faculty_id = self._selected_faculty_id()
            department_id = self._selected_department_id()

            summary = get_period_planning_summary(conn, year, faculty_id, department_id)
            for key, label in self.summary_cards.items():
                label.config(text=str(summary.get(key, 0)))

            pool_rows = get_pool_courses_with_curriculum_status(conn, year, faculty_id, department_id)
            curriculum_rows = get_curriculum_courses_by_year(conn, year, faculty_id, department_id)

            meta: dict[int, dict[str, Any]] = {}
            for row in curriculum_rows:
                meta[row["course_id"]] = {
                    "course_code": row.get("course_code"),
                    "course_name": row.get("course_name"),
                    "score": row.get("score", 0.0),
                }
            for row in pool_rows:
                meta[row["course_id"]] = {
                    "course_code": row.get("course_code"),
                    "course_name": row.get("course_name"),
                    "score": row.get("score", 0.0),
                }

            ids = sorted(meta.keys())
            status_map = get_courses_status_batch(conn, year, ids, faculty_id, department_id)
            rows: list[dict[str, Any]] = []
            for cid in ids:
                rows.append({**meta[cid], **status_map.get(cid, {})})
            # Sıralama: çakışma > müfredatta > yeni öneri/havuz; sonra skor
            rows.sort(
                key=lambda r: (
                    0 if r.get("status_code") == "conflict_both_terms"
                    else 1 if r.get("in_yearly_curriculum")
                    else 2,
                    -float(r.get("score") or 0.0),
                )
            )
            self._yearly_rows = rows
            self._render_yearly_table()
            self._render_term_panels(rows)
        except Exception:
            self.status_var.set("Yıllık görünüm yüklenemedi.")

    @staticmethod
    def _filter_match(row: dict[str, Any], flt: str) -> bool:
        if flt == "Tümü":
            return True
        if flt == "Havuzda":
            return bool(row.get("in_pool"))
        if flt == "Müfredatta":
            return bool(row.get("in_yearly_curriculum"))
        if flt == "Güzde":
            return bool(row.get("in_fall_curriculum"))
        if flt == "Baharda":
            return bool(row.get("in_spring_curriculum"))
        if flt == "Çakışma":
            return row.get("status_code") == "conflict_both_terms"
        if flt == "Yeni öneri":
            return bool(row.get("in_pool")) and not bool(row.get("in_yearly_curriculum"))
        if flt == "Tekrar eklenemez":
            return bool(row.get("in_yearly_curriculum"))
        return True

    def _render_yearly_table(self) -> None:
        tree = self.yearly_tree
        tree.delete(*tree.get_children())
        flt = self.var_filter.get()
        shown = 0
        for row in self._yearly_rows:
            if not self._filter_match(row, flt):
                continue
            tree.insert(
                "",
                tk.END,
                values=(
                    row.get("course_code") or row.get("course_id"),
                    row.get("course_name") or "",
                    self._round(row.get("score")),
                    "Evet" if row.get("in_pool") else "Hayır",
                    "✓" if row.get("in_fall_curriculum") else "—",
                    "✓" if row.get("in_spring_curriculum") else "—",
                    row.get("status_label") or "",
                    row.get("recommendation") or "",
                ),
                tags=(row.get("status_color") or "gray",),
            )
            shown += 1
        if shown == 0:
            tree.insert("", tk.END, values=("", "Kayıt yok / kapsam boş.", "", "", "", "", "", ""), tags=("gray",))

    def _render_term_panels(self, rows: list[dict[str, Any]]) -> None:
        for tree, term in ((self.fall_status_tree, FALL), (self.spring_status_tree, SPRING)):
            tree.delete(*tree.get_children())
            # Bu dönemle ilgili dersler: bu dönem müfredatı + havuz adayları + diğer dönem müfredatı (etiketli)
            relevant = [
                r for r in rows
                if r.get("in_fall_curriculum") or r.get("in_spring_curriculum") or r.get("in_pool")
            ]

            def sort_key(r: dict[str, Any]) -> tuple[int, float]:
                in_this = r.get("in_fall_curriculum") if term == FALL else r.get("in_spring_curriculum")
                can_add = r.get("can_be_added_to_fall") if term == FALL else r.get("can_be_added_to_spring")
                if in_this:
                    rank = 0
                elif r.get("in_pool") and can_add and not r.get("in_yearly_curriculum"):
                    rank = 1
                else:
                    rank = 2
                return (rank, -float(r.get("score") or 0.0))

            relevant.sort(key=sort_key)
            if not relevant:
                tree.insert("", tk.END, values=("", "Kayıt yok.", "", "", ""), tags=("gray",))
                continue
            for r in relevant:
                tree.insert(
                    "",
                    tk.END,
                    values=(
                        r.get("course_code") or r.get("course_id"),
                        r.get("course_name") or "",
                        self._round(r.get("score")),
                        r.get("status_label") or "",
                        r.get("recommendation") or "",
                    ),
                    tags=(r.get("status_color") or "gray",),
                )

    # ------------------------------------------------------------------
    # Bütünlük kontrolü
    # ------------------------------------------------------------------
    def _load_integrity(self) -> None:
        year = self._selected_year()
        if year <= 0:
            return
        try:
            conn = self._conn()
            report = check_yearly_curriculum_integrity(
                conn, year, self._selected_faculty_id(), self._selected_department_id()
            )
            self.integrity_status_var.set(f"Durum: {report.get('status')}")
            self.integrity_tree.delete(*self.integrity_tree.get_children())
            issues = report.get("issues") or []
            if not issues:
                self.integrity_tree.insert("", tk.END, values=("TEMİZ", "—", "Yıllık müfredat bütünlüğü sağlandı."), tags=("green",))
                return
            color_by_sev = {"error": "red", "warning": "yellow", "info": "blue"}
            for issue in issues:
                self.integrity_tree.insert(
                    "",
                    tk.END,
                    values=(
                        issue.get("severity", "").upper(),
                        issue.get("type", ""),
                        issue.get("message", ""),
                    ),
                    tags=(color_by_sev.get(issue.get("severity"), "gray"),),
                )
        except Exception:
            self.integrity_status_var.set("Bütünlük kontrolü yüklenemedi.")

    # ------------------------------------------------------------------
    # Politika
    # ------------------------------------------------------------------
    def _load_current_policy(self) -> None:
        try:
            conn = self._conn()
            policy = resolve_policy(
                conn,
                year=self._selected_year() or 2026,
                faculty_id=self._selected_faculty_id(),
                department_id=self._selected_department_id(),
            )
            if not policy:
                seed_default_policy(conn)
                conn.commit()
                policy = resolve_policy(
                    conn,
                    year=self._selected_year() or 2026,
                    faculty_id=self._selected_faculty_id(),
                    department_id=self._selected_department_id(),
                )
            self._set_policy_text(policy)
        except Exception:
            self.policy_var.set("Politika bilgisi yüklenemedi.")

    def _set_policy_text(self, policy: dict[str, Any] | None) -> None:
        if not policy:
            self.policy_var.set("Aktif politika bulunamadı. Yenile butonu varsayılan 4+4 politikasını oluşturur.")
            return
        self.policy_var.set(
            f"Aktif politika: {policy.get('name')} | hedef {policy.get('total_elective_target')} ders | "
            f"Güz {policy.get('fall_min')}-{policy.get('fall_max')} | "
            f"Bahar {policy.get('spring_min')}-{policy.get('spring_max')} | "
            f"denge toleransı {policy.get('max_semester_imbalance')}"
        )
        self.var_target.set(str(policy.get("total_elective_target") or 8))
        self.var_fall_min.set(str(policy.get("fall_min") or 0))
        self.var_fall_max.set(str(policy.get("fall_max") or 0))
        self.var_spring_min.set(str(policy.get("spring_min") or 0))
        self.var_spring_max.set(str(policy.get("spring_max") or 0))

    def save_policy(self) -> None:
        try:
            year = self._selected_year()
            if year <= 0:
                messagebox.showwarning("Dönem Planlama", "Politika kaydetmek için geçerli bir yıl seçiniz.")
                return
            target = int(self.var_target.get())
            fall_min = int(self.var_fall_min.get())
            fall_max = int(self.var_fall_max.get())
            spring_min = int(self.var_spring_min.get())
            spring_max = int(self.var_spring_max.get())
            faculty_id = self._selected_faculty_id()
            department_id = self._selected_department_id()
            scope_type = "department" if department_id is not None else ("faculty" if faculty_id is not None else "global")
            conn = self._conn()
            policy = create_policy(
                conn,
                name=f"{year} Dönem Planlama Politikası",
                scope_type=scope_type,
                faculty_id=faculty_id,
                department_id=department_id,
                year=year,
                total_elective_target=target,
                fall_min=fall_min,
                fall_max=fall_max,
                spring_min=spring_min,
                spring_max=spring_max,
                max_semester_imbalance=abs(fall_max - spring_max),
                activate=True,
                notes="Masaüstü dönem planlama ekranından oluşturuldu.",
            )
            conn.commit()
            self._set_policy_text(policy)
            self.status_var.set("Politika kaydedildi ve aktif yapıldı.")
            messagebox.showinfo("Dönem Planlama", "Politika kaydedildi. Yeni planlar bu ayarlarla üretilecek.")
        except ValueError as exc:
            messagebox.showwarning("Dönem Planlama", str(exc))
        except Exception:
            messagebox.showerror("Dönem Planlama", self._friendly_backend_error())

    # ------------------------------------------------------------------
    # Plan üretme
    # ------------------------------------------------------------------
    def preview_plan(self) -> None:
        self._run_planning(persist=False, generate_alternatives=False, success_message="Aday plan ön izlemesi hazırlandı.")

    def generate_plan(self) -> None:
        self._run_planning(persist=True, generate_alternatives=False, success_message="Dönem planı üretildi ve geçmişe kaydedildi.")

    def generate_alternatives(self) -> None:
        self._run_planning(persist=True, generate_alternatives=True, success_message="Dönem planı ve alternatif senaryolar üretildi.")

    def _run_planning(self, *, persist: bool, generate_alternatives: bool, success_message: str) -> None:
        year = self._selected_year()
        if year <= 0:
            messagebox.showwarning("Dönem Planlama", "Plan üretmek için geçerli bir yıl seçiniz.")
            return
        try:
            conn = self._conn()
            result = generate_semester_plan(
                conn,
                year=year,
                faculty_id=self._selected_faculty_id(),
                department_id=self._selected_department_id(),
                persist=persist,
                generate_alternatives=generate_alternatives,
                created_by="desktop-ui" if persist else None,
                respect_existing_curriculum=bool(self.var_respect.get()),
            )
            if persist:
                conn.commit()
            self._last_plan_result = result
            self._load_plan_result(result)
            if result.get("policy"):
                self._set_policy_text(result.get("policy"))
            if persist:
                self._last_run_id = int(result["plan_id"]) if result.get("plan_id") else None
                self._load_runs()
                if self._last_run_id is not None:
                    try:
                        self._set_report(generate_human_readable_plan_report(conn, self._last_run_id))
                    except Exception:
                        pass
            selected_count = len(result.get("fall_courses") or []) + len(result.get("spring_courses") or [])
            if selected_count == 0:
                self.status_var.set("Aday ders bulunamadı. Veri ve Karar Merkezi verilerini kontrol edin.")
                messagebox.showwarning("Dönem Planlama", "Seçili kapsamda plana yerleşebilecek aday ders bulunamadı.")
                return
            self.status_var.set(success_message)
            messagebox.showinfo("Dönem Planlama", success_message)
        except Exception:
            messagebox.showerror("Dönem Planlama", self._friendly_backend_error())

    def _load_plan_result(self, result: dict[str, Any]) -> None:
        fall = result.get("fall_courses", []) or []
        spring = result.get("spring_courses", []) or []
        unassigned = result.get("unassigned_courses", []) or result.get("rejected_courses", []) or []
        violations = result.get("constraint_violations", []) or []
        scenarios = result.get("alternative_plans", []) or []
        self._fill_plan_tree(self.fall_tree, fall, empty_text="Güz dönemi için ders yok.")
        self._fill_plan_tree(self.spring_tree, spring, empty_text="Bahar dönemi için ders yok.")
        self._fill_plan_tree(self.unassigned_tree, unassigned, empty_text="Yerleşmeyen ders yok.")
        self._fill_violations(violations)
        self._fill_scenarios(scenarios)
        self._set_plan_summary(
            selected=len(fall) + len(spring),
            fall=len(fall),
            spring=len(spring),
            unassigned=len(unassigned),
            violations=len(violations),
            score=result.get("plan_score", 0.0),
        )

    def _set_plan_summary(self, **values: Any) -> None:
        for key, label in self.plan_summary_labels.items():
            value = values.get(key, "-")
            if key == "score":
                try:
                    value = f"{float(value):.2f}"
                except (TypeError, ValueError):
                    value = "-"
            label.config(text=str(value))

    def _fill_plan_tree(self, tree, rows: list[dict[str, Any]], empty_text: str) -> None:
        tree.delete(*tree.get_children())
        if not rows:
            tree.insert("", tk.END, values=("", empty_text, "", "", "", ""))
            return
        for row in rows:
            tree.insert(
                "",
                tk.END,
                values=(
                    row.get("course_code") or row.get("course_id"),
                    row.get("course_name") or "",
                    self._round(row.get("course_score")),
                    self._round(row.get("expected_demand")),
                    self._round(row.get("expected_capacity")),
                    row.get("explanation") or "",
                ),
            )

    def _fill_violations(self, rows: list[dict[str, Any]]) -> None:
        self.violation_tree.delete(*self.violation_tree.get_children())
        if not rows:
            self.violation_tree.insert("", tk.END, values=("", "", "TEMİZ", "Kısıt ihlali yok.", ""))
            return
        for row in rows:
            self.violation_tree.insert(
                "",
                tk.END,
                values=(
                    row.get("constraint_type"),
                    row.get("course_code") or row.get("course_name") or row.get("course_id"),
                    row.get("severity"),
                    row.get("message"),
                    row.get("suggestion"),
                ),
            )

    def _fill_scenarios(self, rows: list[dict[str, Any]]) -> None:
        self.scenario_tree.delete(*self.scenario_tree.get_children())
        if not rows:
            self.scenario_tree.insert("", tk.END, values=("Alternatif yok", "", "", "", "", ""))
            return
        for row in rows:
            self.scenario_tree.insert(
                "",
                tk.END,
                values=(
                    row.get("scenario_name"),
                    row.get("scenario_type"),
                    self._round(row.get("plan_score")),
                    len(row.get("fall_courses") or []),
                    len(row.get("spring_courses") or []),
                    len(row.get("constraint_violations") or []),
                ),
            )

    @staticmethod
    def _round(value: Any) -> str:
        try:
            return f"{float(value or 0.0):.2f}"
        except (TypeError, ValueError):
            return "0.00"

    # ------------------------------------------------------------------
    # Planı müfredata kaydet (çift-dönem engelli)
    # ------------------------------------------------------------------
    def save_plan_to_curriculum(self) -> None:
        result = self._last_plan_result
        if not result:
            messagebox.showinfo("Dönem Planlama", "Önce bir plan üretin.")
            return
        year = self._selected_year()
        faculty_id = self._selected_faculty_id()
        department_id = self._selected_department_id()
        if year <= 0 or faculty_id is None or department_id is None:
            messagebox.showwarning(
                "Dönem Planlama",
                "Planı müfredata kaydetmek için Yıl + Fakülte + Bölüm seçili olmalıdır (müfredat bölüm bazlıdır).",
            )
            return
        fall_ids = [int(c) for c in result.get("fall_course_ids", [])]
        spring_ids = [int(c) for c in result.get("spring_course_ids", [])]
        if not fall_ids and not spring_ids:
            messagebox.showinfo("Dönem Planlama", "Kaydedilecek ders yok.")
            return
        if not messagebox.askyesno(
            "Dönem Planlama",
            f"{year} yılı {self.department_combo.get()} müfredatı bu planla değiştirilecek "
            f"(Güz: {len(fall_ids)}, Bahar: {len(spring_ids)}). Devam edilsin mi?",
        ):
            return
        try:
            conn = self._conn()
            outcome = save_period_planning_result(
                conn,
                year,
                faculty_id=faculty_id,
                department_id=department_id,
                fall_course_ids=fall_ids,
                spring_course_ids=spring_ids,
                plan_run_id=self._last_run_id,
            )
            conn.commit()
            self.status_var.set(
                f"Plan müfredata kaydedildi (Güz {outcome['fall_written']}, Bahar {outcome['spring_written']})."
            )
            messagebox.showinfo("Dönem Planlama", "Plan müfredata kaydedildi.")
            self._load_yearly_view()
            self._load_integrity()
        except ValueError as exc:
            messagebox.showwarning("Dönem Planlama", str(exc))
        except Exception:
            messagebox.showerror("Dönem Planlama", self._friendly_backend_error())

    # ------------------------------------------------------------------
    # Plan geçmişi / rapor / CSV
    # ------------------------------------------------------------------
    def _load_runs(self) -> None:
        self.run_tree.delete(*self.run_tree.get_children())
        self._run_rows.clear()
        try:
            conn = self._conn()
            rows = list_plan_runs(
                conn,
                year=self._selected_year() or None,
                faculty_id=self._selected_faculty_id(),
                department_id=self._selected_department_id(),
            )
            if not rows:
                self.run_tree.insert("", tk.END, values=("", "", "", "", "", "", "", "Henüz plan yok"))
                return
            for row in rows:
                raw_id = row.get("id")
                if raw_id is None:
                    continue
                iid = str(raw_id)
                self._run_rows[iid] = int(raw_id)
                self.run_tree.insert(
                    "",
                    tk.END,
                    iid=iid,
                    values=(
                        row.get("id"),
                        row.get("year"),
                        row.get("faculty_id") or "Tümü",
                        row.get("department_id") or "Genel",
                        row.get("fall_count"),
                        row.get("spring_count"),
                        self._round(row.get("plan_score")),
                        row.get("status"),
                    ),
                )
        except Exception:
            self.status_var.set("Plan geçmişi yüklenemedi.")

    def load_selected_run(self) -> None:
        selection = self.run_tree.selection()
        if not selection:
            return
        run_id = self._run_rows.get(selection[0])
        if not run_id:
            return
        try:
            conn = self._conn()
            run = get_plan_run(conn, run_id)
            assignments = get_semester_plan_assignments(conn, run_id)
            violations = get_constraint_violations(conn, run_id)
            scenarios = compare_plan_scenarios(conn, run_id)
            self._last_run_id = int(run_id)
            result = {
                "plan_id": run_id,
                "plan_score": run.get("plan_score") if run else 0.0,
                "fall_courses": [a for a in assignments if a.get("assigned_semester") == "fall"],
                "spring_courses": [a for a in assignments if a.get("assigned_semester") == "spring"],
                "unassigned_courses": [a for a in assignments if a.get("assigned_semester") == "unassigned"],
                "fall_course_ids": [int(a["course_id"]) for a in assignments if a.get("assigned_semester") == "fall"],
                "spring_course_ids": [int(a["course_id"]) for a in assignments if a.get("assigned_semester") == "spring"],
                "constraint_violations": violations,
                "alternative_plans": scenarios,
                "warnings": (run or {}).get("warnings", []),
            }
            self._last_plan_result = result
            self._load_plan_result(result)
            if run:
                self.status_var.set(f"Seçili plan açıldı: {run.get('run_name')} | skor {self._round(run.get('plan_score'))}")
                self._set_policy_text(run.get("policy_snapshot") or {})
                self._set_report(generate_human_readable_plan_report(conn, run_id))
        except Exception:
            messagebox.showerror("Dönem Planlama", self._friendly_backend_error())

    def load_report_for_selected_run(self) -> None:
        if self._last_run_id is None:
            messagebox.showinfo("Dönem Planlama", "Önce geçmişten bir plan seçin veya yeni plan üretin.")
            return
        try:
            self._set_report(generate_human_readable_plan_report(self._conn(), self._last_run_id))
        except Exception:
            messagebox.showerror("Dönem Planlama", self._friendly_backend_error())

    def export_plan_csv(self) -> None:
        self._export_csv(kind="plan")

    def export_violations_csv(self) -> None:
        self._export_csv(kind="violations")

    def _export_csv(self, *, kind: str) -> None:
        if self._last_run_id is None:
            messagebox.showinfo("Dönem Planlama", "Önce plan üretin veya geçmişten bir plan seçin.")
            return
        default_name = f"donem_plani_{self._last_run_id}.csv" if kind == "plan" else f"donem_plani_ihlaller_{self._last_run_id}.csv"
        path = filedialog.asksaveasfilename(
            title="CSV kaydet",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV dosyası", "*.csv"), ("Tüm dosyalar", "*.*")],
        )
        if not path:
            return
        try:
            conn = self._conn()
            content = export_semester_plan(conn, self._last_run_id) if kind == "plan" else export_constraint_violations(conn, self._last_run_id)
            with open(path, "w", encoding="utf-8-sig", newline="") as handle:
                handle.write(content)
            messagebox.showinfo("Dönem Planlama", f"CSV kaydedildi:\n{path}")
        except Exception:
            messagebox.showerror("Dönem Planlama", self._friendly_backend_error())

    def _set_report(self, text: str) -> None:
        self.report_text.configure(state=tk.NORMAL)
        self.report_text.delete("1.0", tk.END)
        self.report_text.insert(tk.END, text or "")
        self.report_text.configure(state=tk.DISABLED)
