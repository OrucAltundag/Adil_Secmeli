# -*- coding: utf-8 -*-
# =============================================================================
# app/ui/tabs/view_tab.py — Tablo Goruntuleme / Admin Panel
# =============================================================================
# Veritabanindaki TUM tablolari listeleyip inceleme imkani sunar.
# Sol sidebar: tablo listesi + satir sayilari
# Sag panel: secili tablonun verisi (kolon bazli filtreleme, global arama,
#            siralama, sayfalama)
# SQL Runner: serbest SQL sorgusu calistirma penceresi
# =============================================================================
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import math

from app.core.config import load_app_config
from app.core.permissions import UserContext, can
from app.services.report_table_service import ReportTableService


PAGE_SIZE = 100


class ViewTab(ttk.Frame):
    """
    Admin Panel: Tum tablolari incele.
    - Sol: tablo listesi + satir sayilari
    - Sag: kolon bazli filtreleme, siralama, sayfalama
    - SQL Runner popup
    """

    def __init__(self, parent, app, table_service=None, config=None, user_context=None):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self.config = config or getattr(app, "app_config", None) or load_app_config()
        self.user_context = user_context or getattr(app, "user_context", None) or UserContext.demo_admin(self.config)
        self._table_service_override = table_service

        self.current_table = None
        self._all_rows = []
        self._filtered_rows = []
        self._columns = []
        self._page = 0
        self._sort_col = None
        self._sort_desc = False
        self._col_filters = {}

        self._build_ui()

    def _build_ui(self):
        # --- SOL: Sidebar ---
        sidebar = tk.Frame(self, bg="#0f172a", width=220)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="TABLOLAR", bg="#0f172a", fg="#94a3b8",
                 font=("Segoe UI", 10, "bold"), pady=8).pack(fill=tk.X, padx=8)

        self.lst_tables = tk.Listbox(
            sidebar, bg="#1e293b", fg="#e2e8f0", highlightthickness=0,
            selectbackground="#2563eb", selectforeground="white",
            activestyle="none", font=("Segoe UI", 9), bd=0,
        )
        self.lst_tables.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 4))
        self.lst_tables.bind("<<ListboxSelect>>", self._on_table_select)

        self._lbl_row_count = tk.Label(sidebar, text="", bg="#0f172a", fg="#64748b",
                                       font=("Segoe UI", 8))
        self._lbl_row_count.pack(fill=tk.X, padx=8)

        sql_allowed = self._is_sql_console_allowed()
        sql_button = tk.Button(
            sidebar, text="SQL Calistir", bg="#334155", fg="white",
            font=("Segoe UI", 9), relief="flat", cursor="hand2",
            command=self._open_sql_runner,
            state=(tk.NORMAL if sql_allowed else tk.DISABLED),
        )
        sql_button.pack(fill=tk.X, padx=6, pady=6)
        if not sql_allowed:
            tk.Label(
                sidebar,
                text="SQL Console yalnızca geliştirici/yönetici modunda kullanılabilir.",
                bg="#0f172a",
                fg="#f59e0b",
                font=("Segoe UI", 7),
                wraplength=190,
            ).pack(fill=tk.X, padx=8, pady=(0, 6))

        # --- SAG: Icerik ---
        right = tk.Frame(self, bg="#f8fafc")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Ust: filtre + sayfalama
        toolbar = tk.Frame(right, bg="#e2e8f0", pady=4, padx=6)
        toolbar.pack(fill=tk.X)

        tk.Label(toolbar, text="Genel Ara:", bg="#e2e8f0",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 4))
        self._search_var = tk.StringVar()
        search_entry = tk.Entry(toolbar, textvariable=self._search_var, width=30,
                                font=("Segoe UI", 9))
        search_entry.pack(side=tk.LEFT, padx=(0, 6))
        search_entry.bind("<Return>", lambda e: self._apply_filters())

        tk.Button(toolbar, text="Filtrele", bg="#2563eb", fg="white",
                  font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2",
                  command=self._apply_filters).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="Temizle", bg="#64748b", fg="white",
                  font=("Segoe UI", 8), relief="flat", cursor="hand2",
                  command=self._clear_filters).pack(side=tk.LEFT, padx=2)

        self._lbl_page = tk.Label(toolbar, text="", bg="#e2e8f0",
                                  font=("Segoe UI", 8))
        self._lbl_page.pack(side=tk.RIGHT, padx=4)

        tk.Button(toolbar, text=">>", bg="#475569", fg="white",
                  font=("Segoe UI", 8), relief="flat", width=3,
                  command=lambda: self._change_page(1)).pack(side=tk.RIGHT)
        tk.Button(toolbar, text="<<", bg="#475569", fg="white",
                  font=("Segoe UI", 8), relief="flat", width=3,
                  command=lambda: self._change_page(-1)).pack(side=tk.RIGHT, padx=2)

        # Kolon filtre satirlari
        self._filter_frame = tk.Frame(right, bg="#f1f5f9")
        self._filter_frame.pack(fill=tk.X, padx=2)
        self._filter_entries = {}

        # Treeview
        tree_frame = tk.Frame(right)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0, 2))

        self.tree = ttk.Treeview(tree_frame, show="headings", selectmode="extended")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # Durum cubugu
        self._statusbar = tk.Label(right, text="Tablo secin.",
                                   bg="#e2e8f0", fg="#475569",
                                   font=("Segoe UI", 8), anchor="w", padx=8)
        self._statusbar.pack(fill=tk.X)

    # =========================================================
    #  PUBLIC
    # =========================================================
    def refresh(self):
        self.fill_tables()

    def _service(self):
        if self._table_service_override is not None:
            return self._table_service_override
        conn = getattr(self.db, "conn", None)
        if conn is None:
            raise RuntimeError("Veritabanı bağlantısı yok.")
        return ReportTableService(conn)

    def _is_sql_console_allowed(self) -> bool:
        return can(self.user_context, "use_sql_console", config=self.config)

    def fill_tables(self):
        self.lst_tables.delete(0, tk.END)
        try:
            tables = self._service().list_tables().unwrap()
        except Exception as e:
            messagebox.showerror("DB Hatasi", f"Tablolar listelenemedi:\n{e}")
            return
        for t in tables:
            self.lst_tables.insert(tk.END, t)
        if tables:
            self.lst_tables.selection_clear(0, tk.END)
            self.lst_tables.selection_set(0)
            self.current_table = tables[0]
            self._load_table(tables[0])

    # =========================================================
    #  TABLE LOADING
    # =========================================================
    def _on_table_select(self, _evt=None):
        sel = self.lst_tables.curselection()
        if not sel:
            return
        table = self.lst_tables.get(sel[0])
        self.current_table = table
        self._load_table(table)

    def _load_table(self, table: str):
        """Secilen tabloyu veritabanindan okuyup filtreleme/siralama icin hafizaya alir."""
        self._page = 0
        self._sort_col = None
        self._sort_desc = False
        self._search_var.set("")
        self._col_filters = {}

        try:
            data = self._service().table_head(table, limit=50000).unwrap()
            cols, rows = data["columns"], data["rows"]
        except Exception as e:
            messagebox.showerror("Hata", f"Tablo okunamadi:\n{e}")
            return

        self._columns = list(cols)
        self._all_rows = [list(r) if not isinstance(r, (list, tuple)) else list(r) for r in rows]
        self._filtered_rows = list(self._all_rows)
        self._lbl_row_count.config(text=f"{len(self._all_rows)} satir")

        self._build_column_filters()
        self._setup_tree_columns()
        self._render_page()

    def _setup_tree_columns(self):
        self.tree["columns"] = self._columns
        for c in self._columns:
            self.tree.heading(
                c, text=c,
                command=lambda col=c: self._sort_by(col),
            )
            self.tree.column(c, width=120, anchor="center", minwidth=60)

    def _build_column_filters(self):
        for w in self._filter_frame.winfo_children():
            w.destroy()
        self._filter_entries = {}

        if not self._columns:
            return

        for col in self._columns:
            f = tk.Frame(self._filter_frame, bg="#f1f5f9")
            f.pack(side=tk.LEFT, padx=1, pady=2)
            tk.Label(f, text=col, bg="#f1f5f9", fg="#475569",
                     font=("Segoe UI", 7), width=12, anchor="w").pack(anchor="w")
            var = tk.StringVar()
            e = tk.Entry(f, textvariable=var, width=12, font=("Segoe UI", 7))
            e.pack()
            e.bind("<Return>", lambda ev: self._apply_filters())
            self._filter_entries[col] = var

    # =========================================================
    #  FILTERING + SORTING + PAGINATION
    # =========================================================
    def _apply_filters(self):
        """Global arama ve kolon bazli filtreleri uygulayarak sonuclari gunceller."""
        global_q = self._search_var.get().strip().lower()
        col_queries = {}
        for col, var in self._filter_entries.items():
            v = var.get().strip().lower()
            if v:
                col_queries[col] = v

        result = []
        for row in self._all_rows:
            if global_q:
                if not any(global_q in str(cell).lower() for cell in row):
                    continue
            if col_queries:
                skip = False
                for col, q in col_queries.items():
                    idx = self._columns.index(col) if col in self._columns else -1
                    if idx < 0 or idx >= len(row):
                        continue
                    if q not in str(row[idx]).lower():
                        skip = True
                        break
                if skip:
                    continue
            result.append(row)

        self._filtered_rows = result
        self._page = 0
        self._render_page()

    def _clear_filters(self):
        self._search_var.set("")
        for var in self._filter_entries.values():
            var.set("")
        self._filtered_rows = list(self._all_rows)
        self._page = 0
        self._render_page()

    def _sort_by(self, col: str):
        """Belirtilen kolona gore siralama yapar. Ayni kolona tekrar tiklanirsa yonu tersine cevirir."""
        if self._sort_col == col:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_col = col
            self._sort_desc = False

        idx = self._columns.index(col) if col in self._columns else 0

        def sort_key(row):
            val = row[idx] if idx < len(row) else ""
            if val is None:
                return (1, "")
            try:
                return (0, float(val))
            except (ValueError, TypeError):
                return (0, str(val).lower())

        self._filtered_rows.sort(key=sort_key, reverse=self._sort_desc)
        self._page = 0
        self._render_page()

        arrow = " v" if self._sort_desc else " ^"
        for c in self._columns:
            display = c + (arrow if c == col else "")
            self.tree.heading(c, text=display)

    def _change_page(self, delta: int):
        total_pages = max(1, math.ceil(len(self._filtered_rows) / PAGE_SIZE))
        new_page = self._page + delta
        if 0 <= new_page < total_pages:
            self._page = new_page
            self._render_page()

    def _render_page(self):
        """Filtrelenmis ve siralanmis verinin gecerli sayfasini Treeview'a basar."""
        self.tree.delete(*self.tree.get_children())
        total = len(self._filtered_rows)
        total_pages = max(1, math.ceil(total / PAGE_SIZE))
        start = self._page * PAGE_SIZE
        end = min(start + PAGE_SIZE, total)
        page_rows = self._filtered_rows[start:end]

        for row in page_rows:
            vals = []
            for cell in row:
                if isinstance(cell, float):
                    vals.append(f"{cell:.4f}" if abs(cell) < 1 else f"{cell:.2f}")
                elif cell is None:
                    vals.append("")
                else:
                    vals.append(str(cell))
            self.tree.insert("", tk.END, values=vals)

        self._lbl_page.config(
            text=f"Sayfa {self._page + 1}/{total_pages}  ({total} kayit)"
        )
        self._statusbar.config(
            text=f"{self.current_table or '?'}: {total} kayit gosteriliyor "
                 f"(toplam {len(self._all_rows)})"
        )

    # =========================================================
    #  SQL RUNNER
    # =========================================================
    def _open_sql_runner(self):
        if not self._is_sql_console_allowed():
            messagebox.showwarning(
                "SQL Console",
                "SQL Console yalnızca geliştirici/yönetici modunda kullanılabilir.",
            )
            return
        win = tk.Toplevel(self)
        win.title("SQL Calistir")
        win.geometry("960x600")
        win.configure(bg="#0f172a")

        tk.Label(win, text="SQL Sorgusu:", bg="#0f172a", fg="#94a3b8",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(8, 2))

        txt = tk.Text(win, height=6, bg="#1e293b", fg="#e2e8f0",
                      insertbackground="white", font=("Consolas", 10),
                      relief="flat")
        txt.pack(fill=tk.X, padx=10, pady=(0, 4))
        txt.insert(tk.END, "SELECT name FROM sqlite_master WHERE type='table';")

        btn_frame = tk.Frame(win, bg="#0f172a")
        btn_frame.pack(fill=tk.X, padx=10)
        tk.Button(btn_frame, text="Calistir", bg="#2563eb", fg="white",
                  font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
                  command=lambda: run_sql()).pack(side=tk.LEFT)

        result_lbl = tk.Label(btn_frame, text="", bg="#0f172a", fg="#86efac",
                              font=("Segoe UI", 8))
        result_lbl.pack(side=tk.LEFT, padx=12)

        tree_frame = tk.Frame(win)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 10))

        sql_tree = ttk.Treeview(tree_frame, show="headings")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=sql_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=sql_tree.xview)
        sql_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        sql_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        def run_sql():
            q = txt.get("1.0", tk.END).strip()
            if not q:
                return
            service = self._service()
            if getattr(service, "is_dangerous_sql", lambda _q: False)(q):
                approved = messagebox.askyesno(
                    "SQL Console Uyarısı",
                    "Bu sorgu veriyi veya şemayı değiştirebilir. Devam etmek istiyor musunuz?",
                )
                if not approved:
                    return
            try:
                result = service.run_admin_sql(q, user_id=self.user_context.user_id).unwrap()
                cols, rows = result.get("columns") or [], result.get("rows") or []
                if cols:
                    sql_tree.delete(*sql_tree.get_children())
                    sql_tree["columns"] = cols
                    for c in cols:
                        sql_tree.heading(c, text=c)
                        sql_tree.column(c, width=130, anchor="center")
                    for r in (rows or []):
                        if isinstance(r, sqlite3.Row):
                            sql_tree.insert("", tk.END, values=[r[c] for c in cols])
                        else:
                            sql_tree.insert("", tk.END, values=list(r))
                    result_lbl.config(text=f"{len(rows or [])} satir", fg="#86efac")
                else:
                    result_lbl.config(text="Sorgu basariyla calisti.", fg="#86efac")
            except Exception as e:
                result_lbl.config(text=f"Hata: {e}", fg="#fca5a5")
