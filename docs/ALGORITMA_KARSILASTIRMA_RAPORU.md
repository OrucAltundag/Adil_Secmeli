# Adil Seçmeli – Algoritma Karşılaştırma ve Uygunluk Raporu

**Tarih:** 19 Şubat 2025  
**Kapsam:** Seçmeli ders öneri/atama probleminde kullanılabilecek algoritmaların karşılaştırılması ve mevcut projede hangilerinin mantıklı olduğunun değerlendirilmesi.

---

## 1. PROBLEM TANIMI

**Amaç:** Üniversitede seçmeli ders havuzundan, her bölüm için en uygun dersleri belirlemek ve adil bir sıralama/atama yapmak.

**Girdiler:**
- Başarı (B): Ders not ortalaması, geçme oranı
- Popülerlik (P): Talep sayısı, doluluk oranı
- Trend (T): Yıllara göre performans eğilimi
- Anket (A): Öğrenci memnuniyet puanları

**Çıktı:** Her ders için bir skor; bu skora göre müfredata dahil edilecek dersler belirlenir.

---

## 2. MEVCUT PROJEDEKİ ALGORİTMALAR

| Algoritma | Dosya | Amaç | Durum |
|-----------|-------|------|-------|
| AHP | calculation.py | Kriter ağırlıklarını hesaplama | ✅ Kullanılıyor |
| TOPSIS | calculation.py | Dersleri skorlara göre sıralama | ✅ Kullanılıyor |
| Tarihsel Trend | calculation.py (gecmis_trend_hesapla) | Geçmiş yılların ağırlıklı ortalaması | ⚠️ calc_tab'da referans var, calculation.py'de tanım eksik olabilir |
| Lineer Regresyon | ai_engine.py | Not tahmini | ✅ Kullanılıyor |
| Random Forest | ai_engine.py | Geçti/Kaldı tahmini | ✅ Kullanılıyor |
| Decision Tree | ai_engine.py | Geçti/Kaldı tahmini | ✅ Kullanılıyor |
| TF-IDF + Benzerlik | similarity_engine.py | Ders benzerliği (NLP) | ✅ Kullanılıyor |

---

## 3. ALTERNATİF ALGORİTMALAR VE UYGUNLUK

### 3.1 Çok Kriterli Karar Analizi (MCDM)

| Algoritma | Açıklama | Bu Proje İçin Uygunluk | Öneri |
|-----------|----------|------------------------|-------|
| **AHP** | Kriterleri ikili karşılaştırma ile ağırlıklandırır. | ✅ Uygun | Kullanımaya devam et. |
| **TOPSIS** | İdeal çözüme yakınlık, anti-idealden uzaklık ile sıralama. | ✅ Uygun | Ana sıralama yöntemi olarak kalmalı. |
| **Analitik Hiyerarşi Süreci + VIKOR** | AHP ile ağırlık, VIKOR ile sıralama. | ⚠️ Orta | TOPSIS'e alternatif; benzer sonuçlar verir. |
| **ELECTRE** | Outranking tabanlı; tercih ilişkilerini modeller. | ⚠️ Orta | Karmaşık; TOPSIS daha yaygın ve anlaşılır. |
| **PROMETHEE** | Tercih fonksiyonları ile sıralama. | ⚠️ Orta | TOPSIS kadar popüler değil. |
| **MOORA** | Çok amaçlı optimizasyon. | ⚠️ Düşük | Daha niş; mevcut AHP+TOPSIS yeterli. |

**Sonuç:** AHP + TOPSIS kombinasyonu bu problem için yaygın ve uygun. Değiştirmeye gerek yok.

---

### 3.2 Makine Öğrenmesi (Tahmin ve Sınıflandırma)

| Algoritma | Açıklama | Bu Proje İçin Uygunluk | Öneri |
|-----------|----------|------------------------|-------|
| **Lineer Regresyon** | Not tahmini (sürekli değer). | ✅ Uygun | Devam et. |
| **Random Forest** | Geçti/Kaldı tahmini (sınıflandırma). | ✅ Uygun | Veri az olsa bile mantıklı. |
| **Decision Tree** | Karar kurallarının görselleştirilmesi. | ✅ Uygun | Yorumlanabilirlik avantajı. |
| **XGBoost / LightGBM** | Daha güçlü ensemble modeller. | ⚠️ Orta | Veri büyükse (binlerce kayıt) düşünülebilir. |
| **Lojistik Regresyon** | Geçti/Kaldı için basit sınıflandırma. | ✅ Uygun | RF/DT'ye alternatif; daha basit. |
| **K-NN** | Benzer öğrenci/ders profillerine bakarak tahmin. | ⚠️ Düşük | Özellik uzayı zayıf; bu projede sınırlı fayda. |
| **Neural Network** | Derin öğrenme. | ❌ Uygun değil | Veri boyutu küçük; overfitting riski yüksek. |

**Sonuç:** LR, RF, DT üçlüsü yeterli. Öğrenci-ders atama problemi için XGBoost/NN gereksiz karmaşıklık getirir.

---

### 3.3 Benzerlik ve İlişki Analizi

| Algoritma | Açıklama | Bu Proje İçin Uygunluk | Öneri |
|-----------|----------|------------------------|-------|
| **TF-IDF + Cosine Similarity** | Ders açıklamalarından benzerlik. | ✅ Uygun | "Benzer dersler" önerisi için ideal. |
| **Jaccard Benzerliği** | Öğrenci tercih kümeleri üzerinden. | ⚠️ Orta | "Bu dersi alanlar şunu da aldı" için kullanılabilir. |
| **Collaborative Filtering** | Öğrenci-ders matrisi üzerinden. | ⚠️ Orta | Yeterli veri varsa ileride eklenebilir. |
| **NetworkX / Graf Analizi** | Ders-ders ilişki ağı. | ✅ Uygun | Zaten relations_tab'da var; devam et. |

