# -*- coding: utf-8 -*-
# app/ui/tabs/course_analysis_tab.py
"""
Ders Analiz Laboratuvari sekmesi.

Yapi:
  - Ust: yil + fakulte + ders secimi + "Analizi Baslar" butonu
  - Sol : Kayitli Kriterler (read-only tablo)
  - Orta: Algoritma Adimlari (AHP, Trend, TOPSIS, RF, DT)
  - Sag : Nihai Karar (devasa statu + aciklama)

Hesaplama arka planda threading.Thread ile calisir; sonuc after() ile UI'a basılır.
"""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from app.services.course_analyzer import analyze_single_course

# ---------------------------------------------------------------------------
# Renk paleti
# ---------------------------------------------------------------------------
_STATU_COLORS = {
    1:  {"bg": "#d4edda", "fg": "#155724"},   # yesil
    0:  {"bg": "#fff9c4", "fg": "#856404"},   # sari
    -1: {"bg": "#ffe0b2", "fg": "#7c2d12"},   # turuncu
    -2: {"bg": "#e0e0e0", "fg": "#616161"},   # gri
}
_DEFAULT_COLOR = {"bg": "#f1f5f9", "fg": "#1e293b"}

_STATU_LABELS = {
    1:  "1 — Mufredatta",
    0:  "0 — Havuzda",
    -1: "-1 — Dinlenmede (1 yil)",
    -2: "-2 — Kalici Iptal",
}

_SAYAC_TIPS = {
    0: "Hic dusmedi",
    1: "1 kez dustu — bir kez daha duserse iptal",
    2: "Kalici iptal esigi",
}


# ---------------------------------------------------------------------------
# Tooltip yardimci
# ---------------------------------------------------------------------------
class _Tooltip:
    def __init__(self, widget, text: str):
        self._win = None
        widget.bind("<Enter>", lambda _: self._show(widget, text))
        widget.bind("<Leave>", lambda _: self._hide())

    def _show(self, w, text):
        self._hide()
        x = w.winfo_rootx() + 20
        y = w.winfo_rooty() + w.winfo_height() + 4
        self._win = tw = tk.Toplevel(w)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=text, bg="#fffde7", fg="#1e293b",
                 font=("Segoe UI", 8), relief="solid", bd=1, padx=6, pady=3).pack()

    def _hide(self):
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass
            self._win = None


