# Eksiklik Tamamlama Planı — Öncelik Sıralı

Bu doküman, “neden %100 değil” analizindeki eksiklikleri kapatmak için önerilen adımları öncelik sırasına göre listeler. P0 = kritik (veri bütünlüğü, temel iş kuralları), P1 = önemli (kullanıcı deneyimi, operasyonel olgunluk).

---

## 1. VERİ YAPISI (~%78 → %95+)

### P0 — Dönem Ekseni Havuzda

| # | Görev | Açıklama | Dosyalar |
|---|-------|----------|----------|
| 1.1 | `havuz.donem` kolonu ekle | Havuz satırı dönem (Güz/Bahar) ile ilişkilendirilir; mevcut `yil` ile birlikte `(fakulte_id, yil, donem, ders_id)` benzersiz anahtar olur | `app/db/models.py`, migration/ALTER script |
| 1.2 | Migration hattı (Alembic) | Sürümlü şema değişiklikleri; prod’da tekrarlanabilir “tek yol” | `alembic/`, `alembic.ini` |
| 1.3 | ORM–SQLite–ETL uyumu | `Havuz` modelinde `donem`, `Mufredat.donem` ile tutarlı (Güz/Bahar); tüm JOIN ve filtreler güncellenir | `app/db/models.py`, `app/services/havuz_karar.py`, `app/services/calculation.py` |

### P1 — Tek Kaynak Şema

| # | Görev | Açıklama | Dosyalar |
|---|-------|----------|----------|
| 1.4 | Tek `schema.sql` / ORM kaynak | `models.py` → `alembic revision` veya `schema.sql` tek kaynak; `create_all` ile uyum | `data/schema.sql`, `app/db/` |
| 1.5 | Ders tip uyumu | `tip` / `DersTipi` / `tur` varyantları için tek kolon veya resmî alias; import şeması dokümante | `app/etl/`, `docs/MUFREDAT_EXCEL_SABLONU.md` |

---

## 2. MÜFREDAT YÖNETİMİ (~%70 → %92+)

### P0 — Çift Dönem Üretim

| # | Görev | Açıklama | Dosyalar |
|---|-------|----------|----------|
| 2.1 | `rebuild_school_curricula_dual_semester` | Güz ve Bahar için ayrı pipeline çağrısı veya tek fonksiyon içinde `["Güz","Bahar"]` döngüsü | `app/services/calculation.py` |
| 2.2 | Zincirleme eşitlemede dönem | `havuz_karar.muhendislik_mufredat_durumunu_esitle` dönem bazlı çalışır; `_get_year_curriculum_pairs` dönem parametresi alır | `app/services/havuz_karar.py` |

### P1 — API ve Görünüm

| # | Görev | Açıklama | Dosyalar |
|---|-------|----------|----------|
| 2.3 | REST API’de dönem parametresi | `/havuz`, `/mufredat` endpoint’leri `donem` parametresi alır; varsayılan tutarlı | `app/api/routes.py` |
| 2.4 | Bölüm+yıl+dönem “akademik plan” görünümü | Komisyon perspektifi: tüm sınıflar, yıl boyu tek ekranda | Yeni bileşen veya `pool_tab` / `analysis_tab` genişletmesi |

---

## 3. HAVUZ SİSTEMİ (~%78 → %92+)

### P0 — Dönem Bazlı State Machine

| # | Görev | Açıklama | Dosyalar |
|---|-------|----------|----------|
| 3.1 | Havuz satırında dönem | `havuz.donem` ile Güz/Bahar ayrımı; aynı ders iki dönemde farklı statüde olabilir | `havuz_karar.py`, `calculation.py`, `pool_tab.py` |
| 3.2 | Çapraz dönem kontrolü | Bir dersin Güz statüsünün Bahar’ı (veya tersi) etkilemesi kurallar dokümante; isteğe bağlı otomatik propagasyon | `havuz_karar.py`, dokümantasyon |

### P1 — 4+4 Blok Vurgusu

| # | Görev | Açıklama | Dosyalar |
|---|-------|----------|----------|
| 3.3 | UI’de “4’lü blok” görseli | Kota dağılımı, blok bazlı gösterim; kullanıcı tek bakışta görür | `app/ui/tabs/pool_tab.py`, `tools_tab.py` |

---

## 4. RAPORLAMA (~%63 → %88+)

### P0 — Merkezi Rapor Motoru

| # | Görev | Açıklama | Dosyalar |
|---|-------|----------|----------|
| 4.1 | Skor kaynağı tek merkez | `reporting.py` zaten var; skor mantığı `calculation.py`’den import edilir; UI/export bu modülden beslenir | `app/services/reporting.py`, `app/ui/tabs/tools_tab.py` |
| 4.2 | Skor kaynağı dokümantasyonu | Hangi tablo/alan skor kaynağı; TOPSIS vs anket ayrımı net | `docs/KESINLESME_NEXT_YEAR_ANALIZ.md` güncellemesi |

### P1 — KPI Kartları ve Dil

| # | Görev | Açıklama | Dosyalar |
|---|-------|----------|----------|
| 4.3 | KPI kartları | Yönetici özeti, karşılaştırmalı yıllar, dönem kırılımı | `app/ui/tabs/analysis_tab.py`, `reporting.py` |
| 4.4 | Kullanıcı dili | “Neden bu sıra?” sorusuna yanıt veren kısa açıklamalar; rapor notları genişletilir | `reporting.build_report_snapshot` `notes` alanı |

