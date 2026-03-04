# Adil Seçmeli — Modül Haritası

Bu belge, projedeki `.py` dosyalarının hangi bölümle ilgili olduğunu ve birbirleriyle ilişkisini açıklar. Geliştirme sırasında hangi dosyayı düzenleyeceğinizi hızlıca bulmak için kullanın.

---

## 1. Giriş Noktaları

| Dosya | Bölüm | Açıklama |
|-------|-------|----------|
| `app/main.py` | Ana uygulama | Masaüstü Tkinter uygulamasının giriş noktası. Sekmeleri (ViewTab, AnalysisTab, ToolsTab, CalcTab) oluşturur, veritabanı bağlantısını yönetir. |
| `app/api/main.py` | REST API | Üniversite entegrasyonu için FastAPI uygulaması. `uvicorn app.api.main:app` ile çalıştırılır. |

---

## 2. Veritabanı Katmanı (`app/db/`)

| Dosya | Bölüm | Açıklama |
|-------|-------|----------|
| `database.py` | SQLAlchemy engine | Engine, SessionLocal, Base tanımları. ORM tabanlı servisler bu modülü kullanır. |
| `models.py` | ORM modelleri | Okul, Fakulte, Bolum, Ders, Havuz, Performans, Populerlik, Skor, Mufredat, Ogrenci, Anket vb. tabloların SQLAlchemy modelleri. |
| `sqlite_db.py` | UI DB wrapper | Masaüstü UI için basit sqlite3 wrapper. `connect()`, `tables()`, `head()`, `run_sql()` metodları. |

---

## 3. Kullanıcı Arayüzü (`app/ui/`)

### 3.1 Ana sekmeler (`app/ui/tabs/`)

| Dosya | Bölüm | Açıklama |
|-------|-------|----------|
| `view_tab.py` | Tablo görüntüleme | Tablo listesi, Treeview, filtre, SQL çalıştırıcı. Veritabanı tablolarını görüntüler. |
| `analysis_tab.py` | Analiz & grafik | Grafikler (başarı, popülerlik, skor dağılımı). Matplotlib/Seaborn kullanır. |
| `tools_tab.py` | Rapor & skor | Rapor oluşturma, havuz/müfredat tabloları, Excel export. `muhendislik_mufredat_durumunu_esitle` çağrısı. |
| `calc_tab.py` | Hesaplama & test | Ana hesaplama sekmesi. İçinde: Kriter sayfası, Algoritma kontrolü, Ders Lab, Relations, Havuz alt sekmeleri. |

### 3.2 CalcTab alt bileşenleri

| Dosya | Bölüm | Açıklama |
|-------|-------|----------|
| `criteria_page.py` | Kriter girişi | Ders bazlı kriter verisi (toplam öğrenci, geçen, ortalama, kontenjan, kayıtlı). performans + populerlik tablolarına yazar. |
| `pool_tab.py` | Havuz yönetimi | Havuz tablosu, statü renklendirme, müfredat görünümü. Durum makinesi (1/0/-1/-2). |
| `relations_tab.py` | Ders ilişkileri | NLP benzerlik grafiği (SimilarityEngine), ders ilişki ağları. |
| `course_analysis_tab.py` | Ders analiz laboratuvarı | Tek ders detay analizi (course_analyzer ile). |

### 3.3 Stil ve genel

| Dosya | Bölüm | Açıklama |
|-------|-------|----------|
| `style.py` | UI stil | `apply_style()` — Tkinter/ttk tema ayarları. |

---

## 4. Servis Katmanı (`app/services/`)

| Dosya | Bölüm | Açıklama |
|-------|-------|----------|
| `calculation.py` | Karar motoru | AHP, TOPSIS, trend hesaplama. `KararMotoru`, `run_automatic_scoring`. Performans/popülerlik tablolarından veri okur. |
| `havuz_karar.py` | Havuz kararları | Müfredat durumu eşitleme, statü güncelleme. `muhendislik_mufredat_durumunu_esitle`, `calculate_next_status`. |
| `course_analyzer.py` | Ders analizi | Tek ders detay analizi. `analyze_single_course`. |
| `ai_engine.py` | ML algoritmaları | Lineer Regresyon, Random Forest, Decision Tree. |
| `similarity.py` | Benzerlik (sklearn) | Ders metin benzerliği. |
| `similarity_engine.py` | Benzerlik motoru | TF-IDF + cosine similarity. RelationsTab ve test_similarity tarafından kullanılır. |
| `rules_engine.py` | Kurallar | Ders çakışma kontrolü vb. `ders_cakisma_kontrolu`. |
| `db.py` | Servis DB helper | `db_session` context manager. course_analyzer tarafından kullanılır. |

