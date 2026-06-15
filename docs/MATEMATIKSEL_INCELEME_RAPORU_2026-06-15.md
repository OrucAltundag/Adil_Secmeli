# Matematiksel İnceleme Raporu — Kesinleşme Puanı / AHP / TOPSIS / Trend / ML

**Tarih:** 2026-06-15
**Kapsam:** Spec Bölüm 9–23 (matematiksel doğrulama) + Bölüm 19–20 (3 ders sayısal örnek)
**Yöntem:** Gerçek üretim veritabanı (`data/adil_secmeli.db`) üzerinde gerçek motor fonksiyonları
çalıştırılarak elde edilen sayılar. Hiçbir değer uydurulmamıştır.
**Durum:** DOĞRULAMA (Faz B). Bu rapor mevcut (eski) davranışı belgeler ve düzeltme önerir;
kod değişikliği henüz uygulanmadı (Bölüm 21 gereği "önce eski hali raporla").

---

## 0. Yönetici Özeti (TL;DR)

| Konu | Spec endişesi | Bulgu | Sonuç |
|------|---------------|-------|-------|
| **AHP özvektör** | Doğru mu? | Perron-Frobenius ana özvektör, normalize, toplam=1. CR<0.10. | ✅ DOĞRU |
| **Aktif AHP profili** | Sabit ağırlık mı? | Skor yolu aktif profili (id=11) okuyor; ağırlıklar profilden geliyor, fallback yok. | ✅ KULLANILIYOR |
| **TOPSIS formülü** | Rank-bazlı sahte mi? | Gerçek vektör normalizasyon + S+/S- + C=S⁻/(S⁺+S⁻). | ✅ GERÇEK |
| **"Çok düzenli" skorlar (1.0, 0.83, 0.33, 0)** | Yapay ölçekleme mi? | Formül gerçek; ama **girdiler dejenere** → çıktı rank gibi görünüyor. | ⚠️ KÖK NEDEN FARKLI |
| **Trend nötr skoru** | Veri yoksa nötr mü? | İki implementasyon var; **nötr düzeltme skor yoluna bağlı değil**. | ❌ HATA |
| **ML (LR/RF/DT)** | Nihai kararı bozuyor mu? | `advisory_ml` olarak yönetiliyor; skor yolunda ML **yok**. | ✅ DOĞRU KONUM |

**En kritik 3 bulgu:**
1. **Trend = Başarı çakışması (36/36 ders):** 2022 başlangıç yılında trend kriteri, başarı
   kriterinin birebir kopyası. Trend bağımsız bilgi taşımıyor; başarı iki kez sayılıyor.
2. **Dejenere TOPSIS girdileri:** 2022'de 4 kriterden 3'ü (trend, popülerlik, anket) ayırt
   edici değil (popülerlik ve anket varyansı = 0). Kesinleşme puanı pratikte yalnız başarının
   0–100'e ölçeklenmiş hâli. Bu yüzden skorlar "rank gibi" çıkıyor.
3. **Göreli sıfırlama:** 36 TOPSIS dersinden **8'i (%22)** kesinleşme puanı 0.0 alıp baraj-altı
   (<40) düşüyor — hepsinin başarısı 0.80–0.94 olmasına rağmen, sırf göreli en düşük oldukları için.

---

## 1. Genel Karar Akışı

```
ders_kriterleri / performans / populerlik  (ham veri)
        │
        ▼
_read_course_metrics()            → {basari, trend, populerlik, anket, ortalama_not}  (her biri 0–1)
        │
        ├── aktif AHP profili (resolve_ahp_profile) → ağırlıklar w = [w_basari, w_trend, w_pop, w_anket]
        │
        ▼
topsis_calistir(df, w)            → C (yakınlık katsayısı 0–1) → Kesinlesme_Puani = C×100
        │                            (YALNIZ müfredattaki dersler)
        │
        ├── müfredat DIŞI dersler → _pool_course_score_anket_only(anket) → 50 ± 10  (TOPSIS'e girmez)
        │
        ▼
persist_faculty_year_topsis_scores → havuz.skor
        │
        ▼
karar eşikleri (DROP_SCORE_THRESHOLD=40, DROP_AVERAGE_GRADE_THRESHOLD=45) → müfredatta kal / düş / havuz
```

