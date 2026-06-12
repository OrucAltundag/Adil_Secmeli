# Veri Kalitesi & Olgunluk — Düzeltme Raporu

> Bu rapor, "Biterme Son umut.docx" belgesindeki taleplere göre yapılan kod
> değişikliklerini ve sorulan soruların cevaplarını içerir.

---

## 1. "Raporla Oluştur" Neden Çalışmıyor Görünüyordu?

Buton aslında **çöküp hata vermiyordu** — backend fonksiyonları (`assess_data_readiness_cursor`,
`generate_coverage_report_cursor`) sorunsuz dönüyordu. Sorun, ürettiği sonucun
**yanıltıcı derecede düşük** olmasıydı: hep "VERİ EKSİK" diyordu. Bu yüzden
"çalışmıyor" gibi algılanıyordu.

**Kök neden:** Kapsama/olgunluk hesabında **payda yanlıştı.**

```
Eski payda = fakültedeki TÜM dersler   (örn. Tıp: 39, Mühendislik: 296, İlahiyat: 70)
Kriterli ders sayısı = yalnız MÜFREDATTAKİ dersler (Tıp: 8, Müh: 24, İlahiyat: 8)

criteria_score = 8 / 39 = %20.5   ← belgede gördüğün "%20.5" tam olarak buydu
```

Senin tespitin birebir doğru: **müfredatta olmayan (havuzdaki) bir dersin
performans/popülerlik verisi olması beklenemez.** Eski formül bu dersleri de
paydaya koyup "eksik" sayıyor ve skoru haksızca düşürüyordu.

---

## 2. "Veri Eksik" Diyordu — Nasıl Tamamlanır?

Yeni mantıkta **yalnızca müfredattaki dersler** için şunlar zorunludur:

| Zorunlu (müfredat dersi) | Nereden girilir |
|---|---|
| Kriter (toplam/geçen öğrenci, ortalama, kontenjan, kayıtlı) | Kriter & Havuz → **Kriter Girdi İşlemleri** (elle) ya da **Otomatik Kriter** (not veri seti) |
| Performans (başarı oranı, ortalama not) | Kriter kaydıyla birlikte otomatik yazılır |
| Popülerlik (talep, doluluk) | Kriter kaydıyla birlikte otomatik yazılır |

**Zorunlu DEĞİL (hiçbir ders için):**

| Bilgi amaçlı | Neden zorunlu değil |
|---|---|
| Anket / tercih | Bir ders hiç seçilmemiş olabilir. Eksikliği olgunluğu düşürmez; girilirse karar kalitesini artırır. |

**Olgunluğu yükseltmek için:** Müfredattaki derslerin kriterlerini tamamla.
2022 verisinde 5 fakültenin müfredat dersleri zaten tam → her biri **%100
(decision_ready)**.

---

## 3. Eski vs Yeni Formül

### 3.1. ESKİ Formül (v1) — kaldırıldı

```
payda = fakültedeki tüm ders sayısı (N_all)

criteria_score    = kriterli_ders / N_all × 100
performance_score = perf_ders     / N_all × 100
popularity_score  = pop_ders      / N_all × 100
survey_score      = anketli_ders  / N_all × 100      ← anket de paydaya giriyordu

readiness = 0.40·criteria + 0.15·performance + 0.15·popularity
          + 0.15·survey   + 0.15·validation
```

Sorun: `N_all` çok büyük (havuz dahil) → tüm skorlar düşük; anket zorunlu
sayılıyor.

### 3.2. YENİ Formül (v2) — uygulandı

```
payda = MÜFREDATTAKİ ders sayısı (N_mufredat)   ← zorunlu küme

criteria_score    = kriterli_mufredat_ders / N_mufredat × 100
performance_score = perf_mufredat_ders     / N_mufredat × 100
popularity_score  = pop_mufredat_ders      / N_mufredat × 100

readiness = 0.50·criteria + 0.20·performance + 0.20·popularity + 0.10·validation
            (ANKET formüle GİRMEZ — yalnızca bilgi amaçlı raporlanır)
```

- Müfredat dışı dersler paydada **yok** → eksik perf/pop skoru düşürmez.
- Anket **gate'e girmez**; `survey_required = False`.
- Müfredat tanımlı değilse (kenar durum) eski tüm-ders paydasına güvenli
  şekilde geri düşer (`curriculum_defined = False`).
- `validation_score = 100 − 25 × kritik_doğrulama_sorunu`.

**Kapsama yüzdesi (v2):** `0.50·kriter + 0.25·performans + 0.25·popülerlik`
(müfredat paydası, anket hariç).

**Etki (2022 gerçek veri):**

| Fakülte | Eski olgunluk | Yeni olgunluk |
|---|---:|---:|
| Tıp | 33.2 (low) | **100.0 (decision_ready)** |
| Mühendislik | 27.6 (not_ready) | **100.0 (decision_ready)** |
| İlahiyat | ~33 (low) | **100.0 (decision_ready)** |

