# Adil Seçmeli — Matematiksel/İstatistiksel Hesaplama Denetim Raporu

**Tarih:** 2026-06-15
**Kapsam:** Algoritmaların doğruluğu, girdi/çıktı eşleşmeleri, veri girişleri, müfredat üretim akışı, ders önerisi ve takas özelliği.
**Yöntem:** Çekirdek algoritma kaynak kodu satır satır okundu; üretim hattı (AHP→TOPSIS→açılabilirlik→karar) izlendi; gerçek veritabanı (`data/adil_secmeli.db`) üzerinde fonksiyonel testler çalıştırıldı.

> **Genel sonuç:** Çekirdek matematik (AHP özvektör + tutarlılık oranı, TOPSIS vektör normalizasyonu + ideal çözüm mesafeleri) **doğru ve gerçek hayata uygun** çalışıyor. AHP profil verisi gerçekten yükleniyor ve TOPSIS'e ağırlık olarak besleniyor. Tespit edilen sorunlar çoğunlukla **veri eksikliği** ve birkaç **tasarım/placeholder** kararından kaynaklanıyor; algoritmik hata değil.

---

## 1. Çekirdek Algoritmaların Matematiksel Doğruluğu

### 1.1 AHP — `app/algorithms/mcdm/ahp.py`
| Adım | Uygulama | Değerlendirme |
|------|----------|---------------|
| Ağırlık türetme | Asal özvektör (`np.linalg.eig`, en büyük gerçek özdeğer) | ✅ Doğru |
| λmax | `mean(Aw / w)` | ✅ Doğru |
| Tutarlılık İndeksi (CI) | `(λmax − n)/(n − 1)` | ✅ Doğru |
| Tutarlılık Oranı (CR) | `CI / RI`, RI tablosu n=1..10 | ✅ Doğru |
| Matris doğrulama | Kare, pozitif, sonlu kontrolü | ✅ Sağlam |

**Gerçek veri testi:** Aktif profil (id=11) ağırlıkları `{başarı 0.411, trend 0.201, popülerlik 0.194, anket 0.194}`, toplam = 1.0, **CR = 0.027 < 0.10 → tutarlı**. Beklenen AHP çıktısıyla birebir uyumlu.

### 1.2 TOPSIS (üretim motoru) — `app/services/calculation.py::KararMotoru.topsis_calistir`
| Adım | Uygulama | Değerlendirme |
|------|----------|---------------|
| 1. Normalizasyon | Vektör (karekök toplam) `r_ij = x_ij / √Σx²` | ✅ Doğru |
| 2. Ağırlıklı matris | `v_ij = w_j · r_ij` | ✅ Doğru |
| 3. İdeal çözümler | **Fayda/maliyet ayrımı VAR** (`benefit_map`): fayda → max, maliyet → min | ✅ Doğru ve eksiksiz |
| 4. Mesafeler | Öklid `S+`, `S-` | ✅ Doğru |
| 5. Yakınlık | `C_i = S- / (S+ + S-)`, 0–1, ×100 | ✅ Doğru |

Maliyet (cost) tipi kriterler `criteria_definition_service.criteria_direction_map` üzerinden okunan `is_benefit` bayrağıyla doğru yönde işleniyor — bu, birçok TOPSIS uygulamasında atlanan kritik bir detay.

### 1.3 VIKOR / PROMETHEE — `app/algorithms/mcdm/{vikor,promethee}.py`
- VIKOR: S/R/Q hesapları, `v` uzlaşma parametresi (0.5) **doğru**. Ancak **BENCHMARK_ONLY** modda; gerçek müfredat kararına girmiyor.
- PROMETHEE: aynı şekilde benchmark amaçlı.

### 1.4 Standalone TOPSISRanker — `app/algorithms/mcdm/topsis.py`
- Matematik doğru fakat **fayda/maliyet ayrımı YOK** (her kriter için max=ideal kabul ediliyor). Yalnızca benchmark/karşılaştırma sayfasında kullanıldığından üretim kararını etkilemiyor. **İyileştirme önerisi (P2):** `benefit_map` parametresi eklenerek üretim motoruyla aynı seviyeye getirilmeli.

---

## 2. Girdi → Çıktı Akışı Doğrulaması (Müfredat Üretimi)

