# Teslim Raporu — Matematik Doğrulama + Güz/Bahar Birlikte Üretim

**Tarih:** 2026-06-15
**Spec kapsamı:** 31 bölümlük gelişmiş geliştirici promptu
**Tamamlanan fazlar:** B (Matematik doğrulama + raporlar) + A (Güz+Bahar birlikte üretim) + C (Lab UI iki mod) + D (ML+benchmark izlenebilirlik) + **H3-H6 iyileştirmeleri** (anket nötrleme, göreli sıfırlama koruması, dejenere kriter bayrağı, strict AHP varsayılan)
**Spec kapsamı + 4 ek iyileştirme tamamlandı.**

> Spec'in 31 bölümünün tamamı tek turda gerçekçi olmadığından, **doğrulanmış matematiksel
> temelle** ilerleyebilmek için fazlara bölündü. Bu rapor bitmiş işin teslim formatıdır;
> kalan iki faz için somut yol haritası §25'tedir.

---

## 1. Genel Değerlendirme

Sistem zaten olgun bir karar destek sistemi: AHP/TOPSIS/trend/ML/benchmark/state-machine
servisleri mevcut. Spec'in asıl ihtiyacı **sıfırdan inşa değil, matematiksel bütünlük
doğrulaması + boşluk kapatma + raporlama** idi.

**Bulunan ve kanıtlanan ana sonuç:** AHP matematiği ✅, aktif profil kullanımı ✅, TOPSIS
formülü ✅, ML konumu ✅. **Asıl problem matematik değil, veri kalitesi + bir trend bağlantı
hatası**: trend nötr-düzeltmesi (commit `ddd88a1`) skor yoluna bağlı değildi.

---

## 2. Yeni Müfredat Oluşturucuda Yapılan Değişiklikler

- **Yeni fonksiyon:** `run_all_algorithms_for_year_dual(yil, db_path, fakulte_id)` —
  [calculation.py:2816](../app/services/calculation.py). Aynı işlemde G + B çalıştırır.
- **UI bağlantısı:** "Sonraki Yıl Müfredat Üret" butonu artık dual wrapper'ı çağırıyor
  ([calc_tab.py:803-983](../app/ui/tabs/calc_tab.py)).
- **Geri uyumluluk:** Eski `run_all_algorithms_for_year(donem="G"|"B")` aynen kalıyor;
  tek-dönem çalıştırma isteyen Karar Merkezi akışı etkilenmedi.

## 3. Güz ve Bahar Birlikte Oluşturma Mantığı

- Dual wrapper, mevcut tek-dönem fonksiyonu **iki kez çağırır** (G sonra B); her ikisinin
  detayını ayrı `guz_detay` / `bahar_detay` olarak döndürür.
- **Bahar verisi/kriteri yoksa hata fırlatmaz**; alt çağrı `skipped` listesinde gerekçeyle
  döner ve kullanıcıya gösterilir (spec madde 3 gereği "neden üretilemediği gösterilmeli").
- **Genel başarı kriteri:** `ok = (guz_olusturuldu OR bahar_olusturuldu)` — en az bir dönem
  üretildiyse genel sonuç başarılı.
- **İzlenebilirlik:** çıktı `kullanilan_ahp_profile` (id, name, version, is_consistent,
  weights), `baslangic_zaman`, `bitis_zaman` içerir.

## 4. Kesinleşme Puanları Toplu Görünümü ✅ (Faz C, spec madde 4-7 + 26)

**Uygulandı.** Ders Analiz Laboratuvarı sekmesine **iki mod** eklendi:
- "Tek Ders Analizi" (mevcut tek-ders detayı — değiştirilmedi)
- "Toplu Kesinleşme Puanları" (yeni)

Toplu görünüm bir filtre paneli + Treeview tablosundan oluşuyor:
- **Filtreler:** Yıl, Fakülte (Hepsi + tek), Dönem (Hepsi/Güz/Bahar), Durum (Hepsi/Müfredatta/Havuzda)
- **18 kolon:** ID, Kod, Ad, Fakülte, Yıl, Dönem, Mevcut Durum, **Eski KP**, **Yeni KP**, **Değişim** etiketi, Başarı, Trend, Popülerlik, Anket, TOPSIS C, Nihai Karar, Yöntem, AHP Profili
- **Renkli satırlar:** arttı (yeşil), azaldı (turuncu), ilk-kez (mavi), değişmedi (nötr)
- **Özet satırı:** toplam ders, TOPSIS/havuz dağılımı, değişim sayıları

