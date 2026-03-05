# app/ui/tabs/pool_tab.py
# Havuz Yonetimi sekmesi - Durum Makinesi goruntuleyici

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont


# ---------------------------------------------------------------------------
# Statu sabitleri ve gorsel esleme
# ---------------------------------------------------------------------------
_STATU_ETIKET = {
    1:  "1  (Mufredatta)",
    0:  "0  (Havuzda)",
    -1: "-1 (Dinlenmede - 1 yil)",
    -2: "-2 (Iptal - kalici)",
}

_STATU_TAG = {
    1:  "mufredatta",
    0:  "havuzda",
    -1: "dinlenmede",
    -2: "iptal",
}

_SAYAC_TOOLTIP = {
    0: "Hic dusmedi",
    1: "1 kez mufredattan dustu (bir kez daha duserse iptal)",
    2: "Kalici iptal esigi",
}

# Renk paleti
_RENK = {
    "mufredatta_bg":  "#d4edda",   # acik yesil
    "mufredatta_fg":  "#155724",
    "havuzda_bg":     "#fff9c4",   # acik sari
    "havuzda_fg":     "#1e293b",
    "dinlenmede_bg":  "#ffe0b2",   # acik turuncu
    "dinlenmede_fg":  "#7c2d12",
    "iptal_bg":       "#e0e0e0",   # acik gri
    "iptal_fg":       "#616161",
}


