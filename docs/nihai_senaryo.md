# Nihai Senaryo — Üniversite Seçmeli Ders Karar Destek Sistemi

> **Konum:** Bu doküman; Codex'in ürettiği operasyonel senaryo ile kullanıcı tarafından
> ChatGPT yardımıyla iyileştirilmiş akademik senaryonun birleştirilmiş, projeye
> uyarlanmış nihai halidir. Hedef: 2022 yılı verisiyle, mevcut sayfalar +
> birkaç yeni modül kullanarak uçtan uca tek bir gerçek karar çalıştırması
> ve dönem planı üretmek.
>
> **Statü:** Çalışma dokümanı. Her faz tamamlandıkça bu dosya güncellenir.

## 1. Sistemin Konumlandırılması

Sistem, **fakültenin seçmeli ders havuzunu yöneten karar destek sistemidir.**
Öğrenciye ders seçtirmez. Şu kararı verir:

- Hangi seçmeli ders **müfredatta tutulsun**,
- Hangisi **havuzda bekletilsin**,
- Hangisi **dinlenmeye alınsın**,
- Hangisi **iptal adayı** olsun.

Nihai karar her zaman akademik kurulundur. Sistem; veriye dayalı,
açıklanabilir ve denetlenebilir **öneri** üretir.

## 2. Veri Durumu (2026-06-11 itibarıyla)

- 2022 yılı verisi: 5 fakülte, 714 ders, 328 havuz kaydı mevcut.
- Aktif AHP profili ve aktif karar politikası var.
- `decision_runs` ve `semester_plan_runs` tabloları **boş** — projenin
  ana üretim hedefi bu iki çıktıyı üretmek.

## 3. Uçtan Uca Akış (Nihai)

> **Önemli:** "Öneri" insan girdisi değil, **algoritma çıktısıdır.**
> Hoca önerisi modülü yoktur. Sistem AHP + TOPSIS + trend + veri güveni
> + karar politikası ile dersleri kendi puanlar ve önerir; akademik kurul
> yalnızca onay/red verir.

```
00. Sistem & DB Sağlığı           [mevcut: Sistem Sağlığı]
01. Kapsam Seçimi (yıl/fak/böl)   [global state]
02. Veri Yönetimi & Import        [mevcut: Veri Yönetimi]
03. Veri Kalitesi                 [mevcut: Veri Kalitesi]
04. Kriter Girdi (MANUEL)         [mevcut: Kriterler]  ← Faz 0'da geri alındı
05. AHP Ağırlık Yönetimi          [mevcut, mevcut 4 kriter korunuyor]
06. Karar Politikası              [mevcut]
07. Hazırlık Kontrolü             [mevcut: dc7fdd2]
08. Resmi Karar Çalıştırma        [mevcut, ilk run üretilecek]
09. Ders Kararları & Gerekçe      [mevcut]
10. Önerilen Dersler Ekranı       [YENİ — Faz 3]
11. Hassas Kararlar & Adalet      [mevcut]
12. Akademik Onay                 [mevcut]
13. Havuz Yaşam Döngüsü           [mevcut]
14. Dönem Planlama                [mevcut, ilk plan üretilecek]
15. Raporlama & Dışa Aktarım      [mevcut]
```

## 4. Açılabilirlik Skoru (Yeni — karar ÇIKTISI)

```
Acilabilirlik_Skoru =
    0.45 × TOPSIS_Skoru     +
    0.25 × Talep_Skoru      +
    0.15 × Veri_Guveni      +
    0.10 × Donem_Uygunlugu  +
    0.05 × Kaynak_Uygunlugu
```

