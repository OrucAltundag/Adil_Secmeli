# Eksik kriter hazirlik seti

## Zorunlu alanlar (next year / `_has_generation_criteria`)

- `toplam_ogrenci` > 0  
- `kontenjan` > 0  
- `gecen_ogrenci` >= 0  
- `kayitli_ogrenci` >= 0  
- `basari_ortalamasi` > 0  

Anket zorunlu degildir.

## Dosyalar

| Dosya | Aciklama |
|-------|----------|
| `missing_criteria_placeholder.json` | Sablon yapi (ornekkayit) |
| `../exports/missing_criteria_*.xlsx` | `export_missing_criteria_workbook.py` ile uretilir |

## Komutlar

```bash
# DB’deki eksik mufredat kriterlerini Excel+CSV export
python app/scripts/export_missing_criteria_workbook.py --yil 2022 --donem G

# Excel’i duzenledikten sonra (once dry-run)
python app/scripts/seed_criteria_from_workbook.py exports/missing_criteria_2022_....xlsx
python app/scripts/seed_criteria_from_workbook.py exports/missing_criteria_2022_....xlsx --apply
```

`--apply` olmadan **hicbir yazim yapilmaz**.

## Endustri Muhendisligi / mufredat filtresi

Kriter sayfasinda "Müfredattakiler" listesi artik **mufredattaki tum dersleri** gosterir (DersTipi Zorunlu olanlar dahil).  
Onceki davranista sadece `Seçmeli` etiketli dersler listeleniyordu; ornegin IK Yonetimi (Zorunlu) mufredatta olmasina ragmen gorunmuyordu.
