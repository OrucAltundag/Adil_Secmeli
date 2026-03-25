# -*- coding: utf-8 -*-
# =============================================================================
# app/ui/tabs/pool_tab.py â€” Havuz Yonetimi Sekmesi
# =============================================================================
# Ders havuzunu fakulte/bolum/yil/donem bazinda goruntuler.
# Sol panel: Havuz tablosu (statu renklendirme, strikeout iptal, skor gorunumu)
# Sag panel: Secili bolumun mufredat dersleri
#
# Statu renk kodlari:
#   1  Mufredatta (yesil) | 0 Havuzda (sari)
#  -1  Dinlenmede (turuncu) | -2 Iptal (gri + ustu cizili)
#
# Saglik kontrolu: havuz-mufredat tutarliligini denetler.
# Ogrenci simÃ¼lasyonu: mufredattan ornek ders secim ekrani acar.
# =============================================================================

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont

from app.services.calculation import (
    ensure_pool_visibility_for_curriculum,
    get_faculty_year_topsis_results,
    persist_faculty_year_topsis_scores,
)
from app.services.course_type import build_elective_predicate

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
    - Fakulte / Bolum / Yil filtreleri (dinamik)
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
    def refresh(self, select_latest_year=False):
        self.db_path = getattr(self.app, "db_path", self.db_path)
        prev_fak = self.cb_fakulte.get()
        prev_bol = self.cb_bolum.get()
        prev_yil = self.cb_yil.get()
        prev_donem = self.cb_donem.get()

        self.load_faculties_to_combo(force_latest_year=select_latest_year)

        if not select_latest_year and prev_fak:
            try:
                vals = list(self.cb_fakulte.cget("values") or [])
                if prev_fak in vals:
                    self.cb_fakulte.set(prev_fak)
            except Exception:
                pass
            self.on_faculty_change(None)
            if prev_bol:
                try:
                    bvals = list(self.cb_bolum.cget("values") or [])
                    if prev_bol in bvals:
                        self.cb_bolum.set(prev_bol)
                except Exception:
                    pass
            if prev_yil:
                try:
                    yvals = list(self.cb_yil.cget("values") or [])
                    if prev_yil in yvals:
                        self.cb_yil.set(prev_yil)
                except Exception:
                    pass
            if prev_donem:
                try:
                    self.cb_donem.set(prev_donem)
                except Exception:
                    pass

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
            values=[],
            width=8
        )
        self.cb_yil.pack(side=tk.LEFT, padx=4)
        self.cb_yil.set("")
        self.cb_yil.bind("<<ComboboxSelected>>", lambda e: self.load_pool_data())

        tk.Label(top, text="Donem:", bg="#f1f5f9",
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(12, 4))
        self.cb_donem = ttk.Combobox(top, state="readonly", values=["Guz", "Bahar"], width=8)
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

        ttk.Button(
            actions,
            text="Saglik Kontrolu (Fakulte/Yil)",
            command=self.run_pool_health_check,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(actions, text="Secileni Dinlenmeye Al (-1)",
                   command=lambda: self.set_selected_pool_status(-1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions, text="Secileni Havuzda Yap (0)",
                   command=lambda: self.set_selected_pool_status(0)).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions, text="Secileni Kalici Iptal (-2)",
                   command=lambda: self.set_selected_pool_status(-2)).pack(side=tk.LEFT, padx=5)

        # "Algoritmay Calistir" kaldirildi â€” algoritma islemleri Hesaplama sekmesindedir.

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
        cols = ("ders_id", "ders_adi", "kaynak_bolum", "statu_etiket", "sayac", "skor", "yil")
        self.tree_pool = ttk.Treeview(
            parent, columns=cols, show="headings", selectmode="extended"
        )

        self.tree_pool.heading("ders_id",      text="ID")
        self.tree_pool.heading("ders_adi",     text="Ders Adi")
        self.tree_pool.heading("kaynak_bolum", text="Kaynak Bolum")
        self.tree_pool.heading("statu_etiket", text="Durum")
        self.tree_pool.heading("sayac",        text="Sayac")
        self.tree_pool.heading("skor",         text="Kesinesme Puani")
        self.tree_pool.heading("yil",          text="Yil")

        self.tree_pool.column("ders_id",      width=45,  anchor="center")
        self.tree_pool.column("ders_adi",     width=270)
        self.tree_pool.column("kaynak_bolum", width=170)
        self.tree_pool.column("statu_etiket", width=175, anchor="center")
        self.tree_pool.column("sayac",        width=55,  anchor="center")
        self.tree_pool.column("skor",         width=110, anchor="center")
        self.tree_pool.column("yil",          width=50,  anchor="center")

        # Renk etiketleri â€” normal satirlar
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

        # Sayac tooltip'i kullanici talebiyle kapatildi.
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
        # Tooltip davranisi kapatildi.
        self._hide_tooltip()
        return

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
    def _ensure_year_scores(self, fakulte_id: int, yil: int, donem: str = "G") -> None:
        """
        Secili fakulte + yil icin TOPSIS tabanli kesinlesme puanlarini
        hesaplayip havuz.skor alanina yazar.

        Havuz ekranina gelindiginde, puanlar daha once hesaplanmamis olsa bile
        yil bazli skorlar guncellenmis olur.
        """
        try:
            conn = getattr(self.db, "conn", None)
            if conn is None:
                return
            cur = conn.cursor()
            fakulte_id = int(fakulte_id)

            pack = get_faculty_year_topsis_results(
                cur=cur,
                fakulte_id=fakulte_id,
                akademik_yil=int(yil),
                donem=donem,
            )
            if not pack.get("ok"):
                return

            skor_map = dict(pack.get("scores") or {})
            ders_meta = dict(pack.get("ders_meta") or {})
            if not skor_map:
                return

            persist_faculty_year_topsis_scores(
                cur=cur,
                fakulte_id=fakulte_id,
                akademik_yil=int(yil),
                skor_map=skor_map,
                ders_meta=ders_meta,
                donem=donem,
            )
            conn.commit()
        except Exception as exc:
            print(f"UI Hata (Yil TOPSIS): {exc}")

    def load_faculties_to_combo(self, force_latest_year=False):
        try:
            _, rows = self.db.run_sql("SELECT ad FROM fakulte ORDER BY ad")
            faculties = [r[0] for r in (rows or [])]
            self.cb_fakulte["values"] = faculties
            if faculties and self.cb_fakulte.current() < 0:
                self.cb_fakulte.current(0)

            try:
                _, yil_rows = self.db.run_sql(
                    """
                    SELECT DISTINCT yil FROM (
                        SELECT yil as yil FROM havuz
                        UNION
                        SELECT akademik_yil as yil FROM mufredat
                    )
                    ORDER BY yil
                    """
                )
                if yil_rows:
                    yillar = [str(r[0]) for r in yil_rows]
                    self.cb_yil["values"] = yillar
                    if force_latest_year or self.cb_yil.get() not in yillar:
                        self.cb_yil.set(yillar[-1])
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
        """Secili fakulte/bolum/yil icin havuz ve mufredat verilerini ceker, tablolara basar."""
        fakulte = self.cb_fakulte.get()
        bolum   = self.cb_bolum.get()
        yil     = self.cb_yil.get()
        donem = getattr(self, "cb_donem", None) and self.cb_donem.get() or "Guz"
        donem_norm = str(donem).strip() or "Guz"

        if not fakulte or not yil:
            return

        # Fakulte ID'sini kesin olarak cozumle (ad LIKE degil, birebir)
        fakulte_id = None
        try:
            _, fid_rows = self.db.run_sql(
                "SELECT fakulte_id FROM fakulte WHERE ad = ? LIMIT 1",
                (fakulte,),
            )
            if fid_rows and fid_rows[0] and fid_rows[0][0] is not None:
                fakulte_id = int(fid_rows[0][0])
        except Exception:
            fakulte_id = None

        if fakulte_id is None:
            return

        bolum_id = None
        if bolum:
            try:
                _, bid_rows = self.db.run_sql(
                    "SELECT bolum_id FROM bolum WHERE fakulte_id = ? AND ad = ? LIMIT 1",
                    (int(fakulte_id), bolum),
                )
                if bid_rows and bid_rows[0] and bid_rows[0][0] is not None:
                    bolum_id = int(bid_rows[0][0])
            except Exception:
                bolum_id = None

        # Secili fakulte + yil icin kesinlesme puanlarini hesapla ve havuza yaz
        try:
            conn = getattr(self.db, "conn", None)
            if conn is not None:
                cur = conn.cursor()
                ensure_pool_visibility_for_curriculum(
                    cur=cur,
                    fakulte_id=fakulte_id,
                    akademik_yil=int(yil),
                    donem=donem_norm,
                )
                conn.commit()
        except Exception:
            pass

        try:
            self._ensure_year_scores(fakulte_id, int(yil), donem=donem_norm)
        except Exception:
            pass

        # --- SOL: HAVUZ ---
        self.tree_pool.delete(*self.tree_pool.get_children())

        extra_where = "AND h.statu NOT IN (-1, -2)" if self.hide_resting else ""
        elective_predicate = "0=1"
        try:
            conn = getattr(self.db, "conn", None)
            if conn is not None:
                elective_predicate = build_elective_predicate(conn.cursor(), alias="d")
        except Exception:
            elective_predicate = "0=1"

        q_pool = f"""
            SELECT DISTINCT
                h.ders_id,
                d.ad,
                h.statu,
                h.sayac,
                h.skor,
                h.yil,
                COALESCE(d.bolum_id, h.bolum_id) AS kaynak_bolum_id,
                b.ad AS kaynak_bolum
            FROM havuz h
            LEFT JOIN ders d ON CAST(h.ders_id AS INTEGER) = d.ders_id
            LEFT JOIN bolum b ON b.bolum_id = COALESCE(d.bolum_id, h.bolum_id)
            WHERE h.fakulte_id = ?
              AND h.yil = ?
              AND LOWER(SUBSTR(TRIM(COALESCE(h.donem,'')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
              AND {elective_predicate}
              {extra_where}
            ORDER BY
                CASE WHEN h.skor IS NULL THEN 1 ELSE 0 END,
                h.skor DESC,
                h.statu DESC,
                d.ad
        """
        try:
            _, rows = self.db.run_sql(
                q_pool,
                (int(fakulte_id), int(yil), donem_norm),
            )
            seen = set()
            for d_id, d_ad, statu, sayac, skor, y, _kaynak_bolum_id, kaynak_bolum in (rows or []):
                if d_id in seen:
                    continue
                seen.add(d_id)

                s_val = int(statu) if statu is not None else 0
                tag   = _STATU_TAG.get(s_val, "havuzda")
                etkt  = _STATU_ETIKET.get(s_val, f"{s_val}")

                skor_txt  = f"{float(skor):.2f}" if skor is not None else "-"
                sayac_val = int(sayac) if sayac is not None else 0
                kaynak_bolum_txt = str(kaynak_bolum or "-")
                ders_adi_txt = str(d_ad or "")

                self.tree_pool.insert(
                    "", tk.END,
                    values=(d_id, ders_adi_txt, kaynak_bolum_txt, etkt, sayac_val, skor_txt, y),
                    tags=(tag,)
                )
        except Exception as e:
            print(f"UI Hata (Havuz): {e}")

        # --- SAG: MUFREDAT ---
        self.tree_curr.delete(*self.tree_curr.get_children())
        if not bolum:
            return

        donem = getattr(self, "cb_donem", None) and self.cb_donem.get() or "Guz"
        donem_norm = str(donem).strip() or "Guz"

        q_curr = f"""
            SELECT DISTINCT d.ders_id, d.ad, h.skor
            FROM mufredat m
            JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
            JOIN ders d ON md.ders_id = d.ders_id
            JOIN bolum b ON m.bolum_id = b.bolum_id
            LEFT JOIN havuz h ON h.id = (
                SELECT h2.id
                FROM havuz h2
                WHERE CAST(h2.ders_id AS INTEGER) = d.ders_id
                  AND h2.yil = m.akademik_yil
                  AND LOWER(SUBSTR(TRIM(COALESCE(h2.donem, '')), 1, 1)) = LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1))
                ORDER BY
                    CASE WHEN h2.skor IS NULL THEN 1 ELSE 0 END,
                    h2.skor DESC,
                    h2.id DESC
                LIMIT 1
            )
            WHERE b.fakulte_id = ?
              AND m.akademik_yil = ?
              AND b.ad = ?
              AND LOWER(SUBSTR(TRIM(COALESCE(m.donem,'')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
              AND {elective_predicate}
            ORDER BY
                CASE WHEN h.skor IS NULL THEN 1 ELSE 0 END,
                h.skor DESC,
                d.ad
        """
        try:
            _, rows_r = self.db.run_sql(q_curr, (int(fakulte_id), int(yil), bolum, donem_norm))
            seen_r = set()
            for d_id, d_ad, skor in (rows_r or []):
                if d_id in seen_r:
                    continue
                seen_r.add(d_id)
                skor_txt = f"{float(skor):.2f}" if skor is not None else "-"
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
        fakulte = self.cb_fakulte.get()
        yil = self.cb_yil.get()
        if not (fakulte and yil):
            return
        try:
            _, fid_rows = self.db.run_sql(
                "SELECT fakulte_id FROM fakulte WHERE ad = ? LIMIT 1",
                (fakulte,),
            )
            if not fid_rows:
                return
            fakulte_id = int(fid_rows[0][0])
            donem = getattr(self, "cb_donem", None) and self.cb_donem.get() or "Guz"
            for vals in selected:
                ders_id = int(vals[0])
                self.db.run_sql(
                    """
                    UPDATE havuz
                    SET statu = ?
                    WHERE ders_id = ? AND yil = ? AND fakulte_id = ?
                      AND LOWER(SUBSTR(TRIM(COALESCE(donem,'')), 1, 1)) = LOWER(SUBSTR(TRIM(?), 1, 1))
                    """,
                    (int(new_status), ders_id, int(yil), fakulte_id, donem),
                )
            self.load_pool_data()
        except Exception as e:
            messagebox.showerror("Guncelleme Hatasi", str(e))

    def run_pool_health_check(self):
        """Secili fakulte+yil icin havuz statu dagilimi ve mufredat-havuz senkronizasyon raporunu cikartir."""
        fakulte = self.cb_fakulte.get()
        yil = self.cb_yil.get()
        if not fakulte or not yil:
            messagebox.showwarning("Eksik Secim", "Lutfen once fakulte ve yil secin.")
            return

        try:
            _, fid_rows = self.db.run_sql(
                "SELECT fakulte_id FROM fakulte WHERE ad = ? LIMIT 1",
                (fakulte,),
            )
            if not fid_rows or fid_rows[0][0] is None:
                messagebox.showerror("Hata", "Secilen fakulte icin fakulte_id bulunamadi.")
                return
            fakulte_id = int(fid_rows[0][0])
        except Exception as e:
            messagebox.showerror("Hata", f"Fakulte id cozumlenemedi:\n{e}")
            return

        try:
            donem = getattr(self, "cb_donem", None) and self.cb_donem.get() or "Guz"
            donem_norm = str(donem).strip() or "Guz"
            donem_key = donem_norm[0].lower()

            # 1) Havuz statu dagilimi (secili fakulte + yil)
            q_statu = """
                SELECT
                    COALESCE(statu, 0) AS s,
                    COUNT(*) AS adet
                FROM havuz
                WHERE fakulte_id = ? AND yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = ?
                GROUP BY COALESCE(statu, 0)
            """
            _, rows_st = self.db.run_sql(q_statu, (fakulte_id, int(yil), donem_key))
            statu_counts = {int(r[0]): int(r[1]) for r in (rows_st or [])}

            # 2) Mufredatta olup havuzda olmayan dersler
            q_curr_only = """
                SELECT COUNT(DISTINCT md.ders_id) AS adet
                FROM mufredat m
                JOIN bolum b ON b.bolum_id = m.bolum_id
                JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id
                LEFT JOIN havuz h ON (
                    h.fakulte_id = b.fakulte_id
                    AND h.yil = m.akademik_yil
                    AND CAST(h.ders_id AS INTEGER) = md.ders_id
                )
                WHERE b.fakulte_id = ?
                  AND m.akademik_yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = ?
                  AND h.ders_id IS NULL
            """
            _, rows_c = self.db.run_sql(
                q_curr_only,
                (fakulte_id, int(yil), donem_key),
            )
            curr_not_in_pool = int(rows_c[0][0]) if rows_c and rows_c[0] and rows_c[0][0] is not None else 0

            # 3) Havuzda olup ayni yil/donem mufredatinda olmayan dersler
            q_pool_only = """
                SELECT COUNT(DISTINCT CAST(h.ders_id AS INTEGER)) AS adet
                FROM havuz h
                LEFT JOIN mufredat m ON (
                    m.akademik_yil = h.yil
                    AND m.fakulte_id = h.fakulte_id
                    AND LOWER(SUBSTR(TRIM(COALESCE(m.donem, '')), 1, 1)) = ?
                )
                LEFT JOIN mufredat_ders md ON (
                    md.mufredat_id = m.mufredat_id
                    AND md.ders_id = CAST(h.ders_id AS INTEGER)
                )
                WHERE h.fakulte_id = ?
                  AND h.yil = ?
                  AND LOWER(SUBSTR(TRIM(COALESCE(h.donem, '')), 1, 1)) = ?
                  AND md.ders_id IS NULL
            """
            _, rows_p = self.db.run_sql(
                q_pool_only,
                (donem_key, fakulte_id, int(yil), donem_key),
            )
            pool_not_in_curr = int(rows_p[0][0]) if rows_p and rows_p[0] and rows_p[0][0] is not None else 0

            lines = []
            lines.append(f"Fakulte: {fakulte}")
            lines.append(f"Yil: {yil}  Donem: {donem_norm}")
            lines.append("")
            lines.append("Havuz statu dagilimi:")
            lines.append(f"  statu= 1 (Mufredatta): {statu_counts.get(1, 0)}")
            lines.append(f"  statu= 0 (Havuzda):   {statu_counts.get(0, 0)}")
            lines.append(f"  statu=-1 (Dinlenme):  {statu_counts.get(-1, 0)}")
            lines.append(f"  statu=-2 (Iptal):      {statu_counts.get(-2, 0)}")
            lines.append("")
            lines.append("Mufredat / Havuz senkronizasyonu:")
            lines.append(f"  Mufredatta olup havuzda olmayan ders sayisi : {curr_not_in_pool}")
            lines.append(f"  Havuzda olup mufredatta olmayan ders sayisi : {pool_not_in_curr}")

            msg = "\n".join(lines)
            messagebox.showinfo("Havuz Saglik Kontrolu", msg)
        except Exception as e:
            messagebox.showerror("Hata", f"Saglik kontrolu calistirilirken hata olustu:\n{e}")

    def run_decision_engine(self):
        messagebox.showinfo(
            "Bilgi",
            "Lutfen 'Hesaplama & Test' sekmesinden 'Otomatik Puanlama' butonunu kullanin."
        )

    # =========================================================
    #  SIMULASYON
    # =========================================================
    def open_student_simulation(self):
        """Mufredattaki derslerden ogrenci secim simulasyonu penceresi acar."""
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

