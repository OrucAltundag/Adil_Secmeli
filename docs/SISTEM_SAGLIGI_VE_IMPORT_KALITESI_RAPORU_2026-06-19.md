# Sistem Sağlığı ve Import Kalitesi Açıklama Raporu

**Tarih:** 19 Haziran 2026  
**Amaç:** Sunum sırasında Sistem Sağlığı ve Veri Yönetimi kalite ekranlarının teknik olarak doğru anlatılması

## 1. Tam Sağlık Kontrolü ne yapar?

Tam Sağlık Kontrolü üretim algoritmasını çalıştırıp müfredatı değiştirmez. Kayıtlı
sağlık kontrollerini güvenli örnekler ve salt-okunur denetimler üzerinden çalıştırır;
sonuçları kategori bazında puanlayıp tek raporda birleştirir. Güncel kayıt defterinde
111 ayrı kontrol sınıfı vardır.

Başlıca kontrol grupları:

| Grup | Kontrol örnekleri |
|---|---|
| Veritabanı | SQLite bağlantı, `integrity_check`, `foreign_key_check`, tablo sayısı, rollback edilen yazma testi |
| Şema | Beklenen tablo/kolonlar, tip ve uyumluluk, migrasyon durumu |
| Veri kalitesi | Eksik değer, tekrar, aralık, yetim kayıt, profil çıkarma, IQR aykırı değer |
| Import yönetişimi | Import tabloları, rollback altyapısı, import–canlı veri tutarlılığı |
| AHP | Matris boyutu, karşılıklılık, ağırlık toplamı, CR, kriter ve alternatif tamlığı |
| TOPSIS | Veri uygunluğu, normalizasyon, NaN/sonsuz değer, 0–1 skor aralığı, monoton sıralama |
| Karar Merkezi | Girdi, sıralama, skor, açıklama, karar çalıştırması izlenebilirliği, düşük güven koruması |
| Havuz ve planlama | Durum makinesi, statü geçişi, dönem eşleme, kapasite ve planlama kuralları |
| Raporlama/API/UI | CSV–Excel–PDF, klasör izinleri, API yükleme, sekme ve boş durum dayanıklılığı |
| Güvenlik/mimari | SQL izinleri, riskli desenler, path traversal, hassas log, katman ihlali ve döngüsel import |
| Operasyon | Performans, yavaş sorgu, log, yedekleme, test altyapısı ve bağımlılıklar |

## 2. Sağlık puanı nasıl hesaplanır?

Her kontrol sonucu `OK`, `INFO`, `WARNING`, `CRITICAL`, `FAILED`, `SKIPPED` veya
`FIXED` durumuna dönüşür. Skipped sonuçlar puanı düşürmez. Aktif sonuç katsayıları:

- OK/FIXED = 1,00
- INFO = 0,97
- WARNING = 0,60
- CRITICAL = 0,20
- FAILED = 0,10

Kategori ortalamaları aşağıdaki ağırlıklarla birleşir:

| Puan grubu | Ağırlık |
|---|---:|
| Veritabanı | %15 |
| Şema | %10 |
| Veri kalitesi | %10 |
| AHP/TOPSIS/Karar | %15 |
| Dönem planlama | %8 |
| Raporlama/analiz/benchmark | %10 |
| API/UI | %10 |
| Güvenlik | %10 |
| Mimari | %7 |
| Operasyon | %5 |

Genel statü: `≥90 sağlıklı`, `≥70 uyarılı`, `≥40 riskli`, `<40 kritik`.

## 3. Sağlık ekranında adı verilebilecek algoritmalar

### Doğrudan matematiksel sağlık kontrolü bulunanlar

- **AHP:** ikili karşılaştırma matrisi, karşılıklılık, özvektör/ağırlık toplamı ve CR.
- **TOPSIS:** vektör normalizasyonu, ideal uzaklıklar, skor aralığı ve sıralama geçerliliği.
- **IQR:** sayısal aykırı değer tespiti.
- **Ağırlıklı sağlık skorlaması:** kategori puanlarının bileşik skora dönüşmesi.

### Güncel karar hattında aktif olarak kataloglananlar

- **Lineer Regresyon:** Trend sayfasında sonraki yıl tahmini; DT’ye sızıntısız özellik.
- **ELECTRE TRI-B:** kriter bazlı akademik statü sınıflandırması.
- **Decision Tree:** ELECTRE kararına geçmiş final kararlardan bağımsız ikinci görüş.
- **PROMETHEE II:** müfredat dışı adaylarda net akış ve çeşitlilik kontrollü Top-7.
- **Random Forest:** üretim kararında kullanılmaz; analiz/benchmark kapsamındadır.

