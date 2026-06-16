# Adil Seçmeli — Algoritma Akışı, Sayısal Doğrulama ve Problem Analizi Raporu

**Tarih:** 16 Haziran 2026
**Hazırlanış amacı:** Sistemde kriterlerin nasıl oluştuğunu, AHP → TOPSIS → ML
akışının neden bu sırayla kurulduğunu, hangi algoritmaların eksik olduğunu,
kullanıcıya gösterilen sayısal değerlerin doğruluğunu ve projedeki "problem
mesajlarını" **bir öğrencinin rahatça anlayacağı dilde** açıklamak.

> **Nasıl okunmalı?** Her bölüm "Ne yapılıyor? → Neden? → Hangi algoritma? →
> Daha iyisi için ne yapılabilir?" mantığıyla yazıldı. Teknik terimlerin yanına
> günlük hayattan benzetmeler koydum.

---

## 0. Büyük Resim: Sistemin Karar Boru Hattı (pipeline)

Sistem, bir dersin "açılsın mı, havuzda mı kalsın, iptal mi olsun" kararını tek
bir sezgiyle değil, **arka arkaya çalışan 4 aşamalı bir hat** ile veriyor:

```
1) VERİ + KRİTER        2) AĞIRLIK            3) PUANLAMA           4) DESTEK/DOĞRULAMA
┌─────────────────┐    ┌───────────────┐     ┌────────────────┐    ┌───────────────────┐
│ Not + anket +   │    │  AHP          │     │  TOPSIS        │    │ LR / RF / DT (ML) │
│ müfredat verisi │──► │  ağırlık üret │ ──► │ kesinleşme     │──► │ + Entropi capraz  │
│ → kriter üret   │    │  → profil sakla│     │ puanı (0-100)  │    │ kontrol + adalet  │
└─────────────────┘    └───────────────┘     └────────────────┘    └───────────────────┘
```

- **1. aşama** verinin kendisi ve ondan üretilen sayısal kriterlerdir
  (başarı oranı, doluluk, trend, anket talebi).
- **2. aşama (AHP)** "hangi kriter daha önemli?" sorusunu cevaplar → ağırlıklar.
- **3. aşama (TOPSIS)** her dersi ideal/en kötü dersle kıyaslayıp **0–100 arası
  bir kesinleşme puanı** verir.
- **4. aşama (ML)** kararı *değiştirmez*, **destekler ve doğrular**: makine
  öğrenmesi modelleri "bu karar geçmiş verideki örüntüye uyuyor mu?" diye bakar.

---

## 1. KRİTERLER NASIL OLUŞUYOR? (1. aşama)

### 1.1 Şu an ne yapılıyor?

Bir öğrenci not veri seti + ekstra ders bilgisi yüklendiğinde, sistem **kuralları
ve aritmetiği** kullanarak kriterleri üretiyor. Örnek (kaynak:
`app/services/student_dataset_criteria_service.py:115-119`):

```python
gecen        = round(kayit * gecme_yuzdesi / 100.0)     # geçen öğrenci sayısı
basari_orani = gecen / kayit            if kayit > 0 else 0.0   # 0–1 arası
doluluk_orani = min(kayit / KONTENJAN, 1.0)                     # 0–1 arası (tavan %100)
```

Buradan 4 ana kriter doğuyor:

| Kriter | Anlamı | Nasıl üretiliyor |
|--------|--------|------------------|
| **başarı** | Dersi geçenlerin oranı / ortalama not | `gecen / kayit` |
| **trend** | Yıllar içindeki yön (artıyor mu, azalıyor mu) | geçmiş yıl puanları (trend servisi) |
| **popülerlik** | Talep / doluluk | `min(kayit / kontenjan, 1.0)` |
| **anket** | Öğrencinin dersi seçme isteği | anket katılım/seçim oranı |

### 1.2 Bu veri seti bir "algoritma" gerektiriyor mu?

**Kısa cevap: Kriterleri *üretmek* için zorunlu değil; ama *güvenilirliği
artırmak* için kesinlikle faydalı.**