**Sonuç:** TF-IDF + NetworkX kombinasyonu yerinde. Collaborative filtering ileride "öneri sistemi" eklenirse düşünülebilir.

---

### 3.4 Optimizasyon ve Atama

| Algoritma | Açıklama | Bu Proje İçin Uygunluk | Öneri |
|-----------|----------|------------------------|-------|
| **Doğrusal Programlama (LP)** | Kontenjan, bölüm kısıtları ile maksimizasyon. | ✅ Çok uygun | "En adil atama" için ideal. |
| **Tamsayı Programlama (IP)** | Her bölüme tam sayı ders atama. | ✅ Uygun | LP'nin discrete versiyonu. |
| **Hungarian Algorithm** | Atama problemi (eşleştirme). | ⚠️ Orta | Bire-bir atama varsa uygun; bu projede çoklu seçim var. |
| **Genetik Algoritma** | Evrimsel arama ile en iyi kombinasyonu bulma. | ⚠️ Düşük | LP ile çözülebilir; GA gereksiz karmaşık. |
| **Simulated Annealing** | Benzer şekilde meta-sezgisel. | ⚠️ Düşük | LP tercih edilmeli. |

**Sonuç:** Mevcut projede LP/IP yok. İleride "bölüm başına X ders, toplam kontenjan Y" gibi kısıtlar eklenirse LP eklenmesi mantıklı olur.

---

### 3.5 Basit Metrikler

| Algoritma | Açıklama | Bu Proje İçin Uygunluk | Öneri |
|-----------|----------|------------------------|-------|
| **Ağırlıklı Ortalama** | S = wB·B + wP·P + wA·A | ✅ Uygun | En basit yöntem; TOPSIS'in sadeleştirilmiş hali. |
| **Z-Score Normalizasyon** | Kriterleri standart sapmaya göre normalize et. | ✅ Uygun | TOPSIS'te zaten benzeri yapılıyor. |
| **Min-Max Normalizasyon** | 0–1 aralığına ölçekleme. | ✅ Uygun | TOPSIS'te kullanılabilir. |

**Sonuç:** Basit ağırlıklı ortalama da kullanılabilir; TOPSIS daha sofistike ve tercih edilmeli.

---

## 4. ALGORİTMA SEÇİM ÖZETİ

### Mevcut Projede Kalması Gerekenler ✅

| Algoritma | Gerekçe |
|-----------|---------|
| AHP | Kriter ağırlıkları için standart ve anlaşılır. |
| TOPSIS | Ders sıralaması için uygun; ideal/anti-ideal mesafe mantığı net. |
| Lineer Regresyon | Not tahmini için uygun. |
| Random Forest | Geçti/Kaldı tahmini; veri az olsa bile makul. |
| Decision Tree | Yorumlanabilirlik; komisyona "neden bu karar" anlatmak kolay. |
| TF-IDF + Cosine | Ders benzerliği; "benzer dersler" özelliği için ideal. |
| NetworkX | İlişki grafiği; görselleştirme için faydalı. |

### İleride Eklenebilecekler 🔮

| Algoritma | Ne Zaman |
|-----------|----------|
| Lojistik Regresyon | RF/DT'ye alternatif basit model olarak. |
| LP / IP | Kontenjan ve bölüm kısıtlarıyla "optimal atama" modülü. |
| Collaborative Filtering | Öğrenci bazlı "senin için önerilen dersler" özelliği. |

### Eklenmemesi Gerekenler ❌

| Algoritma | Gerekçe |
|-----------|---------|
| Neural Network | Veri boyutu küçük; overfitting. |
| ELECTRE / PROMETHEE | TOPSIS yeterli; karmaşıklık artar. |
| Genetik Algoritma | LP ile çözülebilir; gereksiz. |

---

## 5. ÖNERİLEN ALGORİTMA MİMARİSİ

```
                    ┌─────────────────────────────────────────┐
                    │         VERİ KAYNAKLARI                  │
                    │  performans, populerlik, anket, havuz    │
                    └──────────────────┬──────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         │                             │                             │
         ▼                             ▼                             ▼
┌─────────────────┐         ┌─────────────────────┐       ┌──────────────────┐
│ AHP (Ağırlık)   │         │ TF-IDF (Benzerlik)  │       │ AI Engine        │
│ Kriter: B,P,T,A │         │ Ders açıklamaları   │       │ LR, RF, DT       │
└────────┬────────┘         └──────────┬──────────┘       │ Tahmin/tahmin    │
         │                             │                  └────────┬─────────┘
         │                             │                           │
         └────────────────┬────────────┴───────────────────────────┘
                          │
                          ▼
                ┌─────────────────────┐
                │ TOPSIS (Sıralama)   │
                │ Ders skorları       │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Havuz Kararı        │
                │ Statü, sayaç        │
                └─────────────────────┘
```

---

## 6. SONUÇ

- **Mevcut algoritma seti (AHP, TOPSIS, LR, RF, DT, TF-IDF)** problem için mantıklı ve yeterli.
- Öncelik, algoritmaları değiştirmek değil; **veri akışını düzeltmek** (kriter sayfası → performans/popülerlik bağlantısı).
- İleride LP tabanlı "optimal atama" modülü ve Collaborative Filtering tabanlı "kişiselleştirilmiş öneri" eklenebilir.