**Buton:** `semester_planning_page.generate_plan()` / Karar Merkezi "Yeni Karar Çalıştır".
**Çekirdek orkestratör:** `calculation.generate_next_year_curricula()` → `get_faculty_year_topsis_results()`.

| Aşama | Konum | Durum |
|-------|-------|-------|
| AHP profili çözümleme | `calculation.py:1169` `resolve_ahp_profile()` | ✅ Yükleniyor |
| AHP ağırlıkları → TOPSIS | `calculation.py:1179` → `:1231` `topsis_calistir(df, agirliklar, …)` | ✅ Gerçekten besleniyor |
| Fayda/maliyet haritası | `calculation.py:1175` `criteria_direction_map()` | ✅ |
| Sadece müfredat dersleri TOPSIS'e girer | `calculation.py:1228` | ⚠️ Tasarım (bkz. 5.1) |
| Havuz dersleri anket-only puan (~50±10) | `calculation.py:1262` | ⚠️ Tasarım (bkz. 5.1) |
| Tutarsız profilde strict-mod hatası | `calculation.py:1185` | ✅ Karar Merkezi yolu güvenli |

**Gerçek veri testi — tüm fakülteler eş zamanlı (2022, Güz):**

| Fakülte | Skor üretildi | TOPSIS dersi | Havuz (anket-only) |
|---------|--------------:|-------------:|-------------------:|
| Tıp | 14 | 4 | 10 |
| Mühendislik ve Doğa | 158 | 12 | 146 |
| Sağlık Bilimleri | 121 | 12 | 109 |
| Güzel Sanatlar | 19 | 4 | 15 |
| İlahiyat | 16 | 4 | 12 |

Tüm fakülteler hatasız sonuç üretti; AHP ağırlıkları aktif profilden geldi.

### TOPSIS sonrası devreye giren algoritma — **Açılabilirlik** (`acilabilirlik_service.py`)
TOPSIS bir akademik kalite skoru verir; bunun ardından dersin **o dönem gerçekten açılabilir** olup olmadığını ölçen bileşik skor hesaplanır:

```
Açılabilirlik = 0.45·TOPSIS + 0.25·Talep + 0.15·Veri_Güveni + 0.10·Dönem_Uygunluk + 0.05·Kaynak_Uygunluk
```

- **Amacı mantıklı:** Yüksek TOPSIS skoru olan ama talebi düşük / verisi zayıf ders açılmamalı — gerçek hayata uygun.
- **Sorun (P1):** `Dönem_Uygunluk` ve `Kaynak_Uygunluk` şu an sabit **100** (placeholder). Bu, her dersin skoruna koşulsuz **+15** ekliyor → skorları yapay olarak şişiriyor ve dersleri birbirine yaklaştırıyor. Gerçek kısıt verisi (`course_semester_availability`, eğitmen/kaynak) bağlanana kadar bu iki bileşen anlamlı ayrım yapmıyor.

---

## 3. Ders Önerisi (Müfredat Dışı) — `pool_recommendation_service.py`

**Buton:** Karar Merkezi "Havuzdan Öner".

| Bileşen | Algoritma | Değerlendirme |
|---------|-----------|---------------|
| 4 kriter türetme | başarı, trend (geçen/toplam), popülerlik (kayıt/kontenjan), anket (katılım/kayıt) | ✅ Mantıklı oranlar |
| Normalizasyon | Min-max (aday küme içinde) | ✅ |
| Skorlama | **Ağırlıklı toplam (SAW/WSM)** × AKTİF AHP ağırlıkları | ⚠️ İsimlendirme: docstring "TOPSIS" diyor ama gerçekte **ağırlıklı toplam**; ideal-nokta mesafesi yok. Yanlış değil, **yanlış etiketli**. |
| Cosine boost | TF-IDF (char n-gram 2–4) + kosinüs benzerliği, +0..5 puan | ✅ Mantıklı (benzer adlı, geçmişte açılmış derslere küçük teşvik) |
| Eşik | Skor ≥ 60 → "AC" (açılması önerilir) | ✅ |

**Gerçek veri testi (2022):** 328 aday, 0 veri_yok; aktif AHP ağırlıkları kullanıldı; en yüksek 5 ders skor 97–99 aralığında listelendi. ✅ Çalışıyor.

