# -*- coding: utf-8 -*-
"""Dönem Planlama Tkinter paneli."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

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


class SemesterPlanningPage(ttk.Frame):
    """Policy tabanlı Güz/Bahar dönem planlama ekranı."""

    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.app = app
        self._run_rows: dict[str, int] = {}
        self._faculty_options: dict[str, int | None] = {"Tüm Fakülteler": None}
        self._department_options: dict[str, int | None] = {"Fakülte Geneli": None}
        self._suppress_events = False
        self._last_run_id: int | None = None
        self.var_target = tk.StringVar(value="8")
        self.var_fall_min = tk.StringVar(value="4")
        self.var_fall_max = tk.StringVar(value="4")
        self.var_spring_min = tk.StringVar(value="4")
        self.var_spring_max = tk.StringVar(value="4")
        self._build_ui()

    def _conn(self):
        conn = getattr(getattr(self.app, "db", None), "conn", None)
        if conn is None:
            raise RuntimeError(self._friendly_backend_error())
        return conn

    @staticmethod
    def _friendly_backend_error() -> str:
        return "Dönem planlama işlemi tamamlanamadı. Veritabanı bağlantısını ve seçili kapsamı kontrol edin."

    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=8)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Dönem Planlama", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Button(header, text="Yenile", command=self.refresh).pack(side=tk.RIGHT)
        self.status_var = tk.StringVar(value="Kapsam seçin ve plan üretin.")
        ttk.Label(header, textvariable=self.status_var).pack(side=tk.RIGHT, padx=8)

        info = ttk.LabelFrame(self, text="Bu sayfa ne işe yarar?", padding=8)
        info.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Label(
            info,
            text=(
                "Karar ve skor verilerini kullanarak seçmeli dersleri Güz ve Bahar dönemlerine dengeli dağıtır. "
                "Önce yıl/fakülte/bölüm kapsamını seçin, adayları kontrol edin, sonra plan üretip kısıt ihlallerini inceleyin."
            ),
            wraplength=1180,
            justify=tk.LEFT,
        ).pack(fill=tk.X)

        controls = ttk.LabelFrame(self, text="Plan Kapsamı ve İşlemler", padding=8)
        controls.pack(fill=tk.X, padx=8, pady=(0, 8))

        ttk.Label(controls, text="Yıl").grid(row=0, column=0, sticky=tk.W, padx=(0, 4), pady=3)
        self.var_year = tk.StringVar(value="2026")
        self.year_combo = ttk.Combobox(controls, textvariable=self.var_year, width=10, state="readonly")
        self.year_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 12), pady=3)
        self.year_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        ttk.Label(controls, text="Fakülte").grid(row=0, column=2, sticky=tk.W, padx=(0, 4), pady=3)
        self.faculty_combo = ttk.Combobox(controls, width=32, state="readonly")
        self.faculty_combo.grid(row=0, column=3, sticky=tk.W, padx=(0, 12), pady=3)
        self.faculty_combo.bind("<<ComboboxSelected>>", self._on_faculty_change)

        ttk.Label(controls, text="Bölüm").grid(row=0, column=4, sticky=tk.W, padx=(0, 4), pady=3)
        self.department_combo = ttk.Combobox(controls, width=32, state="readonly")
        self.department_combo.grid(row=0, column=5, sticky=tk.W, padx=(0, 12), pady=3)
        self.department_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        ttk.Button(controls, text="Adayları Kontrol Et", command=self.preview_plan).grid(row=0, column=6, padx=4, pady=3)
        ttk.Button(controls, text="Plan Üret", command=self.generate_plan).grid(row=0, column=7, padx=4, pady=3)
        ttk.Button(controls, text="Alternatifleri Üret", command=self.generate_alternatives).grid(row=0, column=8, padx=4, pady=3)

        self.policy_var = tk.StringVar(value="Politika bilgisi yükleniyor.")
        ttk.Label(controls, textvariable=self.policy_var, foreground="#334155", wraplength=1120).grid(
            row=1, column=0, columnspan=9, sticky=tk.EW, pady=(8, 0)
        )

        policy_fields = [
            ("Hedef", self.var_target, 6),
            ("Güz Min", self.var_fall_min, 6),
            ("Güz Max", self.var_fall_max, 6),
            ("Bahar Min", self.var_spring_min, 6),
            ("Bahar Max", self.var_spring_max, 6),
        ]
        col = 0
        for label, var, width in policy_fields:
            ttk.Label(controls, text=label).grid(row=2, column=col, sticky=tk.W, padx=(0, 4), pady=(8, 2))
            ttk.Entry(controls, textvariable=var, width=width).grid(row=2, column=col + 1, sticky=tk.W, padx=(0, 12), pady=(8, 2))
            col += 2
        ttk.Button(controls, text="Politikayı Kaydet", command=self.save_policy).grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=4, pady=(8, 2))
        ttk.Button(controls, text="Planı CSV Kaydet", command=self.export_plan_csv).grid(row=3, column=2, columnspan=2, sticky=tk.W, padx=4, pady=(8, 2))
        ttk.Button(controls, text="İhlalleri CSV Kaydet", command=self.export_violations_csv).grid(row=3, column=4, columnspan=2, sticky=tk.W, padx=4, pady=(8, 2))
        controls.columnconfigure(5, weight=1)

        summary = ttk.LabelFrame(self, text="Plan Özeti", padding=8)
        summary.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.summary_labels: dict[str, ttk.Label] = {}
        for idx, (label, key) in enumerate(
            [
                ("Seçilen Ders", "selected"),
                ("Güz", "fall"),
                ("Bahar", "spring"),
                ("Yerleşmeyen", "unassigned"),
                ("İhlal", "violations"),
                ("Plan Skoru", "score"),
            ]
        ):
            ttk.Label(summary, text=f"{label}:").grid(row=0, column=idx * 2, sticky=tk.W, padx=(4, 2))
            value = ttk.Label(summary, text="-", foreground="#0B5CAD")
            value.grid(row=0, column=idx * 2 + 1, sticky=tk.W, padx=(0, 18))
            self.summary_labels[key] = value

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self._build_plan_tab()
        self._build_unassigned_tab()
        self._build_violations_tab()
        self._build_scenarios_tab()
        self._build_report_tab()
        self._build_runs_tab()

    def _build_plan_tab(self) -> None:
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Güz/Bahar Planı")
        panes = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True)
        self.fall_tree = self._make_course_tree(panes, "Güz")
        self.spring_tree = self._make_course_tree(panes, "Bahar")

    def _build_unassigned_tab(self) -> None:
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Yerleşmeyen Dersler")
        self.unassigned_tree = self._make_course_tree(frame, "Plan Dışı Kalanlar", use_paned=False)

    def _build_violations_tab(self) -> None:
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Kısıt İhlalleri")
        self.violation_tree = ttk.Treeview(
            frame,
            columns=("type", "course", "severity", "message", "suggestion"),
            show="headings",
        )
        widths = {"type": 140, "course": 130, "severity": 80, "message": 430, "suggestion": 430}
        for col, text in {
            "type": "Kısıt",
            "course": "Ders",
            "severity": "Seviye",
            "message": "Mesaj",
            "suggestion": "Öneri",
        }.items():
            self.violation_tree.heading(col, text=text)
            self.violation_tree.column(col, width=widths[col], anchor=tk.W)
        self.violation_tree.pack(fill=tk.BOTH, expand=True)

    def _build_scenarios_tab(self) -> None:
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Alternatif Planlar")
        self.scenario_tree = ttk.Treeview(
            frame,
            columns=("name", "type", "score", "fall", "spring", "violations"),
            show="headings",
        )
        for col, text in {
            "name": "Senaryo",
            "type": "Tip",
            "score": "Plan Skoru",
            "fall": "Güz",
            "spring": "Bahar",
            "violations": "İhlal",
        }.items():
            self.scenario_tree.heading(col, text=text)
            self.scenario_tree.column(col, width=150, anchor=tk.W)
        self.scenario_tree.pack(fill=tk.BOTH, expand=True)

    def _build_report_tab(self) -> None:
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Rapor")
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text="Seçili Plan Raporunu Yenile", command=self.load_report_for_selected_run).pack(side=tk.LEFT)
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
            frame,
            columns=("id", "year", "faculty", "department", "fall", "spring", "score", "status"),
            show="headings",
        )
        for col, text in {
            "id": "Run ID",
            "year": "Yıl",
            "faculty": "Fakülte",
            "department": "Bölüm",
            "fall": "Güz",
            "spring": "Bahar",
            "score": "Skor",
            "status": "Durum",
        }.items():
            self.run_tree.heading(col, text=text)
            self.run_tree.column(col, width=100, anchor=tk.W)
        self.run_tree.pack(fill=tk.BOTH, expand=True)
        self.run_tree.bind("<<TreeviewSelect>>", lambda _event: self.load_selected_run())

    def _make_course_tree(self, parent, title: str, use_paned: bool = True):
        box = ttk.LabelFrame(parent, text=title, padding=6)
        if use_paned:
            parent.add(box, weight=1)
        else:
            box.pack(fill=tk.BOTH, expand=True)
        columns = ("code", "name", "score", "demand", "capacity", "explanation")
        tree = ttk.Treeview(box, columns=columns, show="headings")
        headings = {
            "code": "Ders Kodu",
            "name": "Ders Adı",
            "score": "Skor",
            "demand": "Talep",
            "capacity": "Kontenjan",
            "explanation": "Açıklama",
        }
        widths = {"code": 110, "name": 220, "score": 80, "demand": 80, "capacity": 90, "explanation": 420}
        for col in columns:
            tree.heading(col, text=headings[col])
            tree.column(col, width=widths[col], anchor=tk.W)
        tree.pack(fill=tk.BOTH, expand=True)
        return tree

    def refresh(self) -> None:
        try:
            conn = self._conn()
            seed_default_policy(conn)
            conn.commit()
            self._populate_filters(conn)
            policy = resolve_policy(
                conn,
                year=self._selected_year() or 2026,
                faculty_id=self._selected_faculty_id(),
                department_id=self._selected_department_id(),
            )
            self._set_policy_text(policy)
            self._load_runs()
            self.status_var.set("Hazır. Kapsam seçip plan üretebilirsiniz.")
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
                years.update(int(row[0]) for row in cur.fetchall() if row and row[0] is not None)
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
            self._load_runs()
        except Exception:
            messagebox.showerror("Dönem Planlama", self._friendly_backend_error())

    def _on_filter_change(self, _event: Any = None) -> None:
        if self._suppress_events:
            return
        self._load_current_policy()
        self._load_runs()

    def _load_current_policy(self) -> None:
        try:
            policy = resolve_policy(
                self._conn(),
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

    def _selected_year(self) -> int:
        try:
            return int(self.var_year.get() or 0)
        except ValueError:
            return 0

    def _selected_faculty_id(self) -> int | None:
        return self._faculty_options.get(self.faculty_combo.get())

    def _selected_department_id(self) -> int | None:
        return self._department_options.get(self.department_combo.get())

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
            )
            if persist:
                conn.commit()
            self._load_result(result)
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
                self.status_var.set("Aday ders bulunamadı. Veri Yönetimi ve Karar Merkezi verilerini kontrol edin.")
                messagebox.showwarning("Dönem Planlama", "Seçili kapsamda plana yerleşebilecek aday ders bulunamadı.")
                return
            self.status_var.set(success_message)
            messagebox.showinfo("Dönem Planlama", success_message)
        except Exception:
            messagebox.showerror("Dönem Planlama", self._friendly_backend_error())

    def _load_result(self, result: dict[str, Any]) -> None:
        fall = result.get("fall_courses", []) or []
        spring = result.get("spring_courses", []) or []
        unassigned = result.get("unassigned_courses", []) or result.get("rejected_courses", []) or []
        violations = result.get("constraint_violations", []) or []
        scenarios = result.get("alternative_plans", []) or []
        self._fill_course_tree(self.fall_tree, fall, empty_text="Güz dönemi için ders yok.")
        self._fill_course_tree(self.spring_tree, spring, empty_text="Bahar dönemi için ders yok.")
        self._fill_course_tree(self.unassigned_tree, unassigned, empty_text="Yerleşmeyen ders yok.")
        self._fill_violations(violations)
        self._fill_scenarios(scenarios)
        self._set_summary(
            selected=len(fall) + len(spring),
            fall=len(fall),
            spring=len(spring),
            unassigned=len(unassigned),
            violations=len(violations),
            score=result.get("plan_score", 0.0),
        )
        report_lines = []
        if result.get("plan_id"):
            report_lines.append(f"Plan ID: {result.get('plan_id')}")
        for warning in result.get("warnings") or []:
            report_lines.append(f"Uyarı: {warning}")
        for explanation in (result.get("explanations") or [])[:8]:
            report_lines.append(str(explanation))
        self._set_report("\n".join(report_lines) or "Plan raporu için plan üretin veya geçmişten bir plan seçin.")

    def _set_summary(self, **values: Any) -> None:
        for key, label in self.summary_labels.items():
            value = values.get(key, "-")
            if key == "score":
                try:
                    value = f"{float(value):.2f}"
                except (TypeError, ValueError):
                    value = "-"
            label.config(text=str(value))

    def _fill_course_tree(self, tree, rows: list[dict[str, Any]], empty_text: str) -> None:
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
                iid = str(row.get("id"))
                self._run_rows[iid] = int(row.get("id"))
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
            self._load_result(
                {
                    "plan_id": run_id,
                    "plan_score": run.get("plan_score") if run else 0.0,
                    "fall_courses": [a for a in assignments if a.get("assigned_semester") == "fall"],
                    "spring_courses": [a for a in assignments if a.get("assigned_semester") == "spring"],
                    "unassigned_courses": [a for a in assignments if a.get("assigned_semester") == "unassigned"],
                    "constraint_violations": violations,
                    "alternative_plans": scenarios,
                    "warnings": (run or {}).get("warnings", []),
                }
            )
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