class _SearchableCombo(tk.Frame):
    """
    Aranabilir ders secim widget'i.

    Iki modda calisir:
      - GORUNTULEME MODU: Secili ders gosterilir, ok butonuyla liste acilir.
      - ARAMA MODU: Entry'ye odaklaninca veya ok'a tiklaninca acilir,
        yazdikca listbox filtrelenir. Secim yapilinca goruntuleme moduna doner.

    Popup her zaman entry'nin hemen altinda, guncel pozisyonda acilir.
    Scrollbar ile tum liste gezilir, son secilenler ustte gosterilir.
    """

    def __init__(self, parent, width=38, **kw):
        super().__init__(parent, **kw)
        self._all_values = []       # Tum secenekler
        self._selected_value = ""   # Secili ders metni
        self._recent = []           # Son secilen dersler (max 5)
        self._popup = None          # Acik popup Toplevel referansi
        self._callback = None       # Secim sonrasi callback
        self._is_searching = False  # Arama modunda mi?

        # --- Entry: ders adi gosterimi ve arama ---
        self._var = tk.StringVar()
        self.entry = tk.Entry(
            self, textvariable=self._var, width=width,
            font=("Segoe UI", 9),
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # --- Ok butonu: listeyi ac/kapat ---
        self._btn = tk.Button(
            self, text="\u25BC", width=2, font=("Segoe UI", 7),
            relief="flat", bg="#334155", fg="white", cursor="hand2",
            command=self._toggle_popup,
        )
        self._btn.pack(side=tk.LEFT, padx=(1, 0))

        # Olaylar
        self.entry.bind("<FocusIn>", self._on_entry_focus)
        self.entry.bind("<KeyRelease>", self._on_key)
        self.entry.bind("<Return>", lambda e: self._select_current())
        self.entry.bind("<Escape>", lambda e: self._cancel_search())
        self.entry.bind("<Down>", lambda e: self._move_selection(1))
        self.entry.bind("<Up>", lambda e: self._move_selection(-1))

    # ----- Public API -----

    def set_values(self, values: list):
        """Tum secenek listesini ayarla."""
        self._all_values = list(values)

    def get(self):
        """Secili degeri dondur."""
        return self._selected_value or self._var.get()

    def set(self, value: str):
        """Secili degeri programatik olarak ayarla."""
        self._selected_value = value
        self._var.set(value)
        self._is_searching = False

    def bind_select(self, callback):
        """Secim yapildiginda cagrilacak fonksiyon."""
        self._callback = callback

    # ----- Popup yonetimi -----

    def _toggle_popup(self):
        """Ok butonuyla listeyi ac/kapat."""
        if self._popup:
            self._close_popup()
        else:
            self._open_popup(show_all=True)

    def _on_entry_focus(self, _event):
        """Entry'ye tiklandiginda arama moduna gec."""
        if not self._popup:
            self._is_searching = True
            self.entry.select_range(0, tk.END)

    def _on_key(self, event):
        """Her tus basildiginda listeyi filtrele."""
        if event.keysym in ("Return", "Escape", "Up", "Down"):
            return
        if not self._popup:
            self._open_popup(show_all=False)
        self._is_searching = True
        self._refresh_list()

    def _open_popup(self, show_all=False):
        """Popup'i entry'nin hemen altinda ac."""
        if self._popup:
            self._close_popup()

        # Her acilista pozisyonu yeniden hesapla
        self.update_idletasks()
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        pw_width = max(400, self.entry.winfo_width() + self._btn.winfo_width())

        self._popup = pw = tk.Toplevel(self)
        pw.wm_overrideredirect(True)
        pw.wm_geometry(f"{pw_width}x280+{x}+{y}")
        pw.wm_attributes("-topmost", True)
        pw.configure(bg="#1e293b")

        # Arama ipucu
        hint = tk.Label(
            pw, text="Yazmaya baslayin veya listeden secin...",
            bg="#1e293b", fg="#64748b", font=("Segoe UI", 7),
            anchor="w", padx=4,
        )
        hint.pack(fill=tk.X)

        # Listbox + scrollbar
        lb_frame = tk.Frame(pw, bg="#1e293b")
        lb_frame.pack(fill=tk.BOTH, expand=True)

        sb = tk.Scrollbar(lb_frame, orient=tk.VERTICAL)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self._lb = tk.Listbox(
            lb_frame, font=("Segoe UI", 9),
            bg="#1e293b", fg="#e2e8f0",
            selectbackground="#2563eb", selectforeground="white",
            activestyle="none", highlightthickness=0, bd=0,
            yscrollcommand=sb.set,
        )
        self._lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self._lb.yview)

        self._lb.bind("<ButtonRelease-1>", lambda e: self._on_lb_click())
        self._lb.bind("<Double-1>", lambda e: self._on_lb_click())
        self._lb.bind("<Return>", lambda e: self._on_lb_click())

        # Tiklanabilir alan disina tiklaninca kapat
        pw.bind("<FocusOut>", self._on_popup_focus_out)

        if show_all:
            self._is_searching = False
            self._refresh_list()
        else:
            self._refresh_list()

    def _refresh_list(self):
        """Listeyi mevcut arama metnine gore guncelle."""
        if not self._popup or not hasattr(self, "_lb"):
            return

        self._lb.delete(0, tk.END)

        # Arama metnini belirle
        if self._is_searching:
            q = self._var.get().strip().lower()
            # Eger metin secili degerle ayniysa, filtre uygulama (tumunu goster)
            if q == self._selected_value.lower():
                q = ""
        else:
            q = ""

        # Eslesen dersleri bul
        matched = []
        for v in self._all_values:
            if not q or q in v.lower():
                matched.append(v)

        # Son secilenler ustte
        recent_set = set(self._recent)
        top_items = [v for v in matched if v in recent_set]
        rest_items = [v for v in matched if v not in recent_set]

        if top_items:
            for v in top_items[:5]:
                self._lb.insert(tk.END, v)
            self._lb.insert(tk.END, "─" * 40)

        for v in rest_items:
            self._lb.insert(tk.END, v)

        # Secili dersi listede vurgula
        if self._selected_value:
            for i in range(self._lb.size()):
                if self._lb.get(i) == self._selected_value:
                    self._lb.selection_set(i)
                    self._lb.see(i)
                    break

        if not matched:
            self._lb.insert(tk.END, "(Sonuc bulunamadi)")

    def _on_lb_click(self):
        """Listeden secim yapildiginda."""
        sel = self._lb.curselection()
        if not sel:
            return
        val = self._lb.get(sel[0])
        if val.startswith("─") or val == "(Sonuc bulunamadi)":
            return

        self._selected_value = val
        self._var.set(val)
        self._is_searching = False

        # Son secilenler listesine ekle
        if val in self._recent:
            self._recent.remove(val)
        self._recent.insert(0, val)
        self._recent = self._recent[:5]

        self._close_popup()
        if self._callback:
            self._callback(None)

    def _select_current(self):
        """Enter ile secili ogeni onayla."""
        if self._popup and hasattr(self, "_lb"):
            sel = self._lb.curselection()
            if sel:
                self._on_lb_click()
                return
            # Secim yoksa ilk ogeni sec
            if self._lb.size() > 0:
                first = self._lb.get(0)
                if not first.startswith("─") and first != "(Sonuc bulunamadi)":
                    self._lb.selection_set(0)
                    self._on_lb_click()
                    return
        self._close_popup()

    def _cancel_search(self):
        """Escape ile aramayi iptal edip onceki secime don."""
        self._var.set(self._selected_value)
        self._is_searching = False
        self._close_popup()

    def _move_selection(self, delta):
        """Ok tuslari ile listede gezin."""
        if not self._popup or not hasattr(self, "_lb"):
            self._open_popup(show_all=True)
            return

        size = self._lb.size()
        if size == 0:
            return

        sel = self._lb.curselection()
        current = sel[0] if sel else -1
        new_idx = max(0, min(size - 1, current + delta))

        # Ayirici satiri atla
        val = self._lb.get(new_idx)
        if val.startswith("─"):
            new_idx = max(0, min(size - 1, new_idx + delta))

        self._lb.selection_clear(0, tk.END)
        self._lb.selection_set(new_idx)
        self._lb.see(new_idx)

    def _on_popup_focus_out(self, event):
        """Popup disina tiklaninca kapat."""
        try:
            w = self.winfo_containing(event.x_root, event.y_root)
            if w is not None:
                pw = self._popup
                if (w == self.entry or w == self._btn or w == pw
                        or (hasattr(self, "_lb") and w == self._lb)):
                    return
                try:
                    if str(w).startswith(str(pw)):
                        return
                except Exception:
                    pass
        except Exception:
            pass
        self.after(120, self._deferred_close)

    def _deferred_close(self):
        """Geckmeli kapatma - focus hala icerideyse kapatma."""
        try:
            f = self.focus_get()
            if f == self.entry or (hasattr(self, "_lb") and f == self._lb):
                return
        except Exception:
            pass
        self._close_popup()

    def _close_popup(self):
        """Popup'i kapat ve temizle."""
        if self._popup:
            try:
                self._popup.destroy()
            except Exception:
                pass
            self._popup = None


