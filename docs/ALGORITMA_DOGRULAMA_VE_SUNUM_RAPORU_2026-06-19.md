# Algoritma Doğrulama ve Sunum Raporu

**Tarih:** 19 Haziran 2026  
**Kapsam:** Trend/LR, AHP, TOPSIS, ELECTRE TRI-B, Decision Tree ve PROMETHEE II

## 1. Trend ve Lineer Regresyon

### 1.1 Ağırlıklı trend

Gerçek geçmiş başarı değerlerinin en güncel üç yılı kullanılır. Varsayılan ağırlıklar
yeni yıldan eskiye `0,50 / 0,30 / 0,20` şeklindedir. Bir veya iki yıl varsa mevcut
ağırlıklar toplamı 1 olacak şekilde yeniden normalize edilir. Tek yıllık derslerde
trend başarının kopyası yapılmaz; nötr yorumlanır.

### 1.2 LR tahmini

LR servisi hedef yıldan önceki üç kesinleşme puanını `havuz.skor` alanından okur:

```text
x = [1, 2, 3]
y = [t-3 skoru, t-2 skoru, t-1 skoru]
y_tahmin = β0 + β1 × 4
```

- Eksik yıl nötr `50` kabul edilir ve güven düşürülür.
- Tahmin 0–100 aralığında sınırlandırılır.
- `|β1| < 3` ise Stabil, `β1 ≥ 3` Artan, `β1 ≤ -3` Azalan denir.
- Bu sonuç destekleyicidir; tek başına müfredat statüsü değiştirmez.

**Konuşma metni:**

> Trend ekranında gerçek geçmiş değerlerle tahmini ayırıyorum. Gerçek yıllar mavi,
> LR tahmini mor kesik çerçevelidir. Ağırlıklı trend yakın yıllara daha fazla önem
> verir. LR ise son üç kesinleşme puanına doğru uydurup sonraki yılı tahmin eder.
> Eksik geçmiş sıfır sayılmaz; nötr 50 kullanılır ve güven düşürülür.

## 2. AHP ve CR

Kriterler: başarı, trend, popülerlik ve anket. İkili karşılaştırma matrisi karşılıklıdır:
`a_ij = 1/a_ji`. Ana özvektör normalize edilerek ağırlıklar elde edilir ve toplamları 1’dir.

```text
CI = (λmax − n) / (n − 1)
CR = CI / RI
```

Dört kriter için `RI = 0,90`; `CR ≤ 0,10` tutarlı kabul edilir. Karar çalıştırması
strict modda aktif ve tutarlı profil bulamazsa legacy ağırlıklara sessizce düşmez;
çalıştırmayı engeller.

## 3. TOPSIS doğrulaması

### 3.1 Formül

```text
r_ij = x_ij / √Σ(x_ij²)
v_ij = w_j × r_ij
S_i+ = √Σ(v_ij − A_j+)²
S_i− = √Σ(v_ij − A_j−)²
C_i* = S_i− / (S_i+ + S_i−)
Göreli TOPSIS puanı = 100 × C_i*
```

### 3.2 0 ve 100 neden mümkündür?

- Alternatif bütün ayırt edici kriterlerde pozitif ideale eşitse `S+=0`, dolayısıyla `C*=1` ve puan 100’dür.
- Alternatif negatif ideale eşitse `S-=0`, dolayısıyla `C*=0` ve puan 0’dır.
- Bu değerler yuvarlama sonucu değildir; standart TOPSIS’in seçili alternatif kümesine göre göreli yapısıdır.
- `A+=A−` olan kriterin varyansı yoktur ve mesafelere sıfır katkı verir. Ekran bunu artık açıkça uyarır.

### 3.3 Uygulanan düzeltmeler

- TOPSIS evreni artık seçili bölüm müfredatıyla sınırlandırılır.
- Bölüm bazlı aktif AHP profili kullanılır; fakülte profili ancak profil çözümleme politikasına göre fallback’tir.
- Fakülte çapında ideal noktalar hesaplanıp sonradan bölüm filtreleme hatası kaldırılmıştır.
- UI altı ondalığa yuvarlamak yerine 15 anlamlı basamak gösterir.
- Ekranda puan adı `Göreli TOPSIS Puanı` olarak belirtilmiştir.
- Nihai statü yalnız bu göreli 0/100 değerinden üretilmez; ELECTRE ham kriter profilleriyle sınıflandırır.

**Konuşma metni:**

