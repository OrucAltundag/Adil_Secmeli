# Mufredat Excel Sablonu

## Amac

Bu sablon, tum bolumler icin mufredat verisini satir bazli ve kontrollu sekilde sisteme almak icin hazirlandi.

## Onerilen Kolonlar

- `Fakulte`
- `Bolum`
- `Sinif`
- `Akademik Yil`
- `Donem`
- `Ders Kodu`
- `Ders Adi`
- `Kredi`
- `AKTS`
- `Zorunlu_Seçmeli`
- `Havuz Bilgisi`

## Mevcut Sistem Tarafindan Aktif Kullanilan Kolonlar

Su anki import akisi bu kolonlari aktif kullanir:

- `Fakulte`
- `Bolum`
- `Akademik Yil`
- `Donem`
- `Ders Kodu` veya `Ders Adi`

Asagidaki kolonlar sablonda korunur ancak mevcut veri modelinde henuz dogrudan tablo alanina yazilmaz:

- `Sinif`
- `Kredi`
- `AKTS`
- `Zorunlu_Seçmeli`
- `Havuz Bilgisi`

Bu alanlar ikinci asamada veri modeli genisletilirken resmi semaya alinmalidir.

## Import Davranisi

- Import artik tum sistemi silmez.
- Yalnizca Excel icinde gelen `Fakulte + Bolum + Akademik Yil + Donem` kapsami guncellenir.
- Ayni kapsam disindaki diger fakulteler, diger yillar ve diger bolumler korunur.
- `Ders Kodu` varsa once kod ile eslestirme yapilir.
- Kod yoksa `Ders Adi` ile eslestirme denenir.

## Validasyon Kurallari

- `Fakulte`, `Bolum`, `Akademik Yil` bos olamaz.
- `Ders Kodu` veya `Ders Adi` en az birisi dolu olmalidir.
- `Akademik Yil` tek yil (`2024`) veya aralik (`2024/2025`) olarak verilebilir.
- `Donem` yalnizca `Guz/Güz` veya `Bahar` olmalidir.
- Ayni `Fakulte + Bolum + Akademik Yil + Donem + Ders Kodu` tekrar etmemelidir.
- `Zorunlu_Seçmeli` icin izinli degerler: `Zorunlu`, `Secmeli`.
- `Kredi` ve `AKTS` sayisal olmalidir.

## Onerilen Dosya Konumu

- `data/templates/mufredat_ornek_sablon.xlsx`

## Not

Bu sablon satir bazlidir; her satir tek bir dersi temsil eder. Bu yapi, mevcut legacy genis kolonlu formatlara gore daha kolay dogrulanir, test edilir ve yil-butunu mantigina daha rahat evrilir.
