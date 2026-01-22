# app/ui/tabs/view_tab.py
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3


class ViewTab(ttk.Frame):
    """
    📂 Tablo Görüntüle sekmesi.
    - Sol: tablo listesi
    - Sağ: Treeview ile içerik + filtre
    - SQL Runner popup
    """

    def __init__(self, parent, app):
        """
        parent: root içindeki ttk.Notebook
        app: AdilSecmeliApp (root). app.db bekler.
        """
        super().__init__(parent)   # ✅ parent notebook olmalı
        self.app = app
        self.db = app.db

        self.current_table = None

        # --- SOL: Sidebar ---
        self.sidebar = ttk.Frame(self, style="Sidebar.TFrame", width=240)  # ✅ self.frame değil self
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        ttk.Label(self.sidebar, text="Tablolar", style="Sidebar.TLabel") \
            .pack(anchor="w", padx=14, pady=(16, 6))

        self.lst_tables = tk.Listbox(
            self.sidebar,
            bg="#111827", fg="#e5e7eb", highlightthickness=0,
            selectbackground="#334155", activestyle="none"
        )
        self.lst_tables.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.lst_tables.bind("<<ListboxSelect>>", self.on_table_select)

        ttk.Button(
            self.sidebar,
            text="SQL Çalıştır",
            style="Sidebar.TButton",
            command=self.open_sql_runner
        ).pack(fill=tk.X, padx=10, pady=(0, 10))

        # --- SAĞ: İçerik ---
        content_frame = ttk.Frame(self, padding=10)  # ✅ self.frame değil self
        content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        top_view = ttk.Frame(content_frame)
        top_view.pack(fill=tk.X)

        self.search_var = tk.StringVar()
        ttk.Label(top_view, text="Filtre:").pack(side=tk.LEFT)
        ttk.Entry(top_view, textvariable=self.search_var, width=40).pack(side=tk.LEFT, padx=6)
        ttk.Button(top_view, text="Uygula", command=self.apply_filter).pack(side=tk.LEFT)
        ttk.Button(top_view, text="Temizle", command=self.clear_filter).pack(side=tk.LEFT, padx=6)

        self.tree = ttk.Treeview(content_frame, show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self.scroll_x = ttk.Scrollbar(content_frame, orient="horizontal", command=self.tree.xview)
        self.scroll_x.pack(fill=tk.X)
        self.tree.configure(xscrollcommand=self.scroll_x.set)

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
    def refresh(self):
        self.fill_tables()
        self.on_table_select()

    def fill_tables(self):
        self.lst_tables.delete(0, tk.END)

        try:
            tables = self.db.tables()
        except Exception as e:
            messagebox.showerror("DB Hatası", f"Tablolar listelenemedi:\n{e}")
            return

        for t in tables:
            self.lst_tables.insert(tk.END, t)

        if tables:
            self.lst_tables.selection_clear(0, tk.END)
            self.lst_tables.selection_set(0)
            self.current_table = tables[0]

    # ------------------------------------------------------------
    # UI handlers
    # ------------------------------------------------------------
    def on_table_select(self, _evt=None):
        sel = self.lst_tables.curselection()
        if not sel:
            return

        table = self.lst_tables.get(sel[0])
        self.current_table = table

        try:
            cols, rows = self.db.head(table, limit=2000)
            self._populate_tree(cols, rows)
        except Exception as e:
            messagebox.showerror("Hata", f"Tablo okunamadı:\n{e}")

    def _populate_tree(self, cols, rows):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = cols

        for c in cols:
            self.tree.heading(c, text=c, command=lambda col=c: self.sort_by(col, False))
            self.tree.column(c, width=140, anchor="center")

        for r in rows:
            if isinstance(r, sqlite3.Row):
                self.tree.insert("", tk.END, values=[r[c] for c in cols])
            else:
                self.tree.insert("", tk.END, values=list(r))

    def sort_by(self, col, descending: bool):
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children("")]
        try:
            data.sort(key=lambda t: float(t[0]), reverse=descending)
        except Exception:
            data.sort(key=lambda t: t[0], reverse=descending)

        for index, (_, item) in enumerate(data):
            self.tree.move(item, "", index)

        self.tree.heading(col, command=lambda: self.sort_by(col, not descending))

    def clear_filter(self):
        self.search_var.set("")
        self.on_table_select()

    def apply_filter(self):
        if not self.current_table:
            return

        kw = self.search_var.get().strip()
        if not kw:
            self.on_table_select()
            return

        try:
            cols, _ = self.db.head(self.current_table, limit=1)
        except Exception:
            return

        like_cols = " OR ".join([f"CAST({c} AS TEXT) LIKE ?" for c in cols])
        query = f"SELECT * FROM {self.current_table} WHERE {like_cols} LIMIT 2000;"
        params = [f"%{kw}%"] * len(cols)

        try:
            cur = self.db.conn.cursor()
            cur.execute(query, params)
            rows = cur.fetchall()
            cols2 = [d[0] for d in cur.description]
            self._populate_tree(cols2, rows)
        except Exception as e:
            messagebox.showerror("Filtre Hatası", str(e))

    # ------------------------------------------------------------
    # SQL Runner
    # ------------------------------------------------------------
    def open_sql_runner(self):
        win = tk.Toplevel(self)  # ✅ self.frame değil self
        win.title("SQL Çalıştır")
        win.geometry("900x600")

        txt = tk.Text(win, height=10)
        txt.pack(fill=tk.BOTH, expand=False, padx=8, pady=8)
        txt.insert(tk.END, "SELECT name FROM sqlite_master WHERE type='table';")

        frame = ttk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True)

        tree = ttk.Treeview(frame, show="headings")
        tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        sx = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        sx.pack(fill=tk.X)
        tree.configure(xscrollcommand=sx.set)

        def run():
            q = txt.get("1.0", tk.END).strip()
            if not q:
                return

            try:
                cols, rows = self.db.run_sql(q)
                if cols:
                    tree.delete(*tree.get_children())
                    tree["columns"] = cols
                    for c in cols:
                        tree.heading(c, text=c)
                        tree.column(c, width=150, anchor="center")

                    for r in rows:
                        if isinstance(r, sqlite3.Row):
                            tree.insert("", tk.END, values=[r[c] for c in cols])
                        else:
                            tree.insert("", tk.END, values=list(r))
                else:
                    messagebox.showinfo("Tamam", "Sorgu başarıyla çalıştı.")
            except Exception as e:
                messagebox.showerror("SQL Hatası", str(e))

        ttk.Button(win, text="Çalıştır", command=run).pack(pady=(0, 8))
