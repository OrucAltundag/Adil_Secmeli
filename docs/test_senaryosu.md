# Arayüz Test Senaryosu — Uçtan Uca (Kullanıcı Eli)

> **Amaç:** Seçmeli ders karar destek sisteminin tüm akışını **tamamen
> arayüzden** (CLI olmadan) çalıştırmak. 2022 verisiyle bir karar
> çalıştırması ve dönem planı üretmek.
>
> **Sıra önemlidir.** Ok yönünde ilerle; bir adım "Hazır/Tamam" demeden
> sonrakine geçme. İlgili tasarım dokümanı: [nihai_senaryo.md](nihai_senaryo.md).

---

## Adım Haritası

```
0) Sistem Sağlığı
1) Kapsam sabitle (2022 / Fakülte / Güz)
2) Veri Yönetimi + Veri Kalitesi
3) Kriterleri elle gir
4) AHP ağırlıkları (CR ≤ 0.10, aktif)
5) Karar Politikası (aktif) + Hazırlık (Hazır)
6) ⭐ Yeni Karar Çalıştır            → decision_runs
7) Ders Kararları / Önerilen Dersler / Hassas / Adalet / Onay / Havuz
8) ⭐ Plan Üret                      → semester_plan_runs
9) Raporlama & Dışa Aktarım
```

---

## 0) Başlangıç ve Sistem Sağlığı

1. Uygulamayı aç.
2. Gerekirse üst bardan **Veritabanı Seç** → `data/adil_secmeli.db`.
3. **Sistem → 🏥 Sistem Sağlığı** → "Tam Sağlık Kontrolü".
4. **Güvenlik & Hazırlık** sayfasında üretim güvenliğini gör.
5. **Veritabanı Görüntüle**'de fakülte/bölüm/ders/havuz/kriter tablolarının
   geldiğini doğrula.

**Beklenen:** DB bağlı, kritik hata yok, tablolar görünüyor.

---

## 1) Kapsamı Sabitle

Bütün sayfalarda **aynı** kapsamı kullan:

- Akademik yıl: **2022**
- Fakülte: ör. **Mühendislik ve Doğa Bilimleri Fakültesi**
- Bölüm: fakülte geneli ya da tek bölüm
- Dönem: **Güz**

> Sayfalar arası kapsam karışırsa kararlar anlamını yitirir.

---

## 2) Veri Yönetimi ve Veri Kalitesi

1. **Veri → 📥 Veri Yönetimi → Merkez**: 2022 kapsamında toplam ders, veri
   olgunluğu, eksik kriter/anket sayısını gör.
2. (Gerekirse) **Yeni Import** ile müfredat/kriter/anket Excel'i yükle;
   "Kalite uygunsa aktif yap" açık → "Importu Başlat".
3. **Veri → ✓ Veri Kalitesi**: yıl+fakülte seç → "Rapor Oluştur" →
   kapsama raporu, olgunluk skoru, eksik veri matrisi.

**Beklenen:** Veri olgunluğu karar çalıştırmaya yetecek düzeyde; kritik
doğrulama sorunu yok.

---

## 3) Kriterleri Elle Gir  (manuel giriş)

1. **Karar Süreci → 🧮 Kriter & Havuz → 📝 Kriter Girdi İşlemleri**.
2. Fakülte/bölüm/yıl/dönem seç. "Kriter: Girilmedi" olanları bul.
3. Ders seç, alanları gir:
   - Dersi alan toplam öğrenci / geçen öğrenci / not ortalaması
   - Kontenjan / kayıtlı öğrenci
   - Ankete katılan / dersi seçen öğrenci
4. **"Kaydet ve Güncelle"**.

**Beklenen:** Alanlar **aktif** (kilitli değil); başarı oranı, doluluk,
anket tercih oranı **anlık** hesaplanır. Kayıt `ders_kriterleri`,
`performans`, `populerlik` tablolarına yansır; Veri Kalitesi'ndeki eksik
sayıları düşer.

---

## 4) AHP Ağırlıkları

1. **Karar Süreci → ⚖️ AHP Ağırlık Yönetimi**.
2. "+ Yeni Profil" → kapsam (global/fakülte/bölüm) + yıl.
3. **İkili Karşılaştırma**: başarı / trend / popülerlik / anket kriterlerini
   karşılaştır.
4. **"Ağırlıkları Hesapla"** → **CR ≤ 0.10** olmalı.
5. **"Kaydet ve Onayla"** → Onay Akışı → **Profil Listesi → aktif yap**.

**Beklenen:** En az bir **aktif ve tutarlı** AHP profili. Karar Merkezi
bunu kullanacak.

---

## 5) Karar Politikası + Hazırlık Kapısı

1. **Karar Merkezi → Karar Politikaları**: aktif politika yoksa "Yeni
   Varsayılan Politika" → **"Aktif Yap"**. (Eşik mantığı: ≥70 müfredat,
   ≥50 havuz, <40 dinlenme, ≤30 iptal adayı; kalıcı iptal manuel onay.)
