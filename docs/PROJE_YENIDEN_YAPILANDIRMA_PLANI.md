# Adil Seçmeli – Proje Yeniden Yapılandırma Planı

**Tarih:** 19 Şubat 2025  
**Amaç:** Projeyi baştan aşağı düzenlemek, veri akışını tek merkezden yönetmek ve gerçek hayat senaryosuna uyum sağlamak.

---

## 1. MEVCUT DURUM ANALİZİ

### 1.1 Neyi Doğru Yaptın?

| Alan | Durum | Açıklama |
|------|-------|----------|
| **Kriter Sayfası** | ✅ İyi | Manuel veri girişi mantıklı; form tasarımı (toplam öğrenci, geçen, ortalama, kontenjan, kayıtlı) doğru kavramlara dayanıyor. |
| **Performans / Popülerlik Mantığı** | ✅ İyi | Başarı oranı, doluluk oranı gibi metrikler akademik literatüre uygun. |
| **Havuz Yapısı** | ✅ İyi | Statü (1/0/-1), sayaç, skor alanları mantıklı. |
| **AHP/TOPSIS Seçimi** | ✅ İyi | Çok kriterli karar analizi için uygun yöntemler. |
| **Excel İmport** | ✅ İyi | `import_mufredat_excel.py` esnek kolon eşleştirmesi yapıyor. |

### 1.2 Kritik Sorunlar

#### A) Veri Akışı Kopukluğu (En Önemli Sorun)

```
Kriter Sayfası (ders_kriterleri)     Algoritmalar (calculation.py)
        │                                    │
        │  toplam_ogrenci                    │  performans.ortalama_not
        │  gecen_ogrenci                     │  performans.basari_orani
        │  basari_ortalamasi   ──────X──────>│  populerlik.talep_sayisi
        │  kontenjan                          │  populerlik.doluluk_orani
        │  kayitli_ogrenci                    │
        ▼                                    ▼
   ders_kriterleri tablosu           performans + populerlik tabloları
```

**Sonuç:** Kriter sayfasında girdiğin veriler AHP/TOPSIS veya diğer algoritmalara hiç gitmiyor. Algoritmalar sadece `performans` ve `populerlik` tablolarından okuyor.

#### B) Tablo/Şema Tutarsızlıkları

| Sorun | Detay |
|-------|-------|
| **ders_kriterleri** | Hiçbir `schema.sql` veya migration'da `CREATE TABLE` yok. Tablo elle veya başka script ile oluşturulmuş olmalı. |
| **tercih_sayisi vs talep_sayisi** | `calc_tab.py` ve `analysis_tab.py` `pop.tercih_sayisi` kullanıyor; `populerlik` tablosunda ise `talep_sayisi` var. Sorgu hata verebilir. |
| **İki farklı şema** | `schema.sql` (ders_performans_ozeti, popuarlik_olcumu) ile `smart_data_generator.py` (performans, populerlik) farklı tablo isimleri kullanıyor. |

#### C) Gerçek Hayat Veri Kaynakları Belirsiz

- Ders not ortalaması, başarı oranı → Öğrenci Bilgi Sistemi (OBS)
- Talep sayısı, kontenjan → Ders Kayıt Sistemi
- Anket puanları → Öğrenci Anket Sistemi
- Müfredat → Akış / Bologna komisyonu kararları

Şu an sistem bu kaynakların Excel/manuel giriş ile beslenmesini varsayıyor; bu gerçek hayatta genelde OBS entegrasyonu veya dönemsel Excel export ile yapılır.

---

## 2. ÖNERİLEN VERİ MİMARİSİ

### 2.1 Tek Kaynak (Single Source of Truth)

Tüm kriter verileri tek tabloda veya net bir kaynaktan gelmeli:

