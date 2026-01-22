# app/ui/tabs/tools_tab.py
import os
import shutil
import datetime

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import pandas as pd

from app.services.havuz_karar import muhendislik_mufredat_durumunu_esitle


class ToolsTab(ttk.Frame):
    """
    ⚙️ Rapor & Skor Sekmesi

    - Fakülte / Bölüm / Yıl filtreli rapor
    - Havuz + Müfredat tabloları
    - Özet istatistikler
    - CSV / Excel export
    - DB yedek
    - Statü-yıl eşitleme (muhendislik_mufredat_durumunu_esitle)
    """

    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.db = app.db

        self.db_path = getattr(app, "db_path", None)

        # UI refs
        self.cb_fakulte = None
        self.cb_bolum = None
        self.cb_yil = None

        self.lbl_pool_total = None
        self.lbl_pool_avg = None
        self.lbl_pool_rest = None
        self.lbl_pool_chosen = None

        self.tree_pool = None
        self.tree_curr = None

        self.txt_log = None

        self._build_ui()
        self.refresh()

    # =========================================================
    # PUBLIC
    # =========================================================
    def refresh(self):
        """Sekmeye gelince veya 'Yenile' basılınca çağır."""
        self.db_path = getattr(self.app, "db_path", self.db_path)

        self._fill_faculties()
        # seçimler varsa tabloyu bas
        try:
            self.load_report()
        except Exception:
            pass

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):
        # ---------- TOP FILTER BAR ----------
        top = ttk.LabelFrame(self, text="Filtreler", padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Fakülte:").pack(side=tk.LEFT, padx=(0, 6))
        self.cb_fakulte = ttk.Combobox(top, state="readonly", width=28)
        self.cb_fakulte.pack(side=tk.LEFT, padx=(0, 14))
        self.cb_fakulte.bind("<<ComboboxSelected>>", self._on_faculty_change)

        ttk.Label(top, text="Bölüm:").pack(side=tk.LEFT, padx=(0, 6))
        self.cb_bolum = ttk.Combobox(top, state="readonly", width=28)
        self.cb_bolum.pack(side=tk.LEFT, padx=(0, 14))
        self.cb_bolum.bind("<<ComboboxSelected>>", lambda e: self.load_report())

        ttk.Label(top, text="Yıl:").pack(side=tk.LEFT, padx=(0, 6))
        self.cb_yil = ttk.Combobox(top, state="readonly", values=["2022", "2023", "2024", "2025"], width=10)
        self.cb_yil.pack(side=tk.LEFT, padx=(0, 14))
        self.cb_yil.set("2025")
        self.cb_yil.bind("<<ComboboxSelected>>", lambda e: self.load_report())

        ttk.Button(top, text="📌 Rapor Getir", command=self.load_report).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="🔁 Statü/Yıl Eşitle", command=self.sync_status_year).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="🧰 DB Yedekle", command=self.backup_db).pack(side=tk.LEFT, padx=6)

        # ---------- SUMMARY ----------
        summary = ttk.LabelFrame(self, text="Özet", padding=10)
        summary.pack(fill=tk.X, pady=(10, 10))

        # küçük “kart” gibi hizalama
        self.lbl_pool_total = ttk.Label(summary, text="Havuz Toplam: -", width=22)
        self.lbl_pool_avg = ttk.Label(summary, text="Ortalama Skor: -", width=22)
        self.lbl_pool_rest = ttk.Label(summary, text="Dinlenmede(-1): -", width=22)
        self.lbl_pool_chosen = ttk.Label(summary, text="Müfredatta(1): -", width=22)

        self.lbl_pool_total.pack(side=tk.LEFT, padx=10)
        self.lbl_pool_avg.pack(side=tk.LEFT, padx=10)
        self.lbl_pool_rest.pack(side=tk.LEFT, padx=10)
        self.lbl_pool_chosen.pack(side=tk.LEFT, padx=10)

        # ---------- TABLES ----------
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=6)
        paned.pack(fill=tk.BOTH, expand=True)

        left = ttk.LabelFrame(paned, text="🏊 Havuz (Filtreli)", padding=8)
        right = ttk.LabelFrame(paned, text="📚 Müfredat (Filtreli)", padding=8)
        paned.add(left, stretch="always")
        paned.add(right, stretch="always")

        # Havuz tree
        cols_pool = ("ders_id", "ders_adi", "skor", "sayac", "statu", "yil")
        self.tree_pool = ttk.Treeview(left, columns=cols_pool, show="headings", height=16)
        self.tree_pool.pack(fill=tk.BOTH, expand=True)

        self.tree_pool.heading("ders_id", text="ID")
        self.tree_pool.heading("ders_adi", text="Ders Adı")
        self.tree_pool.heading("skor", text="Skor")
        self.tree_pool.heading("sayac", text="Sayaç")
        self.tree_pool.heading("statu", text="Durum")
        self.tree_pool.heading("yil", text="Yıl")

        self.tree_pool.column("ders_id", width=90, anchor="center")
        self.tree_pool.column("ders_adi", width=260)
        self.tree_pool.column("skor", width=80, anchor="center")
        self.tree_pool.column("sayac", width=70, anchor="center")
        self.tree_pool.column("statu", width=120, anchor="center")
        self.tree_pool.column("yil", width=70, anchor="center")

        sb_pool = ttk.Scrollbar(left, orient="vertical", command=self.tree_pool.yview)
        self.tree_pool.configure(yscrollcommand=sb_pool.set)
        sb_pool.pack(side=tk.RIGHT, fill=tk.Y)

        # Müfredat tree
        cols_curr = ("ders_id", "ders_adi", "skor")
        self.tree_curr = ttk.Treeview(right, columns=cols_curr, show="headings", height=16)
        self.tree_curr.pack(fill=tk.BOTH, expand=True)

        self.tree_curr.heading("ders_id", text="ID")
        self.tree_curr.heading("ders_adi", text="Ders Adı")
        self.tree_curr.heading("skor", text="Skor")

        self.tree_curr.column("ders_id", width=90, anchor="center")
        self.tree_curr.column("ders_adi", width=280)
        self.tree_curr.column("skor", width=90, anchor="center")

        sb_curr = ttk.Scrollbar(right, orient="vertical", command=self.tree_curr.yview)
        self.tree_curr.configure(yscrollcommand=sb_curr.set)
        sb_curr.pack(side=tk.RIGHT, fill=tk.Y)

        # ---------- EXPORT / LOG ----------
        bottom = ttk.LabelFrame(self, text="Dışa Aktar / Log", padding=8)
        bottom.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(bottom, text="⬇️ Havuz CSV", command=lambda: self.export_current("pool", "csv")).pack(side=tk.LEFT, padx=6)
        ttk.Button(bottom, text="⬇️ Havuz Excel", command=lambda: self.export_current("pool", "xlsx")).pack(side=tk.LEFT, padx=6)
        ttk.Button(bottom, text="⬇️ Müfredat CSV", command=lambda: self.export_current("curr", "csv")).pack(side=tk.LEFT, padx=6)
        ttk.Button(bottom, text="⬇️ Müfredat Excel", command=lambda: self.export_current("curr", "xlsx")).pack(side=tk.LEFT, padx=6)

        self.txt_log = tk.Text(bottom, height=5)
        self.txt_log.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))

    # =========================================================
    # HELPERS
    # =========================================================
    def log(self, msg: str):
        try:
            self.txt_log.insert(tk.END, msg + "\n")
            self.txt_log.see(tk.END)
        except Exception:
            pass

    def _fill_faculties(self):
        try:
            rows = self.db.run_sql("SELECT ad FROM fakulte")[1] or []
            values = [r[0] for r in rows]
            self.cb_fakulte["values"] = values
            if values and self.cb_fakulte.current() < 0:
                self.cb_fakulte.current(0)
                self._on_faculty_change(None)
        except Exception as e:
            self.log(f"Fakülte yükleme hatası: {e}")

    def _on_faculty_change(self, _event):
        fakulte = self.cb_fakulte.get()
        if not fakulte:
            return

        try:
            res = self.db.run_sql(f"SELECT fakulte_id FROM fakulte WHERE ad = '{fakulte}'")[1]
            if not res:
                return
            fakulte_id = res[0][0]

            res2 = self.db.run_sql(f"SELECT ad FROM bolum WHERE fakulte_id = {fakulte_id}")[1] or []
            bolumler = [r[0] for r in res2]
            self.cb_bolum["values"] = bolumler
            if bolumler:
                self.cb_bolum.current(0)

            self.load_report()
        except Exception as e:
            self.log(f"Bölüm yükleme hatası: {e}")

    # =========================================================
    # REPORT LOAD
    # =========================================================
    def load_report(self):
        fakulte = self.cb_fakulte.get()
        bolum = self.cb_bolum.get()
        yil = self.cb_yil.get()

        if not fakulte or not yil:
            return

        # ---------- HAVUZ ----------
        self.tree_pool.delete(*self.tree_pool.get_children())

        q_pool = f"""
            SELECT
                h.ders_id,
                h.ders_adi,
                h.skor,
                h.sayac,
                h.statu,
                h.yil
            FROM havuz h
            JOIN fakulte f ON h.fakulte_id = f.fakulte_id
            WHERE f.ad = '{fakulte}' AND h.yil = {int(yil)}
            ORDER BY h.skor DESC, h.sayac DESC
        """

        pool_rows = []
        try:
            _, pool_rows = self.db.run_sql(q_pool)
            pool_rows = pool_rows or []
        except Exception as e:
            self.log(f"Havuz sorgu hatası: {e}")

        # tabloya bas + özet hesapla
        total = len(pool_rows)
        rest = 0
        chosen = 0
        skorlar = []

        for ders_id, ders_adi, skor, sayac, statu, yil_ in pool_rows:
            s = float(skor) if skor is not None else 0.0
            skorlar.append(s)

            statu = int(statu) if statu is not None else 0
            if statu == -1:
                rest += 1
                statu_txt = "Dinlenmede (-1)"
            elif statu == 1:
                chosen += 1
                statu_txt = "Müfredatta (1)"
            else:
                statu_txt = "Havuzda (0)"

            self.tree_pool.insert("", tk.END, values=(ders_id, ders_adi, f"{s:.2f}", sayac, statu_txt, yil_))

        avg = (sum(skorlar) / len(skorlar)) if skorlar else 0.0

        self.lbl_pool_total.config(text=f"Havuz Toplam: {total}")
        self.lbl_pool_avg.config(text=f"Ortalama Skor: {avg:.2f}")
        self.lbl_pool_rest.config(text=f"Dinlenmede(-1): {rest}")
        self.lbl_pool_chosen.config(text=f"Müfredatta(1): {chosen}")

        # ---------- MÜFREDAT ----------
        self.tree_curr.delete(*self.tree_curr.get_children())

        if not bolum:
            return

        q_curr = f"""
            SELECT
                d.ders_id,
                d.ad,
                h.skor
            FROM mufredat m
            JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
            JOIN ders d ON md.ders_id = d.ders_id
            JOIN bolum b ON m.bolum_id = b.bolum_id
            LEFT JOIN havuz h ON (h.ders_id = d.ders_id AND h.yil = m.akademik_yil)
            WHERE b.ad = '{bolum}' AND m.akademik_yil = {int(yil)}
            ORDER BY d.ad
        """

        try:
            _, rows_curr = self.db.run_sql(q_curr)
            rows_curr = rows_curr or []
            for ders_id, ders_adi, skor in rows_curr:
                s = float(skor) if skor is not None else None
                self.tree_curr.insert("", tk.END, values=(ders_id, ders_adi, f"{s:.2f}" if s is not None else "---"))
        except Exception as e:
            self.log(f"Müfredat sorgu hatası: {e}")

        self.log(f"Rapor yüklendi → Fakülte={fakulte}, Bölüm={bolum}, Yıl={yil}")

    # =========================================================
    # ACTIONS
    # =========================================================
    def sync_status_year(self):
        if not self.db_path:
            messagebox.showwarning("Uyarı", "DB yolu bulunamadı.")
            return

        if not messagebox.askyesno("Onay", "Statü & yıl eşitleme çalıştırılsın mı?"):
            return

        try:
            muhendislik_mufredat_durumunu_esitle(self.db_path, baslangic_yili=2022, bitis_yili=2025)
            self.log("✅ Statü/Yıl eşitleme tamamlandı.")
            self.load_report()
            messagebox.showinfo("Tamam", "Eşitleme tamamlandı.")
        except Exception as e:
            self.log(f"❌ Eşitleme hatası: {e}")
            messagebox.showerror("Hata", str(e))

    def backup_db(self):
        if not self.db_path or not os.path.exists(self.db_path):
            messagebox.showwarning("Uyarı", "Yedeklenecek DB bulunamadı.")
            return

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"adil_secimli_backup_{ts}.db"

        target = filedialog.asksaveasfilename(
            title="DB Yedek Kaydet",
            defaultextension=".db",
            initialfile=default_name,
            filetypes=[("SQLite DB", "*.db *.sqlite *.sqlite3"), ("Tümü", "*.*")]
        )
        if not target:
            return

        try:
            shutil.copy2(self.db_path, target)
            self.log(f"✅ DB yedeklendi: {target}")
            messagebox.showinfo("Tamam", "Yedek alındı.")
        except Exception as e:
            self.log(f"❌ Yedek hatası: {e}")
            messagebox.showerror("Hata", str(e))

    def export_current(self, which: str, fmt: str):
        """
        which: 'pool' or 'curr'
        fmt: 'csv' or 'xlsx'
        """
        fakulte = self.cb_fakulte.get()
        bolum = self.cb_bolum.get()
        yil = self.cb_yil.get()

        if which == "pool":
            # tree'den dataframe üret
            rows = [self.tree_pool.item(i)["values"] for i in self.tree_pool.get_children()]
            df = pd.DataFrame(rows, columns=["ders_id", "ders_adi", "skor", "sayac", "durum", "yil"])
            default = f"havuz_{fakulte}_{yil}.{fmt}"
        else:
            rows = [self.tree_curr.item(i)["values"] for i in self.tree_curr.get_children()]
            df = pd.DataFrame(rows, columns=["ders_id", "ders_adi", "skor"])
            default = f"mufredat_{bolum}_{yil}.{fmt}"

        if df.empty:
            messagebox.showwarning("Uyarı", "Dışa aktarılacak veri yok.")
            return

        path = filedialog.asksaveasfilename(
            title="Dışa Aktar",
            defaultextension=f".{fmt}",
            initialfile=default,
            filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx"), ("Tümü", "*.*")]
        )
        if not path:
            return

        try:
            if fmt == "csv":
                df.to_csv(path, index=False, encoding="utf-8-sig")
            else:
                df.to_excel(path, index=False)
            self.log(f"✅ Export tamam: {path}")
            messagebox.showinfo("Tamam", "Dışa aktarım tamamlandı.")
        except Exception as e:
            self.log(f"❌ Export hatası: {e}")
            messagebox.showerror("Hata", str(e))