---

## 5. SKOR MANTIĞI (~%74 → %90+)

### P0 — Açıklanabilirlik

| # | Görev | Açıklama | Dosyalar |
|---|-------|----------|----------|
| 5.1 | AHP ağırlıkları UI’da | AHP matrisi ve ağırlıklar (örn. başarı %X, trend %Y) hesaplama/rapor ekranında gösterilir | `app/ui/tabs/calc_tab.py`, `app/services/calculation.py` |
| 5.2 | TOPSIS girdileri özeti | Her ders için kullanılan b_norm, p_norm, a_norm, g_norm özeti (tooltip veya ayrı panel) | `calc_tab.py`, `pool_tab.py` |

### P1 — Varsayılanlar Şeffaflığı

| # | Görev | Açıklama | Dosyalar |
|---|-------|----------|----------|
| 5.3 | Varsayılan politika metni | Anket oranı, eksik veride %50 gibi davranışlar her ekranda kısa metin olarak | `calculation.py` sabitleri, UI’da sabit açıklama bloğu |

---

## 6. TEST EDİLEBİLİRLİK (~%71 → %88+)

### P0 — Dönem Desteği Testleri

| # | Görev | Açıklama | Dosyalar |
|---|-------|----------|----------|
| 6.1 | `test_semester_support` | Havuz ve müfredat dönem parametresi; Güz/Bahar ayrımı test edilir | `app/tests/test_semester_support.py` (yeni) |
| 6.2 | reporting + calculation dönem testleri | `ensure_report_scores`, `build_report_snapshot` dönem parametreli senaryolar | `app/tests/test_reporting.py` |

### P1 — E2E / UI Otomasyonu

| # | Görev | Açıklama | Dosyalar |
|---|-------|----------|----------|
| 6.3 | pytest-qt veya Playwright | Kritik kullanıcı akışları (fakülte seç → havuz yükle → rapor al) regresyon testi | `app/tests/e2e/` (yeni) |

---

## 7. ÜRÜNLEŞME SEVİYESİ (~%54 → %80+)

### P0 — Operasyonel Paket

| # | Görev | Açıklama | Dosyalar |
|---|-------|----------|----------|
| 7.1 | `.env` ile konfigürasyon | `db_path`, `log_level`, `api_host` gibi değişkenler `.env` + `python-dotenv` | `app/core/config.py`, `.env.example` |
| 7.2 | Alembic entegrasyonu | Şema değişiklikleri migration ile; `alembic upgrade head` | `alembic/`, `README.md` |
| 7.3 | Runbook taslağı | Yedek, geri dönüş, hata durumunda izleme adımları | `docs/RUNBOOK.md` |

### P1 — API Güvenliği ve README

| # | Görev | Açıklama | Dosyalar |
|---|-------|----------|----------|
| 7.4 | API güvenliği (anahtar) | Opsiyonel API key veya basit Bearer token; rate limit taslağı | `app/api/main.py`, `routes.py` |
| 7.5 | README genişletmesi | Ortam değişkenleri, güvenli varsayılanlar, CI/CD özeti | `README.md` |

---

## Uygulama Sırası Önerisi

```
Faz 1 (P0 — Veri + İş Kuralları)
├── 1.1, 1.2, 1.3  Havuz donem + migration
├── 2.1, 2.2       Çift dönem müfredat üretimi
├── 3.1, 3.2       Dönem bazlı havuz state machine
└── 6.1, 6.2       Dönem testleri

Faz 2 (P0 — Raporlama + Skor + Operasyon)
├── 4.1, 4.2       Merkezi rapor + dokümantasyon
├── 5.1, 5.2       Skor açıklanabilirliği
├── 7.1, 7.2, 7.3  .env, Alembic, Runbook
└── 6.3            E2E taslağı (opsiyonel)

Faz 3 (P1 — Kullanıcı Deneyimi + Olgunluk)
├── 1.4, 1.5       Tek şema, ders tip uyumu
├── 2.3, 2.4       API dönem, akademik plan görünümü
├── 3.3            4’lü blok UI
├── 4.3, 4.4       KPI kartları, kullanıcı dili
├── 5.3            Varsayılan politika metni
└── 7.4, 7.5       API güvenliği, README
```

---

## Özet Metrik Hedefleri

| Alan | Mevcut | Hedef (Faz 1) | Hedef (Faz 3) |
|------|--------|---------------|---------------|
| Veri yapısı | ~%78 | ~%90 | ~%95 |
| Müfredat yönetimi | ~%70 | ~%85 | ~%92 |
| Havuz sistemi | ~%78 | ~%90 | ~%92 |
| Raporlama | ~%63 | ~%78 | ~%88 |
| Skor mantığı | ~%74 | ~%85 | ~%90 |
| Test edilebilirlik | ~%71 | ~%82 | ~%88 |
| Ürünleşme seviyesi | ~%54 | ~%68 | ~%80 |

---

*Bu plan, `docs/ILK_ASAMA_SISTEM_ANALIZI.md` ve “neden %100 değil” tablosuyla uyumlu olacak şekilde hazırlanmıştır.*
