# -*- coding: utf-8 -*-
# =============================================================================
# app/ui/tabs/pool_tab.py — Havuz Yönetimi Sekmesi (Birleşik Görünüm)
# =============================================================================
# Güz ve bahar havuzu TEK birleşik tabloda gösterilir (güz/bahar filtresi yok).
# Sol: Birleşik Havuz (ders + kredi/akts + güz/bahar/yıllık müfredat durumu +
#      öneri/karar/güven/açıklama, renkli durum).
# Sağ: Üstte Güz Müfredatı, altta Bahar Müfredatı (aynı yıl, yan yana
#      karşılaştırılabilir).
#
# Tüm veriler gerçek servis/repository üzerinden gelir
# (CourseCurriculumStatusService + curriculum_repository birleşik paketi).
# =============================================================================

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from app.repositories.curriculum_repository import get_unified_pool_by_year
from app.services.course_curriculum_status_service import FALL
from app.services.yearly_curriculum_integrity_service import check_yearly_curriculum_integrity

# Durum rengi jetonu -> (arka plan, yazı rengi). Servisten gelen status_color ile eşleşir.
_COLOR_TAGS: dict[str, tuple[str, str]] = {
    "green": ("#d4edda", "#155724"),   # müfredatta
    "blue": ("#dbeafe", "#1e3a8a"),    # havuzda
    "yellow": ("#fff9c4", "#854d0e"),  # inceleme
    "red": ("#fee2e2", "#991b1b"),     # çakışma / tekrar eklenemez
    "purple": ("#ede9fe", "#5b21b6"),  # yeni öneri
    "gray": ("#e5e7eb", "#475569"),    # hesaplanmadı / veri yok
}

# Havuz statü (havuz.statu) kısa etiketleri
_POOL_STATU_LABEL = {
    1: "Müfredatta",
    0: "Havuzda",
    -1: "Dinlenmede",
    -2: "İptal",
}

_FILTERS = [
    "Tümü",
    "Havuzda",
    "Müfredatta",
    "Güzde",
    "Baharda",
    "Çakışma",
    "Tekrar eklenemez",
    "Yeni öneri",
]