Şu anki yöntem **kural tabanlı** (rule-based). Yani burada makine öğrenmesi yok;
sadece "böl, çarp, ortalama al" var. Bunun **iyi** yanı: şeffaf, açıklanabilir,
az veride bile çalışır. **Zayıf** yanı: tamamen "biz formülü böyle seçtik"
mantığına dayanıyor; kriterlerin gerçekten ayırt edici olup olmadığını **veriye
sorarak** doğrulamıyor.

Bir benzetme: Sınav notlarını toplayıp ortalama almak gibi. Doğru ama "hangi ders
notu öğrencileri gerçekten birbirinden ayırıyor?" sorusunu sormaz.

### 1.3 Daha sağlıklı/güvenilir olması için hangi algoritmalar kullanılabilir?

Kriter kalitesini objektif olarak güçlendirmek için klasik 3 yöntem vardır:

| Yöntem | Ne yapar | Neden faydalı |
|--------|----------|---------------|
| **Entropi ağırlıklandırma** | Bir kriter dersler arasında ne kadar *ayrışıyorsa* o kadar çok bilgi taşır kabul eder | Uzman görüşü olmadan, **sadece veriden** objektif ağırlık üretir |
| **CRITIC** | Hem ayrışmayı hem kriterler arası korelasyonu birlikte ele alır | Birbirini tekrar eden kriterleri cezalandırır |
| **Standart sapma yöntemi** | Sadece dağılıma bakar | En basit objektif ölçü |

### 1.4 ✅ Yapılan ekleme: Entropi (objektif) ağırlıklandırma

Bu rapor kapsamında **sisteme eksik olan objektif ağırlıklandırma algoritmasını
ekledim**: `EntropyWeightRanker`.

- **Dosya:** `app/algorithms/mcdm/entropy.py` (yeni)
- **Kayıt:** Benchmark registry'ye `EntropyWeighting` adıyla MCDM grubunda eklendi
  (`app/benchmark/registry.py`).
- **Testler:** `app/tests/unit/test_entropy_weighting.py` (7 test, hepsi geçiyor).

**Ne işe yarar?** AHP'nin ürettiği **öznel** (uzman görüşüne dayalı) ağırlıkların
yanına, **tamamen veriden gelen objektif** bir ağırlık seti koyar. İkisi
çok farklıysa, bu bir uyarıdır: "Uzmanın önemli dediği kriter, veride aslında
dersleri ayırt etmiyor olabilir." Yani AHP'yi **çürütmez, çapraz-kontrol eder.**

**Matematiği (öğrenci dili):**
1. Her kriter sütununu oranlara çevir: `p = değer / sütun_toplamı`
2. Entropiyi (belirsizliği) hesapla: `e = -k · Σ p·ln(p)`
   - Bir kriter tüm derslerde benzerse entropi yüksektir → **az bilgi**.
   - Çok ayrışıyorsa entropi düşüktür → **çok bilgi**.
3. Bilgi çeşitliliği `d = 1 − e`, ağırlık `w = d / Σd`.

Test ile doğrulandı: **tüm derslerde aynı olan (ayırt etmeyen) bir kriter ≈ 0
ağırlık alıyor**, ayırt edici kriter ise yüksek ağırlık alıyor — yani algoritma
doğru davranıyor.

---

## 2. AĞIRLIK → PROFİL → TOPSIS (2. ve 3. aşama)

### 2.1 AHP ile ağırlık üretimi ve profilde saklama

**AHP (Analytic Hierarchy Process)** = kriterleri ikişer ikişer kıyaslayıp
("başarı, popülerlikten kaç kat önemli?") bu kıyaslardan tutarlı ağırlıklar
çıkaran yöntem.

- Varsayılan ağırlıklar (`app/services/ahp_profile_service.py:28`):
  **başarı 0.35, trend 0.25, popülerlik 0.20, anket 0.20** (toplam = 1.00).
- Hesap yöntemi: varsayılan **geometrik ortalama**, alternatif **özvektör**
  (`ahp_calculation_service.py:126-140`). Algoritma sınıfı `AHPRanker` ise
  özvektör (principal eigenvector) kullanır (`app/algorithms/mcdm/ahp.py`).