**İlgili dosyalar:** [calculation.py](../app/services/calculation.py) (`KararMotoru`,
`_read_course_metrics`, `get_faculty_year_topsis_results`, `topsis_calistir`,
`persist_faculty_year_topsis_scores`), [trend_analysis_service.py](../app/services/trend_analysis_service.py),
[ahp_profile_service.py](../app/services/ahp_profile_service.py).

---

## 2. Kullanılan Veri Kaynakları

| Kriter | Tablo | Alan | Formül |
|--------|-------|------|--------|
| Başarı | `performans` / `ders_kriterleri` | `basari_orani` veya `gecen/toplam` | geçen ÷ toplam, [0,1] clamp |
| Trend | `performans.basari_orani` (≤ yıl, son 3 yıl) | geçmiş başarı | ağırlıklı ort. (0.50/0.30/0.20) |
| Popülerlik | `populerlik.doluluk_orani` / `ders_kriterleri` | doluluk | kayıtlı ÷ kontenjan, [0,1] |
| Anket | `ders_kriterleri` | `anket_dersi_secen / anket_katilimci` | [0,1] clamp |

**Veri durumu (DB anlık görüntüsü):** müfredat 2022 (18) + 2023 (3); performans ve
ders_kriterleri **yalnız 2022** (72'şer satır); havuz 2022 (340) + 2023 (41).
→ **2022 sistemin başlangıç yılı**, önceki yıl verisi yok.

---

## 3–5. Kriterler, Sayısal Değerler ve Normalizasyon

**Normalizasyon (TOPSIS vektör yöntemi):** `r_ij = x_ij / √(Σ x_ij²)`. Her kriter sütunu
karekök-toplamına bölünür. Ağırlıklı matris `v_ij = w_j · r_ij`. ✅ Matematiksel olarak doğru.

**Veri kalitesi sorunu (Tıp Fak. 2022, 4 ders):**

| ders_id | Ad | toplam/geçen | kontenjan/kayıtlı | anket(katılım/seçen) | → basari | pop | anket |
|---------|-----|------|------|------|------|------|------|
| 769 | Tıbbi Etik Seçmeli | 50/48 | 60/50 | 44/50 | 0.960 | 0.833 | 1.000 |
| 30 | Toplum Projesi | 50/47 | 60/50 | 44/50 | 0.940 | 0.833 | 1.000 |
| 768 | Klinik Anatomi Seçmeli | 50/44 | 60/50 | 43/50 | 0.880 | 0.833 | 1.000 |
| 29 | Girişimcilik | 50/42 | 60/50 | 42/50 | 0.840 | 0.833 | 1.000 |

> ⚠️ **Veri kalitesi hatası:** `anket_dersi_secen (50) > anket_katilimci (44)` — dersi seçen
> sayısı ankete katılandan büyük olamaz. Oran 50/44=1.136 → 1.0'a clamp ediliyor, bu yüzden
> **tüm derslerde anket=1.000** (varyans 0).
> **Popülerlik** kayıtlı=50/kontenjan=60 → tüm derslerde 0.833 (varyans 0).

---

## 6–8. Aktif AHP Profili, Ağırlıklar, Tutarlılık Oranı

**Aktif profil (gerçek çalıştırma):** `ahp_profile_id = 11`, `is_consistent = True`,
`ahp_fallback_used = False`. → **Aktif profil gerçekten kullanılıyor**, sabit ağırlık değil.

**Ağırlıklar (profil 11):**

| Kriter | Ağırlık |
|--------|---------|
| Başarı | 0.4111 |
| Trend | 0.2006 |
| Popülerlik | 0.1942 |
| Anket | 0.1942 |
| **Toplam** | **1.0000** ✅ |

**AHP matematiği** ([calculation.py:92](../app/services/calculation.py) `ahp_calistir`,
`ahp_tutarlilik_kontrolu`):
- Saaty 4×4 ikili karşılaştırma matrisi, `a[i][j] = 1/a[j][i]` karşılıklılık ✅
- Ana özvektör (Perron-Frobenius) → normalize, Σ=1 ✅
- `λmax = mean((A·w)/w)`, `CI = (λmax−n)/(n−1)`, `CR = CI/RI₄` (RI₄=0.90) ✅
- Legacy Saaty matrisi için CR ≈ 0.089 < 0.10 → geçerli ✅

> ⚠️ **İnce nokta:** `strict_ahp=False` (varsayılan) modda aktif profil çözülemezse sessizce
> legacy Saaty ağırlıklarına düşülüyor (`ahp_fallback_used=True` bayrağıyla). Karar Merkezi
> çağrılarında `strict_ahp=True` yapılmalı ki kullanıcı seçmediği ağırlıklarla karar üretilmesin.
> Ayrıca CR, profilin kendi matrisine göre değil legacy matrise göre hesaplanıyor; profil yalnız
> ağırlık taşıdığı için profilin gerçek tutarlılığı bu CR ile ölçülmüyor.

---

## 9–13. TOPSIS: Karar Matrisi → İdeal Çözümler → S± → C → Kesinleşme

**Gerçek çıktı (Tıp Fak. 2022, ağırlık profil 11):**

Ağırlıklı normalize ideal çözümler:

| Kriter | A⁺ (pozitif ideal) | A⁻ (negatif ideal) | Fark |
|--------|------|------|------|
| Başarı | 0.21774 | 0.19052 | 0.02722 |
| Trend | 0.10624 | 0.09296 | 0.01328 |
| Popülerlik | 0.09708 | 0.09708 | **0.00000** |
| Anket | 0.09708 | 0.09708 | **0.00000** |

> **A⁺ = A⁻ olan kriterler (popülerlik, anket) S+/S-'ye sıfır katkı verir.** Yani TOPSIS
> mesafesi yalnız başarı ve trend ekseninde oluşuyor — ve aşağıda görüleceği gibi bu ikisi
> birbirinin kopyası.

| ders_id | Ad | basari | **trend** | pop | anket | S⁺ | S⁻ | C | **Kesinleşme** |
|---------|-----|--------|-----------|-----|-------|------|------|------|------|
| 769 | Tıbbi Etik | 0.960 | **0.960** | 0.833 | 1.000 | 0.0000 | 0.0303 | 1.0000 | **100.00** |
| 30 | Toplum Projesi | 0.940 | **0.940** | 0.833 | 1.000 | 0.0050 | 0.0252 | 0.8333 | **83.33** |
| 768 | Klinik Anatomi | 0.880 | **0.880** | 0.833 | 1.000 | 0.0202 | 0.0101 | 0.3333 | **33.33** |
| 29 | Girişimcilik | 0.840 | **0.840** | 0.833 | 1.000 | 0.0303 | 0.0000 | 0.0000 | **0.00** |

**Doğrulama:** `C = S⁻/(S⁺+S⁻)`, `Kesinleşme = C×100` ✅ formül birebir doğru.

**KRİTİK GÖZLEM — "çok düzenli skorların" gerçek nedeni:**
- Her ders için **trend = başarı** (0.960=0.960, 0.940=0.940, …). Bütün veri kümesinde
  **36/36 TOPSIS dersinde** bu çakışma var.
- Sebep: 2022 tek yıl olduğundan `_read_course_metrics` trend'i `gecmis=[{2022: basari}]`
  tek-yıl ağırlıklı ortalaması olarak hesaplıyor → trend = o yılın başarısı.
- Popülerlik ve anket sabit (varyans 0). → **4 kriterden yalnız 1'i (başarı) ayırt edici**,
  üstelik trend olarak iki kez sayılıyor.
- Tek ayırt edici eksende TOPSIS, C'yi `min..max` arasında neredeyse doğrusal dağıtır.
  Bu yüzden 1.0 / 0.833 / 0.333 / 0.0 gibi "rank benzeri" değerler çıkıyor.

**Sonuç:** Skorlar **rank-bazlı sahte değil** (formül gerçek), ama **girdi dejenerasyonu**
nedeniyle çıktı rank gibi görünüyor. Bu, spec Bölüm 12/22'nin endişesinin kök nedenidir.

---

## 14. Nihai Karar Eşikleri (Bölüm 23)

[calculation.py:71](../app/services/calculation.py):
- `DROP_SCORE_THRESHOLD = 40.0` → kesinleşme < 40 ise düşme adayı
- `DROP_AVERAGE_GRADE_THRESHOLD = 45.0` → ortalama not < 45 ise düşme adayı

> ⚠️ **Karar kalitesi sorunu:** Yukarıdaki örnekte **Girişimcilik (basari 0.84, not 79.31)**
> kesinleşme 0.0 alıp baraj-altı düşüyor — objektif olarak iyi bir ders, sadece 4 benzer ders
> arasında göreli en düşük olduğu için. Bütün veri kümesinde **8/36 ders (%22)** bu şekilde
> sıfırlanıyor. TOPSIS göreli bir yöntemdir; mutlak eşikle (40) birleştirilince, hepsi iyi olan
> bir kümede en alttaki haksızca cezalandırılır.

---

## 15. Trend Skorunun Etkisi — TESPİT EDİLEN HATA

**İki ayrı trend implementasyonu var:**

| | `gecmis_trend_hesapla` (legacy) | `analyze_trend_values` (nötr-farkında) |
|---|---|---|
| Dosya | [calculation.py:142](../app/services/calculation.py) | [trend_analysis_service.py:55](../app/services/trend_analysis_service.py) |
| Veri yoksa | **0.0 döndürür** | **0.5 (NEUTRAL_TREND_SCORE)** |
| Tek veri noktası | = o değer (başarı) | **0.5 nötr** (`new_course`) |
| Kullanıldığı yer | **`_read_course_metrics` → kesinleşme puanı (havuz.skor)** | `decision_run_service`, lab tek-ders, trend görselleştirme |

**Sorun:** Nötr-trend düzeltmesi (madde 9 gereği, commit `ddd88a1`) `trend_analysis_service`'e
eklendi **ama asıl kesinleşme puanını üreten yola (`_read_course_metrics`) bağlanmadı.**

**Gerçek sayısal kanıt (ders 769, 2022):**
- Legacy yol (skoru üreten): `trend = 0.960` (= başarı)
- Nötr yol (lab'da gösterilen): `trend_score = 0.5`, label = `new_course`

→ **UI'da gösterilen trend (0.5) ile kaydedilen skoru üreten trend (0.96) çelişiyor.**
Madde 9'un "veri yoksa nötr, formülü haksız yükseltme/düşürme" garantisi en kritik yolda ihlal.

---

## 16. ML Algoritmalarının Rolü (Bölüm 13–17)

**Yönetim katmanı** ([algorithm_governance_service.py](../app/services/algorithm_governance_service.py)):
LR, RF, DT üçü de **`ADVISORY_ML`** olarak işaretli — "Destekleyici ML; nihai karar değildir."

**Doğrulama:** `get_faculty_year_topsis_results` → `topsis_calistir` skor yolunda **hiçbir ML
çağrısı yok**. Kesinleşme puanı yalnız AHP+TOPSIS'ten üretiliyor. ML çıktıları ayrı
servislerde (analiz/benchmark) yaşıyor.

| Algoritma | Amaç | Hedef | Nihai karara etki | Risk |
|-----------|------|-------|-------------------|------|
| **LR** | Trend/skor tahmini (destekleyici) | sürekli skor | ❌ Yok (advisory) | Küçük veri → leakage riski; doğrula |
| **RF** | Kesinleşme tahmini (destekleyici) | skor | ❌ Yok (advisory) | "Gerçek=0, tahmin 80–98" → göreli sıfırlama artefaktı (bkz. §14) |
| **DT** | Statü sınıflandırma (destekleyici) | müfredat/havuz | ❌ Yok (advisory) | Tek sınıf → %100 doğruluk anlamsız; "bilgilendirici, güvenilir değil" işaretlenmeli |

> RF'nin "gerçek skor 0 iken tahmin 80–98" gözlemi, §14'teki göreli-sıfırlama ile tutarlı:
> gerçek kesinleşme 0, dersin objektif başarısı (%84) ile çelişiyor; RF objektif özelliklere
> bakıp 80+ tahmin ediyor. Bu, RF hatası değil, **hedef değişkenin (göreli TOPSIS skoru)
> objektif kaliteyi yansıtmamasının** bir belirtisi.

---

## 17. Eski ve Yeni Puan Karşılaştırması

2022 başlangıç yılı olduğundan "önceki decision_run" yok; eski/yeni karşılaştırması ancak
2023+ üretildiğinde veya düzeltme uygulandıktan sonra anlamlı olur. Düzeltme sonrası
karşılaştırma §19'da verilecektir (kod değişikliği uygulandığında).

---

## 18. Tespit Edilen Hatalar (Özet)

| # | Hata | Önem | Dosya |
|---|------|------|-------|
| H1 | Nötr-trend düzeltmesi skor yoluna bağlı değil; legacy yol veri yoksa 0.0 veriyor | 🔴 Yüksek | `calculation.py` `_read_course_metrics` / `gecmis_trend_hesapla` |
| H2 | 2022'de trend = başarı çakışması (36/36); başarı iki kez sayılıyor | 🔴 Yüksek | `_read_course_metrics` (trend kaynağı) |
| H3 | Popülerlik/anket varyansı 0 → 3/4 kriter ayırt edici değil; skor ≈ başarı | 🟠 Orta | veri + `_read_course_metrics` |
| H4 | Göreli TOPSIS + mutlak eşik → iyi dersler 0 alıp düşüyor (8/36) | 🟠 Orta | `topsis_calistir` + eşik mantığı |
| H5 | `anket_dersi_secen > anket_katilimci` (mantıksız veri) → anket hep 1.0 | 🟠 Orta | veri kalitesi / import doğrulama |
| H6 | `strict_ahp=False` sessiz fallback; CR profil matrisine göre değil | 🟡 Düşük | `get_faculty_year_topsis_results` |

---

## 19A. UYGULANAN DÜZELTME — H1 (Trend nötr yolu)

**Değişiklik:** [calculation.py](../app/services/calculation.py) `_read_course_metrics` artık
trend skorunu `analyze_course_trend(...)["trend_score"]`'tan alıyor (legacy
`gecmis_trend_hesapla` yerine).

**Öncesi/Sonrası — Tıp Fakültesi 2022 (4 ders):**

| ders_id | Ad | basari | trend (öncesi) | trend (sonrası) | KP (öncesi) | KP (sonrası) |
|---------|-----|--------|----------------|------------------|-------------|--------------|
| 769 | Tıbbi Etik | 0.960 | **0.960** ❌ | **0.500** ✅ | 100.00 | 100.00 |
| 30 | Toplum Projesi | 0.940 | **0.940** ❌ | **0.500** ✅ | 83.33 | 83.33 |
| 768 | Klinik Anatomi | 0.880 | **0.880** ❌ | **0.500** ✅ | 33.33 | 33.33 |
| 29 | Girişimcilik | 0.840 | **0.840** ❌ | **0.500** ✅ | 0.00 | 0.00 |

**Tüm 2022 ders kümesi (36 TOPSIS dersi):**

| Metrik | Öncesi | Sonrası | Yorum |
|--------|--------|---------|-------|
| trend == başarı (çakışma) | 36/36 (%100) | **1/36 (%3)** | Çift-sayım ortadan kalktı |
| KP = 0 alan ders | 8/36 | 8/36 | H1 dışı (H4: göreli sıfırlama) |
| KP medyan | — | **56.35** | Daha sağlıklı dağılım |
| A⁺ - A⁻ trend ekseninde | 0.0133 | **0.0000** | Trend artık ayırt edici değil (nötr) |

**Yorum:** KP'lar bu örnekte aynı kaldı çünkü popülerlik/anket de sabit (H3/H5 hâlâ açık) ve
yalnız başarı ekseninde sıralama belirleniyor. Ama **trend artık başarının kopyası değil**;
ağırlığın 0.20'si gerçek bilgi taşıdığında (2023+ yıllarda) doğru biçimde devreye girecek.
2023 üretildiğinde 2022 verisi gerçek bir trend sinyali oluşturacak (önceden de aynı yıl
verisini kopyalıyordu, yani değişim).

**Regresyon testleri:** [test_trend_neutral_wiring.py](../app/tests/test_trend_neutral_wiring.py)
— 3 test, hepsi geçiyor. Daha geniş trend/topsis testi seti (62 test) regresyonsuz geçiyor.

---

## 19B. UYGULANAN DÜZELTMELER — H3, H4, H5, H6 (2026-06-15, ek tur)

Daha sonra ele alınmak üzere işaretlenen 4 iyileştirme bu turda **uygulandı, gerçek veride
ölçüldü ve regresyon testleriyle kilitlendi**.

### H5 — Mantıksız anket verisi → nötr ([calculation.py:892](../app/services/calculation.py))

**Sorun:** `anket_dersi_secen=50 > anket_katilimci=44` mantıksız (dersi seçen ankete
katılandan fazla olamaz). Eskiden `max(0, min(1, oran))` ile sessizce 1.0'a clamp ediliyordu;
tüm derslerde anket=1.0 sabit oluyordu.

**Düzeltme:** `oran > 1.0` ise anket=0.5 nötr + log uyarısı.

**Ölçüm (tüm 2022 dersleri):** 328/328 derste anket verisi mantıksızmış. Şimdi hepsi nötr 0.5
(yanıltıcı 1.0 değil). Anket kriteri artık "veri yok" semantiğini doğru taşıyor.

### H4 — Göreli sıfırlama koruması ([calculation.py:71](../app/services/calculation.py))

**Sorun:** TOPSIS göreli; kümede tüm dersler iyi ise en alttaki ders C=0 alıp baraj-altı
düşüyor. Girişimcilik (basari %84) gibi objektif iyi dersler haksızca düşme adayı oluyordu.

**Düzeltme:** Yeni sabit `MIN_RAW_SUCCESS_FLOOR = 0.70`. `should_drop_course`/
`evaluate_drop_reasons`'a `raw_basari_ratio` parametresi. Ham başarı bu eşiğin üstündeyse
yalnız düşük kesinleşme puanı nedeniyle düşme önerilmez (ortalama not bağımsız değerlendirilir).

**Ölçüm (tüm 2022 TOPSIS dersleri):**

| Metrik | Öncesi | Sonrası |
|--------|--------|---------|
| Düşme adayı ders | 13/36 (%36) | **8/36 (%22)** |
| H4 ile korunan ders | — | **5 ders** (ham başarı ≥0.70 olduğu için) |

Girişimcilik, Klinik Anatomi gibi başarısı %80+ olan ama göreli sıfırlanan dersler artık
adil değerlendiriliyor.

### H3 — Dejenere kriter tespiti ([calculation.py:285](../app/services/calculation.py))

**Sorun:** Popülerlik ve anket varyansı 0 (sabit değerler) → 4 kriterden 3'ü TOPSIS
mesafesine sıfır katkı veriyor; kullanıcı "rank gibi" görünen skorların gerçek nedenini
bilmiyor.

**Düzeltme:** `topsis_calistir` meta çıktısına `degenerate_criteria` listesi (A⁺=A⁻ olan
kriterler). Faz C toplu görünüm banner'ında uyarı:
> ⚠ Dejenere kriterler (varyans=0, sıralamaya katkısız): anket, populerlik, trend —
> yeni kesinleşme puanları pratikte yalnız diğer kriterlerden geliyor.

**Ölçüm (2022, tüm fakülteler):** dejenere kriterler = `{anket, populerlik, trend}`.
Kullanıcı artık skorların yalnız başarı ekseninden geldiğini banner'da görüyor.

### H6 — Strict AHP dual wrapper varsayılanı ([calculation.py:2816](../app/services/calculation.py))

**Sorun:** `get_faculty_year_topsis_results(strict_ahp=False)` varsayılan; aktif profil
çözülemezse sessizce legacy Saaty'e düşülüyordu. Karar üretimi kullanıcının seçmediği
ağırlıklarla yapılabiliyordu.

**Düzeltme:** Zinciri akıt: `run_all_algorithms_for_year_dual(strict_ahp=True)` (yeni
varsayılan) → `run_all_algorithms_for_year(strict_ahp)` → `generate_next_year_curricula(strict_ahp)`
→ `get_faculty_year_topsis_results(strict_ahp)`. Tutarsız profil veya çözüm hatası artık
açık `RuntimeError` fırlatır.

**Geriye uyumluluk:** `strict_ahp=False` opt-out parametresi tüm seviyelerde açık; eski
testler ve doğrudan tek-dönem çağrıları aynen çalışıyor.

**Regresyon testleri:** [test_h3_h6_improvements.py](../app/tests/test_h3_h6_improvements.py)
— 13 test, hepsi geçiyor.

---

## 19. (Eski bölüm başlığı korundu — alttaki bölümler kapatıldı)

1. **H1/H2 — Trend birleştirme:** `_read_course_metrics` içindeki `gecmis_trend_hesapla`
   çağrısını `analyze_course_trend(...)["trend_score"]` ile değiştir → tek, nötr-farkında
   trend. Veri yoksa 0.5; tek yıl varsa 0.5 (başarıya çökmez). Bu, başarı/trend çift-sayımını
   da kaldırır.
2. **H3/H5 — Veri kalitesi:** Anket alanı için `secen ≤ katilimci` doğrulaması (import
   katmanı); popülerlik için gerçek doluluk verisi yoksa kriteri TOPSIS'ten düşür veya nötrle.
3. **H4 — Karar eşiği:** Mutlak eşiği (40) göreli TOPSIS skoruna değil, ham kriter kombinasyonuna
   (örn. ağırlıklı ham skor) bağlamayı değerlendir; veya "tüm dersler iyi" durumunda
   sıfırlamayı engelleyen bir taban uygula.
4. **H6 — AHP strict:** Karar Merkezi çağrılarında `strict_ahp=True`.

> Bu düzeltmeler **kalıcı skorları değiştirir**; bu yüzden Faz B (doğrulama) kapsamı dışında
> tutuldu. Onayınızla "düzelt" alt-fazında uygulanıp §19/§20 öncesi-sonrası sayılarla
> raporlanacak (Bölüm 21 akışı).

---

## 20. 3 Ders Üzerinden Sayısal Hesaplama Örneği (Bölüm 20)

**Bağlam:** Tıp Fakültesi, 2022, Güz, AHP profil 11, ağırlıklar w=[0.411, 0.201, 0.194, 0.194].

### Ders A — Tıbbi Etik Seçmeli (id 769)
- Ham: başarı 48/50=**0.960**, trend **0.960** (=başarı, tek yıl), popülerlik 50/60=**0.833**, anket→clamp **1.000**
- Ağırlıklı normalize v = (0.2177, 0.1062, 0.0971, 0.0971) → tüm kriterlerde A⁺'ya en yakın
- S⁺=**0.0000**, S⁻=**0.0303** → C = 0.0303/(0+0.0303) = **1.0000** → **Kesinleşme 100.00**
- **Karar:** Müfredatta güçlü şekilde kalır (≥80).
- *Açıklama:* En yüksek başarıya sahip; trend başarıyla aynı, popülerlik/anket diğerleriyle eşit
  olduğundan ayrım tamamen başarıdan geliyor.

### Ders B — Klinik Anatomi Seçmeli (id 768)
- Ham: başarı 44/50=**0.880**, trend **0.880**, popülerlik **0.833**, anket **1.000**
- S⁺=**0.0202**, S⁻=**0.0101** → C = 0.0101/(0.0202+0.0101) = **0.3333** → **Kesinleşme 33.33**
- **Karar:** Baraj-altı (<40) → düşme adayı.
- *Açıklama:* Başarısı %88 olmasına rağmen, 4 dersin göreli sıralamasında alt-orta konumda;
  TOPSIS göreli mesafe 0.33 verdi. Objektif kaliteye göre bu karar **tartışmalı** (bkz. H4).

### Ders C — Girişimcilik (id 29)
- Ham: başarı 42/50=**0.840**, trend **0.840**, popülerlik **0.833**, anket **1.000**
- S⁺=**0.0303**, S⁻=**0.0000** → C = 0/(0.0303+0) = **0.0000** → **Kesinleşme 0.00**
- **Karar:** Baraj-altı → düşme adayı.
- *Açıklama:* Kümedeki göreli en düşük başarı → negatif ideale çakışık → C=0. **%84 başarılı
  bir ders mutlak olarak iyi**; sıfır puan yalnız göreli konumdan kaynaklanıyor (H4 örneği).

---

## 20A. UYGULANAN DEĞİŞİKLİK — Faz A (Güz+Bahar Birlikte Üretim, Spec madde 3)

**Sorun:** UI'daki "Sonraki Yıl Müfredat Üret" butonu `run_all_algorithms_for_year(donem="G")`
çağırıyordu — yalnız güz üretiliyordu, bahar tarafı boş kalıyordu.

**Çözüm:** Yeni wrapper `run_all_algorithms_for_year_dual(yil, db_path, fakulte_id)`
([calculation.py:2816](../app/services/calculation.py)) hem G hem B'yi ardışık çalıştırır.
Wrapper, mevcut tek-dönem fonksiyonu iki kez çağırır (additive, kırıcı değil).

**Çıktı alanları (spec madde 3 uyumlu):**
- `akademik_yil`, `guz_olusturuldu`, `bahar_olusturuldu`
- `guz_islenen_fakulte`, `bahar_islenen_fakulte`
- `guz_atlanan`, `bahar_atlanan` (her biri reason ile)
- `guz_hata`, `bahar_hata`
- `kullanilan_ahp_profile` (id, name, version, is_consistent, weights)
- `baslangic_zaman`, `bitis_zaman` (ISO UTC)
- `guz_detay`, `bahar_detay` (alt çağrı tam sonuçları)
- `messages` (insana okunabilir özetler)

**UI bağlantısı:** [calc_tab.py:903](../app/ui/tabs/calc_tab.py) → dual wrapper'a yönlendirildi.
Rapor metnine "BAHAR DETAYI" bölümü ve "Yıllık bütünlük durumu" satırı eklendi. Bahar
üretilemezse kullanıcıya açık gerekçe gösteriliyor (spec gereği).

**Gerçek veriyle doğrulama (Tıp Fak. 2022 → 2023):**

```
ok: True
akademik_yil: 2022
guz_olusturuldu: True       bahar_olusturuldu: True
guz_islenen: 1              bahar_islenen: 1
ahp: {id: 11, name: Ss, v: 1, tutarli: True}
zaman: 12:58:38 -> 12:58:38
```

**Regresyon testleri:** [test_dual_semester_run.py](../app/tests/test_dual_semester_run.py)
— 5 test, hepsi geçiyor (wrapper G+B çağırıyor mu, spec alanları doldu mu, bahar eksik
durumunda nazikçe yönetiliyor mu, AHP/zaman izlenebilir mi).

---

## 21. Son Değerlendirme

- **AHP ve TOPSIS matematiği doğru ve gerçek.** Aktif profil gerçekten kullanılıyor; skorlar
  rank-bazlı sahte değil.
- **Asıl problem matematik değil, veri ve bağlama:** başlangıç yılında trend=başarı çakışması,
  popülerlik/anket varyans yokluğu ve göreli-mutlak eşik çelişkisi, kesinleşme puanını
  "başarının rank'i" hâline indiriyor ve iyi dersleri haksız sıfırlıyor.
- **Trend nötr düzeltmesi mevcut ama yanlış yola bağlı** → en yüksek öncelikli düzeltme (H1).
- **ML doğru konumda** (advisory), nihai kararı bozmuyor.

**Sonraki adım:** Onayınızla H1–H6 düzeltmelerini "düzelt" alt-fazında uygular, her biri için
öncesi/sonrası gerçek sayıları bu raporun §19/§20'sine ekler ve regresyon testleriyle kilitlerim.
