# app/ui/tabs/relations_tab.py
import tkinter as tk
from tkinter import ttk, messagebox

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class RelationsTab(ttk.Frame):
    """
    🔗 Ders İlişkileri & Kurallar sekmesi:
    - Fakülte seç
    - Ders listesi
    - NLP benzerlik (SimilarityEngine) çalıştır
    - Top10 skor tablosu + network graph
    """

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self.db_path = getattr(app, "db_path", None)

        self.course_map = {}  # listbox index -> ders_id
        self._build_ui()

    def refresh(self):
        """Sekmeye gelince/yenile basılınca çağır."""
        self.db_path = getattr(self.app, "db_path", self.db_path)

        try:
            fakulteler = [r[0] for r in (self.db.run_sql("SELECT ad FROM fakulte")[1] or [])]
            self.cb_fakulte["values"] = fakulteler
            if fakulteler and self.cb_fakulte.current() < 0:
                self.cb_fakulte.current(0)
        except Exception:
            pass

    # ---------------- UI ----------------
    def _build_ui(self):
        # Üst filtre
        top_frame = tk.Frame(self, bg="#e2e8f0", pady=5)
        top_frame.pack(fill=tk.X)

        tk.Label(top_frame, text="Fakülte:", bg="#e2e8f0").pack(side=tk.LEFT, padx=5)
        self.cb_fakulte = ttk.Combobox(top_frame, state="readonly", width=30)
        self.cb_fakulte.pack(side=tk.LEFT, padx=5)

        tk.Button(top_frame, text="Listele", command=self.load_courses_for_relations).pack(side=tk.LEFT, padx=10)

        # fakülteleri doldur
        try:
            fakulteler = [r[0] for r in (self.db.run_sql("SELECT ad FROM fakulte")[1] or [])]
        except Exception:
            fakulteler = []
        self.cb_fakulte["values"] = fakulteler
        if fakulteler:
            self.cb_fakulte.current(0)

        # split layout
        main_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#f1f5f9")
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Sol: Ders listesi
        left_frame = tk.Frame(main_pane, bg="white", width=250)
        main_pane.add(left_frame, width=260)
        tk.Label(left_frame, text="Ders Listesi", font=("Segoe UI", 10, "bold"), bg="white").pack(pady=5)

        self.lst_rel_courses = tk.Listbox(left_frame, bg="#f8fafc", selectbackground="#3b82f6")
        self.lst_rel_courses.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.lst_rel_courses.bind("<<ListboxSelect>>", self.on_rel_course_select)

        # Orta: Grafik
        center_frame = tk.Frame(main_pane, bg="white")
        main_pane.add(center_frame)
        main_pane.paneconfig(center_frame, stretch="always")

        tk.Label(
            center_frame,
            text="İlişki Ağı (NLP Benzerlik Analizi)",
            font=("Segoe UI", 10, "bold"),
            bg="white"
        ).pack(pady=5)

        self.rel_fig = Figure(figsize=(5, 4), dpi=100)
        self.rel_canvas = FigureCanvasTkAgg(self.rel_fig, master=center_frame)
        self.rel_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Sağ: Skor tablosu
        right_frame = tk.Frame(main_pane, bg="white", width=260)
        main_pane.add(right_frame, width=260)

        tk.Label(right_frame, text="İlişki Puanları (Top 10)", font=("Segoe UI", 10, "bold"), bg="white").pack(pady=5)

        self.tree_scores = ttk.Treeview(right_frame, columns=("ders", "skor"), show="headings")
        self.tree_scores.heading("ders", text="Benzer Ders")
        self.tree_scores.heading("skor", text="Puan")
        self.tree_scores.column("ders", width=160)
        self.tree_scores.column("skor", width=70, anchor="center")
        self.tree_scores.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    # ---------------- Data ----------------
    def load_courses_for_relations(self):
        fakulte = self.cb_fakulte.get()
        if not fakulte:
            return

        query = f"""
            SELECT DISTINCT d.ders_id, d.ad
            FROM ders d
            JOIN fakulte f ON d.fakulte_id = f.fakulte_id
            WHERE f.ad = '{fakulte}'
            ORDER BY d.ad
        """
        try:
            _, rows = self.db.run_sql(query)
        except Exception:
            rows = []

        self.lst_rel_courses.delete(0, tk.END)
        self.course_map = {}

        for idx, row in enumerate(rows or []):
            self.lst_rel_courses.insert(tk.END, row[1])
            self.course_map[idx] = row[0]

    def on_rel_course_select(self, _event):
        sel = self.lst_rel_courses.curselection()
        if not sel:
            return

        # networkx kontrol
        try:
            import networkx as nx
        except Exception:
            messagebox.showwarning("Eksik Paket", "networkx yüklü değil. (pip install networkx)")
            return

        course_id = self.course_map.get(sel[0])
        if course_id is None:
            return

        # SimilarityEngine çalıştır
        try:
            from app.services.similarity_engine import SimilarityEngine
            engine = SimilarityEngine(self.db_path)
            engine.compute_and_save(course_id, top_n=10)
        except Exception as e:
            messagebox.showerror("Benzerlik Hatası", str(e))
            return

        # Skorları çek
        query = f"""
            SELECT d.ad, di.skor
            FROM ders_iliski di
            JOIN ders d ON d.ders_id = di.hedef_ders_id
            WHERE di.kaynak_ders_id = {course_id}
            ORDER BY di.skor DESC
            LIMIT 10
        """
        rows = (self.db.run_sql(query)[1] or [])

        # Sağ tabloyu doldur
        self.tree_scores.delete(*self.tree_scores.get_children())
        for ad, skor in rows:
            self.tree_scores.insert("", tk.END, values=(ad, f"%{float(skor)*100:.1f}"))

        if not rows:
            # grafiği de temizleyelim
            self.rel_fig.clear()
            self.rel_canvas.draw()
            return

        # Grafik çiz
        self.rel_fig.clear()
        ax = self.rel_fig.add_subplot(111)

        G = nx.Graph()
        center_name = self.lst_rel_courses.get(sel[0])
        G.add_node(center_name)

        for ders_adi, skor in rows:
            G.add_node(ders_adi)
            G.add_edge(center_name, ders_adi, weight=float(skor))

        pos = nx.spring_layout(G, k=0.7, center=(0, 0))

        nx.draw_networkx_nodes(G, pos, node_color="#3b82f6", node_size=1800, ax=ax)
        nx.draw_networkx_labels(G, pos, font_size=8, font_color="white", ax=ax)

        weights = [G[u][v]["weight"] * 8 for u, v in G.edges()]
        nx.draw_networkx_edges(G, pos, width=weights, edge_color="#94a3b8", ax=ax)

        ax.set_title(f"'{center_name}' için Ders Benzerlik Ağı")
        ax.axis("off")
        self.rel_canvas.draw()