**Öneri (P2):** Docstring ve UI metnindeki "TOPSIS" ifadesi "ağırlıklı toplam (AHP ağırlıklı)" olarak düzeltilmeli; ya da gerçek `topsis_calistir` çağrısına geçilmeli (tutarlılık için tercih edilir).

---

## 4. Veri Girişleri Denetimi (Sistem Başlangıcı)

**Gerçek DB satır sayıları (doğrulandı):**

| Girdi | Tablo | Adet | Kapsam | Durum |
|-------|-------|-----:|--------|-------|
| Fakülte | `fakulte` | 5 | — | ✅ |
| Bölüm | `bolum` | 9 | — | ✅ |
| Ders | `ders` | 714 | %100 | ✅ |
| Öğrenci | `ogrenci` | 1500 | %100 | ✅ |
| **Kriter** | `ders_kriterleri` | 328 | **%46** | ⚠️ Kısmi |
| **Performans** | `performans` | 72 | **%10** | ❌ Kritik boşluk (trend için) |
| **Popülerlik** | `populerlik` | 72 | **%10** | ⚠️ |
| Anket cevabı | `anket_cevap` | 3120 | — | ✅ |
| Anket sonucu | `anket_sonuclari` | 804 | — | ✅ |
| Müfredat | `mufredat` | 20 | — | ✅ |
| Müfredat-ders | `mufredat_ders` | 80 | — | ✅ |
| Havuz | `havuz` | 361 | — | ✅ |
| AHP profili (aktif) | `ahp_weight_profiles` | 1 | global, CR=0.027 | ✅ |
| Karar politikası | `decision_policies` | 1 | — | ✅ |

**Sonuç:** Ana yapı (ders/öğrenci/müfredat/havuz/AHP/politika) hazır. **Yeni müfredat üretimine engel olan iki kritik boşluk:**
1. **Performans verisi %10** → trend analizi ≥2 yıl geçmiş ister; derslerin ~%90'ı "yetersiz veri" damgası alır. Trend zorunlu alansa kriter kapısı bloklar.
2. **Kriter verisi %46** → %100 tamlık isteyen politikada eksik dersli bölümler bloklanır (yeni ders 2 yıl muafiyeti hariç).

---

## 5. Gerçek Hayat Uygunluğu — Yorum ve Mantık Kontrolü

### 5.1 Havuz dersleri TOPSIS'e girmiyor (⚠️ Tasarım kararı)
Müfredat dışı (havuz) dersler yalnızca anket sinyaliyle ~50±10 puan alıyor; 4 kriterli çok-ölçütlü analiz dışında kalıyor. **Gerçek hayat yorumu:** Bir dersin "müfredata aday" olarak adil değerlendirilmesi için tüm adayların aynı TOPSIS evreninde yarışması beklenir. Mevcut tasarım, havuz derslerini sistematik dezavantaja sokuyor. **Öneri (P1):** Havuz dersleri de (verisi olanlar) TOPSIS evrenine dahil edilmeli; veri yoksa düşük güven etiketiyle işaretlenmeli.

### 5.2 Açılabilirlik sabit +15 (⚠️ Placeholder) — bkz. §2. Gerçek hayatta dönem/kaynak kısıtı her ders için 100 olamaz.

### 5.3 Sessiz AHP geri-düşüşü (⚠️)
`strict_ahp=False` iken profil çözülemezse sessizce legacy Saaty ağırlıklarına düşülüp yalnızca log yazılıyor. Karar Merkezi yolu `strict_ahp=True` ile korunuyor (hata fırlatır) ama otomatik hat sessiz kalabilir. **Öneri (P2):** Sonuç sözlüğüne `ahp_fallback_used` bayrağı UI'da görünür kılınmalı.

---

## 6. Tespit Edilen Sorunlar — Öncelikli Liste