- TOPSIS skoru zaten AHP+TOPSIS hattından geliyor (0–100).
- Talep skoru `populerlik.doluluk_orani` ve anket tercih oranından türetilir.
- Veri güveni `course_decisions.data_confidence_score`'tan gelir (zaten var).
- Dönem uygunluğu: dersin geçmişte hangi dönem açıldığı, hoca uygunluğu vs.
  basit kural seti (Faz 2'de tanımlanacak).
- Kaynak uygunluğu: kontenjan/lab gereksinimi vs. (opsiyonel, başlangıçta 1.0
  varsayılabilir).

Bu skor **Önerilen Dersler ekranında** sıralama için ve **Dönem Planlamada**
seçim/atama için kullanılır. Bir ders akademik olarak güçlü olabilir
(yüksek TOPSIS) ama o dönem dönem uygunluğu/kaynak nedeniyle açılamayabilir
— Açılabilirlik skoru bu farkı yakalar.

**Not:** İlk implementasyonda `Donem_Uygunlugu` ve `Kaynak_Uygunlugu`
sabit 1.0 (= "bilinmiyor, kısıt yok") olarak başlatılabilir. Böylece skor
TOPSIS + Talep + Veri Güveni üzerinden çalışır; kısıt bilgisi eklenince
formül kendiliğinden doğru sonuca yaklaşır.

## 5. Faz Haritası (Sadeleştirilmiş)

| Faz | Konu | Statü | Notlar |
|----:|---|---|---|
| 0 | Codex revert — manuel kriter girişi aç | **Tamam** | A1 yolu seçildi; 3/3 test yeşil |
| 1 | Şema: `course_decisions.acilabilirlik_score` REAL kolonu | **Tamam** | Tek ALTER, idempotent |
| 2 | Karar çalıştırma hattı: ilk gerçek `decision_runs` üret | **Tamam** | CLI: `run_first_decision_2022` |
| 3 | Önerilen Dersler ekranı + Açılabilirlik skoru hesabı | **Tamam** | `acilabilirlik_service` + UI sekmesi |
| 4 | Dönem Planlama bağlantısı: ilk `semester_plan_runs` | **Tamam** | Açılabilirlik aday skoru + CLI |
| 5 | Uçtan uca senaryo testi + rapor dışa aktarımı | **Tamam** | E2E test; 512 paket testi yeşil |

Her faz ayrı commit, ayrı konuşma. Faz arası "tamam" onayı beklenir.

**İptal edilen fazlar (önceki taslakta vardı):**

- ~~Hoca Önerileri modülü~~ — sistem zaten otomatik öneri sunuyor, ayrı modüle gerek yok.
- ~~AHP'ye `hoca_oneri` kriteri eklenmesi~~ — mevcut 4 kriter (basari, trend, populerlik, anket) korunuyor.

## 5.1. Faz 2 — Yapılanlar (özet)

UI'daki "Yeni Karar Çalıştır" butonu zaten kuruluymuş:
`decision_center_page.py:345` → `_execute_run` → `run_all_algorithms_for_year`
→ `generate_next_year_curricula` → `record_decision_run_for_faculty_year`.
Senaryoda `decision_runs` boş çıkıyor olması butona daha hiç basılmadığından.

Faz 2 çıktısı: CLI'dan da koşturulabilen bir wrapper.

**Yeni dosya:** `scripts/run_first_decision_2022.py`

Kullanım:

```bash
# Tüm fakülteler, 2022 Güz (varsayılan)
python -m scripts.run_first_decision_2022

# Belirli bir fakülte
python -m scripts.run_first_decision_2022 --fakulte-id 3

# Bahar dönemi
python -m scripts.run_first_decision_2022 --donem Bahar

# Farklı bir DB
python -m scripts.run_first_decision_2022 --db data/adil_secmeli.db
```

Çıktı: işlenen / atlanan / hatalı fakülteler + öncesi/sonrası
`decision_runs` ve `course_decisions` satır sayıları.

**Çalıştırma şartları:**

- Uygulama kapalı olmalı (DB kilidi).
- 2022 yılı için kriter girişi tamam olmalı; eksik fakülteler "atlanan"
  listesinde görünür.
- Aktif AHP profili ve aktif karar politikası gerekli (mevcut).

**Olası senaryo:** Tüm 5 fakülte için kriter tamlığı tamamsa 5
`decision_runs` satırı, 714 dersin tamamı için `course_decisions` satırı
oluşur. Bir fakültede eksik varsa o atlanır, diğerleri yine işlenir.

## 5.2. Faz 3 — Yapılanlar (özet)

**Yeni servis:** `app/services/acilabilirlik_service.py`

- `compute_acilabilirlik_score(...)` — saf formül (0.45 TOPSIS + 0.25 talep
  + 0.15 veri güveni + 0.10 dönem + 0.05 kaynak), girdileri 0–100'e kelepçeler.
- `derive_talep_score(metrics)` — `populerlik`(doluluk) ve `anket`
  sinyallerinden (0–1) talep skorunu (0–100) türetir.
- `categorize_recommendation(final_status, approval_required)` — 5 kategori:
  Güçlü / Şartlı / Havuzda / Dinlenme / İptal Adayı.
- `list_recommended_courses(conn, run_id)` — kolon doluysa onu, NULL ise
  anlık hesabı kullanır; açılabilirliğe göre azalan sıralı liste döner.

**Karar hattına bağlama:** `decision_run_service.record_decision_run_for_faculty_year`
her ders için açılabilirlik hesaplar ve `course_decisions.acilabilirlik_score`'a
yazar (additif; INSERT'e tek kolon). Yeni run'lar otomatik dolar.

**Yeni UI sekmesi:** Karar Merkezi → "Önerilen Dersler". Seçili run'ın
çıktısını açılabilirlik skoruna göre sıralı gösterir; kategori, TOPSIS,
trend, veri güveni, final statü ve onay durumu sütunları.

**Testler:** `app/tests/test_acilabilirlik_service.py` (17 test) + entegrasyon
testine açılabilirlik kolonu assert'ü. Tümü yeşil.

**Dönem/Kaynak uygunluğu** şu an varsayılan 100.0. Kısıt verisi eklenince
(Faz 4 — Dönem Planlama) bu bileşenler gerçek değerlerle beslenecek.

## 5.3. Faz 4 — Yapılanlar (özet)

Dönem Planlama motoru (`semester_planning_engine.py`) zaten mevcuttu ve
`semester_plan_runs`'a yazıyordu; UI'da "Plan Üret" butonu kuruluydu. İki iş yapıldı:

**1. Açılabilirlik → Planlama bağı.** `_latest_acilabilirlik_scores(...)`
eklendi: kapsamdaki en güncel karar çalıştırmasından `course_decisions.acilabilirlik_score`
okur. `_fetch_candidate_courses` artık aday skorunu **önce açılabilirlikten**
alır, karar çalıştırması yoksa eski `skor` tablosuna düşer (geriye dönük uyumlu).
Böylece "Önerilen Dersler" çıktısı dönem planı aday sıralamasını besler.

**2. CLI script:** `scripts/run_first_semester_plan_2022.py` — tüm fakülteler
için 2022 dönem planı üretir, `semester_plan_runs` öncesi/sonrası sayar.

```bash
python -m scripts.run_first_semester_plan_2022
python -m scripts.run_first_semester_plan_2022 --fakulte-id 3
```

**Ön koşul:** Önce `run_first_decision_2022` koşturulmalı ki açılabilirlik
skorları üretilmiş olsun. Karar yoksa planlama yine çalışır ama `skor`
tablosunu kullanır.

**Testler:** `app/tests/test_acilabilirlik_planning_link.py` (3 test) —
fallback, açılabilirlik ezme, en güncel run kazanır. Tümü + mevcut planlama
testleri yeşil.

**Çalıştırma sırası (özet):**

```
1. python -m scripts.run_first_decision_2022       → decision_runs + açılabilirlik
2. python -m scripts.run_first_semester_plan_2022  → semester_plan_runs
```

## 5.4. Faz 5 — Yapılanlar (özet)

**Yeni test:** `app/tests/test_end_to_end_pipeline.py`

Tek geçici DB üzerinde tüm karar destek hattını uçtan uca koşturur ve
parçaların gerçekten bağlı olduğunu kanıtlar:

1. **Kriter verisi** (3 seçmeli ders, farklı başarı/talep) hazırlanır.
2. **Karar çalıştırma** → `decision_runs` + `course_decisions`; her ders
   kararının `acilabilirlik_score` ile yazıldığı doğrulanır (Faz 3).
3. **Önerilen Dersler** → `list_recommended_courses` azalan açılabilirlik
   sırasında, `oneri_kategori` ile döner (Faz 3).
4. **Dönem Planı** → `generate_semester_plan`; aday skorlarının
   açılabilirlikten geldiği (`score_source == "acilabilirlik"`) ve
   `semester_plan_runs` kaydının yazıldığı doğrulanır (Faz 4).
5. **Dışa aktarım** → `export_semester_plan(... "csv")` CSV üretir, ders
   kodu içeriği doğrulanır.

**Sonuç:** Tüm proje test paketi **512 passed, 1 skipped** (skip önceden
mevcut, DB bağımlı API smoke). Faz 0–5 boyunca hiçbir regresyon yok.

**Mevcut rapor dışa aktarım yolları** (zaten projede):
- `export_semester_plan(conn, run_id, "csv")` — Güz/Bahar atamaları.
- `export_constraint_violations(conn, run_id, "csv")` — kısıt ihlalleri.
- `generate_human_readable_plan_report(conn, run_id)` — insan-okur rapor.
- Raporlama & Analiz sayfasından havuz/müfredat CSV/Excel dışa aktarımı.

## 6. Faz 0 — Yapılanlar (özet)

- `app/ui/tabs/criteria_page.py` HEAD'e geri alındı (Codex'in `MANUAL_CRITERIA_ENTRY_ENABLED=False` değişikliği iptal).
- `app/services/student_dataset_criteria_service.py` HEAD'e geri alındı.
  Servis dosyası silinmedi; "OTOMATIK URETIM" butonundan elle çalıştırılabilir
  durumda (pre-Codex davranışı).
- `app/tests/test_criteria_page.py` HEAD'e geri alındı.
- `app/tests/test_student_dataset_criteria_service.py` (Codex'in eklediği) silindi.
- `data/adil_secmeli.db` — Codex'in auto-import koşturduğu sırada DB'ye yazdığı
  performans/popülerlik satırları **kaldı.** Uygulama açıkken `git checkout`
  başarısız oldu. Uygulama kapatılınca `git checkout HEAD -- data/adil_secmeli.db`
  veya `data/adil_secmeli.db.bak_kriter_temiz_20260520_013904` yedeği geri yüklenmeli.

Sonuç: kullanıcı `Kriterler` sayfasında **manuel veri girer**; gerekirse
"OTOMATIK URETIM" butonuyla 2022 Excel'inden tek seferlik toplu üretim de
yapabilir (eski opsiyonel davranış).

## 7. Manuel Kriter Girişi — Asıl İstenen

Kullanıcının ifadesiyle:

> "Ben o excel girdisini sisteme manuel olarak girmek girdiğimde kriterlerin öyle oluşturmak istedim."

Yani:

- Excel = **referans kaynak** (öğretim üyesi/koordinatör elinde, dışarıda).
- Kullanıcı dersi seçer, alanları okuyarak elle girer:
  - Toplam öğrenci, geçen öğrenci, ortalama not, kontenjan, kayıtlı, anket katılımı, dersi seçen.
- Sistem `update_calculations` ile **anlık olarak** başarı oranı,
  doluluk oranı, anket tercih oranını **otomatik hesaplar**.
- Kaydet → `ders_kriterleri`, `performans`, `populerlik` tablolarına yazılır.

Bu davranış pre-Codex haliyle zaten mevcut — Faz 0 sonrasında geri geldi.
İleride istenirse "Excel ham veri yan paneli" eklenebilir (A2 yolu) ama
şu an gerekli değil.

## 8. Faz 1 — Şema Planı

### 8.1. Mevcut Şemayı Tarama Bulguları

- `ahp_weight_profiles.criteria_keys_json` — mevcut 4 kriter
  (`basari`, `trend`, `populerlik`, `anket`) korunur. Değişiklik yok.
- `decision_runs` — run kaydı; alanlar yeterli.
- `course_decisions` — `topsis_score`, `trend_score`, `data_confidence_score`
  var. **Eklenecek tek kolon:** `acilabilirlik_score`.
- `course_score_breakdowns` — `weights_json`, `contribution_json` zaten var;
  açılabilirlik skoru bileşenleri burada saklanabilir.
- Yeni tablo **gerekmez.** `Önerilen Dersler` ekranı `course_decisions`'tan
  (yeni eklenen `acilabilirlik_score` kolonuyla birlikte) beslenir.

### 8.2. `course_decisions` İçin Tek Yeni Kolon

```sql
ALTER TABLE course_decisions
    ADD COLUMN acilabilirlik_score REAL;
```

`schema_compat.py` zaten idempotent kolon ekleme yapıyor — oraya tek satır
eklenecek. Migration risksiz: NULL default, eski kayıtlar bozulmaz.

### 8.3. Migration Sırası

1. `schema_compat.py` içine `course_decisions.acilabilirlik_score` eklemesi
   idempotent şekilde tanımlanır.
2. Uygulama açıldığında `ensure_reporting_schema()` otomatik uygular.
3. Mevcut `course_decisions` satırı henüz yok → migration risk = 0.

### 8.4. Faz 1 Sonrası Adımlar

Faz 1 minik bir şema değişikliği olduğu için ayrı bir incelemeye gerek yok;
doğrudan koda dökülebilir. Sonra Faz 2 (`decision_runs` üretimi) gelir.

**Faz 1 implementation çıktısı:**

- `app/db/schema_compat.py` içinde `course_decisions` için bir `_add_column_if_missing("acilabilirlik_score", "REAL")` çağrısı.
- Test: yeni kolonun var olduğunu doğrulayan tek satırlık idempotent test.
- Açılabilirlik skoru **hesaplama mantığı Faz 3'te** yazılır (Önerilen Dersler ekranıyla beraber).