# ---------------------------------------------------------------------------
# Ana sekme
# ---------------------------------------------------------------------------
class CourseAnalysisTab(ttk.Frame):
    """Ders Analiz Laboratuvari sekmesi (Tkinter)."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app     = app
        self.db      = app.db
        self._result = None    # son analiz sonucu
        self._running = False

        self._build_ui()
        self.after(300, self._load_initial_data)

    # =========================================================
    #  PUBLIC
    # =========================================================
    def refresh(self):
        self.db = self.app.db
        prev_yil = self.cb_yil.get()
        prev_fak = self.cb_fakulte.get()
        prev_ders = self.cb_ders.get()

        self._load_faculties()

        if prev_yil:
            try:
                yvals = list(self.cb_yil.cget("values") or [])
                if prev_yil in yvals:
                    self.cb_yil.set(prev_yil)
            except Exception:
                pass
        if prev_fak:
            try:
                fvals = list(self.cb_fakulte.cget("values") or [])
                if prev_fak in fvals:
                    self.cb_fakulte.set(prev_fak)
                    self._on_faculty_change(None)
            except Exception:
                pass
        if prev_ders:
            try:
                all_vals = getattr(self.cb_ders, "_all_values", [])
                if prev_ders in all_vals:
                    self.cb_ders.set(prev_ders)
            except Exception:
                pass

    # =========================================================
    #  UI INSASI
    # =========================================================
    def _build_ui(self):
        # ---- 1) UST SECiM BARI ----
        self._build_top_bar()

        # ---- 2) YIL DURUM BANDI ----
        self._build_year_status_bar()

        # ---- 3) SPLIT VIEW ----
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL,
                               sashwidth=5, bg="#cbd5e1")
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Sol (kriterler)
        left = tk.Frame(paned, bg="white")
        paned.add(left, width=280)
        self._build_left_panel(left)

        # Orta (algoritma adimlari)
        mid = tk.Frame(paned, bg="#f8fafc")
        paned.add(mid, width=460)
        self._build_mid_panel(mid)

        # Sag (nihai karar)
        right = tk.Frame(paned, bg="white")
        paned.add(right, width=300)
        self._build_right_panel(right)

    def _build_top_bar(self):
        bar = tk.Frame(self, bg="#1e293b", pady=8, padx=10)
        bar.pack(fill=tk.X)

        lbl_style = {"bg": "#1e293b", "fg": "#94a3b8",
                     "font": ("Segoe UI", 9, "bold")}

        tk.Label(bar, text="Yil:", **lbl_style).pack(side=tk.LEFT, padx=(0, 2))
        self.cb_yil = ttk.Combobox(bar, state="readonly", width=7)
        self.cb_yil.pack(side=tk.LEFT, padx=(0, 10))
        self.cb_yil.bind("<<ComboboxSelected>>", self._on_year_change)

        tk.Label(bar, text="Fakulte:", **lbl_style).pack(side=tk.LEFT, padx=(0, 2))
        self.cb_fakulte = ttk.Combobox(bar, state="readonly", width=28)
        self.cb_fakulte.pack(side=tk.LEFT, padx=(0, 6))
        self.cb_fakulte.bind("<<ComboboxSelected>>", self._on_faculty_change)

        tk.Label(bar, text="Ders:", **lbl_style).pack(side=tk.LEFT, padx=(0, 2))
        self.cb_ders = _SearchableCombo(bar, width=42, bg="#1e293b")
        self.cb_ders.pack(side=tk.LEFT, padx=(0, 10))
        self.cb_ders.bind_select(self._on_ders_selected)

        # Ilerleme cubugu (arka plan analizi icin)
        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=80)
        self.progress.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_start = tk.Button(
            bar, text="Analizi Başlat",
            bg="#2563eb", fg="white",
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            command=self._start_analysis
        )
        self.btn_start.pack(side=tk.LEFT, padx=4)

        tk.Button(
            bar, text="Temizle",
            bg="#475569", fg="white",
            font=("Segoe UI", 9),
            cursor="hand2",
            command=self._clear_all
        ).pack(side=tk.LEFT, padx=4)

    def _build_year_status_bar(self):
        """Yıl bazlı workflow durumunu gösteren ince banner."""
        self._status_bar = tk.Frame(self, bg="#f1f5f9", pady=4, padx=10)
        self._status_bar.pack(fill=tk.X)

        tk.Label(self._status_bar, text="Yıl Durumu:",
                 bg="#f1f5f9", font=("Segoe UI", 8, "bold"),
                 fg="#475569").pack(side=tk.LEFT)

        self._lbl_kriter_status = tk.Label(
            self._status_bar, text="—",
            bg="#e2e8f0", fg="#64748b",
            font=("Segoe UI", 8), padx=8, pady=2, relief="flat"
        )
        self._lbl_kriter_status.pack(side=tk.LEFT, padx=(6, 4))

        self._lbl_algo_status = tk.Label(
            self._status_bar, text="—",
            bg="#e2e8f0", fg="#64748b",
            font=("Segoe UI", 8), padx=8, pady=2, relief="flat"
        )
        self._lbl_algo_status.pack(side=tk.LEFT, padx=(0, 4))

        self._lbl_year_hint = tk.Label(
            self._status_bar, text="",
            bg="#f1f5f9", fg="#94a3b8",
            font=("Segoe UI", 8, "italic")
        )
        self._lbl_year_hint.pack(side=tk.LEFT, padx=(8, 0))

    def _update_year_status_bar(self, fakulte_id: int | None = None, yil: int | None = None):
        """Seçili yıl ve fakülte için workflow durumunu status bar'da günceller."""
        STATUS_LABELS = {
            "not_started": ("Kriter Girilmedi", "#fef2f2", "#dc2626"),
            "partial":     ("Kriter Eksik",      "#fefce8", "#b45309"),
            "completed":   ("Kriter Tamamlandı", "#f0fdf4", "#16a34a"),
        }
        ALGO_LABELS = {
            "not_run": ("Algoritma Çalışmadı", "#fef2f2", "#dc2626"),
            "ran":     ("Algoritmalar Çalıştı", "#f0fdf4", "#16a34a"),
            "failed":  ("Algoritma Hatası",     "#fef2f2", "#dc2626"),
        }

        def _reset():
            self._lbl_kriter_status.configure(text="—", bg="#e2e8f0", fg="#64748b")
            self._lbl_algo_status.configure(text="—", bg="#e2e8f0", fg="#64748b")
            self._lbl_year_hint.configure(text="")

        if fakulte_id is None or yil is None:
            _reset()
            return

        try:
            # Mimari kuralı: UI kendi DB bağlantısını açmaz; paylaşılan
            # bağlantı (app.db.conn) üzerinden çalışır.
            conn = getattr(self.db, "conn", None)
            if conn is None:
                _reset()
                return
            from app.services.yearly_workflow import (
                ensure_yearly_workflow_schema,
                get_faculty_year_status,
            )
            ensure_yearly_workflow_schema(conn)
            status = get_faculty_year_status(conn, int(fakulte_id), int(yil), refresh=False)

            krit_key = str(status.get("criteria_status", "not_started"))
            algo_key = str(status.get("algorithm_run_status", "not_run"))
            algo_at  = status.get("algorithm_run_at") or ""

            k_txt, k_bg, k_fg = STATUS_LABELS.get(krit_key, (krit_key, "#e2e8f0", "#64748b"))
            a_txt, a_bg, a_fg = ALGO_LABELS.get(algo_key, (algo_key, "#e2e8f0", "#64748b"))

            self._lbl_kriter_status.configure(text=k_txt, bg=k_bg, fg=k_fg)
            self._lbl_algo_status.configure(text=a_txt, bg=a_bg, fg=a_fg)

            hint = ""
            if algo_key == "not_run" and krit_key == "not_started":
                hint = "Bu yıl için kriter girilmemiş ve algoritma çalıştırılmamış."
            elif algo_key == "not_run" and krit_key in ("partial", "completed"):
                hint = "Kriterler girilmiş ancak algoritmalar henüz çalıştırılmamış."
            elif algo_key == "ran" and algo_at:
                hint = f"Son çalışma: {algo_at[:16]}"
            self._lbl_year_hint.configure(text=hint)
        except Exception:
            _reset()

    def _build_left_panel(self, parent):
        tk.Label(parent, text="KAYITLI KRITERLER",
                 bg="#dbeafe", font=("Segoe UI", 9, "bold"),
                 anchor="w", padx=6).pack(fill=tk.X)

        self.warn_frame = tk.Frame(parent, bg="#fef2f2")
        self.warn_lbl = tk.Label(
            self.warn_frame,
            text="",
            bg="#fef2f2", fg="#dc2626",
            font=("Segoe UI", 8, "italic"),
            wraplength=240, justify="left", padx=6, pady=4
        )
        self.warn_lbl.pack(fill=tk.X)

        cols = ("Kriter", "Deger")
        self.tree_krit = ttk.Treeview(parent, columns=cols, show="headings",
                                       height=12, selectmode="none")
        self.tree_krit.heading("Kriter", text="Kriter")
        self.tree_krit.heading("Deger", text="Deger")
        self.tree_krit.column("Kriter", width=155)
        self.tree_krit.column("Deger", width=100, anchor="center")

        sb = ttk.Scrollbar(parent, orient="vertical", command=self.tree_krit.yview)
        self.tree_krit.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_krit.pack(fill=tk.BOTH, expand=True, padx=2)

    def _build_mid_panel(self, parent):
        tk.Label(parent, text="ALGORITMA ADIMLARI",
                 bg="#e0f2fe", font=("Segoe UI", 9, "bold"),
                 anchor="w", padx=6).pack(fill=tk.X)

        canvas  = tk.Canvas(parent, bg="#f8fafc", highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        self.mid_scroll = tk.Frame(canvas, bg="#f8fafc")

        self.mid_scroll.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.mid_scroll, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._step_boxes = {}
        steps = [
            ("ahp",    "1. AHP Agirliklar"),
            ("trend",  "2. Trend / LR Tahmini"),
            ("topsis", "3. TOPSIS Skoru"),
            ("rf",     "4. RF Tahmin"),
            ("dt",     "5. DT Karar Gerekcesi"),
        ]
        for key, title in steps:
            grp = tk.LabelFrame(
                self.mid_scroll, text=f"  {title}  ",
                bg="#f8fafc", font=("Segoe UI", 8, "bold"),
                fg="#475569", pady=4, padx=6
            )
            grp.pack(fill=tk.X, padx=6, pady=4)

            # durum etiketi (Bekliyor / Calisıyor / Tamamlandi / Hata)
            state_lbl = tk.Label(grp, text="Bekliyor...",
                                 bg="#f8fafc", fg="#94a3b8",
                                 font=("Segoe UI", 8, "italic"))
            state_lbl.pack(anchor="w")

            # icerik
            txt = tk.Text(grp, height=4, font=("Consolas", 8),
                          bg="#f1f5f9", fg="#1e293b",
                          relief="flat", state="disabled",
                          wrap="word")
            txt.pack(fill=tk.X, pady=(2, 0))

            self._step_boxes[key] = {"frame": grp, "state": state_lbl, "text": txt}

    def _build_right_panel(self, parent):
        tk.Label(parent, text="NIHAI KARAR",
                 bg="#dcfce7", font=("Segoe UI", 9, "bold"),
                 anchor="w", padx=6).pack(fill=tk.X)

        pad = tk.Frame(parent, bg="white", padx=10, pady=10)
        pad.pack(fill=tk.BOTH, expand=True)

        # Buyuk statu etiketi
        self.lbl_statu_big = tk.Label(
            pad, text="—",
            bg="white", fg="#94a3b8",
            font=("Segoe UI", 26, "bold"),
            wraplength=260, justify="center", pady=10
        )
        self.lbl_statu_big.pack(fill=tk.X)

        # Sayac
        sayac_frame = tk.Frame(pad, bg="white")
        sayac_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(sayac_frame, text="Sayac:", bg="white",
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.lbl_sayac = tk.Label(sayac_frame, text="—",
                                   bg="white", font=("Segoe UI", 9))
        self.lbl_sayac.pack(side=tk.LEFT, padx=4)
        _Tooltip(self.lbl_sayac, "Mufredattan dusme sayaci")

        ttk.Separator(pad, orient="horizontal").pack(fill=tk.X, pady=6)

        # Ozet metin
        tk.Label(pad, text="Karar Ozeti:",
                 bg="white", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.txt_summary = tk.Text(
            pad, height=12,
            font=("Segoe UI", 8),
            bg="#f8fafc", fg="#1e293b",
            relief="flat", state="disabled",
            wrap="word"
        )
        self.txt_summary.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

    # =========================================================
    #  VERI YUKLEME
    # =========================================================
    def _load_initial_data(self):
        self._load_faculties()
        self._reset_right_panel("Fakülte ve yıl seçip ders analizi başlatın.")
        self._try_update_year_status()

    def _sync_year_for_faculty(self, fakulte_id: int):
        """
        Secili fakulte icin yalnizca o fakultenin mufredat yillarini listeler
        (global havuz birlesimi yok — baska fakultenin yili gorunmez).
        """
        try:
            if not getattr(self.db, "conn", None):
                self.cb_yil["values"] = tuple()
                self.cb_yil.set("")
                self._global_year_values = []
                return

            _, rows = self.db.run_sql(
                """
                SELECT DISTINCT m.akademik_yil
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                WHERE b.fakulte_id = ?
                ORDER BY m.akademik_yil
                """,
                (int(fakulte_id),),
            )
            fakulte_years = [str(int(r[0])) for r in (rows or []) if r and r[0] is not None]
            previous = self.cb_yil.get()
            self._global_year_values = list(fakulte_years)
            self.cb_yil["values"] = tuple(fakulte_years)
            if previous and previous in fakulte_years:
                self.cb_yil.set(previous)
            elif fakulte_years:
                self.cb_yil.set(fakulte_years[-1])
            else:
                self.cb_yil.set("")
        except Exception as e:
            print(f"[CourseAnalysisTab] _sync_year_for_faculty hatasi: {e}")

    def _refresh_courses_for_scope(self, fakulte_id: int, yil_raw: str | None):
        prev_ders = self.cb_ders.get()
        self._ders_list = []
        self._ders_map = {}

        try:
            yil = int(str(yil_raw or "").strip())
        except Exception:
            self._update_ders_combo("")
            return

        try:
            seen = {}

            _, curriculum_rows = self.db.run_sql(
                """
                SELECT DISTINCT d.ders_id, d.ad
                FROM ders d
                JOIN mufredat_ders md ON d.ders_id = md.ders_id
                JOIN mufredat m ON md.mufredat_id = m.mufredat_id
                JOIN bolum b ON m.bolum_id = b.bolum_id
                WHERE b.fakulte_id = ? AND m.akademik_yil = ?
                ORDER BY d.ad
                """,
                (int(fakulte_id), int(yil)),
            )
            for r in (curriculum_rows or []):
                seen[int(r[0])] = (int(r[0]), str(r[1] or ""))

            _, havuz_rows = self.db.run_sql(
                """
                SELECT DISTINCT CAST(h.ders_id AS INTEGER), COALESCE(d.ad, 'Ders ' || h.ders_id)
                FROM havuz h
                LEFT JOIN ders d ON CAST(h.ders_id AS INTEGER) = d.ders_id
                WHERE h.fakulte_id = ? AND h.yil = ?
                ORDER BY 2
                """,
                (int(fakulte_id), int(yil)),
            )
            for r in (havuz_rows or []):
                ders_id = int(r[0])
                if ders_id not in seen:
                    seen[ders_id] = (ders_id, str(r[1] or ""))

            self._ders_list = [
                (f"{ders_id} — {ders_adi}", ders_id)
                for ders_id, ders_adi in sorted(seen.values(), key=lambda item: (str(item[1]), item[0]))
            ]
            self._ders_map = {display: ders_id for display, ders_id in self._ders_list}
            self._update_ders_combo("")
            if prev_ders and prev_ders in getattr(self.cb_ders, "_all_values", []):
                self.cb_ders.set(prev_ders)
        except Exception as e:
            print(f"[CourseAnalysisTab] kapsamli ders listesi hatasi: {e}")
            self._ders_list = []
            self._ders_map = {}
            self._update_ders_combo("")

    def _load_faculties(self):
        try:
            if not getattr(self.db, "conn", None):
                return
            _, rows = self.db.run_sql("SELECT fakulte_id, ad FROM fakulte ORDER BY ad")
            vals = [str(r[1]) for r in (rows or [])]
            self._fakulte_map = {str(r[1]): int(r[0]) for r in (rows or [])}
            self.cb_fakulte["values"] = tuple(vals)
            if vals:
                try:
                    self.cb_fakulte.current(0)
                except tk.TclError:
                    self.cb_fakulte.set(vals[0])
                self._on_faculty_change(None)
            self.update_idletasks()
        except Exception as e:
            print(f"[CourseAnalysisTab] _load_faculties hatasi: {e}")

    def _on_faculty_change(self, _event):
        fak = self.cb_fakulte.get()
        if not fak:
            return
        try:
            fid = getattr(self, "_fakulte_map", {}).get(fak)
            if fid is None:
                _, rows = self.db.run_sql(
                    "SELECT fakulte_id FROM fakulte WHERE TRIM(ad) = TRIM(?)", (fak,)
                )
                if not rows:
                    self._ders_list = []
                    self._ders_map = {}
                    self._update_ders_combo("")
                    return
                fid = int(rows[0][0])
            self._sync_year_for_faculty(fid)
            self._refresh_courses_for_scope(fid, self.cb_yil.get())
            self._clear_results_for_new_scope()
            self._try_update_year_status()
        except Exception as e:
            print(f"[CourseAnalysisTab] fakulte degisimi hatasi: {e}")
            self._ders_list = []
            self._ders_map = {}
            self._update_ders_combo("")

    def _on_year_change(self, _event=None):
        fak = self.cb_fakulte.get()
        if not fak:
            self._ders_list = []
            self._ders_map = {}
            self._update_ders_combo("")
            return
        try:
            fid = getattr(self, "_fakulte_map", {}).get(fak)
            if fid is None:
                _, rows = self.db.run_sql(
                    "SELECT fakulte_id FROM fakulte WHERE TRIM(ad) = TRIM(?)",
                    (fak,),
                )
                if not rows:
                    self._ders_list = []
                    self._ders_map = {}
                    self._update_ders_combo("")
                    return
                fid = int(rows[0][0])
            self._refresh_courses_for_scope(int(fid), self.cb_yil.get())
            # Yıl değişince önceki analiz sonucunu temizle (başka yılın verisi görünmesin)
            self._clear_results_for_new_scope()
            self._try_update_year_status()
        except Exception as e:
            print(f"[CourseAnalysisTab] yil degisimi hatasi: {e}")
            self._ders_list = []
            self._ders_map = {}
            self._update_ders_combo("")

    def _clear_results_for_new_scope(self):
        """Yıl veya fakülte değiştiğinde analiz sonuçlarını temizler."""
        self._result = None
        # Kriter tablosu temizle
        try:
            self.tree_krit.delete(*self.tree_krit.get_children())
        except Exception:
            pass
        # Algoritma adımlarını sıfırla
        try:
            for box in self._step_boxes.values():
                box["state"].configure(text="Bekliyor...", fg="#94a3b8")
                t = box["text"]
                t.configure(state="normal")
                t.delete("1.0", "end")
                t.configure(state="disabled")
        except Exception:
            pass
        # Sağ panel sıfırla
        self._reset_right_panel()

    def _reset_right_panel(self, message: str = "Ders seçip 'Analizi Başlat' butonuna basın."):
        """Sağ paneli boş/bekleme durumuna döndürür."""
        try:
            self.lbl_statu_big.configure(
                text="—", bg="white", fg="#94a3b8"
            )
            self.lbl_sayac.configure(text="—")
            t = self.txt_summary
            t.configure(state="normal")
            t.delete("1.0", "end")
            t.insert("end", message)
            t.configure(state="disabled")
            self.warn_frame.pack_forget()
        except Exception:
            pass

    def _try_update_year_status(self):
        """Mevcut fakülte ve yıl için status bar'ı günceller."""
        try:
            fid = getattr(self, "_fakulte_map", {}).get(self.cb_fakulte.get())
            yil_str = self.cb_yil.get()
            yil = int(yil_str) if yil_str else None
            self._update_year_status_bar(fakulte_id=fid, yil=yil)
        except Exception:
            pass

    def _on_ders_selected(self, event=None):
        """Ders seçildiğinde (Analizi Başlat için hazır)."""

    def _update_ders_combo(self, query: str):
        """Ders listesini SearchableCombo'ya yukle."""
        ders_list = getattr(self, "_ders_list", [])
        if not ders_list:
            self.cb_ders.set_values([])
            self.cb_ders.set("")
            self.btn_start.config(state="disabled")
            return
        self.btn_start.config(state="normal")
        all_vals = [d[0] for d in ders_list]
        self.cb_ders.set_values(all_vals)
        if all_vals:
            self.cb_ders.set(all_vals[0])
        else:
            self.cb_ders.set("")

    # =========================================================
    #  ANALIZ BASLAT
    # =========================================================
    def _start_analysis(self):
        if self._running:
            return

        ders_adi = self.cb_ders.get()
        yil_str  = self.cb_yil.get()

        if not ders_adi or not yil_str:
            messagebox.showwarning("Eksik Secim", "Lutfen ders ve yil secin.")
            return

        ders_id = getattr(self, "_ders_map", {}).get(ders_adi)
        if ders_id is None and " — " in ders_adi:
            try:
                ders_id = int(ders_adi.split(" — ")[0].strip())
            except (ValueError, IndexError):
                pass
        if ders_id is None:
            messagebox.showwarning("Ders Bulunamadi",
                "Ders secin veya listeden birini secin.")
            return

        year = int(yil_str)
        import os
        db_path = getattr(self.app, "db_path", None) or getattr(
            self.app, "config_data", {}
        ).get("db_path")
        if not db_path:
            print("[CourseAnalysis] Veritabanı yolu bulunamadı")
            messagebox.showerror("Bağlantı Yok", "Veritabanı yolu belirlenemedi. Lütfen uygulama ayarlarını kontrol edin.")
            return
        db_path = os.path.abspath(db_path)
        if not os.path.exists(db_path):
            print(f"[CourseAnalysis] Veritabanı dosyası mevcut değil: {db_path}")
            messagebox.showerror("Baglanti Yok", "Veritabanına bağlanılamıyor. Lütfen veritabanı yolunu ve erişimi kontrol edin.")
            return

        # UI sifirla
        self._clear_all(keep_selection=True)
        self._set_running(True)

        def _worker():
            result = analyze_single_course(ders_id, year, db_path)
            self.after(0, lambda r=result: self._on_result(r))

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _on_result(self, result: dict):
        self._set_running(False)
        self._result = result

        if "error" in result:
            messagebox.showwarning(
                "Veri Eksik / Hata",
                result["error"]
            )
            self._mark_all_steps_error(result["error"])
            self._reset_right_panel(
                f"Veri Eksik / Hata:\n{result['error']}\n\n"
                "Bu yıl için gerekli veri bulunmadığından analiz yapılamadı.\n"
                "Önce kriter girin, ardından tekrar deneyin."
            )
            return

        self._fill_criteria(
            result.get("criteria", {}),
            result.get("criteria_status", {}),
        )
        self._fill_steps(result.get("steps", {}))
        self._fill_decision(
            result.get("decision", {}),
            result.get("course", {}),
            result.get("steps", {}),
        )
        # Analiz bittikten sonra yıl durum bandını güncelle
        self._try_update_year_status()

    # =========================================================
    #  KRITERLER PANEL
    # =========================================================
    def _fill_criteria(self, criteria: dict, criteria_status: dict | None = None):
        self.tree_krit.delete(*self.tree_krit.get_children())
        criteria_status = criteria_status or {}

        if not criteria:
            self.warn_frame.pack(fill=tk.X, before=self.tree_krit)
            self.warn_lbl.config(text="Bu ders icin kriter verisi bulunamadi.")
            self.btn_start.config(state="normal")
            return

        missing = bool(criteria.get("_missing")) or criteria_status.get("ok") is False
        if missing:
            self.warn_frame.pack(fill=tk.X, before=self.tree_krit)
            self.warn_lbl.config(
                text=criteria_status.get("message")
                or criteria.get("_missing_reason")
                or "Bu ders icin kriter verisi bulunamadi; hesaplanabilen adimlar gosteriliyor."
            )
        else:
            self.warn_frame.pack_forget()
        self.btn_start.config(state="normal")

        def _num(key: str, fmt: str) -> str:
            if missing:
                return "-"
            return fmt.format(criteria.get(key, 0))

        def _ratio(key: str) -> str:
            if missing:
                return "-"
            return f"%{criteria.get(key, 0) * 100:.1f}"

        anket_val = criteria.get('anket_orani', 0.5)
        if missing:
            anket_text = "%50.0 (notr varsayilan)"
        else:
            anket_text = f"%{anket_val*100:.1f}" if anket_val != 0.5 else "%50.0 (varsayilan)"
        rows = [
            ("Veri Durumu",       "Eksik" if missing else "Hazir"),
            ("Toplam Ogrenci",    _num("toplam_ogrenci", "{:.0f}")),
            ("Gecen Ogrenci",     _num("gecen_ogrenci", "{:.0f}")),
            ("Not Ortalamasi",    _num("basari_ortalamasi", "{:.1f}")),
            ("Kontenjan",         _num("kontenjan", "{:.0f}")),
            ("Kayitli (Talep)",   _num("kayitli_ogrenci", "{:.0f}")),
            ("Basari Orani",      _ratio("basari_orani")),
            ("Doluluk Orani",     _ratio("doluluk_orani")),
            ("Anket Orani",       anket_text),
        ]
        for k, v in rows:
            self.tree_krit.insert("", tk.END, values=(k, v))

    # =========================================================
    #  ALGORITMA ADIMLARI PANEL
    # =========================================================
    def _fill_steps(self, steps: dict):
        # AHP
        ahp = steps.get("ahp", {})
        if "error" in ahp:
            self._set_step_state("ahp", "error", f"Hata: {ahp['error']}")
        else:
            w = ahp.get("weights", {})
            cr = ahp.get("CR", 0)
            valid_str = "GECERLI" if ahp.get("valid") else "DIKKAT: CR > 0.10"
            txt = (
                f"Agirliklar:\n"
                f"  Basari   : {w.get('basari',0):.4f} (%{w.get('basari',0)*100:.1f})\n"
                f"  Trend    : {w.get('trend',0):.4f} (%{w.get('trend',0)*100:.1f})\n"
                f"  Populerlik: {w.get('populerlik',0):.4f} (%{w.get('populerlik',0)*100:.1f})\n"
                f"  Anket    : {w.get('anket',0):.4f} (%{w.get('anket',0)*100:.1f})\n"
                f"CR = {cr:.4f}  [{valid_str}]\n"
                f"lambda_max = {ahp.get('lambda_max',0):.4f}  |  "
                f"Sure: {ahp.get('elapsed_ms',0):.1f} ms"
            )
            if ahp.get("note"):
                txt += f"\nNot: {ahp.get('note')}"
            self._set_step_state("ahp", "ok", txt)

        # Trend
        trend = steps.get("trend", {})
        if "error" in trend:
            self._set_step_state("trend", "error", f"Hata: {trend['error']}")
        else:
            method = trend.get("method", "?")
            method_label = {"sklearn_lr": "sklearn LR", "weighted_average": "Agirlikli Ortalama"}.get(method, method)
            extra = ""
            if method == "sklearn_lr":
                coef = trend.get("coefficient", 0)
                td = trend.get("trend_direction", "?")
                extra = f"\nLR Egim: {coef:+.6f} ({td})"
                wa = trend.get("wa_fallback")
                if wa is not None:
                    extra += f"\nWA Fallback: %{wa*100:.1f}"
            txt = (
                f"Yontem: {method_label}\n"
                f"Yillik gecmis ({trend.get('n_years',0)} yil):\n"
                f"  {trend.get('log','—')}\n"
                f"Tahmin (0-1) : {trend.get('predicted',0):.4f}\n"
                f"Tahmin (0-100): {trend.get('predicted_100',0):.2f}{extra}\n"
                f"Sure: {trend.get('elapsed_ms',0):.1f} ms"
            )
            self._set_step_state("trend", "ok", txt)

        # TOPSIS
        topsis = steps.get("topsis", {})
        if "error" in topsis:
            self._set_step_state("topsis", "error", f"Hata: {topsis['error']}")
        elif topsis.get("status") == "not_calculated" or topsis.get("score_100") is None:
            txt = (
                "Kesinlesme puani henuz hesaplanmadi.\n"
                f"Mesaj: {topsis.get('message', 'Hesaplama verisi yetersiz.')}\n"
                f"Sure: {topsis.get('elapsed_ms',0):.1f} ms"
            )
            self._set_step_state("topsis", "ok", txt)
        else:
            inp = topsis.get("inputs", {})
            txt = (
                f"Girisler (normalize):\n"
                f"  Basari: {inp.get('basari',0):.4f}  Trend: {inp.get('trend',0):.4f}\n"
                f"  Doluluk: {inp.get('doluluk',0):.4f}  Anket: {inp.get('anket',0):.4f}\n"
                f"Yakinlik  (0-1) : {topsis.get('raw_score_01',0):.6f}\n"
                f"Kesinlesme (0-100): {topsis.get('score_100',0):.2f}\n"
                f"Sure: {topsis.get('elapsed_ms',0):.1f} ms"
            )
            if topsis.get("message"):
                txt += f"\nNot: {topsis.get('message')}"
            self._set_step_state("topsis", "ok", txt)

        # RF
        rf = steps.get("rf", {})
        if "error" in rf:
            self._set_step_state("rf", "error", f"Hata: {rf['error']}")
        elif rf.get("status") == "not_calculated":
            txt = (
                "Tahmin hesaplanmadi.\n"
                f"Mesaj: {rf.get('message', 'Kriter verisi yetersiz.')}\n"
                f"Sure: {rf.get('elapsed_ms',0):.1f} ms"
            )
            self._set_step_state("rf", "ok", txt)
        else:
            method = rf.get("method", "?")
            method_label = {"sklearn_rf": "sklearn RandomForest", "rule_based": "Kural Tabanli"}.get(method, method)
            score_txt = ""
            if rf.get("predicted_score") is not None:
                score_txt = f"\nRF Skor: {rf['predicted_score']:.2f}"
            txt = (
                f"Yontem: {method_label}\n"
                f"Tahmin statu: {rf.get('predicted_statu',0)}  "
                f"({rf.get('predicted_label','?')})\n"
                f"Kural: {rf.get('rule','—')}{score_txt}\n"
                f"Not: {rf.get('note','')}\n"
                f"Sure: {rf.get('elapsed_ms',0):.1f} ms"
            )
            self._set_step_state("rf", "ok", txt)

        # DT
        dt = steps.get("dt", {})
        dt_reason = steps.get("dt_reason", "—")
        if "error" in dt:
            self._set_step_state("dt", "error", f"Hata: {dt['error']}")
        elif dt.get("status") == "not_calculated":
            txt = (
                "Karar agaci tahmini hesaplanmadi.\n"
                f"Mesaj: {dt.get('message', 'Kriter verisi yetersiz.')}\n"
                f"Sure: {dt.get('elapsed_ms',0):.1f} ms\n"
                f"---\nKarar Gerekcesi:\n{dt_reason}"
            )
            self._set_step_state("dt", "ok", txt)
        else:
            dt_method = dt.get("method", "?")
            dt_label = {"sklearn_dt": "sklearn DecisionTree", "rule_based": "Kural Tabanli"}.get(dt_method, dt_method)
            txt = (
                f"Yontem: {dt_label}\n"
                f"DT Statu Tahmini: {dt.get('predicted_statu', '?')} "
                f"({dt.get('predicted_label', '?')})\n"
                f"Not: {dt.get('note', '')}\n"
                f"Sure: {dt.get('elapsed_ms',0):.1f} ms\n"
                f"---\nKarar Gerekcesi:\n{dt_reason}"
            )
            self._set_step_state("dt", "ok", txt)

    def _set_step_state(self, key: str, state: str, content: str):
        box = self._step_boxes.get(key)
        if not box:
            return
        if state == "ok":
            box["state"].config(text="Tamamlandi", fg="#16a34a")
            self._set_text(box["text"], content)
        elif state == "error":
            box["state"].config(text="Hata!", fg="#dc2626")
            self._set_text(box["text"], content)
        elif state == "running":
            box["state"].config(text="Calisiyor...", fg="#d97706")
        else:
            box["state"].config(text="Bekliyor...", fg="#94a3b8")

    @staticmethod
    def _set_text(widget: tk.Text, content: str):
        widget.config(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, content)
        widget.config(state="disabled")

    # =========================================================
    #  NIHAI KARAR PANEL
    # =========================================================
    def _fill_decision(self, decision: dict, course: dict, steps: dict | None = None):
        steps = steps or {}
        statu  = decision.get("next", {}).get("statu", 0)
        sayac  = decision.get("next", {}).get("sayac", 0)
        label  = decision.get("label", "?")
        skor   = decision.get("score_final")
        skor_txt = f"{float(skor):.2f} / 100" if isinstance(skor, (int, float)) else "Henuz hesaplanmadi"
        in_muf = decision.get("in_mufredat_this_year", False)
        is_gt  = decision.get("is_ground_truth", False)
        sm     = decision.get("sm_note", "")
        prev   = decision.get("prev", {})
        dt_reason = steps.get("dt_reason", "")
        drop_reasons = decision.get("drop_reasons", []) or []
        drop_txt = ", ".join(drop_reasons) if drop_reasons else "-"

        # Renk
        colors = _STATU_COLORS.get(statu, _DEFAULT_COLOR)
        self.lbl_statu_big.config(
            text=str(_STATU_LABELS.get(statu, label) or label),
            bg=colors["bg"], fg=colors["fg"]
        )

        # Sayac
        sayac_tip = _SAYAC_TIPS.get(sayac, f"Dusme sayaci: {sayac}")
        self.lbl_sayac.config(text=str(sayac))
        _Tooltip(self.lbl_sayac, sayac_tip)

        # Ozet
        prev_yr   = prev.get("year", "?")
        prev_st   = prev.get("statu", "?")
        prev_sc   = prev.get("sayac", "?")
        ders_adi  = course.get("ad", "")

        summary = (
            f"Ders       : {ders_adi}\n"
            f"Kesinlesme : {skor_txt}\n"
            f"Mufredata  : {'Evet' if in_muf else 'Hayir'}\n"
            f"Dusme Neden: {drop_txt}\n"
            f"{'--- Ground Truth ---' if is_gt else ''}\n"
            f"Onceki yil ({prev_yr}): statu={prev_st}, sayac={prev_sc}\n"
            f"Bu yil     : statu={statu}, sayac={sayac}\n"
            f"---------------\n"
            f"DT Aciklama:\n{dt_reason}\n"
            f"---------------\n"
            f"State Machine:\n{sm}"
        )
        self._set_text(self.txt_summary, summary.strip())

    # =========================================================
    #  YARDIMCILAR
    # =========================================================
    def _set_running(self, val: bool):
        self._running = val
        if val:
            self.progress.start(10)
            self.btn_start.config(state="disabled", text="Calisıyor...")
            for key in self._step_boxes:
                self._set_step_state(key, "running", "")
        else:
            self.progress.stop()
            self.btn_start.config(state="normal", text="Analizi Başlat")

    def _mark_all_steps_error(self, msg: str):
        for key in self._step_boxes:
            self._set_step_state(key, "error", msg)

    def _clear_all(self, keep_selection: bool = False):
        # Kriterler
        self.tree_krit.delete(*self.tree_krit.get_children())
        self.warn_frame.pack_forget()

        # Adimlar
        for key in self._step_boxes:
            self._set_step_state(key, "idle", "")
            self._set_text(self._step_boxes[key]["text"], "")

        # Nihai karar
        self.lbl_statu_big.config(text="—", bg="white", fg="#94a3b8")
        self.lbl_sayac.config(text="—")
        self._set_text(self.txt_summary, "")