> Buradaki 100 “mutlak olarak kusursuz”, 0 ise “mutlak olarak değersiz” demek
> değildir. TOPSIS seçili bölümdeki dersleri birbirine göre karşılaştırır. Pozitif
> ideale eşit olan 100, negatif ideale eşit olan 0 alabilir. Bu nedenle puanı
> göreli TOPSIS puanı olarak gösteriyoruz. Ara değerler yuvarlanmadan yüksek
> hassasiyetle veriliyor; varyansı olmayan kriterler ayrıca uyarılıyor. Akademik
> statüyü ELECTRE ham kriter profilleri üzerinden verdiği için TOPSIS uç değerleri
> tek başına müfredat kararına dönüşmüyor.

## 4. ELECTRE TRI-B doğrulaması

ELECTRE TRI-B, her dersi sıralı sınır profilleriyle karşılaştırır. Varsayılan kriterler
başarı, trend, doluluk/talep ve ankettir. AHP ağırlıkları normalize edilir.

Varsayılan eşikler:

- Kayıtsızlık `q = 0,05`
- Tercih `p = 0,15`
- Başarı için veto `v = 0,25`
- Kesme düzeyi `λ = 0,65`
- Sınır profilleri: Müfredat 0,70; Havuz 0,50; Dinlenme 0,40

Kısmi uyum değerleri AHP ağırlıklarıyla toplanır. Bir kriterde profil aleyhine büyük
fark varsa discordance/veto credibility değerini düşürür. Temkinli (pessimistic)
atama, dersin geçtiği en yüksek güvenilir profili seçer; hiçbir profili geçmezse
iptal adayı üretir ve manuel onay ister.

**Doğruluk notu:** Kodda q < p ve veto > p koşulları doğrulanır; λ yalnız 0,50–1,00
aralığında kabul edilir. Çıktıda kategori, credibility, güçlü/zayıf/veto kriterleri
ve bütün profil karşılaştırmaları saklanır.

## 5. Decision Tree ve ELECTRE etkileşimi

DT, ELECTRE’nin etiketlerini yeniden ezberlemek için mevcut run üzerinde eğitilmez.
Yalnız hedef yıldan önceki `completed` ve stale olmayan karar çalıştırmalarının
uygulanmış `final_status` değerleri eğitim hedefidir. Aynı ders/yıl/dönemin tekrar
run’larından yalnız en yenisi kullanılır.

Özellikler:

1. Başarı
2. Ağırlıklı trend
3. LR trend tahmini
4. Popülerlik/doluluk
5. Anket
6. TOPSIS puanı
7. Veri güveni
8. Önceki statü

Hazırlık koşulları:

- En az 100 geçmiş eğitim örneği
- En az iki farklı final statüsü
- Her sınıf için en az 10 örnek
- Mümkünse seçili fakülte/bölüm geçmişi; yetersizse global geçmiş

DT hazır değilse `Veri yetersiz` gösterilir. Eşiği yapay olarak düşürmek veya aynı yıl
verisini eğitime katmak doğruluk değil veri sızıntısı üretir. Yeterli hale getirmek için
önce geçmiş yılların gerçek kararları çalıştırılmalı, akademik olarak sonuçlandırılmalı
ve farklı statülerden yeterli örnek biriktirilmelidir.

ELECTRE–DT sonucu:

- `Uyumlu`: İki yöntem aynı statüyü önerdi.
- `DT daha olumlu`: Geçmiş örüntü ELECTRE’den daha yüksek statü önerdi.
- `DT daha temkinli`: Geçmiş örüntü daha düşük statü önerdi.
- `Veri yetersiz`: Model güvenli şekilde çalıştırılmadı.

DT advisory-only’dir; `should_influence_decision=False`. Çatışma kurul incelemesine
sunulur, final statüyü otomatik değiştirmez.

## 6. PROMETHEE II Top-7 doğrulaması

### 6.1 Aday evreni

Seçili yıl ve fakülte/bölümde bulunan fakat aktif müfredatta yer almayan derslerdir.
Bu nedenle öneri sayısı aday sayısına bağlıdır; yeterli aday varsa en fazla 7 ders seçilir.

### 6.2 Kriterler ve varsayılan ağırlıklar