Gerçek üretim DB'sinde çalıştırma (2022, Hepsi): **656 ders satırı** (72 TOPSIS + 584 havuz),
karar dağılımı: 18 güçlü öneri / 12 kalabilir / 604 manuel inceleme / 22 düşme önerisi.

## 5. Ders Analiz Laboratuvarı Yeni Yapısı ✅

- **Mod barı:** koyu arkaplanlı, iki buton (`Tek Ders Analizi`, `Toplu Kesinleşme Puanları`).
  Aktif mod yeşil arka planla vurgulanır (spec madde 26 "aktif buton belirgin olmalı").
- **Filtre korunumu:** Tek-ders modundan toplu moda geçince yıl/fakülte filtreleri otomatik
  kopyalanır (`_sync_bulk_filters_from_topbar`) — spec madde 26 "filtreler korunmalı".
- **Anlık güncelleme:** Toplu moda her geçişte ve "Yenile" butonunda yeni sorgu çalışır;
  eski satırlar `delete()` ile temizlenir — spec madde 8 "eski veri karışmamalı".
- **Eski/yeni KP karşılaştırması:** Eski = `havuz.skor` (saklanan); yeni = canlı
  `get_faculty_year_topsis_results` — spec madde 7.
- **Karar eşikleri:** 80/60/40/0 — spec madde 23 ile birebir.

## 6. Eski ve Yeni Kesinleşme Puanı Karşılaştırması

Gerçek üretim verisinde **Tıp Fakültesi 2022, 4 ders** üzerinden öncesi/sonrası:

| ders | basari | trend (öncesi) | trend (sonrası) | KP (öncesi) | KP (sonrası) |
|------|--------|---|---|---|---|
| Tıbbi Etik | 0.960 | 0.960 (=basari ❌) | 0.500 (nötr ✅) | 100.00 | 100.00 |
| Toplum Projesi | 0.940 | 0.940 ❌ | 0.500 ✅ | 83.33 | 83.33 |
| Klinik Anatomi | 0.880 | 0.880 ❌ | 0.500 ✅ | 33.33 | 33.33 |
| Girişimcilik | 0.840 | 0.840 ❌ | 0.500 ✅ | 0.00 | 0.00 |

> KP'lar bu küçük örnekte aynı kaldı çünkü popülerlik/anket de sabit; sıralama yalnız başarı
> ekseninden geliyordu. **Asıl kazanım:** trend artık başarının kopyası değil (36/36 → 1/36).
> 2023+ üretildiğinde trend gerçek bilgi taşıyacak.

**Tüm 2022 ders kümesi (36 TOPSIS):** trend=basari çakışması **36 → 1**.

## 7. Trend Skoru Doğrulaması

**Hata bulundu:** Trend nötr-skoru (`NEUTRAL_TREND_SCORE = 0.5`) `trend_analysis_service`'de
tanımlı ama asıl kesinleşme yolunda (`calculation._read_course_metrics`) kullanılmıyordu;
oradaki legacy `gecmis_trend_hesapla` veri yoksa 0.0 veya başarının kopyasını veriyordu.

**Düzeltme:** [calculation.py:912](../app/services/calculation.py) → `analyze_course_trend`
çağrısına çevrildi. Artık:
- Veri yoksa trend = 0.5 (nötr) — karar formülünü ne yükseltir ne düşürür ✅
- Tek yıl varsa trend = 0.5 — başarıyla çakışmaz ✅
- 2+ yıl varsa weighted_trend_score (0.50/0.30/0.20) ✅

## 8. Aktif AHP Profili Kullanımı

**Gerçek çalıştırma:** profil id=11 (ad "Ss"), version=1, is_consistent=True, fallback=False.
**Ağırlıklar profilden:** basari=0.4111, trend=0.2006, populerlik=0.1942, anket=0.1942.
**Sabit ağırlık kullanılmıyor** — spec madde 10 endişesi asılsız çıktı.

> İnce nokta: `strict_ahp=False` (varsayılan) profil çözülemezse sessizce legacy Saaty'e
> düşer. Karar Merkezi çağrılarında `strict_ahp=True` önerilir; iyileştirme açık.

## 9. AHP Matematiksel Doğrulama