- **Tutarlılık Oranı (CR):** AHP'nin "kendi içinde çelişti mi?" testi.
  `CR = CI / RI` ve **CR < 0.10 ise tutarlı** kabul edilir
  (`ahp.py:82-83`, Saaty standardı).

**Profil mantığı:** Üretilen ağırlıklar bir **AHP profili** olarak saklanıyor
(versiyon, kapsam, durum). Böylece "2024 Mühendislik Fakültesi" gibi farklı
bağlamlar için farklı ağırlık setleri tutulabiliyor ve karar anında doğru profil
çağrılıyor. Bu, **kararın izlenebilir** olmasını sağlar (hangi ağırlıkla karar
verildi sorusu cevaplanabilir).

### 2.2 TOPSIS ile kesinleşme puanı

**TOPSIS** = her dersi iki hayalî dersle kıyaslar: **ideal ders** (her kriterde
en iyi) ve **en kötü ders** (her kriterde en kötü). Sonra "bu ders ideale ne
kadar yakın, en kötüye ne kadar uzak?" diye bakar.

Akış (`app/algorithms/mcdm/topsis.py:51-62`):
1. Matrisi normalize et (vektör/L2 normu) → kriterler aynı ölçeğe gelir.
2. **AHP profilinden gelen ağırlıklarla** çarp.
3. İdeal (`max`) ve en kötü (`min`) noktaları bul.
4. Her dersin bu iki noktaya uzaklığını ölç.
5. **Yakınlık katsayısı** `CC = d⁻ / (d⁺ + d⁻)` → **0 ile 1 arası**.
6. Sunumda **×100** ile **0–100 kesinleşme puanına** çevrilir
   (`topsis_explainability_service.py`).

Yani: **AHP "neyin önemli olduğunu", TOPSIS "bu derse kaç puan" sorusunu**
cevaplar. AHP ağırlığı, TOPSIS'in 2. adımındaki çarpan olarak akışa girer.

---

## 3. TOPSIS'TEN SONRA NEDEN LR / RF / DT (yani "LF/RF/DF")? (4. aşama)

> Notunuzdaki "lf rf df" kısaltmaları sistemde **LR (Logistic/Linear Regression),
> RF (Random Forest), DT (Decision Tree)** modellerine karşılık gelir
> (`app/services/ml_algorithm_registry_service.py`).

### 3.1 Bu modeller kararı *vermez*, *destekler* — neden?

TOPSIS zaten net bir puan üretiyor. O hâlde ML'e ne gerek var? Çünkü TOPSIS
**bugünkü kriterlere** bakar; **geçmişin örüntüsüne** bakmaz. ML modelleri tam da
bunu yapar: "Geçmiş yıllarda buna benzer derslere ne oldu?" Rolü bu yüzden
**advisory (destekleyici)** olarak işaretlenmiştir, "production_decision" değil.

| Model | Kısaltma | Görevi | Neden seçildi | Rolü |
|-------|----------|--------|---------------|------|
| **Linear Regression** | LR | Sayısal skor/başarı tahmini | Basit, şeffaf, az veride sağlam | Destekleyici |
| **Decision Tree** | DT | Statü sınıflandırma (aç/havuz/iptal) | "Eğer başarı>X ve doluluk>Y ise…" gibi **insan okuyabilir kurallar** üretir | Destekleyici |
| **Random Forest** | RF | Çok ağaçlı topluluk sınıflandırma | Tek ağacın ezberini (overfit) **oylamayla** düzeltir, en dengeli | Destekleyici / üretim adayı |

### 3.2 Her birinin "neden"i — öğrenci diliyle

- **LR (Regresyon):** Doğru/eğri çizip "bu kriterlerle skor kabaca şu olur" der.
  En sade ve **açıklanabilir** model; az veride bile güvenli baz çizgisi.
- **DT (Karar Ağacı):** 20 sorulu oyun gibi: "Doluluk %80'den fazla mı? Evetse
  şu dala git…" Sonuç **şeffaf bir akış şeması**. Tek başına az veride
  **ezberler** (overfit), bu yüzden tek başına üretimde riskli.
