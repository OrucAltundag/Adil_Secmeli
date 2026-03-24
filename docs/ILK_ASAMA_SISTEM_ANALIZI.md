# Ilk Asama Sistem Analizi

## Mevcut Veri Modeli Ozeti

- `havuz`: yil bazli calisiyor; `ders_id`, `fakulte_id`, `bolum_id`, `statu`, `sayac`, `skor` tutuyor.
- `mufredat`: fakulte + bolum + akademik_yil + donem bazli ust kayit tutuyor.
- `mufredat_ders`: ilgili mufredat satirinin ders baglarini tutuyor.
- `ders`: ders meta verisi; mevcut modelde `sinif` ve `havuz_tipi` gibi alanlar dogrudan tutulmuyor.

## Tespit Edilen Ana Sorunlar

### 1. Rapor & Skor sekmesi

- Fakulte + bolum + yil + donem mantigi havuz sekmesi kadar guvenli degildi.
- `donem` filtresi UI seviyesinde yoktu.
- Skorun hangi mantikla olustugu kullaniciya acik degildi.
- Ayni bolum adinin farkli fakultelerde bulunmasi durumunda mufredat sorgusu karisabilirdi.

### 2. Mufredat Excel importu

- Mevcut akista tum `mufredat` ve `mufredat_ders` kayitlari siliniyordu.
- Bu davranis tek bir Excel importunun sistemdeki diger fakulteleri ve yillari bozmasi riskini olusturuyordu.
- Import yalnizca legacy genis kolon yapisini bekliyordu; satir bazli yeni sablonu desteklemiyordu.

### 3. Test edilebilirlik

- `test_etl.py` ve `test_score_engine.py` bos durumdaydi.
- UI sorgulari servis katmanindan ayrilmadigi icin rapor davranisi dogrudan test edilemiyordu.

## Uygulanan Guvenli Duzeltmeler

- `app/services/reporting.py` eklendi.
- Rapor sekmesi yeni servis uzerinden fakulte + yil + donem farkindali hale getirildi.
- Skor kaynagi (`TOPSIS` veya `Anket 50+-10`) gorunur yapildi.
- Mufredat importu tum sistemi silmek yerine yalnizca hedef kapsamı (fakulte + bolum + yil + donem) degistirecek sekilde guncellendi.
- Yeni satir bazli Excel sablonu desteklenmeye baslandi.
- ETL ve raporlama icin regresyon testleri eklendi.

## Gozlemlenebilir Tamamlanma Degerlendirmesi

| Alan | Oran | Gozlem |
|------|------|--------|
| Veri yapisi | %72 | Temel tablolar ve iliskiler var; ancak sinif/yil-bazli mufredat boyutu ve resmi import semasi tam degil. |
| Mufredat yonetimi | %58 | Otomatik uretim ve import var; fakat yil-butunu bakisi ve sinif bazli model eksik. |
| Havuz sistemi | %64 | State machine ve skor akisi var; fakat 4'lu blok gosterim ve donem tasima mantigi eksik. |
| Raporlama | %55 | UI var; temel veri gorunuyor; yeni iyilestirme yapildi ama skor kartlari ve aciklayici metinler hala genisletilmeli. |
| Skor mantigi | %70 | AHP/TOPSIS ve tek ders analizi var; aciklanabilirlik orta seviyede, son kullanici diliyle sunum eksik. |
| Test edilebilirlik | %52 | Kritik algoritma testleri mevcut; placeholder testler ve UI/ETL kapsami halen sinirli. |
| Urunlesme seviyesi | %46 | Masaustu uygulama calisiyor; fakat operasyonel dokumantasyon, tam import standardi ve surdurulebilir veri yonetimi eksik. |

## Kalan Yuksek Oncelikli Riskler

- `havuz` tablosunun yil bazli ama donemsiz tasarimi, donem bazli raporlama ve havuz gosteriminde sinir olusturuyor.
- Mevcut modelde `sinif` ve "egitim yili butunu" mantigi yapisal olarak birinci sinif alanlariyla temsil edilmiyor.
- Rapor/analiz sekmeleri arasinda ortak KPI tanimi henuz standartlastirilmadi.