Kod: `app/services/data_quality_integration_service.py`
(`assess_data_readiness_cursor`, `generate_coverage_report_cursor`,
`_curriculum_course_ids`, `_count_courses_in_set`).
Test: `app/tests/test_data_quality_maturity.py` (4 test, hepsi yeşil).

---

## 4. Bu Hesapta Algoritma Kullanılıyor mu?

**Hayır.** Olgunluk/kapsama saf **oransal (deterministik) bir formüldür** —
ağırlıklı kapsama yüzdesi. Makine öğrenmesi veya optimizasyon yoktur; olması da
gerekmez (denetlenebilirlik ve açıklanabilirlik için kasıtlı tercih).

### Algoritma kullanılsaydı? (fayda/zarar tablosu)

| Algoritma | Nasıl kullanılırdı | Faydası | Zararı / Riski |
|---|---|---|---|
| **Ağırlıklı oran (mevcut)** | Kapsam yüzdesi = ağırlıklı doluluk | Şeffaf, açıklanabilir, hızlı, denetlenebilir | Veri "kalitesini" değil yalnızca "varlığını" ölçer |
| **Eksik veri imputation (KNN / MICE)** | Eksik kriterleri komşu derslerden tahminle | Eksik dersler için karar üretilebilir | Uydurma veri; akademik kurulda savunulamaz, yanlı sonuç riski |
| **Anomali tespiti (Isolation Forest)** | Tutarsız/aykırı kriter satırlarını işaretle | Hatalı veri girişini yakalar | Eğitim verisi ister; az veride güvenilmez |
| **Lojistik regresyon (kalite sınıflandırma)** | "Karar verilebilir mi?" olasılığı | Olasılıksal eşik | Etiketli geçmiş ister; kara kutu algısı |
| **Bulanık mantık (fuzzy)** | "kısmen yeterli" gibi yumuşak eşikler | İnsana yakın yorum | Kural tasarımı öznel; doğrulaması zor |

**Sonuç:** Veri **olgunluğu** için deterministik oran doğru tercih —
açıklanabilir ve manipülasyona kapalı. Algoritmalar asıl **karar** hattında
(AHP + TOPSIS + trend + veri güveni) kullanılıyor; orada yerinde.

---

## 5. Anket Veri Seti (Yeni)

`scripts/generate_anket_veri_seti.py` → `data/2022_anket_tercih_veri_seti.xlsx`

- 2022 dersleri, her **fakülte için 100 katılımcı** varsayımı.
- Her fakülte için **10–20 ders** rastgele anket kapsamında (hepsi değil).
- Tercih sayıları rastgele (3–100).
- Format **sistemin kendi import formatına uygun** (`AnketSonuclari` +
  `Meta` sayfaları; `ders_kodu` + `tercih_sayisi`). `survey_import_service`
  ile birebir okunabildiği doğrulandı (71 satır, 5 fakülte).

Yeniden üretmek için:
```bash
python -m scripts.generate_anket_veri_seti
```

---

## 6. Kriter Girdi Sayfasına "Anket Belge Girişi"

`app/ui/tabs/criteria_page.py` → yeni buton **"📋 Anket Belge Girişi"**.

- Excel anket dosyasını seçtirir, seçili fakülte+yıl için
  `import_survey_excel` ile içe aktarır (not veri setinden kriter üretmeye
  benzer akış).
- İçe aktarımdan sonra ders listesi ve ilgili görünümler tazelenir.
- Kullanıcıya "anket zorunlu değildir, olgunluğu düşürmez" notu gösterilir.

Böylece **"sistemi anket formatına uydur"** isteğin iki yönlü karşılandı:
veri seti sistemin formatında üretiliyor **ve** sayfadan içe aktarılabiliyor.

---

## 7. Veri Yönetimi Sayfası

Veri Yönetimi'nin olgunluk/kapsama göstergeleri de aynı servis fonksiyonlarını
(`assess_data_readiness_cursor` / `generate_coverage_report_cursor`) kullanır;
formül değişikliği oraya da **otomatik yansır.** Ayrı kod değişikliği gerekmedi.

---

## 8. Senin Test Edeceğin Akış

1. Uygulama → **Veri → Veri Kalitesi**: yıl=2022, fakülte seç → **"Raporla
   Oluştur"**. Artık olgunluk ~%100, "VERİ HAZIR".
2. Özet/Kapsama sekmelerinde "Müfredat (zorunlu) ders" vs "Fakülte toplam ders"
   ayrımını ve anketin "BİLGİ AMAÇLI" etiketini gör.
3. **Kriter & Havuz → Kriter Girdi → "📋 Anket Belge Girişi"** →
   `data/2022_anket_tercih_veri_seti.xlsx` seç → içe aktar.
4. Veri Kalitesi'ni yeniden çalıştır: anket kapsamı artar; olgunluk **düşmez**.