Önemli ifade: Tam Sağlık Kontrolü bu algoritmaların tümüyle yeni resmi karar üretmez.
AHP/TOPSIS için matematiksel smoke kontrolleri, diğerleri için modül/yönetişim/karar
çıktısı kontrolleri ve aktif algoritma kataloğu sunar.

## 4. Sistem Sağlığı konuşma metni

> Buradaki Tam Sağlık Kontrolü yeni müfredat oluşturmaz; karar motorunun güvenli
> çalışması için 111 ayrı teknik kontrolü koordine eder. Veritabanı ve şema
> bütünlüğünden eksik/tekrarlı/aykırı veriye, AHP matrisinin karşılıklılığı ve CR
> değerinden TOPSIS normalizasyonu ve sıralama geçerliliğine kadar ayrı testler
> vardır. Karar izlenebilirliği, havuz durum makinesi, dönem planlama kısıtları,
> raporlama, güvenlik, performans ve mimari de denetlenir. Son puan on farklı
> grubun ağırlıklı birleşimidir. AHP ve TOPSIS örnek veriyle matematiksel olarak
> çalıştırılır; LR, ELECTRE TRI-B, Decision Tree ve PROMETHEE II güncel karar
> hattının aktif algoritmaları olarak ayrıca kataloglanır.

## 5. Import kalite skoru nasıl hesaplanır?

Model sürümü: `weighted_quality_v2_scope_aware`.

Formül:

```text
Kalite =
    0.25 × Ders eşleşme oranı
  + 0.20 × Başarılı satır oranı
  + 0.20 × Sayısal geçerlilik oranı
  + 0.15 × Tamlık skoru
  + 0.10 × Benzersizlik skoru
  + 0.10 × Kapsam tutarlılığı
```

Bileşenler:

- **Ders eşleşme oranı:** Dosyadaki satırların sistemde gerçek dersle eşleşme oranı.
- **Başarılı satır oranı:** Matched/applied/ok/success satırlar tam; kontrollü uyarı satırları kısmi başarılı sayılır.
- **Sayısal geçerlilik:** Geçersiz veya tanımlı aralık dışındaki sayılar oranı düşürür.
- **Tamlık:** Eksik zorunlu alan ve eşleşmeyen dersler cezalandırılır.
- **Benzersizlik:** Aynı satır hash’inin tekrarları puanı düşürür.
- **Kapsam tutarlılığı:** Dosyanın yıl/fakülte/bölüm kapsamı seçili kapsamla çelişmemelidir.

Seviyeler:

- `≥0,80`: Çok iyi / high
- `0,55–0,7999`: Kullanılabilir / medium
- `<0,55`: Riskli / low

### Sert doğrulama kapıları

- Zorunlu kolon veya başlık eksikse import başarısızdır.
- Fakülte/bölüm/yıl kapsamı tutarsızsa manuel inceleme gerekir.
- Sayısal değerlerin tamamı geçersiz/aralık dışıysa manuel inceleme gerekir.
- Sert kapı geçilmezse diğer yüksek bileşenler kaliteyi yapay biçimde yükseltemez;
  skor en fazla 0,5499 olur.

Kalite skoru onay yerine geçmez. Teknik olarak yüksek kaliteli import dahi `Import Onayı`
sekmesinde yetkili tarafından onaylanmadan canlı tablolara uygulanmaz.

## 6. Import Kalitesi konuşma metni

> Kaliteyi Yeniden Hesapla dediğimde sistem yalnız dosyanın açılıp açılmadığına
> bakmıyor. Derslerin sistemle eşleşmesini yüzde 25, başarılı satırları yüzde 20,
> sayısal değer geçerliliğini yüzde 20, zorunlu alan tamlığını yüzde 15,
> benzersizliği yüzde 10 ve yıl–fakülte–bölüm kapsam tutarlılığını yüzde 10
> ağırlıkla ölçüyor. Ayrıca zorunlu kolon veya kapsam hatası gibi kritik sorunlar
> sert kapıdır; diğer iyi değerler bu hatayı telafi edemez. Kalite yeterli olsa
> bile veri doğrudan canlı sisteme geçmez, Import Onayı ekranında yetkili onayı bekler.

