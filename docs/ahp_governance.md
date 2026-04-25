# AHP Governance

Bu dokuman Adil Seçmeli projesinde AHP agirlik sisteminin nasil yonetildigini aciklar. Nihai mufredat/havuz karari varsayilan olarak AHP + TOPSIS + Trend + kural motoru + state machine hatti ile verilir.

## AHP'nin rolu

AHP, karar kriterlerinin goreli onemini akademik olarak savunulabilir bicimde belirlemek icin kullanilir. TOPSIS dersleri siralarken bu AHP agirliklarini kullanir. ML ve benchmark algoritmalari nihai AHP/TOPSIS karar hattinin yerine gecmez.

## Kriter tanimlari

Karar kriterleri `decision_criteria_definitions` tablosunda tutulur. Varsayilan aktif kriterler:

- `basari`: Basari
- `trend`: Trend
- `populerlik`: Populerlik / Doluluk
- `anket`: Anket Talebi

Her kriter icin benefit/cost yonu, tip, kaynak, normalizasyon yontemi ve aktiflik bilgisi saklanir. TOPSIS ideal cozumleri bu benefit/cost yonune gore kurabilir.

## Ikili karsilastirma matrisi

Her AHP profili kriter seti ile ayni boyutta NxN ikili karsilastirma matrisi saklar. Matris kurallari:

- Diagonal degerler 1 olmalidir.
- `matrix[i][j] = 1 / matrix[j][i]` reciprocal kuralina uymalidir.
- Degerler pozitif olmalidir.
- Saaty olcegi 1/9 ile 9 araligindadir.

Matris gecerliyse agirliklar geometrik ortalama/eigenvector yontemiyle hesaplanir ve `weights_json` olarak saklanir.

## Consistency Ratio

Consistency Ratio (CR), ikili karsilastirmalarin tutarliligini olcer. Saaty RI degerleri kullanilir. Varsayilan politika `CR <= 0.10` profilini tutarli kabul eder.

CR siniri asildiginda:

- Profil `validated`, `approved` veya `active` durumuna sessizce gecmez.
- API/UI uyarisi uretilir.
- Politika izin vermiyorsa karar calistirmada kullanilmaz.

## Profil kapsami ve versiyonlama

AHP profilleri `ahp_weight_profiles` tablosunda saklanir. Desteklenen kapsamlar:

- `global`
- `faculty`
- `department`
- yil ve donem bazli varyasyon

Aktif profil cozme onceligi:

1. Bolum + yil + donem
2. Bolum + yil
3. Fakulte + yil + donem
4. Fakulte + yil
5. Bolum genel
6. Fakulte genel
7. Global + yil
8. Global varsayilan

Profil yoksa sistem global varsayilan profili otomatik olusturur.

## Profil yasam dongusu

Status akisi:

`draft -> validated -> pending_approval -> approved -> active -> archived`

Alternatif durum: `rejected`.

Her status degisimi `ahp_profile_approval_logs` tablosunda saklanir. Aktivasyon sirasinda ayni scope/yil/donemdeki eski aktif profil arsivlenir.

## Policy

`ahp_profile_policies` tablosu su kurallari yonetir:

- maksimum CR
- aktivasyon icin onay gerekip gerekmedigi
- tutarsiz profilin draft calismalarda kullanilip kullanilamayacagi
- profil eksikse default kullanimi
- profil degisince eski kararlarin stale isaretlenmesi
- manuel profil icin not/gerekce zorunlulugu

## Decision run baglantisi

Karar calismasi baslamadan once aktif AHP profili cozulur. `decision_runs` icinde su snapshot saklanir:

- `ahp_profile_id`
- `ahp_profile_version`
- `ahp_weights_snapshot_json`
- `ahp_consistency_ratio`
- `ahp_profile_status_at_run`
- `ahp_profile_source`

Boylece profil sonradan degisse bile eski karar hangi agirliklarla uretildigi kaybolmaz.

## TOPSIS skor kirilimi

`course_score_breakdowns` tablosu ders bazli ham degerleri, normalize degerleri, agirliklari ve weighted contribution bilgisini saklar. Bu sayede her ders icin hangi kriterin skora ne kadar etki ettigi raporlanabilir.

## Staleness

Aktif AHP profili degistiginde ayni eski profile bagli karar calismalari `decision_staleness_flags` ile isaretlenir. `decision_runs.stale_flag` ve `recalculate_required` alanlari yeniden hesaplama ihtiyacini gosterir.

## AHP etki aciklamasi

`ahp_impact_explanation_service` profil ve ders bazli aciklama uretir:

- en yuksek agirlikli kriter
- en dusuk agirlikli kriter
- kriterlerin TOPSIS katkisi
- profil CR ve tutarlilik durumu

Ornek: "Bu profilde basari kriteri en yuksek agirliktadir. Bu nedenle basari degeri dusuk derslerin TOPSIS skoru belirgin sekilde sinirlanir."

## Sensitivity analysis

`ahp_sensitivity_service`, karar calismasinda kullanilan agirliklari varsayilan olarak ±%5 oynatir. Her ders icin:

- baz skor
- minimum skor
- maksimum skor
- skor araligi
- karar bucket degisimi
- stabilite seviyesi

hesaplanir. Dusuk stabilite veya karar esigi degisimi olan dersler hassas karar olarak isaretlenir.

## UI kullanimi

Tkinter tarafinda `AHP Ağırlık Yönetimi` sekmesi bulunur. Panelde:

- profil listesi
- profil lifecycle butonlari
- aktiflik ve CR bilgisi
- kriter secimi
- Saaty ikili karsilastirma wizard'i
- matris JSON gorunumu
- agirlik/CR sonuc paneli
- profil etki ozeti

gosterilir.

## API endpointleri

Temel endpointler:

- `GET /api/v1/ahp/criteria`
- `POST /api/v1/ahp/criteria`
- `PATCH /api/v1/ahp/criteria/{criterion_key}`
- `GET /api/v1/ahp/profiles`
- `GET /api/v1/ahp/profiles/active`
- `GET /api/v1/ahp/profiles/{profile_id}`
- `POST /api/v1/ahp/profiles`
- `PATCH /api/v1/ahp/profiles/{profile_id}`
- `POST /api/v1/ahp/profiles/{profile_id}/validate`
- `POST /api/v1/ahp/profiles/{profile_id}/submit`
- `POST /api/v1/ahp/profiles/{profile_id}/approve`
- `POST /api/v1/ahp/profiles/{profile_id}/reject`
- `POST /api/v1/ahp/profiles/{profile_id}/activate`
- `POST /api/v1/ahp/profiles/{profile_id}/archive`
- `POST /api/v1/ahp/profiles/{profile_id}/clone`
- `POST /api/v1/ahp/calculate`
- `POST /api/v1/ahp/consistency-check`
- `GET /api/v1/ahp/profiles/{profile_id}/impact`
- `GET /api/v1/ahp/decision-runs/{run_id}/impact`
- `POST /api/v1/ahp/decision-runs/{run_id}/sensitivity`
- `GET /api/v1/ahp/decision-runs/{run_id}/sensitivity`
- `GET /api/v1/ahp/stale-decisions`
- `POST /api/v1/ahp/stale-decisions/{id}/resolve`

## Net proje ilkesi

AHP agirliklari kodda sabit tutulmaz; global/fakulte/bolum/yil bazli AHP profillerinden gelir. Her profil ikili karsilastirma matrisi, uretilen agirliklar, consistency ratio, onay durumu ve versiyon bilgisiyle saklanir. Karar calismalari kullanilan AHP profilini ve agirlik snapshot'ini kaydeder.

