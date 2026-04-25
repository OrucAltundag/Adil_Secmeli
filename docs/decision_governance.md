# Karar Yonetisimi ve Aciklanabilirlik

Bu dokuman, Adil Secmeli karar hattina eklenen yonetisim katmanini ozetler.

## Yeni karar hatti

Kriter verisi artik su izlenebilir hat uzerinden karar kaydina donusur:

`Kriter verisi -> AHP profil cozumu -> TOPSIS skor/kirilim -> trend etiketi -> veri guveni -> decision policy -> state machine/governance -> aciklama -> hassasiyet -> adalet raporu -> decision_run`

Eski skor, havuz ve mufredat akislari korunur. Yeni tablolar kararlarin hangi profil, esik, veri snapshot'i ve algoritma versiyonuyla uretildigini ek katman olarak saklar.

## AHP profilleri

`ahp_weight_profiles` tablosu AHP agirliklarini profil olarak saklar. Profil kapsam sirasi:

1. bolum + yil
2. fakulte + yil
3. bolum
4. fakulte
5. global + yil
6. global varsayilan

Varsayilan profil yoksa sistem otomatik olarak `basari=0.35`, `trend=0.25`, `populerlik=0.20`, `anket=0.20` agirliklarini olusturur. Pairwise matrix ve consistency ratio kaydedilir. `CR <= 0.10` tutarli kabul edilir; tutarsiz profil sistemi durdurmaz ancak UI/API tarafinda uyarilabilir.

## TOPSIS skor kirilimi

`course_score_breakdowns` her ders icin ham kriter degerleri, normalize degerler, agirlikli degerler, agirliklar, pozitif/negatif ideale uzaklik, yakinlik katsayisi, final skor ve kriter katkilarini saklar. Ders detayi paneli bu alanlari kullanarak "neden bu skor olustu?" sorusunu cevaplar.

## Trend etiketleri

`course_trend_analysis` trend skoruna ek olarak su etiketleri uretir:

- `rising`
- `falling`
- `stable`
- `volatile`
- `insufficient_data`
- `new_course`

Mevcut 50/30/20 agirlikli son yil ortalamasi korunur; buna ek olarak dalgalanma ve veri noktasi sayisi saklanir.

## Decision policy

`decision_policies` karar esiklerini kapsam bazli saklar. Cozumleme AHP profiliyle ayni oncelik sirasini izler. Varsayilan politika:

- `mode=static_threshold`
- `curriculum_keep_threshold=70`
- `pool_threshold=50`
- `rest_threshold=40`
- `cancel_candidate_threshold=30`
- `new_course_grace_period_years=2`
- `require_manual_approval_for_cancel=true`

Eski mufredat uretimindeki dusme esigi, varsayilan durumda policy `rest_threshold` degerinden okunur.

## State machine ve akademik onay

Eski statuler korunur:

- `1`: mufredatta
- `0`: havuzda
- `-1`: dinlenmede
- `-2`: iptal adayi/kalici iptal

Kalici iptal otomatik uygulanmaz. Policy `require_manual_approval_for_cancel=true` ise `-2` onerisi karar kaydinda onay gerektirir ve final durum otomatik olarak sert iptale cekilmez. `course_governance_flags` ile stratejik, akreditasyon, icerik guncelleme, ogretim elemani degisimi ve koruma yili bilgileri tutulur.

## Veri guven skoru

`course_data_confidence` her ders icin 0-1 arasi guven skoru uretir:

- basari verisi: +0.20
- populerlik/doluluk verisi: +0.20
- anket verisi: +0.20
- en az iki yillik trend verisi: +0.20
- guncel veri: +0.10
- minimum anket orneklemi: +0.10

Seviyeler: `high >= 0.75`, `medium >= 0.50`, `low < 0.50`. Eksik veri varsa karar calismasi cokmez; aciklamaya eksik alanlar yazilir.

## Decision run versiyonlama

`decision_runs` her karar calismasini saklar. Alanlar arasinda yil, fakulte, bolum, donem, algoritma versiyonu, AHP profil id, policy id, input data hash, durum ve summary bulunur. Her ders icin `course_decisions` kaydi olusur.

## Aciklama motoru

`course_decision_explanations` kararlar icin makine okunabilir faktor listeleri ve insan okunabilir metin saklar. Dusuk skor, falling trend, dusuk veri guveni, akademik onay, stratejik koruma ve akreditasyon korumasi aciklamaya yansitilir.

## Hassasiyet analizi

`decision_sensitivity_results` her ders icin karar esiklerine yakinligi ve basit agirlik varyasyonlarini kaydeder. Kararlilik seviyeleri:

- `high`: karar sinifi kucuk degisimlerde korunur
- `medium`: skor oynar ama karar sinifi korunur
- `low`: karar esige yakindir veya degisebilir

## Fairness raporu

`decision_fairness_reports` karar calismasi bazinda adalet raporu uretir. Raporda bolum dagilimi, donem dengesi, dusuk veri guveni sayisi, hassas karar sayisi, manuel onay sayisi, iptal/dinlenme/havuz/mufredat sayilari ve basari-talep uyumsuzluklari bulunur.

## Karar Merkezi UI

Ana Tkinter uygulamasina `Karar Merkezi` sekmesi eklendi. Alt bolumler:

- AHP Profilleri
- Karar Politikaları
- Calistirmalar
- Ders Kararlari
- Hassas Kararlar
- Akademik Onay
- Adalet Raporu

Sekme, aktif profilleri ve policyleri listeler, karar calistirmalarini gosterir, yeni calistirma tetikler ve ders detayi/aciklama/veri guveni/fairness raporunu gosterir.

## API endpointleri

Yeni endpointler `/api/v1` altindadir:

- `GET /decision/ahp-profiles`
- `POST /decision/ahp-profiles`
- `POST /decision/ahp-profiles/{profile_id}/activate`
- `GET /decision/policies`
- `POST /decision/policies`
- `POST /decision/policies/{policy_id}/activate`
- `GET /decision/runs`
- `POST /decision/runs/execute`
- `GET /decision/runs/{run_id}`
- `GET /decision/runs/{run_id}/courses`
- `GET /decision/course-decisions/{decision_id}/explanation`
- `GET /decision/runs/{run_id}/fairness`
- `GET /decision/runs/{run_id}/sensitivity`
- `GET /decision/runs/{run_id}/data-confidence`