2. **Karar Merkezi → Hazırlık Kontrolü**: kapsamı seç → "Hazırlığı Yenile".
3. Durum **"Hazır"** olmalı. "Engellendi" ise eksik kriterleri tamamla
   (Adım 3) veya gerekçeli "Override Talep Et".

**Beklenen:** Aktif politika + "Hazır" durumu. Aksi halde karar
çalıştırma engellenir.

---

## 6) ⭐ Resmi Karar Çalıştırma

1. **Karar Merkezi → Çalıştırmalar**. Kapsamı tekrar doğrula.
2. **"Yeni Karar Çalıştır"**.

**Beklenen:** Yeni `decision_runs` kaydı; ders bazlı `course_decisions`
(TOPSIS skoru, trend, veri güveni, **açılabilirlik skoru**, statü önerisi).
Üstteki run listesinde yeni çalıştırma seçilebilir hale gelir.

---

## 7) Sonuçları İnceleme

Üstteki **Run** filtresinden bu çalıştırmayı seç, sonra sekmeler:

1. **Ders Kararları**: eski/önerilen/final statü, TOPSIS, trend, veri
   güveni, stabilite, onay gerekli mi, gerekçe. Satıra tıkla → detay.
2. **Önerilen Dersler** *(yeni)*: **açılabilirlik skoruna göre azalan**
   sıralı. Kategoriler:
   - Açılması Güçlü Önerilen
   - Şartlı Açılması Önerilen (kurul onayı gerekli)
   - Havuzda Kalması Önerilen
   - Dinlenmeye Alınması Önerilen
   - İptal Adayı
3. **Hassas Kararlar**: düşük stabiliteli dersler.
4. **Adalet Raporu**: bölüm/fakülte dengesizliği.
5. **Akademik Onay**: kritik kararları **Onayla / Reddet**.
6. **Havuz Yaşam Döngüsü**: "Yenile" → statü geçişleri; onay bekleyenler.

**Beklenen:** Her ders için "neden bu karar?" açıklanabiliyor; kalıcı iptal
gibi kritik kararlar otomatik kesinleşmiyor, insan onayı bekliyor.

---

## 8) ⭐ Dönem Planlama

1. **Karar Süreci → 📅 Dönem Planlama**. Yıl/fakülte/bölüm seç.
2. Politikayı kontrol et (hedef 8 seçmeli; Güz 4/4, Bahar 4/4). Gerekirse
   "Politikayı Kaydet".
3. "Adayları Kontrol Et" → **"Plan Üret"**.
4. (Opsiyonel) "Alternatifleri Üret".

**Beklenen:** Yeni `semester_plan_runs`; Güz/Bahar planı, yerleşmeyen
dersler, kısıt ihlalleri, alternatif planlar. **Adaylar Adım 6'nın
açılabilirlik skoruyla sıralanır** (karar yoksa eski skor kaynağına düşer).

---

## 9) Raporlama ve Dışa Aktarım

1. **Dönem Planlama**: plan ve kısıt ihlallerini CSV dışa aktar.
2. **Raporlama & Analiz → 📄 Rapor & Yükleme**: "Rapor Getir",
   "DB Yedekle", havuz/müfredat CSV/Excel dışa aktar.
3. **Raporlama & Analiz → 📊 Analiz & Grafik**: KPI kartları, en başarılı/
   en popüler dersler.

**Beklenen:** Akademik kurula sunulacak çıktılar hazır.

---

## Doğrulama Soruları

- Yüksek başarı + yüksek talep ders → "Açılması Güçlü Önerilen" mi?
- Düşük başarı + düşük talep ders → "Dinlenme" / "İptal Adayı" mı?
- Önerilen Dersler'deki yüksek açılabilirlikli dersler, Dönem Planı'na
  girdi mi?
- Adım 6'yı atlayıp Adım 8'i çalıştırırsan plan yine üretiliyor ama
  açılabilirlik beslemesi olmuyor (eski `skor` kaynağı) — farkı gözlemle.

---

## Hızlı Hata Giderme

| Belirti | Olası neden | Çözüm |
|---|---|---|
| "Yeni Karar Çalıştır" engelli | Hazırlık "Hazır" değil | Adım 3 (kriter) → Adım 5 (hazırlık) |
| Bir fakülte "atlandı" | Kriter girişi eksik | O fakülte için Adım 3'ü tamamla |
| Önerilen Dersler boş | Run seçili değil / karar yok | Çalıştırmalar'dan run seç ya da Adım 6 |
| Plan boş / aday yok | Karar veya kriter eksik | Adım 6'yı koştur, kapsamı doğrula |
| AHP onaylanamıyor | CR > 0.10 | İkili karşılaştırmayı yeniden düzenle |

---

## Alternatif: Komut Satırından (UI yerine)

Aynı çıktıları uygulama **kapalıyken** üretmek için:

```bash
python -m scripts.run_first_decision_2022        # Adım 6 — decision_runs
python -m scripts.run_first_semester_plan_2022   # Adım 8 — semester_plan_runs
```

> Önce karar, sonra plan. DB uygulama açıkken kilitlidir.
