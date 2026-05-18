# -*- coding: utf-8 -*-
"""Dönem Planlama Tkinter paneli."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.services.semester_planning_engine import (
    generate_semester_plan,
    get_plan_run,
    list_plan_runs,
)
from app.services.semester_planning_policy_service import (
    seed_default_policy,
)
from app.services.semester_planning_reporting_service import (
    compare_plan_scenarios,
    get_constraint_violations,
    get_semester_plan_assignments,
)


class SemesterPlanningPage(ttk.Frame):
    """Policy tabanli Güz/Bahar dönem planlama ekranı."""

    def __init__(self, parent, app=None):
        super().__init__(parent)
        self.app = app
        self._run_rows: dict[str, int] = {}
        self._build_ui()

    def _conn(self):
        conn = getattr(getattr(self.app, "db", None), "conn", None)
        if conn is None:
            raise RuntimeError(self._friendly_backend_error())
        return conn

    @staticmethod
    def _friendly_backend_error() -> str:
        return "Sistem şu an meşgul, daha sonra tekrar deneyin."

    def _build_ui(self):
        header = ttk.Frame(self, padding=8)
        header.pack(fill=tk.X)
        ttk.Label(header, text="Dönem Planlama", style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Button(header, text="Yenile", command=self.refresh).pack(side=tk.RIGHT)

        filters = ttk.LabelFrame(self, text="Politika ve Plan Parametreleri", padding=8)
        filters.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.var_year = tk.StringVar(value="2026")
        self.var_faculty = tk.StringVar()
        self.var_department = tk.StringVar()
        for label, var, width in [
            ("Yıl", self.var_year, 8),
            ("Fakülte ID", self.var_faculty, 10),
            ("Bölüm ID", self.var_department, 10),
        ]:
            ttk.Label(filters, text=label).pack(side=tk.LEFT, padx=(0, 4))
            ttk.Entry(filters, textvariable=var, width=width).pack(side=tk.LEFT, padx=(0, 8))
        self.btn_generate_plan = ttk.Button(filters, text="Plan Üret", command=self.generate_plan)
        self.btn_generate_plan.pack(side=tk.LEFT, padx=4)
        self.btn_generate_alternatives = ttk.Button(filters, text="Alternatifleri Üret", command=self.generate_plan)
        self.btn_generate_alternatives.pack(side=tk.LEFT, padx=4)

        self.policy_text = tk.Text(filters, height=3, width=70)
        self.policy_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))
        self._build_plan_tab()
        self._build_violations_tab()
        self._build_scenarios_tab()
        self._build_runs_tab()

    def _build_plan_tab(self):
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Güz/Bahar Planı")
        panes = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True)
        self.fall_tree = self._make_tree(panes, "Güz", ("code", "name", "score", "demand", "capacity", "explanation"))
        self.spring_tree = self._make_tree(panes, "Bahar", ("code", "name", "score", "demand", "capacity", "explanation"))

    def _build_violations_tab(self):
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Kısıt İhlalleri")
        self.violation_tree = ttk.Treeview(frame, columns=("type", "course", "severity", "message", "suggestion"), show="headings")
        for col, text in {
            "type": "Kısıt",
            "course": "Ders",
            "severity": "Seviye",
            "message": "Mesaj",
            "suggestion": "Öneri",
        }.items():
            self.violation_tree.heading(col, text=text)
            self.violation_tree.column(col, width=150)
        self.violation_tree.pack(fill=tk.BOTH, expand=True)

    def _build_scenarios_tab(self):
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Alternatif Planlar")
        self.scenario_tree = ttk.Treeview(frame, columns=("name", "type", "score", "fall", "spring", "violations"), show="headings")
        for col, text in {
            "name": "Senaryo",
            "type": "Tip",
            "score": "Plan Skoru",
            "fall": "Güz",
            "spring": "Bahar",
            "violations": "İhlal",
        }.items():
            self.scenario_tree.heading(col, text=text)
            self.scenario_tree.column(col, width=130)
        self.scenario_tree.pack(fill=tk.BOTH, expand=True)

    def _build_runs_tab(self):
        frame = ttk.Frame(self.nb, padding=8)
        self.nb.add(frame, text="Plan Geçmişi")
        self.run_tree = ttk.Treeview(frame, columns=("id", "year", "faculty", "department", "fall", "spring", "score", "status"), show="headings")
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
            self.run_tree.column(col, width=90)
        self.run_tree.pack(fill=tk.BOTH, expand=True)
        self.run_tree.bind("<<TreeviewSelect>>", lambda _e: self.load_selected_run())

    def _make_tree(self, parent, title, columns):
        box = ttk.LabelFrame(parent, text=title, padding=6)
        parent.add(box, weight=1)
        tree = ttk.Treeview(box, columns=columns, show="headings")
        headings = {
            "code": "Ders Kodu",
            "name": "Ders Adı",
            "score": "Skor",
            "demand": "Talep",
            "capacity": "Kontenjan",
            "explanation": "Açıklama",
        }
        for col in columns:
            tree.heading(col, text=headings.get(col, col))
            tree.column(col, width=120)
        tree.pack(fill=tk.BOTH, expand=True)
        return tree

    def _int_or_none(self, value):
        text = str(value or "").strip()
        return int(text) if text else None

    def refresh(self):
        try:
            conn = self._conn()
            policy = seed_default_policy(conn)
            conn.commit()
            self.policy_text.delete("1.0", tk.END)
            self.policy_text.insert(
                tk.END,
                f"Aktif policy: {policy.get('name')} | hedef {policy.get('total_elective_target')} | "
                f"Güz {policy.get('fall_min')}-{policy.get('fall_max')} | Bahar {policy.get('spring_min')}-{policy.get('spring_max')}",
            )
            self._load_runs()
        except Exception:
            messagebox.showerror("Dönem Planlama", self._friendly_backend_error())

    def generate_plan(self):
        try:
            int(self.var_year.get() or 0)
        except ValueError:
            messagebox.showwarning("Dönem Planlama", "Plan üretmek için geçerli bir yıl giriniz.")
            return
        try:
            conn = self._conn()
            result = generate_semester_plan(
                conn,
                year=int(self.var_year.get() or 0),
                faculty_id=self._int_or_none(self.var_faculty.get()),
                department_id=self._int_or_none(self.var_department.get()),
                persist=True,
                generate_alternatives=True,
            )
            conn.commit()
            self._load_result(result)
            self._load_runs()
            messagebox.showinfo("Dönem Planlama", "Dönem planı üretildi.")
        except Exception:
            messagebox.showerror("Dönem Planlama", self._friendly_backend_error())

    def _load_result(self, result):
        self._fill_course_tree(self.fall_tree, result.get("fall_courses", []))
        self._fill_course_tree(self.spring_tree, result.get("spring_courses", []))
        self._fill_violations(result.get("constraint_violations", []))
        self._fill_scenarios(result.get("alternative_plans", []))

    def _fill_course_tree(self, tree, rows):
        tree.delete(*tree.get_children())
        for row in rows:
            tree.insert(
                "",
                tk.END,
                values=(
                    row.get("course_code") or row.get("course_id"),
                    row.get("course_name") or "",
                    round(float(row.get("course_score") or 0.0), 2),
                    round(float(row.get("expected_demand") or 0.0), 2),
                    round(float(row.get("expected_capacity") or 0.0), 2),
                    row.get("explanation") or "",
                ),
            )

    def _fill_violations(self, rows):
        self.violation_tree.delete(*self.violation_tree.get_children())
        for row in rows:
            self.violation_tree.insert("", tk.END, values=(row.get("constraint_type"), row.get("course_id"), row.get("severity"), row.get("message"), row.get("suggestion")))

    def _fill_scenarios(self, rows):
        self.scenario_tree.delete(*self.scenario_tree.get_children())
        for row in rows:
            self.scenario_tree.insert(
                "",
                tk.END,
                values=(
                    row.get("scenario_name"),
                    row.get("scenario_type"),
                    round(float(row.get("plan_score") or 0.0), 2),
                    len(row.get("fall_courses") or []),
                    len(row.get("spring_courses") or []),
                    len(row.get("constraint_violations") or []),
                ),
            )

    def _load_runs(self):
        self.run_tree.delete(*self.run_tree.get_children())
        self._run_rows.clear()
        conn = self._conn()
        rows = list_plan_runs(conn, year=self._int_or_none(self.var_year.get()))
        for row in rows:
            iid = str(row.get("id"))
            self._run_rows[iid] = int(row.get("id"))
            self.run_tree.insert(
                "",
                tk.END,
                iid=iid,
                values=(row.get("id"), row.get("year"), row.get("faculty_id"), row.get("department_id"), row.get("fall_count"), row.get("spring_count"), row.get("plan_score"), row.get("status")),
            )

    def load_selected_run(self):
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
            self._load_result(
                {
                    "fall_courses": [a for a in assignments if a.get("assigned_semester") == "fall"],
                    "spring_courses": [a for a in assignments if a.get("assigned_semester") == "spring"],
                    "constraint_violations": violations,
                    "alternative_plans": scenarios,
                }
            )
            if run:
                self.policy_text.delete("1.0", tk.END)
                self.policy_text.insert(tk.END, f"Seçili run: {run.get('run_name')} | skor {run.get('plan_score')} | durum {run.get('status')}")
        except Exception:
            messagebox.showerror("Dönem Planlama", self._friendly_backend_error())
