# Adil Seçmeli – Proje Analiz Raporu

**Tarih:** 4 Mart 2025  
**Amaç:** Projeyi %90 tamamlama ve gerçek bir üniversiteye entegre edilebilecek seviyeye getirmek için eksikliklerin, fazlalıkların ve öncelikli işlerin analizi.

---

## 1. Genel Özet

| Kriter | Durum | Not |
|--------|--------|-----|
| **Mimari** | ✅ Sağlam | Tkinter masaüstü + SQLite/SQLAlchemy, servis katmanı net |
| **Algoritma** | ✅ Var | AHP, TOPSIS, trend, ML (LR, RF, DT) mevcut |
| **Veri akışı (kriter)** | ✅ Kısmen düzeltilmiş | Kriter sayfası artık performans + popülerlik’e yazıyor |
| **API / Web** | ❌ Yok | FastAPI sadece stub; gerçek üniversite entegrasyonu için gerekli |
| **Kimlik doğrulama** | ❌ Yok | Öğrenci / danışman / admin rolleri tasarımda var, uygulamada yok |
| **Bağımlılık yönetimi** | ❌ Eksik | requirements.txt / pyproject.toml yok |
| **Test** | ⚠️ Kısmi | Test dosyaları var; bir test bozuk, coverage yok |
| **Güvenlik** | ⚠️ Risk | Bazı yerlerde SQL injection riski (parametresiz sorgu) |
| **Dokümantasyon** | ⚠️ Dağınık | data/README, docs/ planları iyi; kök README ve kurulum adımları eksik |

**Tahmini tamamlanma:** ~%65–70. %90 ve üniversite entegrasyonu için aşağıdaki eksiklerin giderilmesi gerekiyor.

---

## 2. Eksiklikler (Öncelik Sırasıyla)

### 2.1 Kritik (P0) – Üniversite Entegrasyonu İçin Şart

| # | Eksik | Açıklama | Öneri |
|---|--------|----------|--------|
| 1 | **REST API yok** | `app/api/routes.py` sadece `pass`. Öğrenci bilgi sistemi (OBS), kayıt sistemi veya anket sistemi ile entegrasyon için API şart. | FastAPI uygulaması aç; en azından ders listesi, skor, müfredat, havuz için GET/POST endpoint’leri tanımla. |
| 2 | **Kimlik doğrulama / yetkilendirme yok** | `docs/system_roles.md` Öğrenci, Danışman, Fakülte Admin, Sistem Admin tanımlı; uygulamada login/rol yok. | Basit JWT veya session tabanlı giriş + rol bazlı endpoint kısıtlaması ekle. |
| 3 | **Bağımlılık listesi yok** | `requirements.txt` veya `pyproject.toml` yok; kurulum ve taşınabilirlik zayıf. | Tüm import’lar (pandas, numpy, scikit-learn, matplotlib, seaborn, sqlalchemy, openpyxl, tkinter vb.) için `requirements.txt` (ve isteğe `pyproject.toml`) oluştur. |
| 4 | **Kök README ve kurulum** | Sadece `data/README.md` var; proje kökünde kurulum ve çalıştırma yok. | Kök `README.md`: kurulum (venv, pip install), DB init sırası (init_script → smart_data_generator → havuz_* → main.py), ortam değişkenleri, kısa mimari açıklama. |

### 2.2 Yüksek (P1) – Tutarlılık ve Güvenlik