```
┌─────────────────────────────────────────────────────────────────┐
│                    VERİ KAYNAKLARI                               │
├─────────────────────────────────────────────────────────────────┤
│  1. Excel Import (Dönem başı)  →  ders_kriterleri / performans   │
│  2. Manuel Giriş (Kriter Sayfası) →  AYNI TABLOLARA yazmalı      │
│  3. OBS Entegrasyonu (İleride) →  Aynı tablolar                 │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  ORTAK TABLOLAR (Algoritmaların Okuduğu Yer)                     │
│  • performans: ortalama_not, basari_orani, akademik_yil          │
│  • populerlik: talep_sayisi, kontenjan, doluluk_orani, yil       │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│  ALGORİTMALAR: AHP, TOPSIS, ML, Havuz Kararı                     │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Önerilen Tablo Yapısı

**Seçenek A – ders_kriterleri'ni Kaldır, performans + populerlik Kullan**

- Kriter sayfası, veriyi doğrudan `performans` ve `populerlik` tablolarına yazar.
- Avantaj: Tek şema, tek kaynak.
- Dezavantaj: performans/populerlik tabloları `akademik_yil` bazlı; kriter sayfası `yil` kullanıyor. Uyum sağlanmalı.

**Seçenek B – ders_kriterleri Ana Kaynak, performans/populerlik Türet**

- Kriter sayfası `ders_kriterleri`'ne yazar.
- Bir senkronizasyon fonksiyonu: `ders_kriterleri` → `performans` + `populerlik` kopyalar.
- Algoritmalar `performans` + `populerlik` okumaya devam eder.
- Avantaj: Manuel giriş ayrı, hesaplama tabloları ayrı; audit trail kolay.
- Dezavantaj: Ekstra senkron adımı gerekir.

**Öneri:** Seçenek A daha sade. Kriter sayfası kaydettiğinde hem `performans` hem `populerlik` tablolarına yazsın (UPSERT mantığıyla).

---

## 3. ADIM ADIM YAPILACAKLAR

### Faz 1: Veri Tutarlılığı (Öncelik: Yüksek)

| # | Görev | Açıklama |
|---|-------|----------|
| 1 | `ders_kriterleri` Tablosunu Tanımla | `schema.sql` veya migration'a `CREATE TABLE ders_kriterleri` ekle (eğer kullanılacaksa). |
| 2 | Kriter → Performans/Popülerlik Bağla | Kriter sayfası "Kaydet" dediğinde, `performans` ve `populerlik` tablolarına da UPSERT yap. |
| 3 | tercih_sayisi → talep_sayisi Düzelt | `calc_tab.py` ve `analysis_tab.py` içinde `tercih_sayisi` → `talep_sayisi` olarak değiştir. |
| 4 | KararMotoru Parametre Uyumu | `calc_tab`'daki TOPSIS çağrısı, `calculation.py`'deki `topsis_calistir` imzası ile uyumlu olsun (sütun adları: basari, trend, populerlik, anket). |

### Faz 2: Gerçek Hayat Veri Akışı

| # | Görev | Açıklama |
|---|-------|----------|
| 5 | Excel Şablonu Belirle | `data/` altında örnek Excel şablonu: Bölüm, Yıl, Ders, Ortalama Not, Başarı Oranı, Kontenjan, Talep. |
| 6 | Import Script Güncelle | Excel import hem müfredat hem kriter (performans/popülerlik) verilerini okuyabilsin. |
| 7 | Varsayılan Değerler | Yeni ders eklendiğinde performans/popülerlik için varsayılan değerler (örn. 0.5) otomatik atansın. |

### Faz 3: Kriter Sayfası İyileştirmeleri

| # | Görev | Açıklama |
|---|-------|----------|
| 8 | Toplu Excel Yükleme | Kriter sayfasına "Excel'den Yükle" butonu ekle; seçilen Excel'den tüm derslerin kriterlerini yüklesin. |
| 9 | Doğrulama | Negatif sayı, ortalama > 100, geçen > toplam gibi hataları engelle. |
| 10 | SQL Injection Koruması | `criteria_page.py` içindeki `f"SELECT ... WHERE ad='{fakulte}'"` gibi ifadeler parametreli sorguya çevrilsin. |

### Faz 4: Dokümantasyon ve Test

| # | Görev | Açıklama |
|---|-------|----------|
| 11 | requirements.txt | Tüm bağımlılıkları (pandas, numpy, scikit-learn, openpyxl, matplotlib, seaborn, networkx, sqlalchemy, tkinter) listele. |
| 12 | Kurulum ve Çalıştırma | README'de: 1) init_script, 2) smart_data_generator, 3) havuz_kumulatif_doldur, 4) main.py sırasıyla anlatılsın. |

---

## 4. VERİ GİRİŞİ – GERÇEK HAYAT SENARYOLARI

### Senaryo 1: Tamamen Manuel (Küçük Fakülte)

- Her dönem sonunda bölüm sekreteri veya komisyon, kriter sayfasından ders bazlı verileri girer.
- Excel’den kopyala-yapıştır veya toplu Excel import ile hızlandırılabilir.

### Senaryo 2: OBS’den Excel Export

- OBS’den “Ders Bazlı Not Özeti” ve “Ders Kayıt Özeti” Excel olarak export edilir.
- Sistem bu Excel’i import eder; gerekirse manuel düzeltme yapılır.

### Senaryo 3: API Entegrasyonu (İleride)

- OBS ve kayıt sistemi REST API sunuyorsa, dönem sonunda otomatik veri çekimi yapılabilir.
- Veriler yine `performans` ve `populerlik` tablolarına yazılır.

**Öneri:** Şu an için Senaryo 1 + 2 desteklensin. Kriter sayfası manuel giriş + Excel import ile çalışsın.

---

## 5. ÖZET ÇİZELGE

| Öncelik | Görev | Etki |
|---------|-------|------|
| P0 | Kriter sayfası → performans + populerlik yazması | Algoritmalar gerçek veriyi kullanır |
| P0 | tercih_sayisi → talep_sayisi düzeltmesi | Sorgu hataları önlenir |
| P1 | ders_kriterleri CREATE TABLE (veya kaldırma) | Şema tutarlılığı |
| P1 | Excel şablon + import | Gerçek hayat uyumu |
| P2 | Toplu Excel yükleme (kriter sayfası) | Kullanıcı deneyimi |
| P2 | SQL injection düzeltmeleri | Güvenlik |
| P3 | requirements.txt + README | Kurulum kolaylığı |

---

Bu plan, projeyi adım adım tutarlı hale getirmek için bir yol haritasıdır. İlk etapta P0 maddeleri uygulanmalıdır.
