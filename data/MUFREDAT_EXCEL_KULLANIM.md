# Müfredat Excel Aktarımı (Güz + Bahar)

## Dosya: `data/2022_mufredat.xlsx`

Her yıl için **2 ayrı müfredat** tanımlanabilir: **Güz** ve **Bahar**.

## Gerekli Sütunlar
| Sütun | Açıklama | Örnek |
|-------|----------|-------|
| Fakülte | Fakülte adı | Mühendislik ve Doğa Bilimleri |
| Bölüm | Bölüm adı | Bilgisayar Mühendisliği |
| Akademik Yıl / Yıl | Yıl | 2022 |
| **Dönem** | Güz veya Bahar | Güz, Bahar |
| Seçmeli Ders 1..10 | Ders adları | Blokzincir Teknolojisi |

## Örnek Yapı (2022 Güz + Bahar)

| Fakülte | Bölüm | Yıl | Dönem | Seçmeli Ders 1 | Seçmeli Ders 2 | ... |
|---------|-------|-----|-------|----------------|----------------|-----|
| Mühendislik... | Bil. Müh. | 2022 | Güz | Ders A | Ders B | ... |
| Mühendislik... | Bil. Müh. | 2022 | Bahar | Ders X | Ders Y | ... |

- **Güz** ve **Bahar** ayrı satırlarda tanımlanır.
- Dönem sütunu yoksa varsayılan **Güz** kullanılır.
- Ders adları veritabanındaki `ders.ad` ile eşleşmeli.

## Çalıştırma
```bash
python -m app.etl.import_mufredat_excel
```
