# Proje Teslim / Durum Raporu — Adil Seçmeli Ders Yönetim Sistemi

**Tarih:** 2026-06-15
**Kapsam:** "Projeyi nihai hale getirme" denetimi + kalan sağlık bulgularının kapatılması

---

## 1. Genel Değerlendirme
Proje keşif aşamasında zaten olgun ve teslim-edilebilir durumda bulundu: tüm
otomatik testler (1 atlanan hariç) geçiyor, canlı sistem sağlığı yüksek, ana
uygulama hatasız import ediliyor. Bu turda kalan mimari/sağlık bulguları
kök nedeninden kapatıldı; sahte/statik veri eklenmedi, mevcut mimari korunup
güçlendirildi.

| Ölçüt | Önce | Sonra |
|---|---|---|
| `app/tests` test sonucu | 555 geçti, **1 başarısız** | **556 geçti, 0 başarısız**, 1 atlandı |
| Canlı sistem sağlığı | 98.3 / 100 | **99.4 / 100** |
| MEDIUM sağlık bulgusu | 5 | **1** (meşru veri; bkz. §15) |
| `app.main` import | ✅ | ✅ |
| Pyright (değişen dosyalar) | — | **0 hata** |

## 2. Düzeltilen Ana Problemler
1. **Mimari katman ihlali (UI → doğrudan DB):** `course_analysis_tab.py` UI içinde
   kendi SQLite bağlantısını açıyordu (mimari guard testi başarısızdı). Paylaşılan
   `app.db.conn` bağlantısına çevrildi.
2. **AHP karşılıklılık (reciprocal) sapması:** Saklı AHP matrisinde üst/alt üçgen
   ayrı yuvarlandığı için ~0.0013 reciprocal sapması vardı (1.75 ↔ 0.571).
   Kalıcı kayıttan önce tam reciprocal'a normalleştirme eklendi; mevcut profil onarıldı.
3. **Import sonrası tutarlılık yanlış pozitifi:** Sağlık kontrolü, başarısız import
   batch'inin tarihsel satır sorunlarını "çözülmemiş" sayıyordu. Kontrol yalnız
   canlı batch'lerin sorunlarını sayacak şekilde düzeltildi.
4. **Bayat hata logu:** `logs/ahp_auto_test.log` içindeki eski (yanlış cwd'den
   çalıştırılmış) ERROR satırı arşivlendi.
5. **Benchmark in-process backend sınıflandırması:** `local_backend.py` mimari
   allowlist'e gerekçesiyle eklendi (UI değil, arka uç adapteri).

## 3. Güncellenen Modüller
- **UI:** `app/ui/tabs/course_analysis_tab.py`
- **Servis:** `app/services/ahp_calculation_service.py` (`enforce_reciprocal_matrix`),
  `app/services/ahp_profile_service.py`, `app/services/architecture_audit_service.py`
- **Health:** `app/health/checks/import_governance_check.py`
- **Veri/Log:** aktif AHP profili matrisi onarıldı; `logs/archive/` altına bayat log taşındı
- **Önceki turlar:** dönem planlama, birleşik havuz, import temizleme, yıllık bütünlük
  altyapısı (bkz. ilgili servis/repository/test dosyaları)

## 4. Eklenen Yeni Özellikler (kümülatif)
- Merkezi `CourseCurriculumStatusService` (havuz/güz/bahar/yıllık durum etiketleri)
- Yıllık müfredat bütünlük kontrolü + motorda bölüm bazlı çift-dönem engeli
- Dönem Planlama sayfası yeniden tasarımı (yıllık görünüm + bütünlük paneli)
- Havuz Yönetimi birleşik görünüm + sağda Güz/Bahar müfredat panelleri
- Import geçmişi temizleme (arşiv tablosuna taşıma, gerçek veri korunur)
- AHP matris reciprocal normalizasyonu

## 5. Çalışır Hale Getirilen / Doğrulanan Sayfalar
Veri Yönetimi (9 alt sekme), Havuz Yönetimi, Dönem Planlama, Ders Analiz
Laboratuvarı (course_analysis_tab), AHP Ağırlık Yönetimi, Karar Merkezi, Sistem
Sağlığı, Benchmark — headless smoke ve/veya test ile doğrulandı.