- **RF (Rastgele Orman):** Yüzlerce farklı karar ağacı kurar, hepsinin oyunu
  toplar. Bir ağaç yanılsa bile çoğunluk düzeltir → **en kararlı tahmin.**
  Kod, veri büyüklüğüne göre ağaç budamasını otomatik ayarlar
  (`app/algorithms/ml/classifiers.py:235-279`): az veride sığ ağaç, çok veride
  tam kapasite — yani **az veride ezbere karşı koruma** var.

### 3.3 Özet cümle (rapora alınabilir)
> TOPSIS "matematiksel olarak en uygun" dersi seçer; LR/DT/RF ise "geçmiş veriye
> göre bu seçim mantıklı mı?" diye ikinci bir gözle bakar. Bu yüzden bunlar
> **karar veren değil, kararı doğrulayan** katmandır.

---

## 4. BENCHMARK PANELİ ALGORİTMA ENVANTERİ — Eksik var mı?

Sistemde kayıtlı algoritmalar (`app/benchmark/registry.py`):

| Grup | Kayıtlı algoritmalar | Rol |
|------|----------------------|-----|
| **MCDM (karar)** | AHP, TOPSIS, VIKOR, PROMETHEE_II, **+ EntropyWeighting (yeni)** | AHP/TOPSIS üretim; diğerleri kıyas |
| **ML baseline** | RandomPredictor, MajorityClass, PopularityRecommender | Kıyas tabanı |
| **ML** | NaiveBayes, LogisticRegression, RandomForest | Destekleyici |
| **ML ileri** | XGBoostLike (yoksa GradientBoosting) | Kıyas |
| **Kümeleme** | KMeans, Hierarchical, DBSCAN | Desen analizi |
| **Yerleştirme** | GaleShapley, Random, Greedy, FCFS, MinimumRegret | Öğrenci-ders atama |

### 4.1 Eksik / gerekli algoritma değerlendirmesi

