# Adil Seçmeli — Güncel Sunum Akışı ve Konuşma Metni

**Tarih:** 19 Haziran 2026  
**Önerilen süre:** 15–20 dakika  
**Demo kapsamı:** 2022 yılı, kriterleri tamamlanmış tek fakülte ve tek bölüm

## 1. Sunumun ana mesajı

Sistem öğrenciye ders seçtiren bir otomasyon değildir. Fakülte ve bölüm yönetimine;
hangi seçmeli derslerin müfredatta korunacağı, hangilerinin havuzda tutulacağı,
hangilerinin dinlenmeye alınacağı ve müfredat dışından hangi derslerin önerileceği
konusunda açıklanabilir karar desteği verir. Algoritmalar öneri üretir; müfredatı
değiştiren işlem yalnızca yetkili kullanıcının açık onayıdır.

## 2. Sunum öncesi hazırlık

- Uygulamayı açıp tek bir fakülte, bölüm ve 2022 kapsamını önceden belirleyin.
- AHP profilinin aktif ve `CR ≤ 0,10` olduğunu kontrol edin.
- Güz ve Bahar için en az birer geçici karar çalıştırması hazır bulundurun.
- Canlı demodan önce aynı kapsamda PROMETHEE II önerilerinin oluştuğunu kontrol edin.
- Sunum sırasında yeni import yapmak zorunda değilsiniz; geçmiş bir import üzerinden kalite ve onay akışını gösterebilirsiniz.
- `Sistemi Sıfırla`, kalıcı iptal ve toplu veri temizliği gibi işlemleri sunum sırasında kullanmayın.

## 3. Güncel ekran sırası ve konuşma metni

### Adım 1 — 🏠 Genel Bakış

**Yapılacak işlem:** Güncellenmiş karar boru hattını gösterin.

**Konuşma metni:**

> Bu sistem veriden başlayıp onaylanabilir bir dönem planına ulaşan karar destek
> hattıdır. Önce sistem ve veri sağlığı kontrol edilir. Geçmiş eğilim ve LR tahmini
> incelenir. Kriterler AHP ile ağırlıklandırılır, TOPSIS ile göreli sıralama yapılır.
> Geçici karar çalıştırmasında ELECTRE TRI-B akademik statüyü önerir, Decision Tree
> geçmiş kararlarla ikinci görüş verir. Müfredat dışı dersler PROMETHEE II ile Top-7
> olarak sıralanır. Son aşamada kurul önizlemeyi değiştirebilir, onaylayabilir ve dönem
> planına dönüştürebilir.

### Adım 2 — 🖥️ Sistem → 🏥 Sistem Sağlığı

**Yapılacak işlem:** `Tam Sağlık Kontrolü` butonuna basın; puan kartlarını ve rapor kategorilerini gösterin.

**Konuşma metni:**

> Tam Sağlık Kontrolü doğrudan yeni müfredat üretmez. Sistemin karar vermeden önce
> güvenilir çalışıp çalışmadığını denetler. Veritabanı bütünlüğü, yabancı anahtarlar,
> şema, eksik ve tekrarlı veriler, AHP matrisinin karşılıklılığı ve CR değeri,
> TOPSIS normalizasyonu ve sıralama monotonluğu, karar izlenebilirliği, havuz durum
> makinesi, dönem planlama kısıtları, dışa aktarım, güvenlik, performans, mimari ve
> yedekleme ayrı kontrollerle sınanır. Son puan bu kategorilerin ağırlıklı birleşimidir.

**Hoca “hangi algoritmalar kontrol ediliyor?” derse:**

> Karar tarafında AHP ve TOPSIS örnek veriyle matematiksel olarak çalıştırılır.
> AHP’de matris boyutu, karşılıklılık, ağırlık toplamı ve CR; TOPSIS’te normalizasyon,
> 0–1 yakınlık aralığı ve sıralama doğrulanır. Veri kalitesinde IQR aykırı değer,
> eksik değer, tekrar ve aralık kontrolleri vardır. Güncel karar hattında ayrıca
> ELECTRE TRI-B, PROMETHEE II, LR ve Decision Tree aktif algoritma kataloğunda
> gösterilir. Sağlık puanı ise on ayrı kontrol grubunun ağırlıklı skorudur.

### Adım 3 — 📥 Veri → 📥 Veri Yönetimi

#### 3.1 Merkez

**Yapılacak işlem:** Yıl, fakülte ve bölüm seçin. Bölüm değiştirerek `Toplam Ders`,
`Genel Kapsama`, `Olgunluk`, `Kriter Eksik` ve `Anket Eksik` kartlarının değiştiğini gösterin.

**Konuşma metni:**

