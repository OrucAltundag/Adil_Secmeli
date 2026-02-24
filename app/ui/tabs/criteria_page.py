import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

class CriteriaPage:
    def __init__(self, parent, db):
        self.parent = parent
        self.db = db
        self.selected_course_id = None

        self._ensure_table()

        # Arayüzü Kur
        self.setup_ui()

    def _ensure_table(self):
        """ders_kriterleri tablosu yoksa oluşturur."""
        if not getattr(self.db, "conn", None):
            return
        try:
            cur = self.db.conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ders_kriterleri (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    ders_id         INTEGER NOT NULL,
                    yil             INTEGER NOT NULL,
                    donem           TEXT    DEFAULT 'Güz',
                    toplam_ogrenci  INTEGER DEFAULT 0,
                    gecen_ogrenci   INTEGER DEFAULT 0,
                    basari_ortalamasi REAL  DEFAULT 0.0,
                    kontenjan       INTEGER DEFAULT 0,
                    kayitli_ogrenci INTEGER DEFAULT 0,
                    UNIQUE(ders_id, yil),
                    FOREIGN KEY(ders_id) REFERENCES ders(ders_id)
                )
            """)
            self.db.conn.commit()
        except Exception as e:
            print(f"ders_kriterleri tablo oluşturma hatası: {e}")

    def setup_ui(self):
        # --- ANA DÜZEN: Üst (Filtre), Sol (Liste), Sağ (Form) ---
        
        # 1. ÜST PANEL: FİLTRELER
        top_frame = tk.Frame(self.parent, bg="#f1f5f9", pady=10, padx=10)
        top_frame.pack(fill=tk.X)
        
        # Filtre Bileşenleri
        self.create_filter_ui(top_frame)

        # 2. ALT PANEL: İÇERİK (PanedWindow ile bölünebilir yapı)
        paned = tk.PanedWindow(self.parent, orient=tk.HORIZONTAL, sashwidth=5, bg="#cbd5e1")
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # A. SOL PANEL: DERS LİSTESİ
        left_frame = tk.Frame(paned, bg="white", width=400)
        paned.add(left_frame)
        
        tk.Label(left_frame, text="DERS LİSTESİ", bg="#e2e8f0", font=("Segoe UI", 10, "bold")).pack(fill=tk.X)
        
        # Treeview
        cols = ("ID", "Ders Adı", "Kriter Durumu")
        self.tree = ttk.Treeview(left_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Ders Adı", text="Ders Adı")
        self.tree.heading("Kriter Durumu", text="Veri Var mı?")
        
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Ders Adı", width=250)
        self.tree.column("Kriter Durumu", width=100, anchor="center")
        
        sb = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Seçim Olayı
        self.tree.bind("<<TreeviewSelect>>", self.on_course_select)

        # B. SAĞ PANEL: VERİ GİRİŞ FORMU
        right_frame = tk.Frame(paned, bg="#f8fafc", width=500)
        paned.add(right_frame)
        
        self.create_form_ui(right_frame)

        # İlk Açılışta Fakülteleri Yükle
        self.load_faculties()

    def create_filter_ui(self, parent):
        # Stil
        lbl_style = {"bg": "#f1f5f9", "font": ("Segoe UI", 9, "bold")}
        
        # Fakülte
        tk.Label(parent, text="Fakülte:", **lbl_style).pack(side=tk.LEFT, padx=5)
        self.cb_fakulte = ttk.Combobox(parent, state="readonly", width=25)
        self.cb_fakulte.pack(side=tk.LEFT, padx=5)
        self.cb_fakulte.bind("<<ComboboxSelected>>", self.on_faculty_change)
        
        # Bölüm
        tk.Label(parent, text="Bölüm:", **lbl_style).pack(side=tk.LEFT, padx=10)
        self.cb_bolum = ttk.Combobox(parent, state="readonly", width=25)
        self.cb_bolum.pack(side=tk.LEFT, padx=5)
        
        # Yıl (varsayılan 2022 - müfredat genelde bu yılda dolu)
        tk.Label(parent, text="Yıl:", **lbl_style).pack(side=tk.LEFT, padx=10)
        self.cb_yil = ttk.Combobox(parent, state="readonly", width=10, values=["2022", "2023", "2024", "2025"])
        self.cb_yil.current(0)
        self.cb_yil.pack(side=tk.LEFT, padx=5)

        # Dönem
        tk.Label(parent, text="Dönem:", **lbl_style).pack(side=tk.LEFT, padx=10)
        self.cb_donem = ttk.Combobox(parent, state="readonly", width=10, values=["Güz", "Bahar"])
        self.cb_donem.current(0)
        self.cb_donem.pack(side=tk.LEFT, padx=5)
        
        # Listele Butonu
        tk.Button(parent, text="Dersleri Getir", bg="#3b82f6", fg="white", font=("Segoe UI", 9, "bold"),
                  command=self.load_courses).pack(side=tk.LEFT, padx=20)

    def create_form_ui(self, parent):
        tk.Label(parent, text="KRİTER VERİ GİRİŞİ", bg="#1e293b", fg="white", 
                 font=("Segoe UI", 11, "bold"), pady=10).pack(fill=tk.X)
        
        self.form_frame = tk.Frame(parent, bg="#f8fafc", padx=20, pady=20)
        self.form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Ders Başlığı
        self.lbl_selected_course = tk.Label(self.form_frame, text="Lütfen soldan bir ders seçiniz.", 
                                            bg="#f8fafc", fg="#334155", font=("Segoe UI", 12, "bold"))
        self.lbl_selected_course.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 20))

        # --- GİRİŞ ALANLARI ---
        
        # 1. Akademik Başarı Verileri
        self.create_section_header(1, "1. Akademik Performans")
        self.ent_toplam_ogrenci = self.create_input_row(2, "Dersi Alan Toplam Öğrenci:", "0")
        self.ent_gecen_ogrenci = self.create_input_row(3, "Dersi Geçen Öğrenci:", "0")
        self.ent_ortalama = self.create_input_row(4, "Ders Not Ortalaması (0-100):", "0.0")
        
        # Otomatik Hesaplanan: Başarı Oranı
        tk.Label(self.form_frame, text="Başarı Oranı (%):", bg="#f8fafc", font=("Segoe UI", 9, "bold")).grid(row=5, column=0, sticky="w", pady=5)
        self.lbl_basari_sonuc = tk.Label(self.form_frame, text="-", bg="#e2e8f0", width=10)
        self.lbl_basari_sonuc.grid(row=5, column=1, sticky="w")

        # 2. Kontenjan ve İlgi
        self.create_section_header(6, "2. Kontenjan ve Popülerlik")
        self.ent_kontenjan = self.create_input_row(7, "Ders Kontenjanı:", "0")
        self.ent_kayitli = self.create_input_row(8, "Kayıtlı Öğrenci (Talep):", "0")
        
        # Otomatik Hesaplanan: Doluluk
        tk.Label(self.form_frame, text="Doluluk Oranı (%):", bg="#f8fafc", font=("Segoe UI", 9, "bold")).grid(row=9, column=0, sticky="w", pady=5)
        self.lbl_doluluk_sonuc = tk.Label(self.form_frame, text="-", bg="#e2e8f0", width=10)
        self.lbl_doluluk_sonuc.grid(row=9, column=1, sticky="w")

        # KAYDET BUTONU
        btn_save = tk.Button(self.form_frame, text="💾 VERİLERİ KAYDET VE GÜNCELLE", 
                             bg="#16a34a", fg="white", font=("Segoe UI", 10, "bold"),
                             command=self.save_data, cursor="hand2")
        btn_save.grid(row=10, column=0, columnspan=2, sticky="ew", pady=30, ipady=5)

    def create_section_header(self, row, text):
        tk.Label(self.form_frame, text=text, bg="#f8fafc", fg="#2563eb", 
                 font=("Segoe UI", 10, "bold", "underline")).grid(row=row, column=0, columnspan=2, sticky="w", pady=(15, 5))

    def create_input_row(self, row, label_text, default_val):
        tk.Label(self.form_frame, text=label_text, bg="#f8fafc").grid(row=row, column=0, sticky="w", pady=5)
        var = tk.StringVar(value=default_val)
        entry = tk.Entry(self.form_frame, textvariable=var, width=15)
        entry.grid(row=row, column=1, sticky="w", padx=10)
        # Her tuşa basıldığında hesaplama yap
        entry.bind("<KeyRelease>", self.update_calculations)
        return entry

    # --- VERİ İŞLEMLERİ ---

    def load_faculties(self):
        if not getattr(self.db, "conn", None):
            return
        try:
            _, rows = self.db.run_sql("SELECT ad FROM fakulte")
            if rows:
                self.cb_fakulte["values"] = [str(r[0]) for r in rows]
                self.cb_fakulte.current(0)
                self.on_faculty_change(None)
        except Exception as e:
            print(f"Fakülte yükleme hatası: {e}")

    def on_faculty_change(self, event):
        fakulte = self.cb_fakulte.get()
        if not fakulte or not getattr(self.db, "conn", None):
            return
        try:
            _, res = self.db.run_sql("SELECT fakulte_id FROM fakulte WHERE ad=?", (fakulte,))
            if not res:
                return
            fid = res[0][0]
            _, res_bolum = self.db.run_sql("SELECT ad FROM bolum WHERE fakulte_id=?", (fid,))
            vals = [str(r[0]) for r in res_bolum] if res_bolum else []
            self.cb_bolum["values"] = vals
            if vals:
                self.cb_bolum.current(0)
        except Exception as e:
            print(f"Bölüm yükleme hatası: {e}")


    def load_courses(self):
        """Müfredattaki dersleri listeler."""
        self.tree.delete(*self.tree.get_children())

        fakulte = self.cb_fakulte.get()
        bolum = self.cb_bolum.get()
        yil = self.cb_yil.get()

        if not (fakulte and bolum and yil):
            messagebox.showwarning("Eksik", "Lütfen Fakülte, Bölüm ve Yıl seçiniz.")
            return

        if not getattr(self.db, "conn", None):
            self.tree.insert("", tk.END, values=("", "Veritabanı bağlantısı yok.", ""))
            return

        try:
            # Önce müfredattan dersleri dene
            query = """
                SELECT DISTINCT d.ders_id, d.ad,
                       CASE WHEN dk.id IS NOT NULL THEN 'Girildi' ELSE 'Bos' END as durum
                FROM mufredat m
                JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
                JOIN ders d ON md.ders_id = d.ders_id
                JOIN bolum b ON m.bolum_id = b.bolum_id
                LEFT JOIN ders_kriterleri dk ON (dk.ders_id = d.ders_id AND dk.yil = ?)
                WHERE b.ad = ? AND m.akademik_yil = ?
                ORDER BY d.ad
            """
            _, rows = self.db.run_sql(query, (int(yil), bolum, int(yil)))

            if not rows:
                # Müfredat boşsa fakültenin tüm seçmeli derslerini göster
                col_tip = self._ders_tip_kolonu()
                fallback = f"""
                    SELECT DISTINCT d.ders_id, d.ad,
                           CASE WHEN dk.id IS NOT NULL THEN 'Girildi' ELSE 'Bos' END as durum
                    FROM ders d
                    JOIN fakulte f ON d.fakulte_id = f.fakulte_id
                    LEFT JOIN ders_kriterleri dk ON (dk.ders_id = d.ders_id AND dk.yil = ?)
                    WHERE f.ad = ? AND (LOWER(COALESCE(d.{col_tip},'')) LIKE '%seçmeli%' OR LOWER(COALESCE(d.{col_tip},'')) LIKE '%secmeli%')
                    ORDER BY d.ad
                """
                try:
                    _, rows = self.db.run_sql(fallback, (int(yil), fakulte))
                except Exception as fallback_err:
                    print(f"Fallback ders sorgusu hatası: {fallback_err}")
                    rows = []

            if not rows:
                self.tree.insert("", tk.END, values=("", "Bu kriterlere uygun ders bulunamadı.", ""))
            else:
                for r in rows:
                    # sqlite3.Row -> tuple (Treeview <object> hatasını önler)
                    vals = (int(r[0]), str(r[1]), str(r[2]))
                    self.tree.insert("", tk.END, values=vals)

        except Exception as e:
            import traceback
            print(f"[Kriter load_courses] Hata: {e}")
            traceback.print_exc()
            messagebox.showerror("Hata", f"Dersler yüklenirken hata oluştu:\n{str(e)}")

    def _has_col(self, table, col):
        try:
            cur = self.db.conn.cursor()
            cur.execute(f"PRAGMA table_info({table})")
            return any(r[1] == col for r in cur.fetchall())
        except Exception:
            return False

    def _ders_tip_kolonu(self):
        """Ders tablosundaki seçmeli/zorunlu sütun adını döner (DersTipi, tip veya tur)."""
        for col in ("DersTipi", "tip", "tur"):
            if self._has_col("ders", col):
                return col
        return "DersTipi"


    def on_course_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        
        item = self.tree.item(sel[0])
        values = item['values']
        
        # GÜVENLİK KONTROLÜ 1: Değerler boş mu?
        if not values or values[0] == "":
            return  # ID yoksa veya boş satırsa işlem yapma
            
        try:
            # GÜVENLİK KONTROLÜ 2: ID gerçekten sayı mı?
            self.selected_course_id = int(values[0])
            course_name = values[1]
        except (ValueError, IndexError):
            # Eğer ID sayıya çevrilemiyorsa (örn: "Ders Bulunamadı" yazısıysa) çık
            self.selected_course_id = None
            self.lbl_selected_course.config(text="Geçersiz seçim.", fg="red")
            return

        yil = self.cb_yil.get()
        # Yıl seçili değilse hata vermesin, varsayılanı korusun
        if not yil: 
            messagebox.showwarning("Uyarı", "Lütfen bir yıl seçiniz.")
            return

        self.lbl_selected_course.config(text=f"Seçilen: {course_name} ({yil})", fg="#0f172a")
        
        # Mevcut veriyi çek: önce ders_kriterleri, yoksa performans+populerlik
        try:
            _, rows = self.db.run_sql(
                "SELECT * FROM ders_kriterleri WHERE ders_id=? AND yil=?",
                (self.selected_course_id, int(yil))
            )

            if rows:
                r = rows[0]
                # id, ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, kontenjan, kayitli_ogrenci
                self.cb_donem.set(str(r[3]) if r[3] else "Güz")
                self.ent_toplam_ogrenci.delete(0, tk.END)
                self.ent_toplam_ogrenci.insert(0, str(r[4] or 0))
                self.ent_gecen_ogrenci.delete(0, tk.END)
                self.ent_gecen_ogrenci.insert(0, str(r[5] or 0))
                self.ent_ortalama.delete(0, tk.END)
                self.ent_ortalama.insert(0, str(r[6] or 0.0))
                self.ent_kontenjan.delete(0, tk.END)
                self.ent_kontenjan.insert(0, str(r[7] or 0))
                self.ent_kayitli.delete(0, tk.END)
                self.ent_kayitli.insert(0, str(r[8] or 0))
            else:
                # ders_kriterleri yoksa performans+populerlikten doldur
                _, pr = self.db.run_sql(
                    "SELECT ortalama_not, basari_orani FROM performans WHERE ders_id=? AND akademik_yil=? LIMIT 1",
                    (self.selected_course_id, int(yil))
                )
                _, po = self.db.run_sql(
                    "SELECT talep_sayisi, kontenjan FROM populerlik WHERE ders_id=? AND akademik_yil=? LIMIT 1",
                    (self.selected_course_id, int(yil))
                )
                if pr and po:
                    ort = float(pr[0][0] or 0)
                    basari = float(pr[0][1] or 0)
                    talep = int(po[0][0] or 0)
                    kont = int(po[0][1] or 50)
                    top_ogr = max(talep, int(talep / (basari or 0.01)) if basari else talep)
                    gecen = int(top_ogr * basari) if basari else 0
                    self.ent_toplam_ogrenci.delete(0, tk.END)
                    self.ent_toplam_ogrenci.insert(0, str(top_ogr))
                    self.ent_gecen_ogrenci.delete(0, tk.END)
                    self.ent_gecen_ogrenci.insert(0, str(gecen))
                    self.ent_ortalama.delete(0, tk.END)
                    self.ent_ortalama.insert(0, f"{ort:.1f}")
                    self.ent_kontenjan.delete(0, tk.END)
                    self.ent_kontenjan.insert(0, str(kont))
                    self.ent_kayitli.delete(0, tk.END)
                    self.ent_kayitli.insert(0, str(talep))
                else:
                    self.clear_form_inputs()

            self.update_calculations()
            
        except Exception as e:
            import traceback
            print(f"[Kriter on_course_select] Veri çekme hatası: {e}")
            traceback.print_exc()
            messagebox.showerror("Hata", f"Veri okunurken hata oluştu: {e}")

    def clear_form_inputs(self):
        """Formu güvenli şekilde temizler"""
        self.ent_toplam_ogrenci.delete(0, tk.END); self.ent_toplam_ogrenci.insert(0, "0")
        self.ent_gecen_ogrenci.delete(0, tk.END); self.ent_gecen_ogrenci.insert(0, "0")
        self.ent_ortalama.delete(0, tk.END); self.ent_ortalama.insert(0, "0.0")
        self.ent_kontenjan.delete(0, tk.END); self.ent_kontenjan.insert(0, "0")
        self.ent_kayitli.delete(0, tk.END); self.ent_kayitli.insert(0, "0")

    def update_calculations(self, event=None):
        """Kullanıcı sayı girdikçe oranları anlık gösterir."""
        try:
            toplam = float(self.ent_toplam_ogrenci.get())
            gecen = float(self.ent_gecen_ogrenci.get())
            if toplam > 0:
                basari = (gecen / toplam) * 100
                self.lbl_basari_sonuc.config(text=f"%{basari:.1f}", fg="green")
            else:
                self.lbl_basari_sonuc.config(text="-")
                
            kontenjan = float(self.ent_kontenjan.get())
            kayitli = float(self.ent_kayitli.get())
            if kontenjan > 0:
                doluluk = (kayitli / kontenjan) * 100
                self.lbl_doluluk_sonuc.config(text=f"%{doluluk:.1f}", fg="blue")
            else:
                self.lbl_doluluk_sonuc.config(text="-")
        except ValueError:
            pass

    def save_data(self):
        if not self.selected_course_id:
            messagebox.showwarning("Uyarı", "Lütfen önce listeden işlem yapılacak dersi seçiniz.")
            return

        yil   = self.cb_yil.get()
        donem = self.cb_donem.get()

        try:
            c_id    = int(self.selected_course_id)
            top_ogr = int(self.ent_toplam_ogrenci.get().strip() or 0)
            gecen   = int(self.ent_gecen_ogrenci.get().strip() or 0)
            ort     = float(self.ent_ortalama.get().strip() or 0.0)
            kont    = int(self.ent_kontenjan.get().strip() or 0)
            kayit   = int(self.ent_kayitli.get().strip() or 0)

            # Türetilen oranlar
            basari_orani = (gecen / top_ogr) if top_ogr > 0 else 0.0
            doluluk_orani = min(kayit / kont, 1.0) if kont > 0 else 0.0

            cur = self.db.conn.cursor()

            # ── 1. ders_kriterleri: UNIQUE constraint olmayabilir, DELETE+INSERT kullan ──
            cur.execute(
                "DELETE FROM ders_kriterleri WHERE ders_id=? AND yil=?",
                (c_id, int(yil))
            )
            cur.execute("""
                INSERT INTO ders_kriterleri
                    (ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci,
                     basari_ortalamasi, kontenjan, kayitli_ogrenci)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (c_id, int(yil), donem, top_ogr, gecen, ort, kont, kayit))

            # ── 2. performans: algoritmalar buradan okur (UNIQUE yok, DELETE+INSERT) ──
            cur.execute(
                "DELETE FROM performans WHERE ders_id=? AND akademik_yil=? AND donem=?",
                (c_id, int(yil), donem)
            )
            cur.execute("""
                INSERT INTO performans
                    (ders_id, akademik_yil, donem, ortalama_not, basari_orani)
                VALUES (?, ?, ?, ?, ?)
            """, (c_id, int(yil), donem, ort, basari_orani))

            # ── 3. populerlik: algoritmalar buradan okur ──────────────────
            cur.execute(
                "DELETE FROM populerlik WHERE ders_id=? AND akademik_yil=? AND donem=?",
                (c_id, int(yil), donem)
            )
            cur.execute("""
                INSERT INTO populerlik
                    (ders_id, akademik_yil, donem, talep_sayisi, kontenjan, doluluk_orani)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (c_id, int(yil), donem, kayit, kont, doluluk_orani))

            self.db.conn.commit()

            messagebox.showinfo("Başarılı",
                f"Veriler kaydedildi.\n"
                f"Başarı oranı: %{basari_orani*100:.1f}  |  "
                f"Doluluk: %{doluluk_orani*100:.1f}")

            self.load_courses()

        except ValueError:
            messagebox.showerror("Hata", "Lütfen sayısal alanlara sadece rakam giriniz!")
        except Exception as e:
            import traceback
            print(f"[Kriter Kaydet] SQL Hatası: {e}")
            traceback.print_exc()
            messagebox.showerror("Kritik Hata", f"Veritabanına yazılamadı:\n{e}")



























































            