| Kriter | Ağırlık | Hesaplama |
|---|---:|---|
| Akademik/bölüm uygunluğu | 0,20 | Aynı bölüm 100, fakülte düzeyi aday 85 |
| Müfredat boşluğu katkısı | 0,20 | `0,60×akademik uygunluk + 0,40×çakışmama` |
| Anket talebi | 0,15 | Veri yoksa nötr 50; oy varsa logaritmik bonus |
| Kaynak uygunluğu | 0,15 | Öğretim bilgisi yoksa nötr 50, varsa 100 |
| Dönem/AKTS uygunluğu | 0,10 | Dönem eşleşirse 100, diğer dönemde 65, veri yoksa 50 |
| Tekrar/çakışma azlığı | 0,10 | Müfredat içeriğiyle Jaccard benzerliğinin tersi |
| Sektörel/güncel değer | 0,05 | Şimdilik nötr 50 |
| Veri güveni | 0,05 | Açıklama, AKTS, kredi, anket ve kaynak bileşenlerinin tamlığı |

Not: AHP profili sekiz PROMETHEE kriterinin tamamını içermiyorsa belgelenmiş uzman
varsayılanları kullanılır. Kaynak ve sektörel değer verisi eksikse nötr değer kullanıldığı
UI gerekçesinde açıkça görülmelidir; nötr değer gerçek ölçüm gibi yorumlanmamalıdır.

### 6.3 Net akış

Her aday diğer tüm adaylarla kriter bazında karşılaştırılır. V-shape tercih fonksiyonunda
varsayılan `q=5`, `p=20` kullanılır.

```text
π(a,b) = Σ w_j × P_j(a_j − b_j)
φ+(a) = Σ π(a,b) / (n−1)
φ−(a) = Σ π(b,a) / (n−1)
φ(a) = φ+(a) − φ−(a)
```

Net akış teorik olarak `[-1, 1]` aralığındadır. Büyük değer daha güçlü adayı gösterir.

### 6.4 Çeşitlilik kontrollü seçim

Saf PROMETHEE sırasındaki birbirine çok benzer derslerin Top-7’yi doldurmaması için
MMR-benzeri ikinci seçim uygulanır:

```text
çeşitlilik skoru = 0,75 × normalize(net akış) − 0,25 × en yüksek içerik benzerliği
```

Bu nedenle ekrandaki seçili sıra her zaman net akışın katı azalan sırası olmayabilir;
bu hata değil, bilinçli çeşitlilik kuralıdır. `promethee_rank` saf sıralamayı,
`rank` çeşitlilik sonrası seçili sırayı temsil eder.

**Konuşma metni:**

> PROMETHEE II müfredat dışındaki adayları sekiz kriterle ikili karşılaştırır.
> Phi artı diğer adaylara ne kadar üstün olduğunu, phi eksi ne kadar geride kaldığını,
> net akış da bu ikisinin farkını gösterir. Yalnız en yüksek akışları almak benzer
> içerikli dersleri tekrar ettirebileceği için yüzde 75 sıralama, yüzde 25 içerik
> çeşitliliğiyle ikinci seçim yapılıyor. Bu yüzden seçilen yedi dersin sırası net
> akışta tamamen monoton görünmeyebilir. Veri olmayan anket veya kaynak alanları
> sıfırla cezalandırılmıyor; nötr 50 kabul edilip gerekçede belirtiliyor.

## 7. Havuz yaşam döngüsü ve müfredat yazma güvenliği

- `Nihai Müfredatı Hazırla` yalnız Güz/Bahar önizlemesi üretir.
- Karar satırı olmayan mevcut ders güvenli biçimde korunur.
- Düşen ders için PROMETHEE Top-7 içinden otomatik yedek önerilebilir.
- `Ders Değiştir` yalnız pending önizleme JSON’unu değiştirir; canlı müfredatı yazmaz.
- Hiç değişiklik yapılmadan otomatik önizleme korunabilir.
- `Müfredatı Reddet` yalnız review durumunu rejected yapar; canlı müfredatı değiştirmez.
- Yalnız `Müfredatı Onayla`, hedef yıl Güz/Bahar derslerini resmi müfredat tablosuna yazar.

## 8. Doğrulama sonucu

Bu değişiklik paketi için algoritma, veri kapsamı, karar yönetişimi, UI smoke,
havuz ve dönem planlama testleri çalıştırılmıştır. Hedefli paketlerde 64/64 ve
76/76 test başarılıdır. Ayrıca bölüm kapsamının legacy fakülte sorgusuyla yeniden
genişlemesini engelleyen özel regresyon testi eklenmiştir.