> Bu kartlar artık seçili yıl, fakülte ve bölüm kapsamına göre hesaplanır. Böylece
> bir fakültenin toplam eksiğini görmekle yetinmeyip eksiğin hangi bölümde olduğunu
> doğrudan tespit edebiliyoruz. Tamamlanacak veri tablosu kriter, performans,
> popülerlik, anket ve trend eksiklerini ayrı ayrı gösterir.

#### 3.2 Yeni Import

**Yapılacak işlem:** Veri tiplerini ve `Şablon Oluştur` alanını gösterin; importu çalıştırmanız gerekmez.

**Konuşma metni:**

> Yeni veri önce doğrulama ve onay kuyruğuna alınır. Onay verilmeden canlı karar
> tabloları değişmez. Şablon, seçili veri tipine uygun kolonları kullanıcıya verir.

#### 3.3 Import Geçmişi

**Yapılacak işlem:** Bir import satırını seçip `Import Kaydını İncele` deyin.

**Konuşma metni:**

> Her import; dosya, yıl, fakülte, bölüm, durum, kalite skoru, satır sayısı ve
> yükleme zamanı ile izlenir. Bu kayıtlar veri soy ağacını ve denetlenebilirliği sağlar.

#### 3.4 Kalite Kontrol

**Yapılacak işlem:** `Kaliteyi Yeniden Hesapla` butonuna basın.

**Konuşma metni:**

> Import kalite skoru tek bir satır sayımı değildir. Ders eşleşmesi yüzde 25,
> başarılı satır oranı yüzde 20, sayısal geçerlilik yüzde 20, alan tamlığı yüzde 15,
> benzersizlik yüzde 10 ve kapsam tutarlılığı yüzde 10 ağırlıkla değerlendirilir.
> Zorunlu kolon, kapsam veya sayısal geçerlilikte kritik sorun varsa sert doğrulama
> kapısı devreye girer ve yüksek görünen diğer bileşenlerin hatayı gizlemesine izin vermez.

#### 3.5 Import Onayı

**Yapılacak işlem:** Onay bekleyen satırı gösterin. `Onayla ve Sisteme Uygula` ile
`Reddet` butonlarının onay mesajlarını açıklayın; canlı demoda uygulamanız şart değildir.

**Konuşma metni:**

> Doğrulanan import burada yetkili kararını bekler. Onaylanırsa canlı tablolara
> uygulanır; reddedilirse canlı sistem değişmez. Kullanıcıdan açık onay alındığı için
> yanlışlıkla veri değiştirme riski azaltılır.

### Adım 4 — 📥 Veri → ✓ Veri Kalitesi

**Yapılacak işlem:** Aynı kapsamı seçip `Rapor Oluştur` deyin. `Veri Özeti`, `Kapsama
Raporu`, `Veri Olgunluğu`, `Eksik Veri Matrisi` ve `Doğrulama Sorunları` bölümlerini gösterin.

**Konuşma metni:**

> Veri Yönetimi tek importun teknik kalitesini ölçerken Veri Kalitesi Merkezi tüm
> karar kapsamının yeterliliğini ölçer. Burada hangi derslerde hangi alanın eksik
> olduğunu ve bunun karar hazırlığına etkisini rapor üzerinden görebiliyoruz.

### Adım 5 — 📥 Veri → 📈 Trend

**Yapılacak işlem:** Yıl, fakülte ve ders seçip `Trendi Göster` deyin.

**Konuşma metni:**

> Mavi sütunlar gerçek geçmiş başarı verileridir. Ağırlıklı trend son üç yılı
> yeni yıldan eskiye yüzde 50, yüzde 30 ve yüzde 20 ağırlıkla birleştirir. Mor ve
> kesik çerçeveli sütun Lineer Regresyon tahminidir. LR, son üç kesinleşme puanına
> `y = β0 + β1x` doğrusu uydurup bir sonraki yılı tahmin eder. Eksik yıl sıfır kabul
> edilmez; dersi haksız cezalandırmamak için nötr 50 kullanılır ve güven seviyesi düşürülür.

### Adım 6 — ⚙️ Karar Süreci → 🧮 Kriter & Havuz → 📝 Kriter Girdi İşlemleri

**Yapılacak işlem:** Fakülte, bölüm, yıl ve dönemi seçip `Dersleri Getir` deyin; bir ders seçin.

**Konuşma metni:**

> Bu ekran import ekranı değildir; seçili dersin başarı, not ortalaması, kontenjan,
> kayıtlı öğrenci, doluluk ve anket değerlerini ayrıntılı inceleme ve gerektiğinde
> yetkili manuel düzeltme ekranıdır. Dosya aktarımı tek merkez olan Veri Yönetimi’nde yapılır.