| # | Öncelik | Sorun | Konum | Tür |
|---|---------|-------|-------|-----|
| 1 | **P1** | Performans verisi %10 → trend bloklaması | `performans` tablosu | Veri |
| 2 | **P1** | Kriter verisi %46 → tamlık kapısı bloklaması | `ders_kriterleri` | Veri |
| 3 | **P1** | Açılabilirlik dönem/kaynak sabit 100 (+15 şişirme) | `acilabilirlik_service.py:46` | Placeholder |
| 4 | **P1** | Havuz dersleri TOPSIS dışı (anket-only) | `calculation.py:1262` | Tasarım |
| 5 | P2 | "Havuzdan Öner" gerçekte SAW; "TOPSIS" yanlış etiketli | `pool_recommendation_service.py` | Etiket |
| 6 | P2 | Standalone TOPSISRanker'da fayda/maliyet yok | `algorithms/mcdm/topsis.py` | Eksik (benchmark) |
| 7 | P2 | Sessiz AHP geri-düşüşü UI'da görünmüyor | `calculation.py:1198` | UX/şeffaflık |
| 8 | P3 | `ahp_weight_page.py.conflict.bak` artık dosya | `app/ui/tabs/` | Temizlik |

---

## 7. Adım Adım Uygulama Planı

**Bu PR'da uygulananlar:**
- ✅ **Ders önerisi ↔ müfredat takas özelliği + butonu** (Madde 9). Yeni servis `curriculum_swap_service.py` + Karar Merkezi "Önerilen Dersler" sekmesine "↔ Müfredattaki Bir Dersle Takas Et" butonu. Gerçek DB'de test edildi (statü, havuz, müfredat-ders senkronu + denetim kaydı + AKTS uyarısı).

**Sonraki adımlar (öneri):**
1. **P1 – Veri tamamlama:** 2020–2022 performans ve eksik kriter kayıtlarını ETL ile içeri al; trend kapısını besle.
2. **P1 – Açılabilirlik:** `course_semester_availability` ve eğitmen/kaynak tablolarından `dönem_uygunluk`/`kaynak_uygunluk` türet; sabit 100'ü kaldır.
3. **P1 – Havuz TOPSIS:** Verisi olan havuz derslerini TOPSIS evrenine dahil et; güven etiketi ekle.
4. **P2 – İsimlendirme/şeffaflık:** "Havuzdan Öner" etiketini düzelt; `ahp_fallback_used` bayrağını UI'da göster; TOPSISRanker'a `benefit_map` ekle.
5. **P3 – Temizlik:** `.conflict.bak` dosyasını sil.

---

## 8. Müfredat Üretimine Hazırlık — Özet

**Hazır olanlar:** Şema, ders/öğrenci/fakülte/bölüm ana verisi, müfredat+havuz tanımları, aktif & tutarlı AHP profili, karar politikası, çalışan AHP→TOPSIS→açılabilirlik→karar hattı.

**Üretim öncesi tamamlanması gerekenler:** Performans verisi (%10→en az %40), kriter kapsamı (%46→%50+). Aksi halde kriter tamlık kapısı (`can_run_algorithm`) ve hazırlık kapısı (`_readiness_gate`) çoğu bölümü bloklayabilir; bloklamadığında üretilen müfredat az sayıda gerçek TOPSIS dersi + çok sayıda anket-only havuz dersi içerir.

---

## 9. Uygulanan Özellik: Müfredat ↔ Önerilen Ders Takası

**Yeni dosya:** `app/services/curriculum_swap_service.py`
- `swap_curriculum_course(conn, run_id, incoming_course_id, outgoing_course_id, created_by)`: Önerilen/havuz dersini müfredata (final_status=1), müfredat dersini havuza (0) taşır. Hem `course_decisions` hem canlı `havuz.statu` ve `mufredat_ders` senkronlanır; `curriculum_swaps` denetim tablosuna kayıt yazılır. AKTS/kredi/bölüm farkı **uyarı** olarak döner (engellemez).
- `list_curriculum_courses_for_run(conn, run_id)`: Takas için müfredattaki dersleri listeler.

**UI:** `app/ui/tabs/decision_center_page.py` → "Önerilen Dersler" sekmesi:
- "↔ Müfredattaki Bir Dersle Takas Et" butonu.
- Seçilen önerilen ders için, müfredattaki dersleri listeleyen modal seçim penceresi açılır; kullanıcı çıkacak dersi seçince takas uygulanır ve liste tazelenir.

**Doğrulama (gerçek DB, run 33):** Havuz dersi (id=3) ↔ müfredat dersi (id=29) takası: `final_status` 3→1, 29→0; havuz 2 kayıt, müfredat-ders 1 kayıt güncellendi; AKTS farkı (5↔2) uyarısı üretildi. Test sonrası DB ilk haline döndürüldü.