class PoolTab(ttk.Frame):
    """Birleşik havuz + Güz/Bahar müfredat karşılaştırma ekranı."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self.db_path = getattr(app, "db_path", None)
        self._pool_rows: list[dict[str, Any]] = []
        self.var_filter = tk.StringVar(value="Tümü")
        self.var_search = tk.StringVar()
        self._build_ui()
        self.after(200, self.refresh)

    # =========================================================
    #  PUBLIC
    # =========================================================
    def refresh(self, select_latest_year: bool = False):
        self.db_path = getattr(self.app, "db_path", self.db_path)
        prev_fak = self.cb_fakulte.get()
        prev_bol = self.cb_bolum.get()
        prev_yil = self.cb_yil.get()
        self.load_faculties_to_combo(force_latest_year=select_latest_year)
        if not select_latest_year and prev_fak:
            try:
                if prev_fak in list(self.cb_fakulte.cget("values") or []):
                    self.cb_fakulte.set(prev_fak)
            except Exception:
                pass
            self.on_faculty_change(None)
            for combo, prev in ((self.cb_bolum, prev_bol), (self.cb_yil, prev_yil)):
                try:
                    if prev and prev in list(combo.cget("values") or []):
                        combo.set(prev)
                except Exception:
                    pass
        self.load_pool_data()

    # =========================================================
    #  UI
    # =========================================================
    def _build_ui(self):
        top = tk.Frame(self, bg="#f1f5f9", pady=8, padx=10)
        top.pack(fill=tk.X)

        tk.Label(top, text="Fakülte:", bg="#f1f5f9", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=4)
        self.cb_fakulte = ttk.Combobox(top, state="readonly", width=30)
        self.cb_fakulte.pack(side=tk.LEFT, padx=4)
        self.cb_fakulte.bind("<<ComboboxSelected>>", self.on_faculty_change)

        tk.Label(top, text="Bölüm:", bg="#f1f5f9", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(12, 4))
        self.cb_bolum = ttk.Combobox(top, state="readonly", width=24)
        self.cb_bolum.pack(side=tk.LEFT, padx=4)
        self.cb_bolum.bind("<<ComboboxSelected>>", lambda e: self.load_pool_data())

        tk.Label(top, text="Yıl:", bg="#f1f5f9", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(12, 4))
        self.cb_yil = ttk.Combobox(top, state="readonly", values=[], width=8)
        self.cb_yil.pack(side=tk.LEFT, padx=4)
        self.cb_yil.set("")
        self.cb_yil.bind("<<ComboboxSelected>>", lambda e: self.load_pool_data())

        ttk.Button(top, text="Yenile", command=self.load_pool_data).pack(side=tk.LEFT, padx=14)
        ttk.Button(top, text="Yıllık Bütünlük / Sağlık", command=self.run_pool_health_check).pack(side=tk.LEFT)

        # Arama + filtre + havuz statü aksiyonları
        actions = tk.Frame(self, bg="#e2e8f0", pady=5, padx=8)
        actions.pack(fill=tk.X)
        tk.Label(actions, text="Ara:", bg="#e2e8f0", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        entry = ttk.Entry(actions, textvariable=self.var_search, width=22)
        entry.pack(side=tk.LEFT, padx=(4, 12))
        entry.bind("<KeyRelease>", lambda e: self._render_pool_table())
        tk.Label(actions, text="Filtre:", bg="#e2e8f0", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        filter_combo = ttk.Combobox(actions, textvariable=self.var_filter, values=_FILTERS, width=16, state="readonly")
        filter_combo.pack(side=tk.LEFT, padx=(4, 12))
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self._render_pool_table())

        # Havuz statü aksiyonları — sonraki yıl müfredatı oluşturulunca GİZLENİR
        # (hesaplanmış havuz üzerinde değişiklik yapılması doğru olmaz).
        self._pool_action_frame = tk.Frame(actions, bg="#e2e8f0")
        self._pool_action_frame.pack(side=tk.LEFT)
        ttk.Button(self._pool_action_frame, text="Seçileni Havuzda Yap (0)", command=lambda: self.set_selected_pool_status(0)).pack(side=tk.LEFT, padx=3)
        ttk.Button(self._pool_action_frame, text="Dinlenmeye Al (-1)", command=lambda: self.set_selected_pool_status(-1)).pack(side=tk.LEFT, padx=3)
        ttk.Button(self._pool_action_frame, text="Kalıcı İptal (-2)", command=lambda: self.set_selected_pool_status(-2)).pack(side=tk.LEFT, padx=3)
        self._pool_action_locked_lbl = tk.Label(
            actions, text="", bg="#e2e8f0", fg="#991b1b", font=("Segoe UI", 8, "bold"),
        )

        self.lbl_summary = tk.Label(actions, text="", bg="#e2e8f0", fg="#334155", font=("Segoe UI", 8, "italic"))
        self.lbl_summary.pack(side=tk.RIGHT, padx=6)

        self._build_legend()

        # Split: sol birleşik havuz | sağ (üst güz / alt bahar müfredatı)
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=5, bg="#cbd5e1")
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=4)

        left = tk.Frame(paned, bg="white")
        paned.add(left, width=980, minsize=600)
        tk.Label(left, text="BİRLEŞİK HAVUZ (Güz + Bahar)", bg="#dbeafe", font=("Segoe UI", 10, "bold")).pack(fill=tk.X)
        self._build_pool_tree(left)

        right = tk.Frame(paned, bg="white")
        paned.add(right, minsize=360)
        right_paned = tk.PanedWindow(right, orient=tk.VERTICAL, sashwidth=5, bg="#cbd5e1")
        right_paned.pack(fill=tk.BOTH, expand=True)

        fall_box = tk.Frame(right_paned, bg="white")
        right_paned.add(fall_box, minsize=140)
        tk.Label(fall_box, text="GÜZ MÜFREDATI", bg="#dcfce7", font=("Segoe UI", 10, "bold")).pack(fill=tk.X)
        self.tree_fall = self._build_curr_tree(fall_box)

        spring_box = tk.Frame(right_paned, bg="white")
        right_paned.add(spring_box, minsize=140)
        tk.Label(spring_box, text="BAHAR MÜFREDATI", bg="#fef9c3", font=("Segoe UI", 10, "bold")).pack(fill=tk.X)
        self.tree_spring = self._build_curr_tree(spring_box)

        # §1.3: "Örnek Öğrenci Seçimi" modülü kaldırıldı (gereksiz). Yöntem
        # open_student_simulation kod tabanında bırakıldı (çağrısız), ileride temizlenebilir.

    def _build_legend(self):
        legend = tk.Frame(self, bg="#f8fafc")
        legend.pack(fill=tk.X, padx=6, pady=(2, 0))
        items = [
            ("blue", "Havuzda"),
            ("green", "Müfredatta"),
            ("purple", "Yeni öneri"),
            ("red", "Çakışma / tekrar eklenemez"),
            ("gray", "Veri yok"),
        ]
        for color, text in items:
            bg, fg = _COLOR_TAGS[color]
            tk.Label(legend, text=f" {text} ", bg=bg, fg=fg, font=("Segoe UI", 8), padx=6).pack(side=tk.LEFT, padx=3, pady=2)

    def _configure_color_tags(self, tree: ttk.Treeview) -> None:
        for name, (bg, fg) in _COLOR_TAGS.items():
            tree.tag_configure(name, background=bg, foreground=fg)

    def _build_pool_tree(self, parent):
        cols = ("code", "name", "credit", "ects", "pool", "fall", "spring", "yearly", "reco", "decision", "confidence", "explanation")
        tree = ttk.Treeview(parent, columns=cols, show="headings", selectmode="extended")
        headings = {
            "code": ("Kod", 90), "name": ("Ders Adı", 210), "credit": ("Kredi", 50), "ects": ("AKTS", 50),
            "pool": ("Havuz Durumu", 100), "fall": ("Güz", 45), "spring": ("Bahar", 50), "yearly": ("Yıllık", 50),
            "reco": ("Öneri", 150), "decision": ("Karar", 170), "confidence": ("Güven", 60), "explanation": ("Açıklama", 320),
        }
        for col, (text, width) in headings.items():
            tree.heading(col, text=text)
            anchor = tk.CENTER if col in ("credit", "ects", "fall", "spring", "yearly", "confidence") else tk.W
            tree.column(col, width=width, anchor=anchor)
        self._configure_color_tags(tree)
        sb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True)
        self.tree_pool = tree

    def _build_curr_tree(self, parent) -> ttk.Treeview:
        cols = ("code", "name", "credit", "ects", "term", "status", "note")
        tree = ttk.Treeview(parent, columns=cols, show="headings")
        headings = {
            "code": ("Kod", 90), "name": ("Ders Adı", 200), "credit": ("Kredi", 50), "ects": ("AKTS", 50),
            "term": ("Dönem", 60), "status": ("Müfredat Durumu", 130), "note": ("Açıklama", 220),
        }
        for col, (text, width) in headings.items():
            tree.heading(col, text=text)
            anchor = tk.CENTER if col in ("credit", "ects", "term") else tk.W
            tree.column(col, width=width, anchor=anchor)
        self._configure_color_tags(tree)
        sb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True)
        return tree

    # =========================================================
    #  FİLTRE / KAPSAM ÇÖZÜMLEME
    # =========================================================
    def load_faculties_to_combo(self, force_latest_year=False):
        try:
            _, rows = self.db.run_sql("SELECT ad FROM fakulte ORDER BY ad")
            faculties = [r[0] for r in (rows or [])]
            self.cb_fakulte["values"] = faculties
            if faculties and self.cb_fakulte.current() < 0:
                self.cb_fakulte.current(0)
            if faculties:
                self.on_faculty_change(None, force_latest_year=force_latest_year)
        except Exception:
            pass

    def _refresh_years_for_faculty(self, fakulte_id: int, force_latest_year: bool = False):
        years: list[int] = []
        try:
            _, rows = self.db.run_sql(
                """
                SELECT DISTINCT m.akademik_yil
                FROM mufredat m JOIN bolum b ON b.bolum_id = m.bolum_id
                WHERE b.fakulte_id = ? ORDER BY 1
                """,
                (int(fakulte_id),),
            )
            years = sorted({int(r[0]) for r in (rows or []) if r and r[0] is not None})
        except Exception:
            years = []
        # Havuzdan da yıl topla (müfredat olmasa bile havuz olabilir)
        try:
            _, hrows = self.db.run_sql(
                "SELECT DISTINCT yil FROM havuz WHERE fakulte_id = ? ORDER BY 1", (int(fakulte_id),)
            )
            for r in (hrows or []):
                if r and r[0] is not None:
                    years.append(int(r[0]))
        except Exception:
            pass
        years = sorted(set(years))
        yil_values = [str(y) for y in years]
        self.cb_yil["values"] = yil_values
        if yil_values and (force_latest_year or self.cb_yil.get() not in yil_values):
            self.cb_yil.set(yil_values[-1])

    def on_faculty_change(self, _event, force_latest_year: bool = False):
        fakulte = self.cb_fakulte.get()
        if not fakulte:
            return
        try:
            fid = self._faculty_id(fakulte)
            if fid is None:
                return
            _, rows_b = self.db.run_sql("SELECT ad FROM bolum WHERE fakulte_id = ? ORDER BY ad", (fid,))
            bolumler = ["Fakülte Geneli"] + [r[0] for r in (rows_b or [])]
            self.cb_bolum["values"] = bolumler
            if self.cb_bolum.current() < 0:
                self.cb_bolum.current(0)
            self._refresh_years_for_faculty(fid, force_latest_year=force_latest_year)
            self.load_pool_data()
        except Exception:
            pass

    def _faculty_id(self, name: str) -> int | None:
        try:
            _, rows = self.db.run_sql("SELECT fakulte_id FROM fakulte WHERE ad = ? LIMIT 1", (name,))
            if rows and rows[0] and rows[0][0] is not None:
                return int(rows[0][0])
        except Exception:
            return None
        return None

    def _department_id(self, faculty_id: int, name: str) -> int | None:
        if not name or name == "Fakülte Geneli":
            return None
        try:
            _, rows = self.db.run_sql(
                "SELECT bolum_id FROM bolum WHERE fakulte_id = ? AND ad = ? LIMIT 1", (int(faculty_id), name)
            )
            if rows and rows[0] and rows[0][0] is not None:
                return int(rows[0][0])
        except Exception:
            return None
        return None

    # =========================================================
    #  VERİ YÜKLEME
    # =========================================================
    def _next_year_curriculum_exists(self, conn, faculty_id, department_id, year: int) -> bool:
        """Bu havuz yılından (year) sonraki yıl (year+1) için müfredat üretilmiş mi?"""
        try:
            cur = conn.cursor()
            params: list = [int(year) + 1]
            scope = ""
            if department_id is not None:
                scope = " AND m.bolum_id = ?"; params.append(int(department_id))
            elif faculty_id is not None:
                scope = " AND b.fakulte_id = ?"; params.append(int(faculty_id))
            cur.execute(
                "SELECT 1 FROM mufredat m "
                "JOIN bolum b ON b.bolum_id=m.bolum_id "
                "JOIN mufredat_ders md ON md.mufredat_id=m.mufredat_id "
                f"WHERE m.akademik_yil = ?{scope} LIMIT 1",
                params,
            )
            return cur.fetchone() is not None
        except Exception:
            return False

    def _update_pool_action_visibility(self, conn, faculty_id, department_id, year: int):
        """§4: Sonraki yıl müfredatı oluşturulduysa havuz statü butonlarını gizle/kilitle."""
        locked = self._next_year_curriculum_exists(conn, faculty_id, department_id, year)
        frame = getattr(self, "_pool_action_frame", None)
        lbl = getattr(self, "_pool_action_locked_lbl", None)
        if frame is None or lbl is None:
            return
        if locked:
            if frame.winfo_manager() == "pack":
                frame.pack_forget()
            lbl.config(
                text=f"🔒 {year + 1} müfredatı oluşturulduğu için {year} havuzunda statü değişikliği kapalı."
            )
            if lbl.winfo_manager() != "pack":
                lbl.pack(side=tk.LEFT, padx=6)
        else:
            if lbl.winfo_manager() == "pack":
                lbl.pack_forget()
            if frame.winfo_manager() != "pack":
                frame.pack(side=tk.LEFT)

    def load_pool_data(self):
        fakulte = self.cb_fakulte.get()
        yil = self.cb_yil.get()
        if not fakulte or not yil:
            return
        faculty_id = self._faculty_id(fakulte)
        if faculty_id is None:
            return
        department_id = self._department_id(faculty_id, self.cb_bolum.get())
        conn = getattr(self.db, "conn", None)
        if conn is None:
            return
        try:
            bundle = get_unified_pool_by_year(conn, int(yil), faculty_id, department_id)
        except Exception as exc:
            self.lbl_summary.config(text=f"Havuz verisi yüklenemedi: {exc}")
            return

        self._pool_rows = bundle.get("pool_courses", [])
        fall = bundle.get("fall_curriculum", [])
        spring = bundle.get("spring_curriculum", [])
        summary = bundle.get("summary", {})

        # Çakışma (her iki dönem) tespiti — müfredat panelleri için
        fall_ids = {r["course_id"] for r in fall}
        spring_ids = {r["course_id"] for r in spring}
        conflicts = fall_ids & spring_ids

        self._render_pool_table()
        self._fill_curriculum_tree(self.tree_fall, fall, conflicts)
        self._fill_curriculum_tree(self.tree_spring, spring, conflicts)
        self._update_pool_action_visibility(conn, faculty_id, department_id, int(yil))

        self.lbl_summary.config(
            text=(
                f"Güz: {summary.get('fall_count', 0)}  |  Bahar: {summary.get('spring_count', 0)}  |  "
                f"Yıllık: {summary.get('yearly_total', 0)}  |  Havuz: {summary.get('pool_count', 0)}  |  "
                f"Yeni öneri: {summary.get('new_suggestion_count', 0)}  |  Çakışma: {summary.get('conflict_count', 0)}"
            )
        )

    def _filter_match(self, row: dict[str, Any]) -> bool:
        flt = self.var_filter.get()
        search = (self.var_search.get() or "").strip().lower()
        if search:
            hay = f"{row.get('course_code', '')} {row.get('course_name', '')}".lower()
            if search not in hay:
                return False
        if flt == "Tümü":
            return True
        if flt == "Havuzda":
            return bool(row.get("in_pool")) and not bool(row.get("in_yearly_curriculum"))
        if flt == "Müfredatta":
            return bool(row.get("in_yearly_curriculum"))
        if flt == "Güzde":
            return bool(row.get("in_fall_curriculum"))
        if flt == "Baharda":
            return bool(row.get("in_spring_curriculum"))
        if flt == "Çakışma":
            return row.get("status_code") == "conflict_both_terms"
        if flt == "Tekrar eklenemez":
            return bool(row.get("in_yearly_curriculum"))
        if flt == "Yeni öneri":
            return bool(row.get("in_pool")) and not bool(row.get("in_yearly_curriculum"))
        return True

    def _render_pool_table(self):
        tree = self.tree_pool
        tree.delete(*tree.get_children())
        shown = 0
        for row in self._pool_rows:
            if not self._filter_match(row):
                continue
            pool_status = row.get("pool_status")
            pool_label = _POOL_STATU_LABEL.get(pool_status, "-") if pool_status is not None else "-"
            confidence = row.get("confidence_score")
            conf_txt = f"{float(confidence):.2f}" if confidence is not None else "-"
            # Yeni öneri ise renk morumsu olsun (havuz adayı, müfredatta değil)
            color = row.get("status_color") or "gray"
            if color == "blue" and row.get("in_pool") and not row.get("in_yearly_curriculum"):
                color = "purple"
            tree.insert(
                "",
                tk.END,
                values=(
                    row.get("course_code") or row.get("course_id"),
                    row.get("course_name") or "",
                    row.get("credit") if row.get("credit") is not None else "-",
                    row.get("ects") if row.get("ects") is not None else "-",
                    pool_label,
                    "✓" if row.get("in_fall_curriculum") else "—",
                    "✓" if row.get("in_spring_curriculum") else "—",
                    "✓" if row.get("in_yearly_curriculum") else "—",
                    row.get("recommendation_status") or row.get("recommendation") or "",
                    row.get("final_decision") or row.get("status_label") or "",
                    conf_txt,
                    row.get("explanation") or "",
                ),
                tags=(color,),
            )
            shown += 1
        if shown == 0:
            tree.insert("", tk.END, values=("", "Kayıt yok / kapsam boş.", "", "", "", "", "", "", "", "", "", ""), tags=("gray",))

    def _fill_curriculum_tree(self, tree: ttk.Treeview, rows: list[dict[str, Any]], conflicts: set[int]) -> None:
        tree.delete(*tree.get_children())
        if not rows:
            tree.insert("", tk.END, values=("", "Müfredat dersi yok.", "", "", "", "", ""), tags=("gray",))
            return
        for row in rows:
            cid = row["course_id"]
            is_conflict = cid in conflicts
            note = "Her iki dönemde de var (çakışma)" if is_conflict else "Yıllık müfredatta"
            tree.insert(
                "",
                tk.END,
                values=(
                    row.get("course_code") or cid,
                    row.get("course_name") or "",
                    row.get("credit") if row.get("credit") is not None else "-",
                    row.get("ects") if row.get("ects") is not None else "-",
                    "Güz" if row.get("term") == FALL else "Bahar",
                    row.get("curriculum_status") or "Müfredatta",
                    note,
                ),
                tags=("red" if is_conflict else "green",),
            )

    # =========================================================
    #  AKSİYONLAR
    # =========================================================
    def _selected_pool_course_ids(self) -> list[int]:
        out: list[int] = []
        for it in self.tree_pool.selection():
            vals = self.tree_pool.item(it)["values"]
            if not vals:
                continue
            # ilk kolon kod; course_id'yi _pool_rows üzerinden eşle
            code = str(vals[0])
            match = next((r for r in self._pool_rows if str(r.get("course_code")) == code), None)
            if match:
                out.append(int(match["course_id"]))
        return out

    def set_selected_pool_status(self, new_status: int):
        course_ids = self._selected_pool_course_ids()
        if not course_ids:
            messagebox.showinfo("Bilgi", "Önce havuzdan ders seçin.")
            return
        fakulte = self.cb_fakulte.get()
        yil = self.cb_yil.get()
        if not (fakulte and yil):
            return
        faculty_id = self._faculty_id(fakulte)
        if faculty_id is None:
            return
        # §4: Sonraki yıl müfredatı oluşturulmuşsa hesaplanmış havuz kilitli.
        conn = getattr(self.db, "conn", None)
        department_id = self._department_id(faculty_id, self.cb_bolum.get())
        if conn is not None and self._next_year_curriculum_exists(conn, faculty_id, department_id, int(yil)):
            messagebox.showwarning(
                "Havuz Kilitli",
                f"{int(yil) + 1} müfredatı oluşturulduğu için {yil} havuzunda statü değişikliği "
                "yapılamaz (hesaplanmış havuz korunur).",
            )
            return
        try:
            for ders_id in course_ids:
                # Birleşik yönetim: dersin o yıl/fakülte tüm dönem havuz satırlarını günceller.
                self.db.run_sql(
                    "UPDATE havuz SET statu = ? WHERE CAST(ders_id AS INTEGER) = ? AND yil = ? AND fakulte_id = ?",
                    (int(new_status), int(ders_id), int(yil), int(faculty_id)),
                )
            self.load_pool_data()
        except Exception as e:
            messagebox.showerror("Güncelleme Hatası", str(e))

    def run_pool_health_check(self):
        fakulte = self.cb_fakulte.get()
        yil = self.cb_yil.get()
        if not fakulte or not yil:
            messagebox.showwarning("Eksik Seçim", "Lütfen önce fakülte ve yıl seçin.")
            return
        faculty_id = self._faculty_id(fakulte)
        if faculty_id is None:
            return
        department_id = self._department_id(faculty_id, self.cb_bolum.get())
        conn = getattr(self.db, "conn", None)
        if conn is None:
            return
        try:
            report = check_yearly_curriculum_integrity(conn, int(yil), faculty_id, department_id)
        except Exception as e:
            messagebox.showerror("Hata", f"Bütünlük kontrolü çalıştırılamadı:\n{e}")
            return
        summary = report.get("summary", {})
        lines = [
            f"Fakülte: {fakulte}  |  Yıl: {yil}",
            f"Durum: {report.get('status')}",
            "",
            f"Güz müfredatı     : {summary.get('fall_count', 0)} ders",
            f"Bahar müfredatı   : {summary.get('spring_count', 0)} ders",
            f"Yıllık toplam     : {summary.get('yearly_total', 0)} ders",
            f"Havuz             : {summary.get('pool_count', 0)} ders",
            f"Yeni öneri        : {summary.get('new_suggestion_count', 0)} ders",
            f"Çakışma           : {summary.get('conflict_count', 0)} ders",
        ]
        issues = report.get("issues") or []
        if issues:
            lines.append("")
            lines.append("Bulgular:")
            for issue in issues:
                lines.append(f"  [{issue.get('severity', '').upper()}] {issue.get('message', '')}")
        messagebox.showinfo("Yıllık Müfredat Bütünlük / Havuz Sağlık", "\n".join(lines))

    def run_decision_engine(self):
        messagebox.showinfo("Bilgi", "Lütfen 'Hesaplama & Test' sekmesinden 'Otomatik Puanlama' butonunu kullanın.")

    # =========================================================
    #  SİMÜLASYON
    # =========================================================
    def open_student_simulation(self):
        courses = []
        for tree in (self.tree_fall, self.tree_spring):
            for item in tree.get_children():
                vals = tree.item(item)["values"]
                if vals and vals[1] and vals[1] != "Müfredat dersi yok.":
                    courses.append((vals[0], vals[1], vals[4]))
        if not courses:
            messagebox.showwarning("Uyarı", "Müfredatta ders yok! Önce müfredat oluşturun.")
            return
        sim_win = tk.Toplevel(self)
        sim_win.title(f"Öğrenci Ders Seçim Ekranı - {self.cb_yil.get()}")
        sim_win.geometry("640x540")
        sim_win.configure(bg="#f8fafc")
        tk.Label(
            sim_win, text=f"{self.cb_yil.get()} DERS SEÇİMİ (Güz + Bahar)",
            font=("Segoe UI", 14, "bold"), bg="#f8fafc", fg="#1e293b",
        ).pack(pady=14)
        tk.Label(
            sim_win, text="Müfredat komisyonunca onaylanan dersler aşağıdadır. Almak istediklerinizi işaretleyin.",
            bg="#f8fafc",
        ).pack(pady=(0, 8))
        check_frame = tk.Frame(sim_win, bg="white", relief="groove", bd=1)
        check_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=8)
        vars_list = []
        for code, name, term in courses:
            var = tk.IntVar()
            tk.Checkbutton(
                check_frame, text=f"[{term}] {code} - {name}", variable=var, bg="white",
                font=("Segoe UI", 10), anchor="w", padx=10, pady=3,
            ).pack(fill=tk.X)
            vars_list.append((f"{code} - {name}", var))

        def save_selection():
            secilen = [n for n, v in vars_list if v.get() == 1]
            if not secilen:
                messagebox.showwarning("Uyarı", "Hiç ders seçmediniz!")
                return
            messagebox.showinfo("Onay", "Seçilen Dersler:\n\n" + "\n".join(f"  + {s}" for s in secilen) + "\n\nKaydınız tamamlandı!")
            sim_win.destroy()

        tk.Button(
            sim_win, text="Seçimi Onayla ve Kaydet", bg="#22c55e", fg="white",
            font=("Segoe UI", 10, "bold"), command=save_selection,
        ).pack(pady=18, ipadx=10)