### Adım 7 — ⚙️ Karar Süreci → ⚖️ AHP Ağırlık Yönetimi

**Yapılacak işlem:** Aktif profili, `İkili Karşılaştırma` sekmesini, ağırlıkları ve CR’yi gösterin.

**Konuşma metni:**

> AHP, başarı, trend, popülerlik ve anket kriterlerinin göreli önemini Saaty
> ölçeğindeki ikili karşılaştırmalardan üretir. Matris karşılıklıdır; bir kriter
> diğerine 3 kat önemliyse ters hücre 1/3 olur. Ana özvektör normalize edilerek
> ağırlıklar elde edilir. `CR = CI/RI` değeri 0,10 veya altındaysa yargılar tutarlı
> kabul edilir. Karar çalıştırması yalnız aktif ve tutarlı profil kullanır.

### Adım 8 — ⚙️ Karar Süreci → 📐 TOPSIS Kararı

**Yapılacak işlem:** Aynı bölüm için `Hesapla` deyin; bir satır seçerek formül dökümünü gösterin.

**Konuşma metni:**

> TOPSIS önce karar matrisini vektör normuyla normalize eder, AHP ağırlıklarıyla
> çarpar, pozitif ve negatif ideal noktaları bulur. `C* = S-/(S+ + S-)` göreli
> yakınlık katsayısıdır. Ekran ara değerleri 15 anlamlı basamakla gösterir.
> Bir ders seçili alternatifler içinde pozitif ideale tam eşitse 100, negatif
> ideale eşitse 0 çıkabilir; bu yuvarlama hatası değil, standart TOPSIS’in göreli
> yapısıdır. Ekran ayrıca `A+=A-` olan, yani sıralamaya katkı vermeyen kriterleri uyarır.

### Adım 9 — ⚙️ Karar Süreci → 🧮 Kriter & Havuz → Algoritma Kontrol & Ders Lab

**Yapılacak işlem:** Fakülte ve yılı seçip `Sonraki Yıl Kararını Hesapla` deyin.

**Konuşma metni:**

> Bu buton müfredatı doğrudan değiştirmez. Seçili fakültenin bölümleri için Güz ve
> Bahar geçici karar çalıştırmalarını üretir ve Karar Merkezi’ne aktarır. Kontrol
> panelinde yalnız üretim hattının anlaşılır adımları olan veri kontrolü, trend,
> AHP ve TOPSIS bulunur. LR Trend sayfasında, DT Karar Merkezi’nde ikinci görüş
> olarak, RF ise analiz ve benchmark kapsamında tutulduğu için burada ayrı buton değildir.

### Adım 10 — ⚙️ Karar Süreci → 🎯 Karar Merkezi → Hazırlık Kontrolü

**Yapılacak işlem:** `Hazırlığı Yenile` deyin. Güz veya Bahar karar satırına tıklayın.

**Konuşma metni:**

> Hazırlık kapısı kriter tamlığı, doğrulama sorunları, aktif AHP profili ve karar
> politikasını kontrol eder. Karar tablosunda bir satıra tıkladığımda üstteki yıl,
> fakülte, bölüm, dönem ve Karar Çalıştırması filtreleri otomatik olarak o kayda
> eşitlenir. Bir engelleme talebi reddedilirse yalnız talep reddedilir; karar,
> havuz ve müfredat değişmez. Onaylanan engelleme ise geçici karar çıktısını temizler.

### Adım 11 — Karar Merkezi → Karar Politikaları

**Yapılacak işlem:** Aktif politikayı, λ ve sınır profillerini gösterin.

**Konuşma metni:**

> Buradaki 70, 50 ve 40 değerleri yalnız TOPSIS puan barajı değildir. ELECTRE TRI-B
> için Müfredat, Havuz ve Dinlenme sınır profillerinin başlangıç değerleridir.
> ELECTRE her kriterde kayıtsızlık q, tercih p ve gerektiğinde veto eşiğini uygular.
> Ağırlıklı uyumdan credibility hesaplanır; credibility λ değerini geçerse ders
> ilgili profili aşmış kabul edilir. Varsayılan atama kuralı temkinli yaklaşımdır.

### Adım 12 — Karar Merkezi → Ders Kararları

**Yapılacak işlem:** Bir ders seçerek detay ve açıklamayı gösterin.

**Konuşma metni:**

> Eski statü, ELECTRE önerisi, göreli TOPSIS puanı, ELECTRE güvenilirliği,
> Decision Tree ikinci görüşü, ELECTRE–DT karşılaştırması, final statü, trend,
> veri güveni ve gerekçe aynı satırda görülebilir. DT yalnız hedef yıldan önceki
> tamamlanmış final kararlarla eğitilir; başarı, trend, LR trend tahmini, doluluk,
> anket, TOPSIS, veri güveni ve eski statüyü kullanır. En az 100 geçmiş örnek,
> en az iki sınıf ve sınıf başına 10 kayıt yoksa “Veri yetersiz” yazar. Bu durumda
> sistem tahmin uydurmaz ve ELECTRE kararını değiştirmez.