class PoolTab(ttk.Frame):
    """
    Havuz Yonetimi sekmesi:
    - Fakulte / Bolum / Yil filtreleri (2022-2025)
    - Ders havuzu tablosu (statu renklendirme + strikeout iptal)
    - Mufredat tablosu
    - Aciklama / Legend kutusu
    """

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self.db_path = getattr(app, "db_path", None)

        self.hide_resting = False

        # Strikeout font iptal satirlari icin
        self._font_normal    = tkfont.Font(family="Segoe UI", size=9)
        self._font_strikeout = tkfont.Font(family="Segoe UI", size=9, overstrike=True)

        self._build_ui()
        self.after(200, self.refresh)

    # =========================================================
    #  PUBLIC
    # =========================================================
    def refresh(self):
        self.db_path = getattr(self.app, "db_path", self.db_path)
        self.load_faculties_to_combo()
        self.load_pool_data()

    # =========================================================
    #  UI INSASI
    # =========================================================
    def _build_ui(self):
        # --- 1) UST FILTRELER ---
        top = tk.Frame(self, bg="#f1f5f9", pady=8, padx=10)
        top.pack(fill=tk.X)

        tk.Label(top, text="Fakulte:", bg="#f1f5f9",
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=4)
        self.cb_fakulte = ttk.Combobox(top, state="readonly", width=32)
        self.cb_fakulte.pack(side=tk.LEFT, padx=4)
        self.cb_fakulte.bind("<<ComboboxSelected>>", self.on_faculty_change)

        tk.Label(top, text="Bolum:", bg="#f1f5f9",
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(12, 4))
        self.cb_bolum = ttk.Combobox(top, state="readonly", width=24)
        self.cb_bolum.pack(side=tk.LEFT, padx=4)
        self.cb_bolum.bind("<<ComboboxSelected>>", lambda e: self.load_pool_data())

        tk.Label(top, text="Yil:", bg="#f1f5f9",
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(12, 4))
        self.cb_yil = ttk.Combobox(
            top, state="readonly",
            values=["2022", "2023", "2024", "2025"],
            width=8
        )
        self.cb_yil.pack(side=tk.LEFT, padx=4)
        self.cb_yil.current(0)
        self.cb_yil.bind("<<ComboboxSelected>>", lambda e: self.load_pool_data())

        tk.Label(top, text="Donem:", bg="#f1f5f9",
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(12, 4))
        self.cb_donem = ttk.Combobox(top, state="readonly", values=["Güz", "Bahar"], width=8)
        self.cb_donem.pack(side=tk.LEFT, padx=4)
        self.cb_donem.current(0)
        self.cb_donem.bind("<<ComboboxSelected>>", lambda e: self.load_pool_data())

        ttk.Button(top, text="Getir", command=self.load_pool_data).pack(
            side=tk.LEFT, padx=14)

        # --- 2) AKSIYONLAR ---
        actions = tk.Frame(self, bg="#e2e8f0", pady=5, padx=8)
        actions.pack(fill=tk.X)

        self.btn_toggle = tk.Button(
            actions, text="Dinlenmedekileri Gizle",
            bg="#fca5a5", font=("Segoe UI", 8),
            command=self.toggle_resting_courses
        )
        self.btn_toggle.pack(side=tk.LEFT, padx=5)

        ttk.Button(actions, text="Secileni Dinlenmeye Al (-1)",
                   command=lambda: self.set_selected_pool_status(-1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions, text="Secileni Havuzda Yap (0)",
                   command=lambda: self.set_selected_pool_status(0)).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions, text="Secileni Kalici Iptal (-2)",
                   command=lambda: self.set_selected_pool_status(-2)).pack(side=tk.LEFT, padx=5)

        ttk.Button(actions, text="Algoritmay Calistir",
                   command=self.run_decision_engine).pack(side=tk.RIGHT, padx=5)

        # --- 3) LEGEND (Aciklama Kutusu) ---
        self._build_legend()

        # --- 4) SPLIT VIEW ---
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=5, bg="#cbd5e1")
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=4)

        # SOL: HAVUZ
        left = tk.Frame(paned, bg="white")
        paned.add(left, width=800)
        tk.Label(left, text="DERS HAVUZU",
                 bg="#dbeafe", font=("Segoe UI", 10, "bold")).pack(fill=tk.X)

        self._build_pool_tree(left)

        # SAG: MUFREDAT
        right = tk.Frame(paned, bg="white")
        paned.add(right)
        tk.Label(right, text="MUFREDAT",
                 bg="#dcfce7", font=("Segoe UI", 10, "bold")).pack(fill=tk.X)

        self._build_curr_tree(right)

        tk.Button(
            right, text="Ornek Ogrenci Secimi Baslat",
            bg="#22c55e", fg="white", font=("Segoe UI", 9, "bold"),
            command=self.open_student_simulation
        ).pack(fill=tk.X, pady=4, padx=4)

    def _build_legend(self):
        """Durum kodlari ve sayac mantigini gosteren aciklama kutusu."""
        legend = tk.LabelFrame(
            self, text="  Durum Aciklamasi  ",
            bg="#f8fafc", font=("Segoe UI", 8, "bold"),
            fg="#475569", pady=4, padx=8
        )
        legend.pack(fill=tk.X, padx=6, pady=(2, 0))

        items = [
            (_RENK["mufredatta_bg"],  _RENK["mufredatta_fg"],
             "statu= 1  | Mufredatta      : Ders o yil aktif mufredatta."),
            (_RENK["havuzda_bg"],     _RENK["havuzda_fg"],
             "statu= 0  | Havuzda         : Mufredattan disarda, aday."),
            (_RENK["dinlenmede_bg"],  _RENK["dinlenmede_fg"],
             "statu=-1  | Dinlenmede      : Mufredattan yeni dustu, 1 yil secilemeez."),
            (_RENK["iptal_bg"],       _RENK["iptal_fg"],
             "statu=-2  | Kalici Iptal    : 2 kez dustugu icin sistemden cikarildi."),
        ]

        for bg, fg, metin in items:
            tk.Label(
                legend, text=metin,
                bg=bg, fg=fg,
                font=("Consolas", 8),
                anchor="w", padx=6, pady=1,
                relief="flat"
            ).pack(fill=tk.X, pady=1)

        tk.Label(
            legend,
            text="Sayac: 0=Hic dusmedi | 1=1 kez dustu (1 hak kaldi) | 2=Kalici iptal",
            bg="#f1f5f9", fg="#64748b",
            font=("Segoe UI", 8, "italic"),
            anchor="w", padx=6
        ).pack(fill=tk.X, pady=(2, 0))

    def _build_pool_tree(self, parent):
        cols = ("ders_id", "ders_adi", "statu_etiket", "sayac", "skor", "yil")
        self.tree_pool = ttk.Treeview(
            parent, columns=cols, show="headings", selectmode="extended"
        )

        self.tree_pool.heading("ders_id",      text="ID")
        self.tree_pool.heading("ders_adi",     text="Ders Adi")
        self.tree_pool.heading("statu_etiket", text="Durum")
        self.tree_pool.heading("sayac",        text="Sayac")
        self.tree_pool.heading("skor",         text="Kesinesme Puani")
        self.tree_pool.heading("yil",          text="Yil")

        self.tree_pool.column("ders_id",      width=45,  anchor="center")
        self.tree_pool.column("ders_adi",     width=310)
        self.tree_pool.column("statu_etiket", width=175, anchor="center")
        self.tree_pool.column("sayac",        width=55,  anchor="center")
        self.tree_pool.column("skor",         width=110, anchor="center")
        self.tree_pool.column("yil",          width=50,  anchor="center")

        # Renk etiketleri — normal satirlar
        self.tree_pool.tag_configure(
            "mufredatta",
            background=_RENK["mufredatta_bg"],
            foreground=_RENK["mufredatta_fg"],
            font=self._font_normal,
        )
        self.tree_pool.tag_configure(
            "havuzda",
            background=_RENK["havuzda_bg"],
            foreground=_RENK["havuzda_fg"],
            font=self._font_normal,
        )
        self.tree_pool.tag_configure(
            "dinlenmede",
            background=_RENK["dinlenmede_bg"],
            foreground=_RENK["dinlenmede_fg"],
            font=self._font_normal,
        )
        # Iptal: gri arka plan + strikeout font
        self.tree_pool.tag_configure(
            "iptal",
            background=_RENK["iptal_bg"],
            foreground=_RENK["iptal_fg"],
            font=self._font_strikeout,
        )

        sb = ttk.Scrollbar(parent, orient="vertical", command=self.tree_pool.yview)
        self.tree_pool.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_pool.pack(fill=tk.BOTH, expand=True)

        # Sayac icin tooltip
        self.tree_pool.bind("<Motion>", self._on_pool_tree_motion)
        self._tooltip_win = None

    def _build_curr_tree(self, parent):
        cols = ("ders_id", "ders_adi", "skor")
        self.tree_curr = ttk.Treeview(parent, columns=cols, show="headings")
        self.tree_curr.heading("ders_id",  text="ID")
        self.tree_curr.heading("ders_adi", text="Ders Adi")
        self.tree_curr.heading("skor",     text="Kesinesme Puani")
        self.tree_curr.column("ders_id",  width=45,  anchor="center")
        self.tree_curr.column("ders_adi", width=260)
        self.tree_curr.column("skor",     width=100, anchor="center")
        self.tree_curr.pack(fill=tk.BOTH, expand=True)

    # =========================================================
    #  TOOLTIP (Sayac icin)
    # =========================================================
    def _on_pool_tree_motion(self, event):
        item = self.tree_pool.identify_row(event.y)
        if not item:
            self._hide_tooltip()
            return
        vals = self.tree_pool.item(item, "values")
        if len(vals) < 4:
            self._hide_tooltip()
            return
        try:
            sayac = int(vals[3])
        except (ValueError, TypeError):
            self._hide_tooltip()
            return
        metin = _SAYAC_TOOLTIP.get(sayac, f"Dusme sayaci: {sayac}")
        self._show_tooltip(event, metin)

    def _show_tooltip(self, event, metin: str):
        self._hide_tooltip()
        x = self.winfo_rootx() + event.x + 14
        y = self.winfo_rooty() + event.y + 14
        self._tooltip_win = tw = tk.Toplevel(self)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tw, text=metin,
            bg="#fffde7", fg="#1e293b",
            font=("Segoe UI", 8),
            relief="solid", bd=1, padx=6, pady=3
        ).pack()

    def _hide_tooltip(self):
        if self._tooltip_win:
            try:
                self._tooltip_win.destroy()
            except Exception:
                pass
            self._tooltip_win = None

    # =========================================================
    #  DATA LOADERS
    # =========================================================
    def load_faculties_to_combo(self):
        try:
            _, rows = self.db.run_sql("SELECT ad FROM fakulte ORDER BY ad")
            faculties = [r[0] for r in (rows or [])]
            self.cb_fakulte["values"] = faculties
            if faculties and self.cb_fakulte.current() < 0:
                self.cb_fakulte.current(0)

            # Yıl listesini havuz tablosundan dinamik çek; varsayılan 2022-2025
            try:
                _, yil_rows = self.db.run_sql(
                    "SELECT DISTINCT yil FROM havuz WHERE yil BETWEEN 2022 AND 2025 ORDER BY yil"
                )
                if yil_rows:
                    yillar = [str(r[0]) for r in yil_rows]
                    self.cb_yil["values"] = yillar
                    if self.cb_yil.get() not in yillar:
                        self.cb_yil.current(0)
            except Exception:
                pass

            if faculties:
                self.on_faculty_change(None)
        except Exception:
            pass

    def on_faculty_change(self, _event):
        fakulte = self.cb_fakulte.get()
        if not fakulte:
            return
        try:
            _, rows = self.db.run_sql(
                "SELECT fakulte_id FROM fakulte WHERE ad = ?", (fakulte,)
            )
            if not rows:
                return
            fid = int(rows[0][0])
            _, rows_b = self.db.run_sql(
                "SELECT ad FROM bolum WHERE fakulte_id = ? ORDER BY ad", (fid,)
            )
            bolumler = [r[0] for r in (rows_b or [])]
            self.cb_bolum["values"] = bolumler
            if bolumler and self.cb_bolum.current() < 0:
                self.cb_bolum.current(0)
            self.load_pool_data()
        except Exception:
            pass

    def toggle_resting_courses(self):
        self.hide_resting = not self.hide_resting
        if self.hide_resting:
            self.btn_toggle.config(text="Dinlenmedekileri Goster", bg="#86efac")
        else:
            self.btn_toggle.config(text="Dinlenmedekileri Gizle",  bg="#fca5a5")
        self.load_pool_data()

    def load_pool_data(self):
        fakulte = self.cb_fakulte.get()
        bolum   = self.cb_bolum.get()
        yil     = self.cb_yil.get()

        if not fakulte or not yil:
            return

        # --- SOL: HAVUZ ---
        self.tree_pool.delete(*self.tree_pool.get_children())

        extra_where = "AND h.statu NOT IN (-1, -2)" if self.hide_resting else ""

        q_pool = f"""
            SELECT DISTINCT
                h.ders_id, d.ad, h.statu, h.sayac, h.skor, h.yil
            FROM havuz h
            JOIN ders d ON h.ders_id = d.ders_id
            JOIN fakulte f ON h.fakulte_id = f.fakulte_id
            WHERE f.ad LIKE ?
              AND h.yil = ?
              {extra_where}
            ORDER BY h.statu DESC, h.skor DESC
        """
        try:
            _, rows = self.db.run_sql(q_pool, (f"%{fakulte}%", int(yil)))
            seen = set()
            for d_id, d_ad, statu, sayac, skor, y in (rows or []):
                if d_id in seen:
                    continue
                seen.add(d_id)

                s_val = int(statu) if statu is not None else 0
                tag   = _STATU_TAG.get(s_val, "havuzda")
                etkt  = _STATU_ETIKET.get(s_val, f"{s_val}")

                skor_txt  = f"{float(skor):.2f}" if skor is not None else "0.00"
                sayac_val = int(sayac) if sayac is not None else 0

                self.tree_pool.insert(
                    "", tk.END,
                    values=(d_id, d_ad, etkt, sayac_val, skor_txt, y),
                    tags=(tag,)
                )
        except Exception as e:
            print(f"UI Hata (Havuz): {e}")

        # --- SAG: MUFREDAT ---
        self.tree_curr.delete(*self.tree_curr.get_children())
        if not bolum:
            return

        donem = getattr(self, "cb_donem", None) and self.cb_donem.get() or "Güz"
        donem_norm = str(donem).strip() or "Güz"

        q_curr = """
            SELECT DISTINCT d.ders_id, d.ad, h.skor
            FROM mufredat m
            JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
            JOIN ders d ON md.ders_id = d.ders_id
            JOIN bolum b ON m.bolum_id = b.bolum_id
            LEFT JOIN havuz h ON (h.ders_id = d.ders_id AND h.yil = m.akademik_yil)
            WHERE m.akademik_yil = ? AND b.ad LIKE ?
              AND (LOWER(COALESCE(m.donem,'Güz')) = LOWER(?))
            ORDER BY d.ad
        """
        try:
            _, rows_r = self.db.run_sql(q_curr, (int(yil), f"%{bolum}%", donem_norm))
            seen_r = set()
            for d_id, d_ad, skor in (rows_r or []):
                if d_id in seen_r:
                    continue
                seen_r.add(d_id)
                skor_txt = f"{float(skor):.2f}" if skor is not None else "---"
                self.tree_curr.insert("", tk.END, values=(d_id, d_ad, skor_txt))
        except Exception as e:
            print(f"UI Hata (Mufredat): {e}")

    # =========================================================
    #  AKSIYONLAR
    # =========================================================
    def _selected_pool_items(self):
        items = self.tree_pool.selection()
        return [self.tree_pool.item(it)["values"] for it in items if self.tree_pool.item(it)["values"]]

    def set_selected_pool_status(self, new_status: int):
        selected = self._selected_pool_items()
        if not selected:
            messagebox.showinfo("Bilgi", "Oncelikle havuzdan ders secin.")
            return
        yil = self.cb_yil.get()
        if not yil:
            return
        try:
            for vals in selected:
                ders_id = int(vals[0])
                self.db.run_sql(
                    "UPDATE havuz SET statu = ? WHERE ders_id = ? AND yil = ?",
                    (int(new_status), ders_id, int(yil))
                )
            self.load_pool_data()
        except Exception as e:
            messagebox.showerror("Guncelleme Hatasi", str(e))

    def run_decision_engine(self):
        messagebox.showinfo(
            "Bilgi",
            "Lutfen 'Hesaplama & Test' sekmesinden 'Otomatik Puanlama' butonunu kullanin."
        )

    # =========================================================
    #  SIMULASYON
    # =========================================================
    def open_student_simulation(self):
        curr_items = self.tree_curr.get_children()
        if not curr_items:
            messagebox.showwarning("Uyari", "Mufredatta ders yok! Once algoritmay calistirin.")
            return

        sim_win = tk.Toplevel(self)
        sim_win.title(f"Ogrenci Ders Secim Ekrani - {self.cb_yil.get()} Guz Donemi")
        sim_win.geometry("620x520")
        sim_win.configure(bg="#f8fafc")

        tk.Label(
            sim_win,
            text=f"{self.cb_yil.get()} GUZ DONEMI DERS SECIMI",
            font=("Segoe UI", 14, "bold"), bg="#f8fafc", fg="#1e293b"
        ).pack(pady=14)

        tk.Label(
            sim_win,
            text="Mufredat Komisyonu tarafindan onaylanan dersler asagidadir.\n"
                 "Almak istediklerinizi isaretleyiniz.",
            bg="#f8fafc"
        ).pack(pady=(0, 8))

        check_frame = tk.Frame(sim_win, bg="white", relief="groove", bd=1)
        check_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=8)

        vars_list = []
        for item in curr_items:
            d_id, d_ad, skor = self.tree_curr.item(item)["values"]
            var = tk.IntVar()
            tk.Checkbutton(
                check_frame, text=f"{d_ad}  (Puan: {skor})",
                variable=var, bg="white",
                font=("Segoe UI", 10), anchor="w", padx=10, pady=4
            ).pack(fill=tk.X)
            vars_list.append((d_ad, var))

        def save_selection():
            secilen = [n for n, v in vars_list if v.get() == 1]
            if not secilen:
                messagebox.showwarning("Uyari", "Hic ders secmediniz!")
                return
            msg = "Secilen Dersler:\n\n" + "\n".join(f"  + {s}" for s in secilen)
            msg += "\n\nKaydiniz tamamlandi!"
            messagebox.showinfo("Onay", msg)
            sim_win.destroy()

        tk.Button(
            sim_win, text="Secimi Onayla ve Kaydet",
            bg="#22c55e", fg="white", font=("Segoe UI", 10, "bold"),
            command=save_selection
        ).pack(pady=18, ipadx=10)