## 6. Çalışır Hale Getirilen Butonlar
Import sayfası butonları (import/önizle/onayla/reddet/rollback/diff/kalite/etki/
**geçmişi temizle**), havuz statü butonları, dönem planlama (üret/kaydet/CSV),
sağlık kontrolü — gerçek servis çağrılarına bağlı; denetimde bozuk buton bulunmadı.

## 7. Veritabanı Değişiklikleri
- `import_batches_archive` tablosu (import temizleme için dinamik oluşturulur)
- `mufredat_ders.semester_plan_run_id` vb. önceki migration alanları korunur
- Aktif AHP profili `pairwise_matrix_json` tam reciprocal'a onarıldı (veri düzeltmesi)
- Şema mutasyonları schema_compat/Alembic sınırında; UI/servis şema değiştirmez

## 8. Algoritma ve Benchmark Durumu
AHP / TOPSIS / karar motoru gerçek veriyle çalışıyor; AHP matris şekli, ağırlık
toplamı, CR ve reciprocal kontrolleri **OK**. Benchmark platformu algoritma
kayıt/izleme merkezi olarak çalışıyor. Trend nötr-skor mantığı geçmiş yıl verisi
olmayan durumları bozmadan ele alıyor.

## 9. Import / Rollback Durumu
Import, önizleme, doğrulama, onay, red, rollback ve **geçmiş temizleme (arşivleme)**
çalışıyor. Temizleme yalnız terminal + karara bağlı olmayan batch'leri arşivler;
canlı/onaylı/karar-referanslı kayıtları ve gerçek veri tablolarını korur.

## 10. Havuz / Müfredat / Dönemsel Planlama
Havuz tek birleşik tabloda; sağda Güz (üst) / Bahar (alt) müfredatı aynı ekranda.
Güz+bahar aynı akademik yılın parçaları olarak değerlendiriliyor; aynı ders aynı
yıl iki döneme otomatik eklenmiyor; çakışma ve "tekrar eklenemez" durumları etiketli.

## 11. Trend ve Karar Motoru
Trend hesaplama gerçek veriyle; eksik geçmiş yılda nötr skor. AHP/TOPSIS ve nihai
kararlar `decision_run` üretiyor, sonuç + kullanılan algoritmaları kaydediyor.

## 12. Sistem Sağlığı ve Güvenlik
Sistem sağlığı tüm değerleri canlı hesaplıyor (skor **99.4/100**). Güvenlik/üretim
kontrolleri (SQL Console, runtime şema mutasyonu, ortam modu) policy ile yönetiliyor;
üretim varsayılanları güvenli (architecture guard testleriyle doğrulanıyor).

## 13. Test Sonuçları
`python -m pytest app/tests` → **556 geçti, 1 atlandı, 0 başarısız** (~39 sn).
Pyright değişen dosyalarda 0 hata. Mimari guard testleri 7/7.

## 14. Oluşturulan Raporlar
Bu rapor: `docs/PROJE_TESLIM_DURUM_RAPORU_2026-06-15.md`.

## 15. Kalan Riskler (manuel kontrol)
- **IQR aykırı değer uyarısı (MEDIUM, kasıtlı bırakıldı):** `ders.kredi` (>4.5) ve
  `ders.akts` (>8.0) için aykırı değerler — bunlar **meşru akademik master veridir**
  (yüksek/düşük kredili dersler). Gerçek veriyi değiştirmek doğru olmayacağından
  uyarı bilinçli olarak bırakıldı; veri girişi hatası değildir.
- `data/adil_secmeli.db` ve `logs/` değişiklikleri commit edilmedi (kullanıcı kararı).
- UI doğrulamaları headless yapıldı; istenirse gerçek pencerede görsel onay alınabilir.

## 16. Nihai Sonuç
Proje **teslim-edilebilir** durumdadır: uygulama açılıyor, sayfalar ve kritik
butonlar gerçek backend işlemleri yapıyor, veriler gerçek kayıt/servis/algoritma
çıktısından geliyor, testler ve sağlık kontrolleri yeşil. Kalan tek MEDIUM bulgu
gerçek veri doğasından kaynaklanan, kasıtlı bırakılmış bilgilendirici bir uyarıdır.
