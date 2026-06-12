# Hibrit Karar Modeli (AHP-TOPSIS) ve Karşılaştırmalı Değerlendirme

> Final sunumu gereği: **en az 1 hibrit model + en az 2 farklı algoritma +
> karşılaştırmalı değerlendirme.** Bu doküman bunu tek pakette karşılar ve
> bitirme kitapçığının "Algoritmalar ve Hesaplamalar" bölümüne doğrudan konabilir.

## 1. Neden Hibrit?

Tek bir MCDM yöntemi iki ayrı işi yapamaz:
- **AHP**, kriterlerin **ağırlığını** uzman ikili karşılaştırmasından türetir
  (ama alternatifleri sıralamaz).
- **TOPSIS**, alternatifleri **ideal çözüme yakınlığa** göre sıralar (ama
  ağırlığı dışarıdan ister).

**Hibrit fikir:** AHP'nin ürettiği ağırlıkları TOPSIS'e besle. Böylece
"hangi kriter ne kadar önemli" (AHP) ile "hangi ders ideale ne kadar yakın"
(TOPSIS) tek modelde birleşir. Literatürde **AHP-TOPSIS** bilinen bir hibrit
MCDM yaklaşımıdır.

## 2. Karşılaştırılan Üç Model

Aynı ders-kriter matrisi üzerinde çalıştırılır (`hybrid_model_service.py`):

| Model | Ağırlık | Sıralama yöntemi | Rol |
|---|---|---|---|
| **Eşit Ağırlıklı TOPSIS** | eşit (1/n) | TOPSIS | Baseline 1 |
| **AHP-SAW** | AHP | Ağırlıklı toplam (SAW) | Baseline 2 |
| **AHP-TOPSIS Hibrit** | AHP | TOPSIS | **Bu projenin modeli** |

Üçü de **bağımsız** çalışır; aralarındaki fark, ağırlık kaynağı (eşit vs AHP)
ve sıralama yöntemidir (toplam vs ideal-çözüm).

## 3. Hesaplama Adımları

### 3.1 TOPSIS (eşit ve hibrit ortak)
1. Vektör normalizasyonu: `r_ij = x_ij / sqrt(Σ x_ij²)`
2. Ağırlıklı matris: `v_ij = r_ij · w_j`  (eşit modelde w eşit, hibritte AHP)
3. İdeal `A⁺` ve negatif-ideal `A⁻` çözümler (fayda/maliyet yönüne göre)
4. Uzaklıklar: `S⁺ᵢ = ‖vᵢ − A⁺‖`, `S⁻ᵢ = ‖vᵢ − A⁻‖`
5. Yakınlık: `Cᵢ = S⁻ᵢ / (S⁺ᵢ + S⁻ᵢ)` ∈ [0,1], büyük = iyi

### 3.2 AHP-SAW (baseline 2)
1. Min-max normalizasyon (maliyet kriterleri ters çevrilir)
2. `Skorᵢ = Σ (norm_ij · w_j^AHP)`

## 4. Karşılaştırma Metriği — Sıralama Korelasyonu

Üç modelin ürettiği **sıralamalar** arasında:
- **Spearman ρ** — sıra korelasyonu (1 = tam örtüşme)
- **Kendall τ** — sıra uyum/uyumsuzluk oranı

Yüksek korelasyon → yöntemler aynı kararı veriyor (model seçimi sonucu az
etkiliyor). Düşük korelasyon → kriterler çelişiyor; ağırlıklandırma ve sıralama
yöntemi sonucu belirgin değiştiriyor.

> Not: Kriterler birbirine paralel/monoton olduğunda üç yöntem de güçlü uyum
> gösterir (ρ≈1). Ağırlıklar çarpıklaştıkça veya kriterler çeliştikçe hibrit,
> eşit-ağırlıktan ayrışır.

## 5. Çalıştırma

```bash
python -m scripts.compare_models_2022 --yil 2022 --fakulte-id 1 --donem Guz
```

Çıktı: üç modelin ders sıralaması + Spearman/Kendall korelasyon tablosu
(sunuma/kitapçığa hazır metin).

## 6. Performans Metrikleri (final eki)

Sınıflandırma/regresyon modelleri için doğruluk oranına **ek** metrikler
(`ml_evaluation_service.py`): Precision, Recall, F1, ROC-AUC, RMSE, MAE,
MAPE, R², **False Error Rate (FER)**, **White Testi**, ayrıca benchmark'ta
Spearman / Kendall / Wilcoxon. Hocanın istediği "en az 3 ek metrik" fazlasıyla
karşılanır.

## 7. Dosyalar

- `app/services/hybrid_model_service.py` — saf hibrit + karşılaştırma çekirdeği
- `scripts/compare_models_2022.py` — gerçek veriyle karşılaştırma raporu
- `app/tests/test_hybrid_model.py` — 8 birim testi
- `app/services/ml_evaluation_service.py` — FER + White Test + MAPE eklentileri
- `app/tests/test_ml_extra_metrics.py` — 5 metrik testi
