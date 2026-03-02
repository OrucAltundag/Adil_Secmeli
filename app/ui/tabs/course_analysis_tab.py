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
from tkinter import ttk, messagebox

from app.services.course_analyzer import analyze_single_course, VeriEksikHatasi


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


def _sq(s: str) -> str:
    return str(s).replace("'", "''")


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
        self._load_faculties()

    # =========================================================
    #  UI INSASI
    # =========================================================
    def _build_ui(self):
        # ---- 1) UST SECiM BARI ----
        self._build_top_bar()

        # ---- 2) SPLIT VIEW ----
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
        self.cb_yil = ttk.Combobox(bar, state="readonly",
                                   values=["2022", "2023", "2024", "2025"], width=7)
        self.cb_yil.current(0)
        self.cb_yil.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(bar, text="Fakulte:", **lbl_style).pack(side=tk.LEFT, padx=(0, 2))
        self.cb_fakulte = ttk.Combobox(bar, state="readonly", width=28)
        self.cb_fakulte.pack(side=tk.LEFT, padx=(0, 6))
        self.cb_fakulte.bind("<<ComboboxSelected>>", self._on_faculty_change)

        tk.Label(bar, text="Ders:", **lbl_style).pack(side=tk.LEFT, padx=(0, 2))
        self.cb_ders = ttk.Combobox(bar, state="normal", width=38)
        self.cb_ders.pack(side=tk.LEFT, padx=(0, 10))
        self.cb_ders.bind("<KeyRelease>", self._on_ders_search)

        # Ilerleme cubugu (arka plan analizi icin)
        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=80)
        self.progress.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_start = tk.Button(
            bar, text="Analizi Baslar",
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

    def _load_faculties(self):
        try:
            _, rows = self.db.run_sql("SELECT ad FROM fakulte ORDER BY ad")
            vals = [r[0] for r in (rows or [])]
            self.cb_fakulte["values"] = vals
            if vals and self.cb_fakulte.current() < 0:
                self.cb_fakulte.current(0)
            self._on_faculty_change(None)
        except Exception:
            pass

    def _on_faculty_change(self, _event):
        fak = self.cb_fakulte.get()
        if not fak:
            return
        try:
            _, rows = self.db.run_sql(
                f"SELECT fakulte_id FROM fakulte WHERE ad='{_sq(fak)}'"
            )
            if not rows:
                return
            fid = int(rows[0][0])

            _, ders_rows = self.db.run_sql(f"""
                SELECT DISTINCT d.ders_id, d.ad
                FROM ders d
                WHERE d.fakulte_id = {fid}
                ORDER BY d.ad
            """)
            # Format: "id — ad" (arama icin)
            self._ders_list = [
                (f"{r[0]} — {r[1]}", int(r[0])) for r in (ders_rows or [])
            ]
            self._ders_map = {display: d_id for display, d_id in self._ders_list}
            self._update_ders_combo(self.cb_ders.get().strip())
        except Exception as e:
            print(f"[CourseAnalysisTab] fakulte degisimi hatasi: {e}")

    def _on_ders_search(self, event):
        """Arama: yazdikca liste filtrelenir (case insensitive, icerir)."""
        q = (self.cb_ders.get() or "").strip().lower()
        self._update_ders_combo(q)

    def _update_ders_combo(self, query: str):
        """Ders listesini query ile filtrele; combobox values guncelle."""
        if not getattr(self, "_ders_list", []):
            return
        q = (query or "").lower()
        if not q:
            filtered = [d[0] for d in self._ders_list]
        else:
            filtered = [
                d[0] for d in self._ders_list
                if q in d[0].lower()
            ]
        self.cb_ders["values"] = filtered
        if filtered and self.cb_ders.current() < 0:
            self.cb_ders.current(0)

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
        db_path = getattr(self.app, "db_path", None) or getattr(
            self.app, "config_data", {}
        ).get("db_path")
        if not db_path:
            messagebox.showerror("Baglanti Yok", "Veritabani yolu belirlenemedi.")
            return

        import os
        if not os.path.exists(db_path):
            messagebox.showerror("Baglanti Yok", f"Veritabani bulunamadi: {db_path}")
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
            return

        self._fill_criteria(result.get("criteria", {}))
        self._fill_steps(result.get("steps", {}))
        self._fill_decision(
            result.get("decision", {}),
            result.get("course", {}),
            result.get("steps", {}),
        )

    # =========================================================
    #  KRITERLER PANEL
    # =========================================================
    def _fill_criteria(self, criteria: dict):
        self.tree_krit.delete(*self.tree_krit.get_children())

        if not criteria:
            self.warn_frame.pack(fill=tk.X, before=self.tree_krit)
            self.warn_lbl.config(text="Bu ders icin kriter verisi bulunamadi.")
            self.btn_start.config(state="disabled")
            return

        self.warn_frame.pack_forget()
        self.btn_start.config(state="normal")

        rows = [
            ("Toplam Ogrenci",    f"{criteria.get('toplam_ogrenci', 0):.0f}"),
            ("Gecen Ogrenci",     f"{criteria.get('gecen_ogrenci', 0):.0f}"),
            ("Not Ortalamasi",    f"{criteria.get('basari_ortalamasi', 0):.1f}"),
            ("Kontenjan",         f"{criteria.get('kontenjan', 0):.0f}"),
            ("Kayitli (Talep)",   f"{criteria.get('kayitli_ogrenci', 0):.0f}"),
            ("Basari Orani",      f"%{criteria.get('basari_orani', 0)*100:.1f}"),
            ("Doluluk Orani",     f"%{criteria.get('doluluk_orani', 0)*100:.1f}"),
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
            self._set_step_state("ahp", "ok", txt)

        # Trend
        trend = steps.get("trend", {})
        if "error" in trend:
            self._set_step_state("trend", "error", f"Hata: {trend['error']}")
        else:
            txt = (
                f"Yillik gecmis ({trend.get('n_years',0)} yil):\n"
                f"  {trend.get('log','—')}\n"
                f"Tahmin (0-1) : {trend.get('predicted',0):.4f}\n"
                f"Tahmin (0-100): {trend.get('predicted_100',0):.2f}\n"
                f"Sure: {trend.get('elapsed_ms',0):.1f} ms"
            )
            self._set_step_state("trend", "ok", txt)

        # TOPSIS
        topsis = steps.get("topsis", {})
        if "error" in topsis:
            self._set_step_state("topsis", "error", f"Hata: {topsis['error']}")
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
            self._set_step_state("topsis", "ok", txt)

        # RF
        rf = steps.get("rf", {})
        if "error" in rf:
            self._set_step_state("rf", "error", f"Hata: {rf['error']}")
        else:
            txt = (
                f"Tahmin statu: {rf.get('predicted_statu',0)}  "
                f"({rf.get('predicted_label','?')})\n"
                f"Kural: {rf.get('rule','—')}\n"
                f"Not: {rf.get('note','')}\n"
                f"Sure: {rf.get('elapsed_ms',0):.1f} ms"
            )
            self._set_step_state("rf", "ok", txt)

        # DT
        dt_reason = steps.get("dt_reason", "—")
        self._set_step_state("dt", "ok", dt_reason)

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
    def _fill_decision(self, decision: dict, course: dict, steps: dict = None):
        steps = steps or {}
        statu  = decision.get("next", {}).get("statu", 0)
        sayac  = decision.get("next", {}).get("sayac", 0)
        label  = decision.get("label", "?")
        skor   = decision.get("score_final", 0)
        in_muf = decision.get("in_mufredat_this_year", False)
        is_gt  = decision.get("is_ground_truth", False)
        sm     = decision.get("sm_note", "")
        prev   = decision.get("prev", {})
        dt_reason = steps.get("dt_reason", "")

        # Renk
        colors = _STATU_COLORS.get(statu, _DEFAULT_COLOR)
        self.lbl_statu_big.config(
            text=_STATU_LABELS.get(statu, label),
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
            f"Kesinlesme : {skor:.2f} / 100\n"
            f"Mufredata  : {'Evet' if in_muf else 'Hayir'}\n"
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
            self.btn_start.config(state="normal", text="Analizi Baslar")

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