---

## 5. ETL ve Yardımcı Araçlar

| Dosya | Bölüm | Açıklama |
|-------|-------|----------|
| `app/etl/import_mufredat_excel.py` | Müfredat Excel import | Excel’den müfredat verisi yükleme. |
| `app/etl/import_dersler_master.py` | Ders master import | Ders listesi import. |
| `app/utils/import_excel.py` | Genel Excel import | Performans/popülerlik verisi import. |
| `app/utils/etl.py` | ETL yardımcıları | Veri dönüşüm fonksiyonları. |
| `app/utils/logger.py` | Loglama | Logging yapılandırması. |

---

## 6. Scriptler (`app/scripts/`)

| Dosya | Bölüm | Açıklama |
|-------|-------|----------|
| `init_script.py` | DB başlatma | İlk veritabanı kurulumu. |
| `smart_data_generator.py` | Sahte veri | Test için performans/popülerlik/havuz verisi üretir. |
| `havuz_kumulatif_doldur.py` | Havuz doldurma | Havuz tablosunu kümülatif doldurur. |
| `havuz_2022_doldur.py` | 2022 havuz | 2022 yılı havuz verisi. |
| `import_real_data.py` | Gerçek veri import | Gerçek veri import scripti. |
| `update_db_for_pool.py` | Havuz DB güncelleme | Havuz şeması güncellemesi. |
| `fix_havuz_table.py` | Havuz tablo düzeltme | Havuz tablosu düzeltmeleri. |
| `fill_pool_manual.py` | Manuel havuz | Manuel havuz doldurma. |
| `reset.py` | Sıfırlama | Veritabanı sıfırlama. |

---

## 7. API (`app/api/`)

| Dosya | Bölüm | Açıklama |
|-------|-------|----------|
| `main.py` | FastAPI app | Uygulama instance’ı, router dahil etme. |
| `routes.py` | REST endpoint’ler | `/api/v1/dersler`, `/skorlar`, `/havuz`, `/mufredat`, `/fakulteler`. |

---

## 8. Çekirdek (`app/core/`)

| Dosya | Bölüm | Açıklama |
|-------|-------|----------|
| `config.py` | Ayarlar | PROJECT_NAME, VERSION, DATABASE_URL, WEIGHTS. |
| `state.py` | Uygulama durumu | AppState, dinleyiciler. |
| `exceptions.py` | Özel hatalar | Özel exception sınıfları. |

---

## 9. Testler (`app/tests/`)

| Dosya | Bölüm | Açıklama |
|-------|-------|----------|
| `test_db.py` | DB bağlantı testi | SessionLocal, Havuz modeli ile basit bağlantı testi. |
| `test_score_engine.py` | Skor motoru | Skor hesaplama testleri. |
| `test_assignment_engine.py` | Atama motoru | Atama testleri. |
| `test_etl.py` | ETL testleri | Import testleri. |
| `test_similarity.py` | Benzerlik testi | SimilarityEngine testi. |
| `test_single_analysis.py` | Tek analiz testi | course_analyzer, havuz_karar testleri. |
| `check_db_results.py` | DB sonuç kontrolü | Veritabanı sonuç doğrulama. |
| `reset_counters.py` | Sayaç sıfırlama | Sayaç alanlarını sıfırlama. |

---

## 10. Veri Akışı (Özet)

```
config.json (db_path)
    ↓
Database (sqlite_db) ←→ UI (view_tab, analysis_tab, tools_tab, calc_tab)
    ↓
performans + populerlik tabloları
    ↓
calculation.py (AHP, TOPSIS) → skor tablosu
    ↓
havuz_karar.py → havuz statü güncellemesi
```

---

## 11. Geliştirme Yaparken

| Yapacağınız iş | İlgili dosya(lar) |
|----------------|-------------------|
| Yeni sekme ekleme | `main.py`, `app/ui/tabs/` |
| Veritabanı şeması değişikliği | `app/db/models.py`, `data/schema*.sql` |
| Algoritma değişikliği | `app/services/calculation.py` |
| Kriter girişi değişikliği | `app/ui/tabs/criteria_page.py` |
| API endpoint ekleme | `app/api/routes.py` |
| Excel import değişikliği | `app/etl/`, `app/utils/import_excel.py` |
