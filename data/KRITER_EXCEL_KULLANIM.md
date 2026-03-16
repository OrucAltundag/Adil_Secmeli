# Ders Kriterleri Excel Toplu Yükleme

## Kullanım
- **UI:** Hesaplama & Test → Kriter Girdi İşlemleri → "Excel'den Toplu Yükle"
- **Komut:** `python -m app.etl.import_kriterler_excel kriterler.xlsx`

## Gerekli Kolonlar
| Kolon | Açıklama | Örnek |
|-------|----------|-------|
| DersAdı veya DersID veya Kod | Ders tanımlayıcı | Yazılım Mühendisliği, 101 |
| Yıl | Akademik yıl | 2023 |
| Dönem | Güz veya Bahar (opsiyonel) | Güz |

## Opsiyonel Kolonlar
| Kolon | Açıklama | Varsayılan |
|-------|----------|------------|
| ToplamÖğrenci | Dersi alan toplam öğrenci | 0 |
| GeçenÖğrenci | Dersi geçen öğrenci | 0 |
| Ortalama | Ders not ortalaması | 0 |
| Kontenjan | Ders kontenjanı | 0 |
| KayıtlıÖğrenci | Kayıtlı/talep sayısı | 0 |
| AnketKatılımcı | Ankete katılan | 0 |
| AnketDersiSeçen | Bu dersi seçen | 0 |

## Örnek Excel Yapısı

| DersAdı | Yıl | Dönem | ToplamÖğrenci | GeçenÖğrenci | Ortalama | Kontenjan | KayıtlıÖğrenci |
|---------|-----|-------|---------------|--------------|----------|-----------|----------------|
| Yazılım Mühendisliği | 2023 | Güz | 80 | 65 | 72.5 | 50 | 45 |
| Veri Tabanları | 2023 | Güz | 100 | 85 | 68.0 | 60 | 55 |

- Ders adları veritabanındaki `ders.ad` ile eşleşmeli
- DersID veya Kod kullanılırsa doğrudan eşleşme yapılır
