# Algoritma Kontrol & Ders Lab — İlgili Tüm Dosyalar

Bu belge, **Algoritma Kontrol & Ders Lab** bölümüyle ilgili tüm dosyaları listeler. Manuel düzeltme yaparken bu dosyalara bakabilirsiniz.

---

## Özet Akış

```
calc_tab.py (Ana sekme)
    └── setup_algo_panel() içinde:
        ├── Üst: Genel Kontrol (MOCK, TREND, AHP, TOPSIS, LR, RF, DT butonları)
        └── Alt: CourseAnalysisTab (Yıl, Fakülte, Ders seçimi + KAYITLI KRİTERLER, ALGORİTMA ADIMLARI, NİHAİ KARAR)
                    └── course_analyzer.py (analyze_single_course) çağrılır
```

---

## 1. UI Dosyaları

### `app/ui/tabs/calc_tab.py`
**Rol:** Ana Hesaplama sekmesi. Algoritma Kontrol & Ders Lab alt sekmesini barındırır.

| Bölüm | Satır civarı | Açıklama |
|-------|--------------|----------|
| sub_nb, page_algos | 34-52 | Alt sekmeler (Kriter, Algoritma Kontrol, Relations, Havuz) |
| _on_sub_tab_changed | 57-65 | Alt sekme değişince Ders Lab refresh — **Ders listesi boş kalma sorunu için kritik** |
| setup_algo_panel | 99-165 | Genel Kontrol (algoritma butonları) + CourseAnalysisTab (page_lab) |
| refresh() | 59-92 | page_lab.refresh() çağrısı |

**Ders listesi boşluğu ile ilgili:** `_on_sub_tab_changed` içinde `idx == 1` (Algoritma Kontrol sekmesi) seçildiğinde `page_lab.refresh()` çağrılıyor. Bu, Ders dropdown'ının sekme açıldığında yeniden yüklenmesini sağlıyor.

---

### `app/ui/tabs/course_analysis_tab.py`
**Rol:** Ders Analiz Laboratuvarı — Yıl, Fakülte, Ders seçimi, KAYITLI KRİTERLER, ALGORİTMA ADIMLARI, NİHAİ KARAR panelleri.

| Bölüm | Satır civarı | Açıklama |
|-------|--------------|----------|
| _build_top_bar | 124-167 | Yıl, Fakülte, Ders combobox'ları, Analizi Başlat, Temizle butonları |
| _build_left_panel | 169-195 | KAYITLI KRİTERLER tablosu (tree_krit) |
| _build_mid_panel | 197-245 | ALGORİTMA ADIMLARI (AHP, Trend, TOPSIS, RF, DT) |
| _build_right_panel | 247-284 | NİHAİ KARAR (lbl_statu_big, sayac, txt_summary) |
| _load_faculties | 289-307 | Fakülte listesini yükler, _on_faculty_change tetikler |
| _on_faculty_change | 309-385 | Fakülte seçilince ders listesini yükler — **Ders dropdown doldurma** |
| _update_ders_combo | 392-420 | Ders combobox values güncelleme |
| _start_analysis | 426-450 | Analizi Başlat → analyze_single_course çağrısı |
| _fill_criteria, _fill_steps, _fill_decision | 326-455 | Sonuçların panellere yazılması |

**Ders listesi için sorgular (_on_faculty_change):**
- Müfredat yolu: `mufredat_ders` → `mufredat` → `bolum` (fakulte_id)
- Ders tablosu: `ders WHERE fakulte_id = ?`
- Fallback: `havuz WHERE fakulte_id = ?` (LEFT JOIN ders)

---

## 2. Servis Dosyaları

### `app/services/course_analyzer.py`
**Rol:** Tek ders analizi. `analyze_single_course(ders_id, year, db_path)` — AHP, TOPSIS, Trend, RF, DT hesaplar.

| Bölüm | Açıklama |
|-------|----------|
| _fetch_criteria | ders_kriterleri, performans, populerlik tablolarından kriter verisi |
| _fetch_gecmis_trend | Geçmiş yıl başarı oranları |
| _run_ahp, _run_topsis_single, _run_trend, _run_rf_simple | Algoritma adımları |
| VeriEksikHatasi | Kriter verisi yoksa fırlatılır — "Lütfen kriter sayfasından giriş yapınız" mesajı |

---

### `app/services/db.py`
**Rol:** `course_analyzer` için thread-safe SQLite bağlantısı. `db_session(db_path)` context manager.

---

### `app/services/calculation.py`
**Rol:** KararMotoru (AHP, TOPSIS), `run_automatic_scoring`. Genel Kontrol butonlarından (MOCK, AHP, TOPSIS vb.) çağrılır.

---

## 3. Veritabanı

### `app/db/sqlite_db.py`
**Rol:** UI tarafı DB erişimi. `run_sql(query, params)` — CourseAnalysisTab bu sınıfı kullanır.

---

## 4. Bağımlılık Sırası

```
course_analysis_tab.py
    ├── app.services.course_analyzer (analyze_single_course)
    │       ├── app.services.db (db_session)
    │       ├── app.services.havuz_karar (calculate_next_status)
    │       └── app.services.calculation (KararMotoru)
    └── app.db → app.db.sqlite_db (UI için; app.db aslında sqlite_db.Database)
```

---

## 5. Dosya Yolları (Kopyala-Yapıştır)

```
app/ui/tabs/calc_tab.py
app/ui/tabs/course_analysis_tab.py
app/services/course_analyzer.py
app/services/db.py
app/services/calculation.py
app/services/havuz_karar.py
app/db/sqlite_db.py
```

---

## 6. Bilinen Sorun ve Çözüm Noktaları

| Sorun | İlgili dosya | İlgili fonksiyon/satır |
|-------|--------------|-------------------------|
| Ders dropdown boş | course_analysis_tab.py | _on_faculty_change, _update_ders_combo |
| Sekme açılınca ders yüklenmiyor | calc_tab.py | _on_sub_tab_changed (idx==1'de refresh) |
| Kriter verisi bulunamadı | course_analyzer.py | _fetch_criteria, VeriEksikHatasi |
| KAYITLI KRİTERLER boş | course_analysis_tab.py | _fill_criteria (_start_analysis sonrası çağrılır) |

---

## 7. Test Komutu

```bash
# Uygulamayı çalıştır
python -m app.main

# Sonra: Hesaplama & Test → Algoritma Kontrol & Ders Lab
# Fakülte seç → Ders dropdown dolu olmalı
```