| # | Eksik | Açıklama | Öneri |
|---|--------|----------|--------|
| 5 | **SQL injection riski** | `tools_tab.py`: `f"SELECT ... WHERE ad = '{fakulte}'"` — kullanıcıdan gelen değer doğrudan sorguda. Benzer riskler `pool_tab.py`, `course_analysis_tab.py` (fakülte adı). | Tüm metin parametreleri parametreli sorgu ile ver: `WHERE ad = ?`, `cur.execute(query, (fakulte,))`. |
| 6 | **Şema tutarsızlığı** | `data/schema.sql` eski tablo isimleri: `ders_performans_ozeti`, `popuarlik_olcumu`, `tercih_sayisi`. Uygulama `performans`, `populerlik`, `talep_sayisi` kullanıyor. İki şema dosyası karışıklık yaratıyor. | Tek resmî şema belirle (örn. `schema_updated.sql` veya SQLAlchemy modellerinden üret); `schema.sql`’i güncelle veya “legacy” diye işaretle. Yeni kurulumlar tek şema ile yapılsın. |
| 7 | **Bozuk test** | `app/tests/test_db.py` `from models import DersDinlendirme, SessionLocal` kullanıyor. `DersDinlendirme` `app/db/models.py`’de yok; import path de `app.db.models` olmalı. | Import’u `app.db.models` ve mevcut modellere göre düzelt; ya `DersDinlendirme` modelini ekle ya da bu testi farklı bir senaryoya (örn. Havuz/Performans) çevir. |
| 8 | **Tablo adı güvenliği** | `sqlite_db.py` `head()`: `f"SELECT * FROM {table}"` — `table` `tables()`’dan gelse bile whitelist kontrolü yok. | Tablo adı için whitelist: `if table not in self.tables(): raise ValueError(...)`. |

### 2.3 Orta (P2) – Kullanılabilirlik ve Raporlama

| # | Eksik | Açıklama | Öneri |
|---|--------|----------|--------|
| 9 | **Kullanılmayan sekmeler** | `PoolTab` ve `RelationsTab` tanımlı ama `main.py` notebook’a eklenmiyor. | Ya sekmeleri ekle (Havuz yönetimi, İlişkiler) ya da kod tabanından kaldır; yarım bırakılmış özellik kalmasın. |
| 10 | **Excel şablonu ve dokümantasyon** | Gerçek hayat senaryosu: OBS’den Excel export → import. Hangi kolonların olması gerektiği ve örnek dosya net değil. | `data/` altında örnek Excel şablonu (ders, yıl, ortalama not, başarı oranı, kontenjan, talep) ve kısa “Veri içe aktarma” dokümanı ekle. |
| 11 | **Kriter sayfası toplu yükleme** | Yeniden yapılandırma planında “Excel’den toplu kriter yükleme” var; kriter sayfasında tek ders manuel, toplu Excel yok. | Kriter sayfasına “Excel’den Yükle” butonu ekle; şablona uygun Excel’i okuyup performans/popülerlik (ve isteğe ders_kriterleri) güncelle. |
| 12 | **Test coverage** | pytest var, pytest-cov veya coverage config yok; hangi modüllerin test edildiği görünmüyor. | `pytest-cov` ekle; `pytest --cov=app` ve gerekirse `.coveragerc` ile rapor üret. |

### 2.4 Düşük (P3) – İyileştirmeler

| # | Eksik | Açıklama | Öneri |
|---|--------|----------|--------|
| 13 | **Loglama ve denetim** | data/README’de “Kim, neyi, neden atadı?” deniyor; uygulamada merkezi log/audit yok. | Kritik işlemlerde (skor güncelleme, atama, config değişikliği) loglama ekle (dosya veya DB). |
| 14 | **Config versiyonlama** | Ağırlıklar (wB, wP, wA) config’te; değişiklik geçmişi tutulmuyor. | Config değişikliklerini audit log’a yaz veya config’i versiyonlu sakla. |
| 15 | **main.py eski yorum** | “4. SEKME: HESAPLAMA & TEST (EKSİK OLAN KISIM BURASIYDI)” — sekme eklendi, yorum güncel değil. | Yorumu “4. SEKME: HESAPLAMA & TEST” gibi güncel ifadeyle değiştir. |

---

## 3. Fazlalıklar / Temizlenmesi Gerekenler

| # | Fazlalık | Açıklama | Öneri |
|---|----------|----------|--------|
| 1 | **main.py içinde tekrarlanan kod** | `fill_tables`, `on_table_select`, `sort_by`, `apply_filter` vb. büyük bloklar yorum satırı; asıl mantık ViewTab’da. | Yorum bloklarını kaldır; tek kaynak ViewTab kalsın. |
| 2 | **Çift şema dosyası** | `schema.sql` ve `schema_updated.sql` farklı tablo/kolon isimleri; karışıklık. | Tek resmî şemada birleştir; diğerini arşivle veya sil. |
| 3 | **Gereksiz import** | `main.py` içinde `CriteriaPage` doğrudan import ediliyor; sadece `CalcTab` içinde kullanılıyor. | İhtiyaca göre import’u `CalcTab` içine taşıyabilirsiniz (opsiyonel, küçük temizlik). |
| 4 | **Kullanılmayan rapor dosyası** | `reports/fairness_dashboard.html` statik artifact; uygulama içinden üretilmiyor olabilir. | Ya uygulama “Rapor & Skor” ile bu raporu üretsin ya da “örnek çıktı” olarak docs’a taşıyın. |

