# =============================================================================
# app/ui/tabs/criteria_page.py — Kriter Girdi Sayfası
# =============================================================================
# Ders bazlı kriter verisi girişi: toplam_ogrenci, gecen_ogrenci, ortalama,
# kontenjan, kayitli. Kaydetme: ders_kriterleri + performans + populerlik tablolarına
# yazar. Algoritmalar (calculation.py) performans/popülerlik'ten okur.
# =============================================================================

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
        """ders_kriterleri tablosu yoksa oluşturur; anket alanları yoksa ekler."""
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
                    anket_katilimci INTEGER DEFAULT 0,
                    anket_dersi_secen INTEGER DEFAULT 0,
                    UNIQUE(ders_id, yil),
                    FOREIGN KEY(ders_id) REFERENCES ders(ders_id)
                )
            """)
            # Eski tablolarda anket sütunları yoksa ekle
            for col in ("anket_katilimci", "anket_dersi_secen"):
                try:
                    cur.execute(f"ALTER TABLE ders_kriterleri ADD COLUMN {col} INTEGER DEFAULT 0")
                    self.db.conn.commit()
                except sqlite3.OperationalError:
                    pass  # Sütun zaten varsa
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

        # Kriter durumu filtresi
        tk.Label(parent, text="Kriter:", **lbl_style).pack(side=tk.LEFT, padx=10)
        self.cb_kriter_filtre = ttk.Combobox(parent, state="readonly", width=12,
                                            values=["Tümü", "Girildi", "Girilmedi"])
        self.cb_kriter_filtre.current(0)
        self.cb_kriter_filtre.pack(side=tk.LEFT, padx=5)

        # Müfredat filtresi
        tk.Label(parent, text="Müfredat:", **lbl_style).pack(side=tk.LEFT, padx=10)
        self.cb_mufredat_filtre = ttk.Combobox(parent, state="readonly", width=14,
                                              values=["Tümü", "Müfredattakiler"])
        self.cb_mufredat_filtre.current(0)
        self.cb_mufredat_filtre.pack(side=tk.LEFT, padx=5)
        
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

        # 3. Anket Kriteri (düşük etki; yakın puanlarda ayırıcı)
        self.create_section_header(10, "3. Anket Tercihi")
        self.ent_anket_katilimci = self.create_input_row(11, "Ankete Katılan Toplam Öğrenci:", "0")
        self.ent_anket_dersi_secen = self.create_input_row(12, "Bu Dersi Seçen Öğrenci:", "0")
        tk.Label(self.form_frame, text="Anket Tercih Oranı (%):", bg="#f8fafc", font=("Segoe UI", 9, "bold")).grid(row=13, column=0, sticky="w", pady=5)
        self.lbl_anket_sonuc = tk.Label(self.form_frame, text="-", bg="#e2e8f0", width=10)
        self.lbl_anket_sonuc.grid(row=13, column=1, sticky="w")

        # KAYDET BUTONU
        btn_save = tk.Button(self.form_frame, text="💾 VERİLERİ KAYDET VE GÜNCELLE", 
                             bg="#16a34a", fg="white", font=("Segoe UI", 10, "bold"),
                             command=self.save_data, cursor="hand2")
        btn_save.grid(row=14, column=0, columnspan=2, sticky="ew", pady=30, ipady=5)

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
        """Fakültedeki seçmeli dersleri listeler; Güz/Bahar ve kriter filtresine göre."""
        self.tree.delete(*self.tree.get_children())

        fakulte = self.cb_fakulte.get()
        bolum = self.cb_bolum.get()
        yil = self.cb_yil.get()
        donem = self.cb_donem.get()
        kriter_filtre = self.cb_kriter_filtre.get()
        mufredat_filtre = getattr(self, "cb_mufredat_filtre", None)
        muf_val = (mufredat_filtre.get() or "").strip() if mufredat_filtre else ""
        sadece_mufredat = muf_val in ("Müfredattakiler", "Müfredattaki")

        if not (fakulte and yil and donem):
            messagebox.showwarning("Eksik", "Lütfen Fakülte, Yıl ve Dönem seçiniz.")
            return

        if not getattr(self.db, "conn", None):
            self.tree.insert("", tk.END, values=("", "Veritabanı bağlantısı yok.", ""))
            return

        try:
            col_tip = self._ders_tip_kolonu()
            donem_norm = "Güz" if donem == "Güz" else "Bahar"

            if sadece_mufredat:
                # Sadece o fakülte, yıl, dönem müfredatındaki dersler
                query = f"""
                    SELECT DISTINCT d.ders_id, d.ad,
                           CASE WHEN dk.id IS NOT NULL THEN 'Girildi' ELSE 'Bos' END as durum
                    FROM ders d
                    JOIN fakulte f ON d.fakulte_id = f.fakulte_id
                    JOIN mufredat m ON m.fakulte_id = f.fakulte_id
                      AND m.akademik_yil = ? AND LOWER(COALESCE(m.donem,'Güz')) = LOWER(?)
                    JOIN mufredat_ders md ON md.mufredat_id = m.mufredat_id AND md.ders_id = d.ders_id
                    LEFT JOIN ders_kriterleri dk ON (dk.ders_id = d.ders_id AND dk.yil = ?
                        AND (dk.donem = ? OR dk.donem IS NULL OR dk.donem = ''))
                    WHERE f.ad = ?
                      AND (LOWER(COALESCE(d.{col_tip},'')) LIKE '%seçmeli%'
                           OR LOWER(COALESCE(d.{col_tip},'')) LIKE '%secmeli%')
                    ORDER BY d.ad
                """
                _, rows = self.db.run_sql(query, (int(yil), donem_norm, int(yil), donem_norm, fakulte))
            else:
                query = f"""
                    SELECT d.ders_id, d.ad,
                           CASE WHEN dk.id IS NOT NULL THEN 'Girildi' ELSE 'Bos' END as durum
                    FROM ders d
                    JOIN fakulte f ON d.fakulte_id = f.fakulte_id
                    LEFT JOIN ders_kriterleri dk ON (dk.ders_id = d.ders_id AND dk.yil = ?
                        AND (dk.donem = ? OR dk.donem IS NULL OR dk.donem = ''))
                    WHERE f.ad = ?
                      AND (LOWER(COALESCE(d.{col_tip},'')) LIKE '%seçmeli%'
                           OR LOWER(COALESCE(d.{col_tip},'')) LIKE '%secmeli%')
                    ORDER BY d.ad
                """
                _, rows = self.db.run_sql(query, (int(yil), donem_norm, fakulte))

            # Kriter filtresi uygula
            if kriter_filtre == "Girildi":
                rows = [r for r in (rows or []) if str(r[2]) == "Girildi"]
            elif kriter_filtre == "Girilmedi":
                rows = [r for r in (rows or []) if str(r[2]) != "Girildi"]

            if not rows:
                self.tree.insert("", tk.END, values=("", "Bu kriterlere uygun ders bulunamadı.", ""))
            else:
                for r in rows:
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

    def _check_in_mufredat(self, yil: int, donem: str) -> bool:
        """Ders bu yıl/dönem/bölüm müfredatında mı?"""
        bolum = self.cb_bolum.get()
        if not bolum:
            return False
        try:
            _, rows = self.db.run_sql("""
                SELECT 1 FROM mufredat m
                JOIN mufredat_ders md ON m.mufredat_id = md.mufredat_id
                JOIN bolum b ON m.bolum_id = b.bolum_id
                WHERE md.ders_id = ? AND m.akademik_yil = ?
                  AND LOWER(COALESCE(m.donem,'Güz')) = LOWER(?)
                  AND b.ad = ?
                LIMIT 1
            """, (self.selected_course_id, yil, donem, bolum))
            return bool(rows)
        except Exception:
            return False

    def _update_form_readonly(self):
        """1 ve 2. kriterler filtreye göre; anket her zaman açık."""
        # Müfredattakiler filtresi veya ders müfredattaysa → 1 ve 2 açık
        readonly = not getattr(self, "_course_in_mufredat", True)
        state = "disabled" if readonly else "normal"
        for w in (self.ent_toplam_ogrenci, self.ent_gecen_ogrenci, self.ent_ortalama,
                  self.ent_kontenjan, self.ent_kayitli):
            w.config(state=state)
        # Anket her zaman açık
        self.ent_anket_katilimci.config(state="normal")
        self.ent_anket_dersi_secen.config(state="normal")


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

        donem = self.cb_donem.get() or "Güz"
        self.lbl_selected_course.config(text=f"Seçilen: {course_name} ({yil} {donem})", fg="#0f172a")

        # Müfredattakiler filtresi seçiliyse liste zaten müfredat dersleri → 1 ve 2 açık
        # Değilse sadece bu ders müfredattaysa 1 ve 2 açık. Anket her zaman açık.
        muf_filtre = getattr(self, "cb_mufredat_filtre", None)
        muf_val = (muf_filtre.get() or "").strip() if muf_filtre else ""
        if muf_val in ("Müfredattakiler", "Müfredattaki"):
            self._course_in_mufredat = True  # Listelenen dersler müfredatta
        else:
            self._course_in_mufredat = self._check_in_mufredat(int(yil), donem)
        self._update_form_readonly()

        # Mevcut veriyi çek: ders_kriterleri (donem eşleşmeli; NULL/boş eski kayıtlar her iki dönemde)
        try:
            _, rows = self.db.run_sql(
                """SELECT * FROM ders_kriterleri WHERE ders_id=? AND yil=?
                   AND (donem = ? OR donem IS NULL OR donem = '')""",
                (self.selected_course_id, int(yil), str(donem).strip())
            )
            if not rows:
                _, rows = self.db.run_sql(
                    "SELECT * FROM ders_kriterleri WHERE ders_id=? AND yil=? LIMIT 1",
                    (self.selected_course_id, int(yil))
                )

            if rows:
                r = rows[0]
                # id, ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci, basari_ortalamasi, kontenjan, kayitli_ogrenci, anket_katilimci, anket_dersi_secen
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
                # Anket alanları (indeks 9, 10 - yoksa 0)
                self.ent_anket_katilimci.delete(0, tk.END)
                self.ent_anket_katilimci.insert(0, str(r[9] if len(r) > 9 and r[9] is not None else 0))
                self.ent_anket_dersi_secen.delete(0, tk.END)
                self.ent_anket_dersi_secen.insert(0, str(r[10] if len(r) > 10 and r[10] is not None else 0))
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
                    self.ent_anket_katilimci.delete(0, tk.END)
                    self.ent_anket_katilimci.insert(0, "0")
                    self.ent_anket_dersi_secen.delete(0, tk.END)
                    self.ent_anket_dersi_secen.insert(0, "0")
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
        self.ent_anket_katilimci.delete(0, tk.END); self.ent_anket_katilimci.insert(0, "0")
        self.ent_anket_dersi_secen.delete(0, tk.END); self.ent_anket_dersi_secen.insert(0, "0")

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

            # Anket tercih oranı: dersi seçen / ankete katılan
            # anket_kat=0 ise %0.0 göster (kriter alanı boş kalmasın, eksik sayılmasın)
            anket_kat = float(self.ent_anket_katilimci.get() or 0)
            anket_secen = float(self.ent_anket_dersi_secen.get() or 0)
            if anket_kat > 0:
                oran = min(100.0, (anket_secen / anket_kat) * 100)
                self.lbl_anket_sonuc.config(text=f"%{oran:.1f}", fg="#7c3aed")
            else:
                self.lbl_anket_sonuc.config(text="%0.0", fg="#7c3aed")
        except ValueError:
            pass

    def save_data(self):
        if not self.selected_course_id:
            messagebox.showwarning("Uyarı", "Lütfen önce listeden işlem yapılacak dersi seçiniz.")
            return

        yil = int(self.cb_yil.get())
        donem = (self.cb_donem.get() or "Güz").strip()
        donem_db = "Güz" if str(donem).lower() in ("güz", "guz") else ("Bahar" if str(donem).lower() == "bahar" else donem)
        in_mufredat = getattr(self, "_course_in_mufredat", True)

        try:
            c_id = int(self.selected_course_id)
            ank_kat = int(self.ent_anket_katilimci.get().strip() or 0)
            ank_sec = int(self.ent_anket_dersi_secen.get().strip() or 0)
            top_ogr = gecen = ort = kont = kayit = 0
            if in_mufredat:
                top_ogr = int(self.ent_toplam_ogrenci.get().strip() or 0)
                gecen = int(self.ent_gecen_ogrenci.get().strip() or 0)
                ort = float(self.ent_ortalama.get().strip() or 0.0)
                kont = int(self.ent_kontenjan.get().strip() or 0)
                kayit = int(self.ent_kayitli.get().strip() or 0)

            basari_orani = (gecen / top_ogr) if top_ogr > 0 else 0.0
            doluluk_orani = min(kayit / kont, 1.0) if kont > 0 else 0.0

            cur = self.db.conn.cursor()

            # ── 1. ders_kriterleri ──
            cur.execute("DELETE FROM ders_kriterleri WHERE ders_id=? AND yil=?", (c_id, yil))
            cur.execute("""
                INSERT INTO ders_kriterleri
                    (ders_id, yil, donem, toplam_ogrenci, gecen_ogrenci,
                     basari_ortalamasi, kontenjan, kayitli_ogrenci,
                     anket_katilimci, anket_dersi_secen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (c_id, yil, donem, top_ogr, gecen, ort, kont, kayit, ank_kat, ank_sec))

            if in_mufredat:
                cur.execute(
                    "DELETE FROM performans WHERE ders_id=? AND akademik_yil=? AND donem=?",
                    (c_id, yil, donem_db)
                )
                cur.execute("""
                    INSERT INTO performans
                        (ders_id, akademik_yil, donem, ortalama_not, basari_orani)
                    VALUES (?, ?, ?, ?, ?)
                """, (c_id, yil, donem_db, ort, basari_orani))
                cur.execute(
                    "DELETE FROM populerlik WHERE ders_id=? AND akademik_yil=? AND donem=?",
                    (c_id, yil, donem_db)
                )
                cur.execute("""
                    INSERT INTO populerlik
                        (ders_id, akademik_yil, donem, talep_sayisi, kontenjan, doluluk_orani)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (c_id, yil, donem_db, kayit, kont, doluluk_orani))

            self.db.conn.commit()

            msg = "Veriler kaydedildi."
            if in_mufredat:
                msg += f"\nBaşarı oranı: %{basari_orani*100:.1f}  |  Doluluk: %{doluluk_orani*100:.1f}"
            else:
                msg += "\n(Müfredatta olmayan ders – sadece anket kaydedildi.)"
            messagebox.showinfo("Başarılı", msg)
            self.load_courses()

        except ValueError:
            messagebox.showerror("Hata", "Lütfen sayısal alanlara sadece rakam giriniz!")
        except Exception as e:
            import traceback
            print(f"[Kriter Kaydet] SQL Hatası: {e}")
            traceback.print_exc()
            messagebox.showerror("Kritik Hata", f"Veritabanına yazılamadı:\n{e}")



























































            