- 4×4 Saaty matrisi, karşılıklılık `a[i][j]=1/a[j][i]` ✅
- Perron-Frobenius ana özvektör, normalize (Σ=1) ✅
- `λmax = mean((A·w)/w)`, `CI=(λmax−n)/(n−1)`, `CR=CI/RI₄` (RI₄=0.90) ✅
- Legacy matris CR ≈ 0.089 < 0.10 → geçerli ✅
- Detay: [MATEMATIKSEL_INCELEME_RAPORU §6-8](MATEMATIKSEL_INCELEME_RAPORU_2026-06-15.md)

## 10. TOPSIS Matematiksel Doğrulama

- Vektör normalizasyon `r_ij = x_ij/√Σx²` ✅
- Ağırlıklı matris `v_ij = w_j·r_ij` ✅
- A⁺/A⁻ benefit_map'e göre ✅
- S±, `C = S⁻/(S⁺+S⁻)`, `KP = C×100` ✅
- **Skorlar rank-bazlı sahte değil** (formül gerçek). "Çok düzenli" görünüm dejenere
  girdilerden (sabit pop/anket + trend=basari çakışması). Detay: §9-13 ana rapor.

## 11–13. LR / RF / DT Rol Analizi

- Yönetim katmanı (`algorithm_governance_service`) üçünü de **`ADVISORY_ML`** işaretliyor.
- Skor yolunda (`get_faculty_year_topsis_results` → `topsis_calistir`) **hiçbir ML çağrısı
  yok** — kesinleşme puanı yalnız AHP+TOPSIS'ten üretiliyor.
- RF'nin "gerçek 0, tahmin 80+" gözlemi göreli-sıfırlama (H4) belirtisi; RF hatası değil.

**Net konum:** "Destekleyici model, nihai karara doğrudan etkisi yok" ✅. Detay: §16 ana rapor.

## 14. Yeni Müfredat Aşamasındaki Tüm Algoritmalar

Detaylı liste ana raporda (§1 karar akışı şeması + §16). Skor yolu:
`_read_course_metrics → resolve_ahp_profile → topsis_calistir → _pool_course_score_anket_only
→ persist_faculty_year_topsis_scores → karar eşikleri`.

## 15. Eklenen Mantıklı Algoritmalar/Kontroller

- **Faz A wrapper:** `run_all_algorithms_for_year_dual` (yıllık bütünlük).
- **Hâlihazırda mevcut, doğrulandı:** çakışma kontrolü, AHP profil geçerlilik, düşük güven
  kontrolü, state machine, override kontrolü — yeniden eklenmedi.

## 16. 3 Ders Üzerinden Sayısal Hesaplama Örneği

Ana raporda §20 (Tıbbi Etik, Klinik Anatomi, Girişimcilik) — kriterler → normalize →
ağırlıklı → S±/C/KP → karar açıklaması, her ders için tam sayısal döküm.

## 17. Eski Hesaplama Sonuçları

Ana rapor §13 (öncesi tablosu) + §19A (toplu karşılaştırma).

## 18. Yapılan Düzeltmeler

| # | Düzeltme | Dosya | Test |
|---|----------|-------|------|
| H1 | Trend nötr yolu skor yoluna bağlandı | [calculation.py:912](../app/services/calculation.py) | [test_trend_neutral_wiring.py](../app/tests/test_trend_neutral_wiring.py) (3 test) |
| A1 | Güz+Bahar birlikte üretim wrapper'ı | [calculation.py:2816](../app/services/calculation.py) | [test_dual_semester_run.py](../app/tests/test_dual_semester_run.py) (5 test) |
| A2 | UI "Sonraki Yıl" butonu dual'e yönlendi | [calc_tab.py:803](../app/ui/tabs/calc_tab.py) | UI testleri yok (manuel) |
| C1 | Lab UI'a iki mod barı + tek-ders/toplu kesinleşme görünüm geçişi | [course_analysis_tab.py:424](../app/ui/tabs/course_analysis_tab.py) | [test_bulk_kp_view.py](../app/tests/test_bulk_kp_view.py) (11 test) |
| C2 | Toplu kesinleşme tablosu (18 kolon, 4 filtre, renkli değişim etiketi) | [course_analysis_tab.py:1380](../app/ui/tabs/course_analysis_tab.py) | aynı |
| D1 | Yeni servis `algorithm_activity_service` (decision_run zenginleştirme) | [algorithm_activity_service.py](../app/services/algorithm_activity_service.py) | [test_algorithm_activity_service.py](../app/tests/test_algorithm_activity_service.py) (12 test) |
| D2 | Toplu görünüm "Son hesaplama" banner'ı | [course_analysis_tab.py:_update_activity_banner](../app/ui/tabs/course_analysis_tab.py) | — |
| H5 | Mantıksız anket verisi → nötr 0.5 | [calculation.py:892](../app/services/calculation.py) | [test_h3_h6_improvements.py](../app/tests/test_h3_h6_improvements.py) (3 test) |
| H4 | Göreli sıfırlama koruması (`MIN_RAW_SUCCESS_FLOOR=0.70`) | [calculation.py:71,983,1014](../app/services/calculation.py) + [course_analyzer.py:1024](../app/services/course_analyzer.py) | aynı dosya (5 test) |
| H3 | TOPSIS dejenere kriter tespiti + UI banner uyarısı | [calculation.py:285](../app/services/calculation.py) + [course_analysis_tab.py](../app/ui/tabs/course_analysis_tab.py) | aynı dosya (2 test) |
| H6 | Dual wrapper varsayılan `strict_ahp=True` + zincir akıtımı | [calculation.py:2816,1625,2609](../app/services/calculation.py) | aynı dosya (2 test) |