---

## 4. Üniversite Entegrasyonu İçin Gerekenler (Özet)

Gerçek bir üniversiteye entegre edilebilir seviye için:

1. **API katmanı**  
   Ders listesi, skor, müfredat, havuz, (opsiyonel) atama sonuçları için REST endpoint’leri. OBS veya kayıt sistemi bu API’yi çağırabilmeli.

2. **Kimlik ve roller**  
   Öğrenci / danışman / fakülte admin / sistem admin için giriş ve rol bazlı erişim. `system_roles.md`’deki endpoint’lerle uyumlu olacak şekilde yetkilendirme.

3. **Veri alışverişi**  
   Excel import (OBS export) ile uyumlu şablon ve dokümantasyon; ileride API ile otomatik veri çekimi için hazırlık.

4. **Kurulum ve bakım**  
   `requirements.txt`, kök README, kurulum ve DB init sırası; böylece IT birimi tek dokümandan kurabilsin.

5. **Güvenlik ve denetim**  
   Parametreli SQL, (mümkünse) tablo adı whitelist’i; kritik işlemlerde loglama.

---

## 5. Önerilen İş Sırası (%90 Tamamlama Hedefi)

| Sıra | Görev | Öncelik | Tahmini etki |
|------|--------|---------|---------------|
| 1 | requirements.txt + kök README (kurulum, DB init) | P0 | Kurulum tekrarlanabilir |
| 2 | API stub’ı gerçek endpoint’lere çevirme (ders, skor, müfredat, havuz) | P0 | Entegrasyon için zemin |
| 3 | Basit kimlik doğrulama + rol (en azından API için) | P0 | Üniversite güvenlik beklentisi |
| 4 | SQL injection düzeltmeleri (tools_tab, pool_tab, course_analysis_tab) | P1 | Güvenlik |
| 5 | test_db.py düzeltmesi + (opsiyonel) pytest-cov | P1 | Test güvenilirliği |
| 6 | Tek resmî şema + schema dokümantasyonu | P1 | Tutarlı veritabanı |
| 7 | PoolTab / RelationsTab kararı (ekle veya kaldır) | P2 | Net özellik seti |
| 8 | Excel şablonu + kriter sayfası “Excel’den Yükle” | P2 | Gerçek veri akışı |
| 9 | Kritik işlemlerde loglama | P3 | Denetim |

Bu sıra ile proje hem %90 tamamlanmış hem de üniversite ortamında entegre edilebilecek bir tabana getirilebilir.

---

## 6. Mevcut Güçlü Yönler

- **Kriter → performans/popülerlik bağlantısı:** `criteria_page.save_data()` hem `ders_kriterleri` hem `performans` hem `populerlik` tablolarına yazıyor; algoritmalar aynı kaynaktan okuyabiliyor.
- **AHP/TOPSIS ve otomasyon:** `calculation.py` KararMotoru, `run_automatic_scoring` ve havuz/müfredat güncellemesi işlevsel.
- **Havuz ve müfredat:** Havuz statü/sayaç/skor, müfredat eşitleme (`muhendislik_mufredat_durumunu_esitle`) mantıklı tasarlanmış.
- **ETL ve Excel:** Müfredat/kriter import için altyapı ve esnek kolon eşleştirmesi mevcut.
- **Dokümantasyon:** `data/README.md`, `PROJE_YENIDEN_YAPILANDIRMA_PLANI.md`, `system_roles.md` ve terminoloji dokümanları iyi bir temel sunuyor.

---

**Rapor sonu.** İsterseniz bir sonraki adımda önce P0 maddelerinden (requirements.txt, README, API, kimlik doğrulama) biri için somut patch/plan çıkarabilirim.
