import tkinter as tk
from tkinter import ttk, messagebox

def _sq(s: str) -> str:
    """Basit SQL kaçış (tek tırnak)."""
    return str(s).replace("'", "''")

class PoolTab(ttk.Frame):
    """
    🏊 Havuz Yönetimi sekmesi:
    - Fakülte / Bölüm / Yıl filtreleri
    - Havuz + Müfredat tabloları
    - Dinlenmedekileri gizle/göster
    """

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.db = app.db
        self.db_path = getattr(app, "db_path", None)

        self.hide_resting = False

        self._build_ui()

        # İlk yükleme
        self.after(200, self.refresh)

    # =========================================================
    #  PUBLIC
    # =========================================================
    def refresh(self):
        """DB değiştiğinde / sekmeye gelince çağır."""
        self.db_path = getattr(self.app, "db_path", self.db_path)
        self.load_faculties_to_combo()
        self.load_pool_data()

    # =========================================================
    #  UI
    # =========================================================
    def _build_ui(self):
        # --- 1) ÜST FİLTRELER ---
        top = tk.Frame(self, bg="#f1f5f9", pady=10, padx=10)
        top.pack(fill=tk.X)

        tk.Label(top, text="1. Fakülte:", bg="#f1f5f9", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=5)
        self.cb_fakulte = ttk.Combobox(top, state="readonly", width=35)
        self.cb_fakulte.pack(side=tk.LEFT, padx=5)
        self.cb_fakulte.bind("<<ComboboxSelected>>", self.on_faculty_change)

        tk.Label(top, text="2. Bölüm:", bg="#f1f5f9", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(15, 5))
        self.cb_bolum = ttk.Combobox(top, state="readonly", width=25)
        self.cb_bolum.pack(side=tk.LEFT, padx=5)
        self.cb_bolum.bind("<<ComboboxSelected>>", lambda e: self.load_pool_data())

        tk.Label(top, text="3. Yıl:", bg="#f1f5f9", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(15, 5))
        self.cb_yil = ttk.Combobox(top, state="readonly", values=["2022", "2023", "2024", "2025"], width=10)
        self.cb_yil.pack(side=tk.LEFT, padx=5)
        self.cb_yil.current(0) # Varsayılan 2022
        self.cb_yil.bind("<<ComboboxSelected>>", lambda e: self.load_pool_data())

        ttk.Button(top, text="Verileri Getir", command=self.load_pool_data).pack(side=tk.LEFT, padx=20)

        # --- 2) AKSİYONLAR ---
        actions = tk.Frame(self, bg="#e2e8f0", pady=6, padx=8)
        actions.pack(fill=tk.X)

        self.btn_toggle = tk.Button(
            actions,
            text="🔴 Dinlenmedekileri Gizle",
            bg="#fca5a5",
            font=("Segoe UI", 8),
            command=self.toggle_resting_courses
        )
        self.btn_toggle.pack(side=tk.LEFT, padx=6)

        # Opsiyonel butonlar
        ttk.Button(actions, text="Seçileni Dinlenmeye Al (-1)", command=lambda: self.set_selected_pool_status(-1)).pack(side=tk.LEFT, padx=6)
        ttk.Button(actions, text="Seçileni Havuzda Yap (0)", command=lambda: self.set_selected_pool_status(0)).pack(side=tk.LEFT, padx=6)

        # Algoritma tetikleme
        ttk.Button(actions, text="⚙️ Algoritmayı Çalıştır", command=self.run_decision_engine).pack(side=tk.RIGHT, padx=6)

        # --- 3) SPLIT VIEW (HAVUZ | MÜFREDAT) ---
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=5, bg="#cbd5e1")
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # SOL: HAVUZ
        left = tk.Frame(paned, bg="white")
        paned.add(left, width=750)
        tk.Label(left, text="DERS HAVUZU (Seçilen Fakülte & Yıl)", bg="#e2e8f0", font=("Segoe UI", 10, "bold")).pack(fill=tk.X)

        cols_pool = ("ID", "Ders Adı", "Puan", "Sayaç", "Durum", "Yıl")
        self.tree_pool = ttk.Treeview(left, columns=cols_pool, show="headings", selectmode="extended")
        
        self.tree_pool.heading("ID", text="ID")
        self.tree_pool.column("ID", width=50, anchor="center")
        
        self.tree_pool.heading("Ders Adı", text="Ders Adı")
        self.tree_pool.column("Ders Adı", width=300)
        
        self.tree_pool.heading("Puan", text="Puan")
        self.tree_pool.column("Puan", width=60, anchor="center")
        
        self.tree_pool.heading("Sayaç", text="Sayaç")
        self.tree_pool.column("Sayaç", width=50, anchor="center")
        
        self.tree_pool.heading("Durum", text="Durum")
        self.tree_pool.column("Durum", width=120, anchor="center")
        
        self.tree_pool.heading("Yıl", text="Yıl")
        self.tree_pool.column("Yıl", width=50, anchor="center")

        # Renk Etiketleri
        self.tree_pool.tag_configure("resting", background="#fee2e2", foreground="#b91c1c") # Kırmızı
        self.tree_pool.tag_configure("chosen", background="#dcfce7", foreground="#15803d")  # Yeşil
        self.tree_pool.tag_configure("active", background="white")                          # Beyaz

        sb_pool = ttk.Scrollbar(left, orient="vertical", command=self.tree_pool.yview)
        self.tree_pool.configure(yscrollcommand=sb_pool.set)
        sb_pool.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_pool.pack(fill=tk.BOTH, expand=True)

        # SAĞ: MÜFREDAT
        right = tk.Frame(paned, bg="white")
        paned.add(right)
        tk.Label(right, text="MÜFREDAT (Seçilen Bölüm & Yıl)", bg="#dcfce7", font=("Segoe UI", 10, "bold")).pack(fill=tk.X)

        cols_curr = ("ID", "Ders Adı", "Kesinleşme Puanı")
        self.tree_curr = ttk.Treeview(right, columns=cols_curr, show="headings")
        self.tree_curr.heading("ID", text="ID"); self.tree_curr.column("ID", width=50, anchor="center")
        self.tree_curr.heading("Ders Adı", text="Ders Adı")
        self.tree_curr.heading("Kesinleşme Puanı", text="Kesinleşme Puanı"); self.tree_curr.column("Kesinleşme Puanı", width=80, anchor="center")
        
        self.tree_curr.pack(fill=tk.BOTH, expand=True)

        tk.Button(
            right,
            text="👤 Örnek Öğrenci Seçimi Başlat",
            bg="#22c55e",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            command=self.open_student_simulation
        ).pack(fill=tk.X, pady=5, padx=5)

    # =========================================================
    #  DATA LOADERS
    # =========================================================
    def load_faculties_to_combo(self):
        try:
            _, rows = self.db.run_sql("SELECT ad FROM fakulte ORDER BY ad")
            faculties = [r[0] for r in (rows or [])]
            self.cb_fakulte["values"] = faculties
            if faculties:
                if self.cb_fakulte.current() < 0:
                    self.cb_fakulte.current(0)
                self.on_faculty_change(None)
        except Exception:
            pass

    def on_faculty_change(self, _event):
        fakulte = self.cb_fakulte.get()
        if not fakulte: return

        try:
            q_id = f"SELECT fakulte_id FROM fakulte WHERE ad = '{_sq(fakulte)}'"
            _, rows = self.db.run_sql(q_id)
            if not rows: return
            fakulte_id = rows[0][0]

            q_b = f"SELECT ad FROM bolum WHERE fakulte_id = {int(fakulte_id)} ORDER BY ad"
            _, rows_b = self.db.run_sql(q_b)
            bolumler = [r[0] for r in (rows_b or [])]

            self.cb_bolum["values"] = bolumler
            if bolumler:
                if self.cb_bolum.current() < 0:
                    self.cb_bolum.current(0)

            self.load_pool_data()
        except Exception:
            pass

    def toggle_resting_courses(self):
        self.hide_resting = not self.hide_resting
        if self.hide_resting:
            self.btn_toggle.config(text="🟢 Dinlenmedekileri Göster", bg="#86efac")
        else:
            self.btn_toggle.config(text="🔴 Dinlenmedekileri Gizle", bg="#fca5a5")
        self.load_pool_data()

    def load_pool_data(self):
        fakulte = self.cb_fakulte.get()
        bolum = self.cb_bolum.get()
        yil = self.cb_yil.get()

        if not fakulte or not yil:
            return

        # --- 1. SOL TARAF: HAVUZ (DERS HAVUZU) ---
        self.tree_pool.delete(*self.tree_pool.get_children())

        extra_where = "AND h.statu != -1" if self.hide_resting else ""
        
        # SORGUNUN GÜNCELLENMİŞ HALİ
        # LIKE kullanıldı, DISTINCT eklendi, Yıl filtresi garanti edildi.
        q_pool = f"""
            SELECT DISTINCT
                h.ders_id,
                d.ad,
                h.skor,
                h.sayac,
                h.statu,
                h.yil
            FROM havuz h
            JOIN ders d ON h.ders_id = d.ders_id
            JOIN fakulte f ON h.fakulte_id = f.fakulte_id
            WHERE f.ad LIKE '%{_sq(fakulte[:10])}%'  -- Fakülte adının başı tutsun yeter
              AND h.yil = {int(yil)}                  -- Yıl filtresi
              {extra_where}
            ORDER BY h.statu DESC, h.skor DESC        -- Önce seçilenler(1), sonra yüksek puanlılar
        """
        
        try:
            _, rows = self.db.run_sql(q_pool)
            
            # Tekrar eden ID'leri önlemek için set kullanalım (Python tarafı garantisi)
            added_ids = set()

            for d_id, d_ad, skor, sayac, statu, y in (rows or []):
                if d_id in added_ids: continue
                added_ids.add(d_id)

                s_val = int(statu) if statu is not None else 0
                
                # Görsel Ayarlar
                if s_val == 1:
                    tag = "chosen"
                    durum_txt = "✅ Müfredatta (1)"
                elif s_val == -1:
                    tag = "resting"
                    durum_txt = "⛔ Dinlenmede (-1)"
                else:
                    tag = "active"
                    durum_txt = "Havuzda (0)"

                skor_txt = f"{float(skor):.3f}" if skor else "0.000"
                
                self.tree_pool.insert("", tk.END, values=(d_id, d_ad, skor_txt, sayac, durum_txt, y), tags=(tag,))
        
        except Exception as e:
            print(f"UI Hata (Havuz): {e}")

        # --- 2. SAĞ TARAF: MÜFREDAT ---
        self.tree_curr.delete(*self.tree_curr.get_children())
        
        if not bolum: return

        q_curr = f"""
            SELECT DISTINCT d.ders_id, d.ad, h.skor
            FROM mufredat m
            JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
            JOIN ders d ON md.ders_id = d.ders_id
            JOIN bolum b ON m.bolum_id = b.bolum_id
            LEFT JOIN havuz h ON (h.ders_id = d.ders_id AND h.yil = m.akademik_yil)
            WHERE m.akademik_yil = {int(yil)}
              AND b.ad LIKE '%{_sq(bolum[:5])}%'
            ORDER BY d.ad
        """
        try:
            _, rows_r = self.db.run_sql(q_curr)
            added_right_ids = set()

            for d_id, d_ad, skor in (rows_r or []):
                if d_id in added_right_ids: continue
                added_right_ids.add(d_id)

                skor_txt = f"%{float(skor):.1f}" if skor is not None else "---"
                self.tree_curr.insert("", tk.END, values=(d_id, d_ad, skor_txt))
        except Exception as e:
            print(f"UI Hata (Müfredat): {e}")

    # =========================================================
    #  ACTIONS
    # =========================================================
    def _selected_pool_items(self):
        items = self.tree_pool.selection()
        if not items: return []
        selected = []
        for it in items:
            vals = self.tree_pool.item(it)["values"]
            if len(vals) >= 6:
                selected.append(vals)
        return selected

    def set_selected_pool_status(self, new_status: int):
        selected = self._selected_pool_items()
        if not selected:
            messagebox.showinfo("Bilgi", "Önce havuzdan ders seçmelisin 🙂")
            return

        yil = self.cb_yil.get()
        if not yil: return

        try:
            for ders_id, *_rest in selected:
                q = f"UPDATE havuz SET statu = {int(new_status)} WHERE ders_id = {int(ders_id)} AND yil = {int(yil)}"
                self.db.run_sql(q)
            self.load_pool_data()
        except Exception as e:
            messagebox.showerror("Güncelleme Hatası", str(e))

    def run_decision_engine(self):
        """App tarafında move_to_curriculum gibi bir fonksiyon varsa çağırır."""
        # Şimdilik sadece uyarı verelim veya calculation'ı main üzerinden tetiklesin
        messagebox.showinfo("Bilgi", "Lütfen 'Hesaplama & Test' sekmesinden 'Otomatik Puanlama' butonunu kullanın.")

    # =========================================================
    #  SIMULATION
    # =========================================================
    def open_student_simulation(self):
        curr_items = self.tree_curr.get_children()
        if not curr_items:
            messagebox.showwarning("Uyarı", "Müfredatta ders yok! Önce algoritmayı çalıştırın.")
            return

        sim_win = tk.Toplevel(self)
        sim_win.title("🎓 Öğrenci Ders Seçim Ekranı (Simülasyon)")
        sim_win.geometry("600x500")
        sim_win.configure(bg="#f8fafc")

        tk.Label(
            sim_win,
            text=f"{self.cb_yil.get()} GÜZ DÖNEMİ DERS SEÇİMİ",
            font=("Segoe UI", 14, "bold"),
            bg="#f8fafc",
            fg="#1e293b"
        ).pack(pady=15)

        tk.Label(
            sim_win,
            text="Müfredat Komisyonu tarafından onaylanan dersler aşağıdadır.\n"
                 "Lütfen almak istediklerinizi işaretleyiniz.",
            bg="#f8fafc"
        ).pack(pady=(0, 10))

        check_frame = tk.Frame(sim_win, bg="white", relief="groove", bd=1)
        check_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        vars_student_select = []
        for item in curr_items:
            ders_id, ders_name, ders_score = self.tree_curr.item(item)["values"]
            var = tk.IntVar()
            cb = tk.Checkbutton(
                check_frame,
                text=f"{ders_name} (Puan: {ders_score})",
                variable=var,
                bg="white",
                font=("Segoe UI", 10),
                anchor="w",
                padx=10,
                pady=5
            )
            cb.pack(fill=tk.X)
            vars_student_select.append((ders_name, var))

        def save_selection():
            selected = [name for name, var in vars_student_select if var.get() == 1]
            if not selected:
                messagebox.showwarning("Uyarı", "Hiç ders seçmediniz!")
                return

            msg = "Seçilen Dersler:\n\n" + "\n".join(f"✅ {s}" for s in selected)
            msg += "\n\nKaydınız başarıyla tamamlandı!"
            messagebox.showinfo("Onay", msg)
            sim_win.destroy()

        tk.Button(
            sim_win,
            text="Seçimi Onayla ve Kaydet",
            bg="#22c55e",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            command=save_selection
        ).pack(pady=20, ipadx=10)