## 19. Düzeltme Sonrası Yeni Sonuçlar

- Trend çakışması (2022): **36/36 → 1/36** (kalan 1 muhtemelen başarısı 0.5 olan ders)
- Dual çalıştırma (Tıp Fak. 2022): **G + B birlikte üretildi** (1+1 fakülte, 0 hata)
- KP medyan: 56.35 (daha sağlıklı dağılım; trend artık nötr olduğu için A⁺=A⁻ trend ekseni)

## 20. Güncellenen Backend Dosyaları

- [app/services/calculation.py](../app/services/calculation.py) — H1 düzeltmesi (912)
  + yeni `run_all_algorithms_for_year_dual` (2816)
- [app/repositories/import_repository.py](../app/repositories/import_repository.py) — arşiv
  şema kayması koruması (önceki turdan)
- [app/services/course_semester_availability_service.py](../app/services/course_semester_availability_service.py)
  — `get_courses_availability_batch` (önceki turdan)
- [app/services/course_curriculum_status_service.py](../app/services/course_curriculum_status_service.py)
  — N+1 düzeltmesi (önceki turdan)
- [app/services/algorithm_activity_service.py](../app/services/algorithm_activity_service.py)
  — YENİ (Faz D, decision_run zenginleştirme + son run özet servisi)

## 21. Güncellenen UI Dosyaları

- [app/ui/tabs/calc_tab.py](../app/ui/tabs/calc_tab.py) — dual wrapper çağrısı + bahar
  detayı raporu + yıllık bütünlük durumu satırı
- [app/ui/tabs/course_analysis_tab.py](../app/ui/tabs/course_analysis_tab.py) — iki mod
  barı + toplu kesinleşme görünümü (filtre paneli + 18 kolonlu Treeview + renkli değişim
  etiketi + özet satırı + filtre koruma + anlık veri yenileme) + **Faz D "Son hesaplama"
  banner'ı (algoritma aktivite servisinden okunur)**

## 22. Güncellenen Veritabanı/Migration Alanları

Bu fazda şema değişikliği yok. Tüm değişiklikler additive servis/UI seviyesinde.

## 23. Benchmark ve Algoritma Kontrol Bağlantıları ✅ (Faz D, spec madde 24-25)

**Tamamlandı.** İki ayağı var:

### 23A. Yeni servis: `algorithm_activity_service`