| Algoritma | Durum | Kullanılırsa ne değişir? | Kullanılmazsa ne olur? |
|-----------|-------|--------------------------|------------------------|
| **Entropi ağırlık** | ✅ bu raporda eklendi | AHP ağırlıkları objektif veriyle çapraz-kontrol edilir; güven artar | AHP tek başına kalır; "ağırlıklar gerçekten doğru mu?" sorusu cevapsız |
| **CRITIC** | Önerilir (yok) | Birbirini tekrar eden kriterleri ayıklar | Korelasyonlu kriterler çifte ağırlık alabilir |
| **Decision Tree (DT)** | Registry'de tanımlı, sınıf ayrıca eklenebilir | Kararın "şeffaf kural" hâli görülür | RF'nin açıklanması zorlaşır (DT, RF'nin okunabilir hâlidir) |
| **Gradient Boosting** | Var (XGBoost fallback) | Yeterli veri varsa en yüksek doğruluk | Sadece RF ile yetinilebilir |
| **Sıralama doğrulaması (Spearman/Kendall)** | Hibrit serviste var | AHP-TOPSIS vs Entropi vs eşit-ağırlık sıralamaları sayısal kıyaslanır | Modellerin birbirine ne kadar uyduğu ölçülemez |

**Sonuç:** Sistem MCDM tarafında zaten zengindi; **tek belirgin eksik objektif
ağırlıklandırmaydı ve eklendi.** ML tarafında kritik bir boşluk yok; isteğe bağlı
güçlendirme CRITIC ve gerçek XGBoost kurulumudur.

---

## 5. SAYISAL DEĞER DENETİMİ (kullanıcıya gösterilen sayılar doğru mu?)

Kullanıcının sayılarla buluştuğu sayfalar (`app/ui/tabs/`, `app/ui/benchmark/
pages/`) tek tek tarandı. Bulgular ve yapılan düzeltmeler:

### 5.1 ✅ Düzeltilen: Adalet panelinde oranların yüzdesiz gösterimi
- **Yer:** `app/ui/benchmark/pages/allocation_fairness_page.py`
- **Sorun:** "Top-K Memnuniyet" ve "Koltuk Doluluk" değerleri `0.85` gibi
  **ham oran** olarak gösteriliyordu; oysa kullanıcı **%85** bekler. Aynı ekranda
  bazı değerler yüzde, bazıları oran olunca kafa karışıyordu.
- **Düzeltme:** `_fmt_ratio_pct()` yardımcı fonksiyonu eklendi; bu iki kart artık
  `%85` biçiminde gösteriliyor. Sayısal olmayan ("—") değerler korunuyor.

### 5.2 İncelendi — matematiksel olarak doğru bulunanlar
- **TOPSIS kesinleşme puanı** (`topsis_explainability_service.py`): `closeness`
  zaten 0–1 arası, ×100 ile 0–100'e çevriliyor → **doğru**.
- **AHP ağırlık yüzdeleri** (`ahp_weight_page.py`): `w×100` gösterimi, ağırlıklar
  zaten toplamı 1 olacak şekilde normalize edildiği için **doğru**.
- **Veri kapsama skoru** (`data_coverage_service.py`): ağırlıklar
  (0.40+0.20+0.15+0.15+0.05+0.05) **tam 1.00** → **doğru**.
- **CR çubuğu** (`ahp_weight_page.py`): `min(cr/0.20, 1.0)` ile sınırlanıyor;
  metin gerçek CR'yi yazdığı için yanıltıcı değil, ama **iyileştirme önerisi**
  aşağıda.

### 5.3 İyileştirme önerileri (düşük öncelik, davranışı bozmadığı için elle bırakıldı)
- **CR çubuğu:** CR > 0.20 olduğunda çubuk hep %100 doluyor; gerçek değer metinde
  yazsa da görsel olarak 0.20 ile 0.30 ayırt edilemiyor. Öneri: kırmızı "aşırı
  tutarsız" bölgesi eklemek.
- **Güven/oran etiketleri:** "0-1 arası" altyazılı kartlarda değer her zaman
  0–1 olmalı; backend yanlışlıkla yüzde gönderirse koruma yok. Öneri: tek bir
  ortak biçimlendirici kullanmak (adalet panelinde başlatıldı).

### 5.4 Bundan sonra kullanılacak (önerilen) algoritmalar
- **Çapraz-doğrulama (k-fold)** ML skorlarında: tek bölünme yerine k-katlı →
  daha güvenilir doğruluk.
- **Spearman/Kendall sıra korelasyonu** ile AHP-TOPSIS ↔ Entropi sıralamalarının
  uyumunu rapor etmek (hibrit serviste altyapı var).
- **Duyarlılık analizi** (ağırlıkları ±%10 oynatınca sıralama değişiyor mu?) —
  `sensitivity_analysis_service.py` mevcut; karar ekranında öne çıkarılabilir.

---

## 6. PROJEDEKİ "PROBLEM MESAJLARI" — Liste ve Çözümler

"Problem mesajları"nı iki kaynaktan topladım: (a) Ruff statik analiz, (b) Pylance
(VS Code "Problems" panelinin kullandığı `basic` tip kontrolü).

### 6.1 ✅ Çözülen gerçek problemler

| # | Dosya | Problem | Çözüm |
|---|-------|---------|-------|
| 1 | `app/ui/tabs/ahp_weight_page.py.conflict.bak` | Eski merge çakışması artığı dosya | **Silindi** |
| 2 | 20 dosya | Kullanılmayan `import`'lar (F401) | **Otomatik temizlendi** |
| 3 | `pool_recommendation_service.py:82` | `aktif_ids` atanıp hiç kullanılmıyor (ölü kod) | **Kaldırıldı** |
| 4 | `data_collection_priority_service.py:150` | `dept_count` ölü kod | **Kaldırıldı** |
| 5 | `pool_tab.py:518` | `rows` ölü kod | **Kaldırıldı** |
| 6 | `auth_service.py:83` | `== True` (SQLAlchemy'de yanlış idiom) | `.is_(True)` yapıldı |
| 7 | `criteria_page.py` | Tek satıra sıkıştırılmış ifadeler (E701/E702) | Ayrı satırlara bölündü |
| 8 | `data_quality_page.py:557` | `lambda` ataması (E731) | `def` fonksiyona çevrildi |

Bu düzeltmelerden sonra **uygulama kodunda (test dışı) anlamlı stil/ölü-kod
problemi kalmadı**; `python -m compileall` ve 94 birim testi sorunsuz geçiyor.

### 6.2 Bilinçli bırakılanlar (problem değil, tasarım tercihi)
- **E402 (import en üstte değil):** `main.py`, `decision_run_service.py`,
  `api/routes.py` gibi yerlerde importlar bilerek `sys.path` ayarı / gecikmeli
  (lazy) yükleme / döngüsel bağımlılık önleme için aşağıda. Taşımak riskli ve
  gereksiz; bu yüzden dokunulmadı.
- **Test dosyalarındaki küçük stiller** (birkaç noktalı virgül, kullanılmayan
  değişken): davranışı etkilemez; ileride toplu temizlik için bırakıldı.

### 6.3 Pylance (`basic`) tip uyarıları hakkında dürüst not
VS Code "Problems" paneli `typeCheckingMode: basic` ile yaklaşık **490 tip
uyarısı** gösterebilir. Bunların büyük çoğunluğu **gerçek hata değil**, tip
katılığı kaynaklı gürültüdür (ör. `sqlite3.Row` erişimi, `Optional` üyeler,
`Any` dönüşler). Bu projede SQLite satırları ve dinamik sözlükler yoğun
kullanıldığından bu uyarılar beklenen türdendir. **Hepsini "düzeltmek" hem
gerçekçi değil hem de riskli** olurdu (gereksiz `assert`/`cast` kalabalığı). Bu
yüzden bu turda **çalışmayı bozabilecek tip-gürültüsüne dokunulmadı**; gerçek
mantık/ölü-kod problemleri (6.1) hedeflendi ve çözüldü. Tip uyarılarını azaltmak
ileride ayrı, planlı bir iş kalemi olarak ele alınmalıdır (örn. repository
katmanında tiplenmiş veri sınıfları kullanmak).

---

## 7. Yapılan Tüm Değişikliklerin Özeti

**Yeni eklenen:**
- `app/algorithms/mcdm/entropy.py` — Entropi objektif ağırlıklandırma algoritması.
- `app/tests/unit/test_entropy_weighting.py` — 7 birim testi (hepsi geçiyor).
- Bu rapor.

**Değiştirilen:**
- `app/algorithms/mcdm/__init__.py`, `app/benchmark/registry.py` — Entropi kaydı.
- `app/ui/benchmark/pages/allocation_fairness_page.py` — oran→yüzde gösterimi.
- `auth_service.py`, `data_collection_priority_service.py`, `pool_tab.py`,
  `pool_recommendation_service.py`, `criteria_page.py`, `data_quality_page.py` —
  ölü kod / stil düzeltmeleri.
- 20 dosyada kullanılmayan import temizliği.

**Silinen:**
- `app/ui/tabs/ahp_weight_page.py.conflict.bak` — eski çakışma artığı.

**Doğrulama:** `python -m compileall app` temiz; ilgili birim testleri (TOPSIS,
Entropi ve diğer unit testler — toplam 94 test) **PASS**.

---

### Tek paragrafta kapanış
Sistem kriterleri **kural/aritmetik** ile üretiyordu; bunu objektif olarak
denetlemek için **Entropi ağırlıklandırma** eklendi. **AHP** kriter önemini,
**TOPSIS** ders puanını üretir; **LR/DT/RF** ise kararı vermez, geçmiş veriyle
**doğrular**. Kullanıcıya gösterilen sayılar büyük oranda doğruydu; adalet
panelindeki oran/yüzde tutarsızlığı düzeltildi. Projedeki gerçek problem
mesajları (ölü kod, çakışma artığı, hatalı idiom, kullanılmayan importlar)
temizlendi; tip-katılığı kaynaklı gürültü ise bilinçli olarak ayrı bir iş kalemi
olarak işaretlendi.
