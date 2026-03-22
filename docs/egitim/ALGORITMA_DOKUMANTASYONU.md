# Adil Secmeli Ders Asistani — Algoritma Dokumantasyonu

> **Hedef Kitle:** Bu dokuman, projedeki algoritmalari anlamak isteyen ogrenciler icin hazirlanmistir.
> Her algoritma once teorik olarak, sonra projede nasil kodlandigini gostererek anlatilmistir.

---

## Icindekiler

1. [Projenin Genel Yapisi](#1-projenin-genel-yapisi)
2. [AHP — Analitik Hiyerarsi Prosesi](#2-ahp--analitik-hiyerarsi-prosesi)
3. [TOPSIS — Ideal Cozume Yakinlik Siralamasi](#3-topsis--ideal-cozume-yakinlik-siralamasi)
4. [Trend Analizi ve Lineer Regresyon](#4-trend-analizi-ve-lineer-regresyon)
5. [Random Forest — Kesinlesme Puani Tahmini](#5-random-forest--kesinlesme-puani-tahmini)
6. [Decision Tree — Statu Tahmini](#6-decision-tree--statu-tahmini)
7. [Havuz Durum Makinesi (State Machine)](#7-havuz-durum-makinesi-state-machine)
8. [NLP — Ders Benzerlik Motoru](#8-nlp--ders-benzerlik-motoru)
9. [Kurallar Motoru (Rules Engine)](#9-kurallar-motoru-rules-engine)
10. [Mufredat Uretim Pipeline'i](#10-mufredat-uretim-pipelinei)
11. [Algoritmalarin Birlikte Calismasi](#11-algoritmalarin-birlikte-calismasi)

---

## 1. Projenin Genel Yapisi

Bu proje, universitelerdeki **secmeli derslerin adil ve veriye dayali olarak mufredatta kalip kalmayacagina** karar veren bir karar destek sistemidir.

### Karar Sureci Ozeti

```
Ders Verileri (performans, populerlik, anket)
        |
        v
   [AHP] --> Kriter agirliklari belirlenir
        |
        v
  [TOPSIS] --> Her derse 0-100 arasi "Kesinlesme Puani" verilir
        |
        v
  [Trend/LR] --> Gecmis yillardan gelecek basari orani tahmin edilir
        |
        v
  [RF + DT] --> Makine ogrenmesi ile puan ve statu tahmini
        |
        v
  [State Machine] --> Havuz statusu guncellenir (mufredatta/havuzda/dinlenmede/iptal)
        |
        v
  Yeni Mufredat Olusturulur
```

### Dosya Yapisi

| Dosya | Gorev |
|-------|-------|
| `app/services/calculation.py` | AHP, TOPSIS, mufredat uretimi |
| `app/services/ai_engine.py` | Lineer Regresyon, Random Forest, Decision Tree |
| `app/services/course_analyzer.py` | Tek ders detayli analiz servisi |
| `app/services/havuz_karar.py` | State Machine (durum makinesi) |
| `app/services/similarity.py` | NLP benzerlik motoru |
| `app/services/rules_engine.py` | Ogrenci bazli kural kontrolu |

---

## 2. AHP — Analitik Hiyerarsi Prosesi

### Teori

AHP, Thomas Saaty tarafindan gelistirilmis bir **cok kriterli karar verme** yontemidir. Temel fikir sudur: "Birden fazla kritere gore karar verirken, her kriterin ne kadar onemli oldugunu sistematik olarak belirle."

Bu projede 4 kriter vardir:

| Kriter | Aciklama |
|--------|----------|
| **Basari** | Dersi gecen ogrenci orani (gecen / toplam) |
| **Trend** | Son 3 yilin agirlikli basari ortalamasi |
| **Populerlik** | Dersin doluluk orani (kayitli / kontenjan) |
| **Anket** | Ogrenci anket tercih orani |

### AHP Nasil Calisir?

**Adim 1: Ikili Karsilastirma Matrisi Olustur**

Karar verici, kriterleri birbiriyle karsilastirir. Ornegin "Basari, Trend'den 2 kat onemli" denir:

```
         Basari  Trend  Populerlik  Anket
Basari   [1,     2,     4,          5    ]
Trend    [0.5,   1,     3,          4    ]
Populerlik[0.25, 0.33,  1,          2    ]
Anket    [0.20,  0.25,  0.50,       1    ]
```

> **Okuma Kilavuzu:** Matrisin i. satir j. sutun degeri "i. kriter, j. kriterden kac kat onemli?" sorusunun cevabi.
> Ornegin matris[0][1] = 2 demek "Basari, Trend'den 2 kat onemli" demek.
> Matris[1][0] = 0.5 ise bunun tersi: "Trend, Basari'nin yarisinda onemli."

**Adim 2: Normalizasyon ve Agirlik Hesabi**

Her sutunun toplami hesaplanir, sonra her hucre kendi sutun toplamina bolunur (normalizasyon). Her satirin ortalamasi o kriterin agirligini verir.

**Adim 3: Tutarlilik Kontrolu (CR)**

Karsilastirmalar tutarli mi? Ornegin "A > B ve B > C ise A > C olmali" gibi. CR < 0.10 ise tutarlidir.

### Projedeki Kod

**Dosya:** `app/services/calculation.py`, `KararMotoru` sinifi

```python
class KararMotoru:
    def ahp_calistir(self):
        # 4 kriter: basari, trend, populerlik, anket
        matris = [
            [1,    2,    4,    5],      # Basari satirı
            [0.5,  1,    3,    4],      # Trend satirı
            [0.25, 0.33, 1,    2],      # Populerlik satirı
            [0.20, 0.25, 0.50, 1]       # Anket satirı
        ]

        # Adım 1: Her sutunun toplamini hesapla
        sutun_top = [sum(col) for col in zip(*matris)]
        # Ornek: sutun_top[0] = 1 + 0.5 + 0.25 + 0.20 = 1.95

        # Adım 2: Her hucreyi kendi sutun toplamina bol, satirlarin ortalamasini al
        agirliklar = [
            sum([(r[i] / (sutun_top[i] or 1)) for i in range(4)]) / 4
            for r in matris
        ]

        # Adım 3: Agirliklari normalize et (toplam = 1.0)
        s = sum(agirliklar) or 1.0
        agirliklar = [a / s for a in agirliklar]
        return agirliklar
        # Tipik sonuc: [0.4935, 0.3116, 0.1296, 0.0654]
        # Yani: Basari %49, Trend %31, Populerlik %13, Anket %7
```

> **Ne Anlama Geliyor?** Sonuc diyor ki:
> - Basari en onemli kriter (%49 agirlik)
> - Trend (gecmis yillarin gidisati) ikinci (%31)
> - Populerlik ucuncu (%13)
> - Anket en az etkili (%7)

### Tutarlilik Kontrolu (CR) Kodu

```python
def ahp_tutarlilik_kontrolu(self, matris=None, agirliklar=None):
    n = len(matris)  # 4

    # Matris × Agirlik vektoru = Agirlikli toplam
    weighted_sum = [
        sum(matris[i][j] * agirliklar[j] for j in range(n))
        for i in range(n)
    ]

    # Lambda degerleri: agirlikli_toplam / agirlik
    lambda_vals = [weighted_sum[i] / agirliklar[i] for i in range(n)]

    # Lambda_max: ortalamalari
    lambda_max = sum(lambda_vals) / n

    # Tutarlilik Indeksi (CI)
    ci = (lambda_max - n) / (n - 1)

    # Tutarlilik Orani (CR) = CI / RI
    # RI_4 = 0.90 (4 kriter icin sabit tablo degeri)
    cr = ci / RI_4

    # CR < 0.10 ise matris tutarlidir
    return cr, cr < 0.10, lambda_max
```

> **RI Nedir?** Random Index — rastgele olusturulmus matrislerin ortalama CI degeri. 4 kriter icin 0.90'dir. Bu sabit deger literaturden gelir.

---

## 3. TOPSIS — Ideal Cozume Yakinlik Siralamasi

### Teori

TOPSIS (Technique for Order Preference by Similarity to Ideal Solution), alternatifleri **en iyi duruma en yakin, en kotu duruma en uzak** olacak sekilde siralar.

Ornek: 5 ders var. Hangi ders "en iyi"? Her dersin basari, trend, populerlik ve anket degerleri var. TOPSIS butun bu kriterleri tek bir skora donusturur.

### TOPSIS Nasil Calisir?

```
Adim 1: Karar matrisini normalize et (vektor normalizasyonu)
Adim 2: AHP agirliklarini uygula
Adim 3: Pozitif ideal (en iyi) ve negatif ideal (en kotu) cozumleri bul
Adim 4: Her alternatifin ideal cozumlere Oklid uzakligini hesapla
Adim 5: Yakinlik katsayisi hesapla → 0 ile 1 arasi skor
```

### Projedeki Kod

**Dosya:** `app/services/calculation.py`, `KararMotoru.topsis_calistir()`

```python
def topsis_calistir(self, df, agirliklar):
    sutunlar = ["basari", "trend", "populerlik", "anket"]
    w = [float(a) / sum(agirliklar) for a in agirliklar]  # Normalize agirliklar

    # ---------------------------------------------------------------
    # ADIM 1: Vektor Normalizasyonu
    # ---------------------------------------------------------------
    # Her sutun icin: r_ij = x_ij / sqrt(SUM(x_ij^2))
    #
    # Neden? Farkli birimleri (oran, puan, yuzde) ortak olcege getirmek.
    sqrt_sums = {}
    for c in sutunlar:
        sq = sum(float(x) ** 2 for x in df[c].fillna(0))
        sqrt_sums[c] = math.sqrt(sq) if sq > 1e-10 else 1.0

    R = df.copy()
    for c in sutunlar:
        R[c] = df[c].fillna(0).apply(lambda x: float(x) / sqrt_sums[c])

    # ---------------------------------------------------------------
    # ADIM 2: Agirlikli Normalize Matris
    # ---------------------------------------------------------------
    # V_ij = w_j * r_ij
    # AHP'den gelen agirliklar burada devreye girer.
    V = pd.DataFrame()
    for i, c in enumerate(sutunlar):
        V[c] = R[c] * w[i]

    # ---------------------------------------------------------------
    # ADIM 3: Ideal Cozumler
    # ---------------------------------------------------------------
    # Pozitif ideal (A+): Her sutunun MAKSIMUM degeri
    # Negatif ideal (A-): Her sutunun MINIMUM degeri
    A_plus  = {c: V[c].max() for c in sutunlar}
    A_minus = {c: V[c].min() for c in sutunlar}

    # ---------------------------------------------------------------
    # ADIM 4-5: Uzakliklar ve Yakinlik Katsayisi
    # ---------------------------------------------------------------
    sonuclar = []
    for i, (idx, row) in enumerate(df.iterrows()):
        v_row = V.iloc[i]

        # S+ : Pozitif ideale uzaklik (dusuk iyi)
        s_plus = math.sqrt(
            sum((v_row[c] - A_plus[c]) ** 2 for c in sutunlar)
        )

        # S- : Negatif ideale uzaklik (yuksek iyi)
        s_minus = math.sqrt(
            sum((v_row[c] - A_minus[c]) ** 2 for c in sutunlar)
        )

        # Yakinlik Katsayisi: CI = S- / (S+ + S-)
        # 1.0'a yakin = cok iyi, 0.0'a yakin = cok kotu
        ci = s_minus / (s_plus + s_minus)

        # 0-100 arasina olcekle
        skor_100 = ci * 100

        sonuclar.append({
            "ders_id": int(row["ders_id"]),
            "AHP_TOPSIS_Skor": round(ci, 6),       # 0-1 arasi
            "Kesinlesme_Puani": round(skor_100, 2), # 0-100 arasi
            "S+": round(s_plus, 6),
            "S-": round(s_minus, 6),
        })

    # En yuksek skordan en dusuge sirala
    df_sonuc = pd.DataFrame(sonuclar).sort_values(
        by="AHP_TOPSIS_Skor", ascending=False
    )
    return df_sonuc, meta
```

### Somut Ornek

Diyelim 3 ders var:

| Ders | Basari | Trend | Populerlik | Anket |
|------|--------|-------|------------|-------|
| A    | 0.85   | 0.80  | 0.70       | 0.60  |
| B    | 0.60   | 0.55  | 0.90       | 0.80  |
| C    | 0.40   | 0.35  | 0.30       | 0.20  |

AHP agirliklari: [0.49, 0.31, 0.13, 0.07]

1. **Normalizasyon:** Her sutunu sqrt(toplamkare) ile bol
2. **Agirliklandirma:** Normalize degerleri agirliklarla carp
3. **Ideal cozum:** Her sutunun max'i (A+) ve min'i (A-)
4. **Uzakliklar:** Her dersin A+'ya ve A-'ya Oklid uzakligi
5. **Sonuc:** A dersi en yuksek CI alir → mufredatta kalir; C dersi en dusuk → mufredattan duser

> **Onemli:** Sadece **mufredattaki dersler** TOPSIS pipeline'ina girer. Havuzdaki (mufredat disi) dersler yalnizca anket bazli sabit puanlanir: `skor = 50 + (anket - 0.5) * 20`

---

## 4. Trend Analizi ve Lineer Regresyon

### Teori

Bir dersin **gecmis yillardaki basari oranlarina bakarak gelecek yili tahmin** eder. Iki yontem kullanilir:

1. **Agirlikli Ortalama (Weighted Average):** Yeterli veri yoksa (< 3 yil)
2. **sklearn LinearRegression:** 3+ yil veri varsa, en kucuk kareler yontemiyle dogru uydurma

### Projede Nasil Calisir?

**Dosya:** `app/services/course_analyzer.py`, `_run_trend_lr()`

#### Yontem 1: Agirlikli Ortalama

```python
def gecmis_trend_hesapla(self, gecmis_list):
    # gecmis_list: [{"yil": 2024, "oran": 0.85}, {"yil": 2023, "oran": 0.70}, ...]
    # En yeni yil en yuksek agirligi alir

    agirlik_sirasi = [0.50, 0.30, 0.20]
    # 2024'un basarisi %50 agirlik
    # 2023'un basarisi %30 agirlik
    # 2022'nin basarisi %20 agirlik

    toplam_puan = 0.0
    toplam_agirlik = 0.0

    for i, item in enumerate(gecmis_list):
        agirlik = agirlik_sirasi[i] if i < len(agirlik_sirasi) else 0.0
        oran = float(item.get("oran", 0))
        toplam_puan += oran * agirlik
        toplam_agirlik += agirlik

    trend = toplam_puan / toplam_agirlik
    return trend
```

**Ornek Hesaplama:**

| Yil  | Basari Orani | Agirlik |
|------|-------------|---------|
| 2024 | %85         | 0.50    |
| 2023 | %70         | 0.30    |
| 2022 | %60         | 0.20    |

`trend = (0.85 × 0.50 + 0.70 × 0.30 + 0.60 × 0.20) / (0.50 + 0.30 + 0.20)`
`trend = (0.425 + 0.210 + 0.120) / 1.0 = 0.755 → %75.5`

#### Yontem 2: sklearn LinearRegression (3+ yil veri varsa)

```python
if len(gecmis_list) >= 3:
    from sklearn.linear_model import LinearRegression
    import numpy as np

    # X: yillar, Y: basari oranlari
    years = np.array([g["yil"] for g in gecmis_list]).reshape(-1, 1)
    rates = np.array([g["oran"] for g in gecmis_list])

    # Model egit
    lr = LinearRegression()
    lr.fit(years, rates)

    # Gelecek yili tahmin et
    next_year = max(g["yil"] for g in gecmis_list) + 1
    lr_pred = float(np.clip(lr.predict([[next_year]])[0], 0, 1))

    # Egim (coefficient) yonu gosterir
    coef = float(lr.coef_[0])
    # coef > 0.005  → yukselis trendi
    # coef < -0.005 → dusus trendi
    # aradaki       → stabil
```

> **LinearRegression Ne Yapar?** Yil-basari verisine bir dogru (y = mx + b) uydurur.
> `coef` (egim/m) pozitifse basari yillara gore yukseliyor, negatifse dusuyor.
> Bu dogruyu bir sonraki yila uzatarak tahmin yapar.

---

## 5. Random Forest — Kesinlesme Puani Tahmini

### Teori

Random Forest, **birden fazla karar agacinin bir araya gelmesiyle** olusan bir topluluk (ensemble) ogrenmesi yontemidir.

- Her agac, verinin rastgele bir alt kumesinden ogrenilir
- Tahmin yapilirken tum agaclarin sonuclari birlestirilir (ortalama/oylama)
- Tek bir agaca gore cok daha **kararlı** (robust) sonuc verir

Bu projede RF, bir dersin **0-100 arasi kesinlesme puanini** tahmin eder.

### Kullanilan Ozellikler (Features)

| Ozellik | Aciklama |
|---------|----------|
| `basari_orani` | Dersi gecen ogrenci orani (0-1) |
| `ortalama_not` | Ortalama gecme notu (0-100) |
| `doluluk_orani` | Kontenjan doluluk orani (0-1) |
| `anket_orani` | Anket tercih orani (0-1) |
| `trend` | Son 3 yilin hareketli ortalamasi |
| `sayac` | Mufredattan dusme sayaci (0, 1, 2) |

### Projedeki Kod

**Dosya:** `app/services/ai_engine.py`, `HavuzAIEngine` sinifi

```python
class HavuzAIEngine:
    def train(self, fakulte_id=None):
        df = self._load_training_data(fakulte_id=fakulte_id)
        # Minimum 10 satir egitim verisi gerekli
        if len(df) < MIN_SAMPLES_SKLEARN:
            return False

        feat = self._feature_cols()
        X = df[feat].values              # Ozellik matrisi (N x 6)
        y_skor = np.clip(df["skor"].values, 0, 100)  # Hedef: kesinlesme puani

        # Random Forest Regressor (surekli deger tahmini)
        self.model_rf = RandomForestRegressor(
            n_estimators=100,   # 100 karar agaci olustur
            max_depth=8,        # Her agacin maksimum derinligi 8
            random_state=42,    # Tekrarlanabilirlik icin sabit seed
        )
        self.model_rf.fit(X, y_skor)
        return True

    def predict_kesinlesme(self, features: dict) -> float:
        """Yeni bir ders icin kesinlesme puani tahmin et"""
        X = self._dict_to_X(features)
        return float(np.clip(self.model_rf.predict(X)[0], 0, 100))
```

### Egitim Verisinin Kaynagi

```python
def _load_training_data(self, fakulte_id=None):
    # havuz + performans + populerlik + ders_kriterleri tablolari
    # JOIN ile birlestirilir
    q = text("""
        SELECT
            h.statu, h.sayac, h.skor,
            p.basari_orani, p.ortalama_not,
            pop.doluluk_orani,
            -- Anket orani hesapla
            CASE WHEN dk.anket_katilimci > 0
                 THEN dk.anket_dersi_secen / dk.anket_katilimci
                 ELSE 0.5 END AS anket_orani
        FROM havuz h
        LEFT JOIN performans p ON ...
        LEFT JOIN populerlik pop ON ...
        LEFT JOIN ders_kriterleri dk ON ...
    """)

    # Trend hesabi: Son 3 yilin hareketli ortalamasi
    df["trend"] = (
        df.sort_values("yil")
        .groupby("ders_id")["basari_orani"]
        .transform(lambda x: x.rolling(3, min_periods=1).mean())
    )
```

### K-Fold Cross-Validation

Modelin gercek performansini olcmek icin K-Fold kullanilir:

```python
def run_kfold(self, algorithm_type="rf", k=5):
    cv = KFold(n_splits=k, shuffle=True, random_state=42)

    model = RandomForestRegressor(n_estimators=100, max_depth=8)
    scores = cross_val_score(model, X, y, cv=cv,
                             scoring="neg_mean_absolute_error")
    mae = -scores.mean()
    # MAE: Ortalama Mutlak Hata — dusuk olması iyi

    # Ozellik onemliligi (feature importance)
    model.fit(X, y)
    importances = list(zip(feat_names, model.feature_importances_))
    # Hangi ozellik tahmin icin en onemli? (basari_orani genelde 1.)
```

> **K-Fold Ne Yapar?** Veriyi K parcaya boler. Her seferinde K-1 parcayla egitir, kalan 1 parcayla test eder.
> Bu islemi K kez tekrarlar. Sonuc: Modelin "gercek dunyada" ne kadar iyi calistiginin guvenilir olcusu.

### Kural Tabanli Fallback

Egitim verisi yetersiz oldugunda (< 10 satir), sklearn yerine kural tabanli tahmin devreye girer:

```python
# course_analyzer.py'den:
if basari >= 0.70 and doluluk >= 0.50:
    pred_statu = STATU_MUFREDATTA     # Yuksek basari + yuksek doluluk
elif basari >= 0.40 and doluluk >= 0.30:
    pred_statu = STATU_MUFREDATTA     # Yeterli
elif basari < 0.40:
    pred_statu = STATU_DINLENMEDE     # Dusuk basari
else:
    pred_statu = STATU_HAVUZDA        # Orta duzey
```

---

## 6. Decision Tree — Statu Tahmini

### Teori

Karar Agaci, verideki oruntuleri bularak **if-else benzeri kurallar** olusturur. Insanlar icin anlasilmasi en kolay ML modelidir.

Bu projede DT, dersin gelecek yilki **statusunu** tahmin eder:
- `1`: Mufredatta kalacak
- `0`: Havuzda bekleyecek
- `-1`: Dinlenmede
- `-2`: Kalici iptal

### Projedeki Kod

```python
# ai_engine.py'den:
self.model_dt = DecisionTreeClassifier(
    max_depth=5,       # Agacin derinligi (asiri uyumu onler)
    random_state=42,
)
# X: 6 ozellik matrisi
# y_statu: her kaydin statu degeri (1, 0, -1, -2)
self.model_dt.fit(X, y_statu)

def predict_statu(self, features: dict) -> int:
    X = self._dict_to_X(features)
    return int(self.model_dt.predict(X)[0])
```

### Ozellik Onemliligi

K-Fold calistirildiktan sonra her ozelligin tahmindeki etkisi olculur:

```python
importances = list(zip(feat_names, model.feature_importances_))
# Ornek cikti:
#   basari_orani       : 0.45  ###############
#   doluluk_orani      : 0.22  #######
#   ortalama_not       : 0.15  #####
#   trend              : 0.10  ###
#   anket_orani        : 0.05  ##
#   sayac              : 0.03  #
```

> **max_depth=5 Neden?** Agac cok derinlesse egitim verisini "ezberler" (overfitting).
> Sınırlı derinlik, modelin genellesme yetenegini arttirir.

---

## 7. Havuz Durum Makinesi (State Machine)

### Teori

Her dersin havuzdaki durumu yildan yila bir "durum makinesi" ile takip edilir. Bu, belirsizligi ortadan kaldiran ve tutarli kurallar koyan bir yapidir.

### Durumlar

| Statu | Deger | Aciklama |
|-------|-------|----------|
| **Mufredatta** | `1` | Ders aktif olarak mufredatta |
| **Havuzda** | `0` | Mufredata aday, bekliyor |
| **Dinlenmede** | `-1` | Mufredattan dustu, 1 yil ceza |
| **Kalici Iptal** | `-2` | 2 kez dustukten sonra kalici iptal |

### Gecis Kurallari (Durum Diyagrami)

```
                    +-----------+
          secildi   |           |   secilmedi (1. dusme)
    +-------------->| MUFREDATTA|------------------+
    |               |   (1)     |                  |
    |               +-----------+                  v
    |                     ^                  +------------+
    |                     |  secildi         | DINLENMEDE |
    |                     |                  |   (-1)     |
    |               +-----------+            +-----+------+
    |               |           |                  |
    +---------------+  HAVUZDA  |<----- 1 yil ----+
                    |   (0)     |     ceza doldu
                    +-----------+
                                                   |
                                             2. dusme (sayac >= 2)
                                                   v
                                            +-----------+
                                            |   IPTAL   |
                                            |   (-2)    |
                                            +-----------+
```

### Projedeki Kod

**Dosya:** `app/services/havuz_karar.py`

```python
STATU_MUFREDATTA = 1
STATU_HAVUZDA    = 0
STATU_DINLENMEDE = -1
STATU_IPTAL      = -2
MAKS_DUSME_SAYACI = 2

def calculate_next_status(prev_statu, prev_sayac, in_mufredat_this_year):
    """
    Onceki yilin durumuna gore yeni yilin durumunu belirler.

    Parametreler:
        prev_statu: Onceki yilin statusu (1, 0, -1, -2)
        prev_sayac: Onceki yilin dusme sayaci
        in_mufredat_this_year: Bu yil mufredata secildi mi?

    Donus: (yeni_statu, yeni_sayac)
    """

    # KURAL 1: Kalici iptal degismez
    if prev_statu == STATU_IPTAL:
        return STATU_IPTAL, prev_sayac
        # Bir kez -2 olduysa sonsuza kadar -2

    # KURAL 2: Dinlenmede → 1 yil ceza bitti → Havuza don
    if prev_statu == STATU_DINLENMEDE:
        return STATU_HAVUZDA, prev_sayac
        # Secilse bile bu yil alinamaz, sadece havuza doner

    # KURAL 3: Onceki yil mufredattaydi
    if prev_statu == STATU_MUFREDATTA:
        if in_mufredat_this_year:
            return STATU_MUFREDATTA, prev_sayac  # Mufredatta kaliyor
        else:
            yeni_sayac = prev_sayac + 1           # Dustu! Sayac artar
            if yeni_sayac >= MAKS_DUSME_SAYACI:
                return STATU_IPTAL, yeni_sayac    # 2. dusme → Kalici iptal
            return STATU_DINLENMEDE, yeni_sayac   # 1. dusme → 1 yil ceza

    # KURAL 4: Onceki yil havuzdaydi
    if prev_statu == STATU_HAVUZDA:
        if in_mufredat_this_year:
            return STATU_MUFREDATTA, prev_sayac   # Mufredata girdi
        else:
            return STATU_HAVUZDA, prev_sayac      # Havuzda kaldi

    # Bilinmeyen deger → guvenli varsayilan
    return STATU_HAVUZDA, prev_sayac
```

### Ornek Senaryo

| Yil | Statu | Sayac | Olay |
|-----|-------|-------|------|
| 2022 | 1 (Mufredatta) | 0 | Baslangic (ground truth) |
| 2023 | -1 (Dinlenmede) | 1 | TOPSIS puani dusuk → mufredat disi → 1. dusme |
| 2024 | 0 (Havuzda) | 1 | Ceza doldu, havuza dondu |
| 2025 | 1 (Mufredatta) | 1 | Yeniden secildi, mufredata girdi |

> **Kritik Kural:** Sayac SADECE `statu=1` (mufredatta) iken mufredat disi kaldiginda artar. Havuzda veya dinlemedeyken sayac HIC artmaz.

---

## 8. NLP — Ders Benzerlik Motoru

### Teori

Dogal Dil Isleme (NLP) ile derslerin **icerik aciklamalari** arasindaki benzerlik hesaplanir. Bu, "Nesne Yonelimli Programlama" dersinin "Yazilim Muhendisligi" dersine benzedigini otomatik olarak bulmak icin kullanilir.

**Yontem: TF-IDF + Cosine Similarity**

1. **TF-IDF (Term Frequency - Inverse Document Frequency):**
   - Her kelimenin bir ders icin ne kadar onemli oldugunu hesaplar
   - Cok gecen ama her yerde olan kelimeler (ve, ile, icin) dusuk agirlik alir
   - Nadir ama anlamli kelimeler (algoritma, veritabani, nesne) yuksek agirlik alir

2. **Cosine Similarity:**
   - Iki TF-IDF vektoru arasindaki aciyi olcer
   - 1.0 = ayni icerik, 0.0 = tamamen farkli

### Projedeki Kod

**Dosya:** `app/services/similarity.py`

```python
# Turkce stop-words (anlamsiz kelimeleri filtrele)
TURKCE_STOP_WORDS = {
    "ve", "veya", "ile", "için", "bir", "bu", "şu", "o",
    "da", "de", "olarak", "gibi", "kadar", ...
}

class SimilarityEngine:
    def get_related_courses(self, target_course_id, top_n=10):
        # 1. Tum dersleri ve iceriklerini cek
        dersler = self.db.query(Ders.ders_id, Ders.ad, Ders.bilgi).all()
        df = pd.DataFrame(dersler, columns=['id', 'ad', 'icerik'])

        # 2. Stop-words temizle
        def _remove_stopwords(text):
            words = text.lower().split()
            return " ".join(
                w for w in words
                if w not in TURKCE_STOP_WORDS and len(w) > 1
            )
        df['icerik'] = df['icerik'].apply(_remove_stopwords)

        # 3. TF-IDF matrisini olustur
        tfidf = TfidfVectorizer(
            max_features=500,              # En onemli 500 kelime
            stop_words=list(TURKCE_STOP_WORDS)
        )
        tfidf_matrix = tfidf.fit_transform(df['icerik'])
        # Sonuc: Her ders bir vektor (500 boyutlu)

        # 4. Cosine Similarity hesapla
        cosine_sim = cosine_similarity(
            tfidf_matrix[target_index],    # Hedef dersin vektoru
            tfidf_matrix                   # Tum derslerin vektorleri
        )

        # 5. En benzer top_n dersi sirala
        similarity_scores = list(enumerate(cosine_sim[0]))
        sorted_scores = sorted(
            similarity_scores,
            key=lambda x: x[1],
            reverse=True
        )[1:top_n+1]  # Kendisini cikar (1.0 skor)

        # 6. Sadece anlamli iliskileri dondur (> %10 benzerlik)
        for i, score in sorted_scores:
            if score > 0.1:
                results.append({"ders": df.iloc[i]['ad'], "skor": score})

        return results, graph_data
```

### Ornek Cikti

```
Hedef Ders: "Nesne Yonelimli Programlama"

Benzer Dersler:
  1. Yazilim Muhendisligi     → 0.72 (%72 benzerlik)
  2. Java Programlama         → 0.65 (%65)
  3. Tasarim Oruntuleri       → 0.58 (%58)
  4. Veritabani Yonetimi      → 0.31 (%31)
  5. Web Programlama          → 0.28 (%28)
```

---

## 9. Kurallar Motoru (Rules Engine)

### Aciklama

Ogrenci bazinda ders secim uygunlugu kontrol eden kural tabanli bir sistemdir. ML kullanimaz; is kurallari dogrudan kodlanmistir.

**Dosya:** `app/services/rules_engine.py`

### 3 Kural

```python
def is_course_eligible_for_student(ogrenci_id, ders_id, secilen_dersler, db):

    # KURAL 1: Engel Kontrolu
    # Ogrenci bu dersten daha once kalmis mi?
    rows = db.run_sql(
        "SELECT failed_before FROM kayit WHERE ogr_id=? AND ders_id=?",
        (ogrenci_id, ders_id)
    )
    if rows and failed_before == True:
        return False, "Ogrenci bu dersten daha once kalmis"

    # KURAL 2: Kontenjan Kontrolu
    # Dersin kontenjani dolu mu?
    kont_rows = db.run_sql("""
        SELECT kontenjan, talep_sayisi
        FROM populerlik WHERE ders_id=? AND akademik_yil=?
    """)
    if kayitli >= kontenjan:
        return False, "Kontenjan dolu"

    # KURAL 3: Cakisma Kontrolu
    # Secilen derslerle saat cakismasi var mi?
    cakisanlar = ders_cakisma_kontrolu(tum_liste)
    if cakisma_var:
        return False, "Gun/saat cakismasi"

    return True, "OK"
```

### Cakisma Kontrolu Algoritmasi

```python
def ders_cakisma_kontrolu(ders_listesi):
    # Her ders cifti icin:
    for i in range(len(ders_listesi)):
        for j in range(i + 1, len(ders_listesi)):
            d1, d2 = ders_listesi[i], ders_listesi[j]

            # Ayni gun mu?
            if gun1 != gun2:
                continue  # Farkli gun → cakisma yok

            # Saat cakismasi: [bas1, bit1] ile [bas2, bit2] kesisiyor mu?
            # Cakisma YOKSA: bit1 <= bas2 VEYA bit2 <= bas1
            # Cakisma VARSA: bunun tersi
            cakisma = not (bit1 <= bas2 or bit2 <= bas1)
```

---

## 10. Mufredat Uretim Pipeline'i

### Genel Akis

Bu, tum algoritmalarin bir arada calistigi ana pipeline'dir.

**Dosya:** `app/services/calculation.py`, `generate_next_year_curricula()`

```
2022 (Ground Truth — Baz yil)
    |
    v
[1] Her bolumun mevcut mufredatini oku
    |
    v
[2] Tum aday dersler icin TOPSIS skorlari hesapla
    |
    v
[3] Her ders icin: Skor < 40 VEYA ortalama_not < 45?
    |                     |
    |  Evet: DUSER        |  Hayir: KALIR
    v                     v
[4] Dusen dersin yerine havuzdan en yuksek puanli aday sec
    |
    v
[5] Yeni mufredat olustur ve kaydet
    |
    v
[6] Havuz statu/sayac guncelle (State Machine)
    |
    v
Sonraki yil (2023 → 2024 → 2025 → ...)
```

### Koddan Kritik Parcalar

#### Dusme Karari

```python
# Barajlar
DROP_SCORE_THRESHOLD = 40.0          # Kesinlesme puani baraj
DROP_AVERAGE_GRADE_THRESHOLD = 45.0  # Ortalama not baraj

def should_drop_course(score_100, average_grade):
    reasons = []
    if score_100 < 40.0:
        reasons.append("Kesinlesme puani 40 altinda")
    if average_grade < 45.0:
        reasons.append("Gecme not ortalamasi 45 altinda")
    return len(reasons) > 0, reasons
```

#### Yeni Aday Secimi

```python
# Dusme oldugunda yeni ders secim onceligi:
# 1. Ayni bolumden, en yuksek kesinlesme puanli
# 2. Bolumde aday yoksa, fakulte genelinden en yuksek puanli
# 3. Hala yetmezse, dusen derslerden en iyileri geri eklenir (kontenjan korunumu)

bolum_ici = [d for d in adaylar if d.bolum_id == mevcut_bolum_id]
fakulte_geneli = [d for d in adaylar if d not in bolum_ici]

for d_id in bolum_ici + fakulte_geneli:
    if len(yeni) >= hedef_adet:
        break
    yeni.append(d_id)
```

#### Zincirleme Uretim

```python
def rebuild_school_curricula(db_path, base_year=2022):
    # Adim 1: 2022 sonrasi her seyi sil (temiz sayfa)
    reset_future_curricula(db_path, base_year=2022)

    # Adim 2: Zincirleme uret (2022→2023, 2023→2024, 2024→2025, ...)
    # Ayni cift tekrar edilmeye basladiginda dur (denge noktasi)
    generate_curricula_until_stable(db_path, max_rounds=8)
```

---

## 11. Algoritmalarin Birlikte Calismasi

### Tek Ders Analiz Akisi

**Dosya:** `app/services/course_analyzer.py`, `analyze_single_course()`

Bu fonksiyon tum algoritmalari sirayla cagirip birlestirir:

```
analyze_single_course(course_id=42, year=2024)
    |
    |-- [1] _fetch_course_meta()      → Ders adi, tipi, fakulte bilgisi
    |
    |-- [2] _fetch_criteria()          → Basari orani, doluluk, ortalama not, anket
    |
    |-- [3] _fetch_gecmis_trend()      → Son 3 yilin basari oranlari
    |
    |-- [4] _fetch_prev_pool()         → Onceki yilin statu/sayac bilgisi
    |
    |-- [5] _run_ahp()                 → AHP agirliklari ve CR (tutarlilik)
    |
    |-- [6] _run_trend_lr()            → Gelecek basari tahmini (%75.5)
    |
    |-- [7] _run_topsis_single()       → Kesinlesme puani (68.45/100)
    |
    |-- [8] _run_rf()                  → RF kesinlesme tahmini (72.1/100)
    |
    |-- [9] should_drop_course()       → Dusme karari (68.45 > 40 → Hayir)
    |
    |-- [10] calculate_next_status()   → State Machine (statu=1, sayac=0)
    |
    |-- [11] _run_dt()                 → DT statu tahmini (1 = Mufredatta)
    |
    v
    Sonuc: {
        "decision": {
            "score_final": 68.45,
            "in_mufredat_this_year": True,
            "label": "Mufredatta",
            "next": {"statu": 1, "sayac": 0}
        },
        "steps": {
            "ahp":    {...},
            "trend":  {...},
            "topsis": {...},
            "rf":     {...},
            "dt":     {...}
        }
    }
```

### Karar Oncelik Sirasi

Son karari kim verir? Algoritmalarin rolu su sekildedir:

| Sira | Algoritma | Rol | Agirlik |
|------|-----------|-----|---------|
| 1 | **AHP** | Kriter agirliklarini belirler | Dolayliı (TOPSIS'e girdi) |
| 2 | **TOPSIS** | Kesinlesme puani hesaplar | **Ana karar verici** |
| 3 | **Trend/LR** | Basari trendini tahmin eder | TOPSIS'e girdi (trend kriteri) |
| 4 | **RF** | Kesinlesme puani dogrulama | Destekleyici (karsilastirma) |
| 5 | **DT** | Statu tahmini | Destekleyici (karsilastirma) |
| 6 | **State Machine** | Final statu belirler | **Kesin karar** |

> **Sonuc:** TOPSIS ana puani hesaplar. Bu puan + ortalama not baraj kontrolunden gecer.
> State Machine ise gecmis yillarla birlikte nihai statuyu belirler.

---

## Ozet Tablosu

| Algoritma | Tur | Kutuphane | Girdi | Cikti |
|-----------|-----|-----------|-------|-------|
| AHP | Cok kriterli karar | Saf Python | Ikili karsilastirma matrisi | Kriter agirliklari (4 deger) |
| TOPSIS | Cok kriterli karar | pandas + math | Ders x Kriter matrisi | 0-100 kesinlesme puani |
| Trend/LR | Regresyon | sklearn | Son 3 yil basari orani | Gelecek basari tahmini (0-1) |
| Random Forest | Ensemble ML | sklearn | 6 ozellik | 0-100 kesinlesme tahmini |
| Decision Tree | Siniflandirma | sklearn | 6 ozellik | Statu tahmini (1/0/-1/-2) |
| State Machine | Durum makinesi | Saf Python | Onceki statu + sayac | Yeni statu + sayac |
| TF-IDF + Cosine | NLP | sklearn | Ders aciklama metinleri | Benzerlik skoru (0-1) |
| Rules Engine | Is kurallari | Saf Python | Ogrenci + ders bilgisi | Uygun/Uygun degil |

---

*Bu dokuman, Adil Secmeli Ders Asistani projesindeki tum algoritmalarin detayli teknik aciklamasini icermektedir.*
*Sorulariniz icin kaynak kodlardaki yorum satirlarini inceleyebilirsiniz.*