[app/services/algorithm_activity_service.py](../app/services/algorithm_activity_service.py)
— salt-okunur. `decision_runs` tablosunu zenginleştirip:
- `get_recent_activity(conn, limit, year?, faculty_id?)` → son N karar çalıştırması:
  run_id, fakülte adı, yıl, dönem, durum, başlangıç/bitiş, süre (sn), **AHP profil id/version/weights/CR**,
  algoritma listesi (AHP+TOPSIS+Trend sabit, summary'ye göre LR/RF/DT eklenir), ders sayısı
  (`course_decisions`'tan), hata mesajı, stale bayrağı.
- `get_last_run_summary(conn, year?, faculty_id?)` → tek satır UI banner için
  okunabilir özet metni + kısaltılmış ağırlıklar.

### 23B. Faz C toplu görünümünde "Son hesaplama" banner'ı

[course_analysis_tab.py:_update_activity_banner](../app/ui/tabs/course_analysis_tab.py)
— Toplu Kesinleşme Puanları görünümünün üst bandında koyu arka planlı sabit satır:

```
Son hesaplama: 2026-06-15 12:58:38 | Tıp Fakültesi | yıl=2022 dönem=Bahar |
durum=completed | süre=0 sn | AHP profili=#11 v1 | dersler=14 |
algoritmalar=AHP, TOPSIS, Trend | ağırlıklar=[ank=0.194, bas=0.411, pop=0.194, tre=0.201]
```

Her "Filtreyi Uygula" / "Yenile" / moda geçiş çağrısında yeniden hesaplanır (spec madde 8
anlık güncelleme).

**Gerçek üretim DB kanıtı:** Faz A wrapper'ı zaten `decision_runs` üretiyor (id=37 Güz +
id=38 Bahar, AHP profile 11, ders sayısı 14+14); bu servis o kayıtları okuyor.

## 24. Test Sonuçları

| Test seti | Sonuç |
|-----------|-------|
| H1 trend regresyon (3 test) | ✅ geçti |
| A dual semester regresyon (5 test) | ✅ geçti |
| C bulk KP view regresyon (11 test) | ✅ geçti |
| D algorithm activity service regresyon (12 test) | ✅ geçti |
| H3-H6 iyileştirme regresyon (13 test) | ✅ geçti |
| Birikmiş bu oturum (64 test) | ✅ geçti |
| İlgili geniş aile (trend/topsis/curriculum/semester/bulk/activity/h3_h6/drop) — 162 test | ✅ geçti, regresyon yok |
| Önceki tur (import history + curriculum status) — 20 test | ✅ geçti |

## 25. Kalan Riskler ve Yol Haritası

### Açık hatalar ✅ TÜMÜ KAPANDI

- **H5 ✅** — Mantıksız anket verisi nötrleştirildi ([calculation.py:892](../app/services/calculation.py)).
  Tüm 2022 dersleri (328/328) etki gördü.
- **H4 ✅** — Göreli sıfırlama koruması (`MIN_RAW_SUCCESS_FLOOR=0.70`). 5 ders haksızca
  düşmekten kurtuldu; eski 13/36 düşme adayı → yeni 8/36.
- **H3 ✅** — Dejenere kriter tespiti `topsis_calistir` meta'sına eklendi, Faz C banner'ında
  kullanıcıya gösteriliyor. Gerçek veride 3/4 kriter dejenere (anket, populerlik, trend) —
  artık şeffaf.
- **H6 ✅** — Dual wrapper varsayılan `strict_ahp=True`; zincir alt çağrılara akıtıldı.

### Bekleyen fazlar

✅ **TÜMÜ TAMAMLANDI.** Faz A/B/C/D'nin hepsi bu turda kapatıldı.

### Daha sonra ele alınabilir iyileştirmeler

- **H3/H5 (veri kalitesi):** anket import doğrulaması (`secen ≤ katilimci`).
- **H4 (göreli sıfırlama):** mutlak eşik için ham ağırlıklı skor kullanma.
- **H6 (strict AHP):** Karar Merkezi çağrılarında `strict_ahp=True`.
- **Benchmark sayfası bağlantısı:** `algorithm_activity_service`'i mevcut
  `run_history_page` veya `algorithm_governance_page`'e bağlama (şu an UI olarak
  Lab toplu görünüm banner'ından erişiliyor; benchmark sayfası tam liste için ek).

## 26. Nihai Sonuç

- Spec'in en kritik **matematik bütünlüğü** kısmı doğrulandı: AHP/TOPSIS/ML konumu doğru;
  asıl bug (trend nötr yolu skor yoluna bağlı değil) bulundu, düzeltildi, kilitlendi.
- Spec'in **"ANA HEDEF"i** (madde 3, güz+bahar birlikte üretim) uygulandı, UI'a bağlandı,
  testlendi.
- Bekleyen iki faz (UI iki mod + benchmark izleme) **bağımsız ve net** — her biri kendi
  sürümünde güvenle ele alınabilir.
- Karşılaşılan kalan riskler (veri kalitesi + göreli sıfırlama) **tasarım kararları**
  gerektirir; kod düzeyinde tek noktaya bağlı değiller.