### Adım 13 — Karar Merkezi → Önerilen Dersler

**Yapılacak işlem:** PROMETHEE II Top-7 tablosunu gösterin.

**Konuşma metni:**

> Bu liste aktif müfredatta olmayan dersler içindir. PROMETHEE II adayları akademik
> bölüm uygunluğu, müfredat boşluğu, anket talebi, kaynak ve dönem uygunluğu,
> içerik çakışmasının azlığı, sektörel değer ve veri güveniyle ikili karşılaştırır.
> Phi artı adayın diğerlerine üstünlüğünü, phi eksi yenilgisini, net akış ise
> farkını gösterir. Ardından birbirinin kopyası dersleri azaltmak için çeşitlilik
> cezası uygulanır ve seçili fakülte/bölüm kapsamında en fazla 7 öneri üretilir.

### Adım 14 — Karar Merkezi → Havuz Yaşam Döngüsü

**Yapılacak işlem:** `Nihai Müfredatı Hazırla` deyin. Gerekirse `Ders Değiştir`
ile önerilen bir dersi seçin; değiştirmeden bırakmanın da mümkün olduğunu anlatın.

**Konuşma metni:**

> Sistem önce Güz ve Bahar için onay bekleyen bir müfredat önizlemesi oluşturur.
> Kararı olmayan mevcut ders güvenli varsayımla korunur. Kurul isterse önerilen
> Top-7 içinden bir dersle takas yapabilir, isterse otomatik önizlemeyi olduğu gibi
> bırakabilir. Bu aşamadaki takas yalnız önizlemeyi değiştirir. `Müfredatı Onayla`
> denildiğinde hedef yıl müfredatı yazılır; `Müfredatı Reddet` yalnız önizlemeyi
> reddeder ve müfredatı değiştirmez.

### Adım 15 — ⚙️ Karar Süreci → 🧮 Kriter & Havuz → Havuz Yönetimi

**Yapılacak işlem:** Onaylanan hedef yılı seçip birleşik havuz ile Güz/Bahar müfredatını gösterin.

**Konuşma metni:**

> Sol tarafta fakülte ve bölümün birleşik seçmeli ders havuzu, sağ tarafta Güz ve
> Bahar müfredatı birlikte görülebilir. Havuz durum makinesi bir dersin müfredat,
> havuz, dinlenme ve iptal statülerini sayaç ve onay kurallarıyla izler. Aynı dersin
> kontrolsüz biçimde tekrar eklenmesi ve dönem çakışmaları bütünlük kurallarıyla engellenir.

### Adım 16 — ⚙️ Karar Süreci → 📅 Dönem Planlama

**Yapılacak işlem:** `Plan Üret` sekmesinde `Adayları Kontrol Et`, ardından gerekirse
`Plan Üret`; Güz/Bahar, Yerleşmeyen ve Kısıt İhlalleri bölümlerini gösterin.

**Konuşma metni:**

> Onaylanmış müfredattaki ders sayıları ve Güz–Bahar dengesi hedef yıl için burada
> planlanır. Planlama aday skoru, dönem uygunluğu, öğretim elemanı, kapasite, ön koşul,
> kaynak ve çakışma kısıtlarını dikkate alır. Planlar ayrıca onaylanabilir,
> reddedilebilir ve aktifleştirilebilir; onay verilmeden müfredata yazılmaz.

### Adım 17 — 📊 Raporlama & Analiz → 📄 Rapor & Yükleme

**Yapılacak işlem:** Şablon indirme ve Havuz/Müfredat CSV–Excel butonlarını gösterin.

**Konuşma metni:**

> Son ekranda import için gereken müfredat, kriter ve anket şablonları indirilebilir.
> Seçili yıl, fakülte ve bölüme göre oluşan müfredat ile anlık havuz durumu CSV veya
> Excel olarak dışa aktarılabilir. Böylece algoritma çıktısı kurul toplantısına,
> arşive veya başka bilgi sistemlerine taşınabilir.

## 4. Kapanış cümlesi

> Özetle sistem, veriyi doğrudan karara dönüştürmek yerine sağlık, kalite, hazırlık,
> çok kriterli sıralama, bağımsız ikinci görüş ve insan onayı katmanlarından geçirir.
> Üretilen her sonuç kapsamı, kullanılan profil ve politika, algoritma çıktısı ve
> gerekçesiyle izlenebilir; nihai akademik yetki her zaman kurulda kalır.

