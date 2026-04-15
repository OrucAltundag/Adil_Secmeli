# NotebookLM Mega Sunum Promptu

Bu dosya, NotebookLM'ye tek parça halinde verilecek gelişmiş sunum promptunu içerir.  
Amaç: Projenin tamamını, teknik savunmaya uygun, canlı demo ile etkileşimli ve sayısal örneklerle desteklenmiş bir sunuma dönüştürmek.

## Kullanım

1. NotebookLM'ye proje kaynaklarını yükleyin.
2. Özellikle şu kaynakları ekleyin:
   - `docs/PROJE_SUNUM_TEKNIK_RAPORU.md`
   - `docs/egitim/ALGORITMA_DOKUMANTASYONU.md`
   - `docs/egitim/KAYNAK_KOD_REFERANSI.md`
   - varsa ekran görüntüleri ve ders analiz ekranı görselleri
3. Aşağıdaki promptu tek parça halinde NotebookLM'ye verin.

---

## Kopyalanacak Prompt

```text
Sen, teknik jüri önünde yapılacak bir bitirme projesi sunumunu hazırlayan üst düzey bir sunum mimarı, anlatı tasarımcısı ve teknik anlatım editörüsün.

Benim projemin adı: “Adil Seçmeli”.

Bu proje, üniversitelerde seçmeli ders kararlarını veri, çok kriterli analiz, kural tabanlı kontrol, belge tabanlı kriter yönetimi ve raporlama ile destekleyen bir akademik karar destek sistemidir.

Senden istediğim şey, bu proje için Türkçe, çok güçlü, savunulabilir, teknik ama anlaşılır, öğretici, jüri karşısında etkili olacak bir sunum kurgusu üretmendir.

Bu sunum:
- 25-30 dakika sürecek
- yaklaşık 18-24 slayttan oluşacak
- her slayt için hem slayta yazılacak içerik hem de konuşma notu içerecek
- sunum ile canlı proje gösterimini iç içe geçirecek
- proje bütününü anlatacak
- ama özellikle algoritmalar, veri akışı, ekran akışı, örnek ders hesaplamaları, canlı demo ve gelecek NLP planı üzerinde derinleşecek

Sunumu hazırlarken aşağıdaki kurallara kesinlikle uy:

1. Sunum dili tamamen Türkçe olsun.
2. Ton teknik, savunulabilir ve öğretici olsun.
3. Gerektiğinde benzetmeler kullan.
4. Sunum genel geçer ve soyut kalmasın; doğrudan bu projeye bağlı olsun.
5. Kaynaklarda olmayan şeyleri kesin gerçekmiş gibi uydurma.
6. Veri eksikse uydurma sayı verme; onun yerine placeholder kullan.
7. Projenin bütününü anlat; sadece algoritma özeti çıkarma.
8. Sunum, akademik jüriye hitap etsin ama anlatım ezberlenebilir ve doğal olsun.
9. Her önemli slayt tek bir ana fikir taşısın; aşırı kalabalık slaytlar üretme.
10. Her teknik kavram için gerektiğinde sezgisel anlatım da üret.

Bu sunumun amacı sadece “projeyi göstermek” değil. Aynı zamanda şu mesajı güçlü şekilde vermek:

“Bu proje, öznel seçmeli ders kararlarını veri temelli, izlenebilir, açıklanabilir ve operasyonel olarak uygulanabilir hale getiren bir karar destek sistemidir.”

Sunumda mutlaka şu başlık eksenleri yer alsın:
- problem tanımı
- neden bu problem önemli
- çözüm yaklaşımı
- genel mimari
- veri kaynakları
- ekranların kullanım akışı
- algoritmaların tek tek rolü
- algoritmaların girdileri ve çıktıları
- hesaplamaya etkileri
- kullanılmasalardı ne olacağı
- örnek ders hesaplamaları
- canlı demo geçişleri
- mevcut güçlü yönler
- mevcut sınırlılıklar
- gelecek geliştirmeler
- özellikle NLP entegrasyonu

Gerçek ekran/sekme adlarını aynen kullan:
- Kriter Giriş
- Algoritma Kontrol & Ders Lab
- Ders Analiz Laboratuvarı
- Havuz Yönetimi

Sunumun içinde canlı demo ile slaytlar dönüşümlü ilerlesin. Kural şu olsun:
- önce slaytta anlat
- sonra projede canlı göster
- sonra tekrar slayta dönüp teknik anlamını bağla

Her canlı geçiş için bana kullanabileceğim kısa ama etkili bir geçiş cümlesi yaz.

Sunumun zorunlu canlı demo senaryosu şu akışta olsun:

1. Önce Havuz Yönetimi ekranına gidilir.
   Burada müfredattaki veya havuzdaki dersler görülür.
   Ama kesinleşme puanlarının karar üretim süreci henüz tamamlanmamıştır veya kullanıcı o aşamaya henüz gelmemiştir.
   Buradaki amaç şu hissi vermektir:
   “Elimde dersler var ama bunların neden seçildiğini veya neden eleneceğini daha bilmiyorum.”

2. Sonra Kriter Giriş ekranına gidilir.
   Burada ilgili fakülte/bölüm/yıl için kriterlerin sisteme girildiği anlatılır.
   Bu aşamada sistemin veri ile beslendiği, yani kararın boşta oluşmadığı vurgulansın.

3. Sonra Algoritma Kontrol & Ders Lab ekranına gidilir.
   Burada algoritmanın çalıştırıldığı anlatılsın.
   Bu ekran, veri girişinden karar üretimine geçişi temsil etsin.

4. Sonra Ders Analiz Laboratuvarı üzerinden tek bir ders özelinde adım adım analiz gösterilsin.
   AHP, Trend/LR, TOPSIS, RF, DT, nihai karar ve karar gerekçesi burada anlatılsın.

5. Daha sonra yeni müfredat üretimi, havuzdan ders seçimi, karar mantığı ve sonuçlar bağlansın.

Sunumda proje bütün olarak ele alınsın. Yalnızca benim özellikle istediğim şeylere odaklanıp geri kalan yapıyı ihmal etme. Ama aşağıdaki alanlara özel slayt veya özel vurgu üret:
- algoritmaların amacı
- algoritmaların kullanılmaması durumunda ne eksik kalacağı
- girdi/çıktı mantığı
- iki gerçek ders örneği
- canlı demo akışı
- havuzdaki 50 sabit puan problemi
- anket etkisi
- gelecekte planlanan NLP etkisi
- en sonda benim sonradan dolduracağım boş sayfa

Sunumda proje şu çerçevede konumlandırılsın:

- Bu bir masaüstü tabanlı karar destek sistemidir.
- Arayüz tarafında Tkinter kullanılır.
- Veri katmanında SQLite / SQLAlchemy yaklaşımı vardır.
- Servis katmanı algoritmaları ve iş kurallarını yürütür.
- Gerektiğinde FastAPI ile entegrasyon yönü vardır.
- Excel / belge tabanlı veri aktarımı sistemin önemli bir parçasıdır.
- Raporlama, izlenebilirlik ve kriter dosyası kaynağı önemlidir.

Şimdi algoritma ve teknik kapsama kurallarını veriyorum. Bunlara kesinlikle uy:

Sunumda aşağıdaki algoritmalar, yöntemler ve teknik mantıklar yer alsın:
- AHP
- AHP ikili karşılaştırma mantığı
- özdeğer / özvektör mantığı
- tutarlılık oranı CR
- lambda_max
- Trend hesabı
- weighted average yaklaşımı
- re-scaling mantığı
- LR bağlamı
- TOPSIS
- normalize etme
- ideal çözüm mantığı
- yakınlık katsayısı
- kesinleşme puanı
- Random Forest
- Decision Tree
- kural tabanlı karar mantığı
- havuz / müfredat geçiş mantığı
- yerine ders seçme stratejisi
- durum makinesi / state machine mantığı
- anket katkısı
- raporlama mantığı
- belge tabanlı kriter kaydı

Her önemli algoritma veya teknik için aşağıdaki alt başlıklar zorunlu olsun:
- Ne işe yarar?
- Neden seçildi?
- Girdileri nelerdir?
- Çıktısı nedir?
- Hesaplamayı nasıl etkiler?
- Bu yöntem kullanılmasaydı ne olurdu?
- Kullanıldığında sistemde ne iyileşti?
- Gerçek hayatta neye benzetilebilir?

Şu benzetmeleri kullan ama gerekirse daha da zenginleştir:
- AHP = jüri üyelerinin kriter önemini oylaması
- TOPSIS = ideal adaya en yakın olanı seçme yarışı
- Trend = öğrencinin son yıllardaki performans grafiği
- re-scaling = takımda eksik oyuncu olduğunda sorumluluğun diğer oyunculara dağılması
- Random Forest = çok sayıda hakemin ortalama kararı
- Decision Tree = soru-cevapla dallanan karar kapısı
- durum makinesi = bir dersin akademik hayat döngüsü

Şimdi çok önemli bir içerik parçası veriyorum. Bunu mutlaka ayrı özel slayt olarak anlat:

Mevcut sistemde bir problem var:
- müfredattaki dersler girilen kriterlere göre artı ve eksi etkiler alarak kesinleşme puanı üretiyor
- ancak havuzda bekleyen dersler çoğu durumda 50 sabit puanda kalabiliyor
- bu durumda müfredattan bir ders düştüğünde yerine gelecek ders 50 puanlı adaylar arasından yeterince akıllı seçilemeyebilir

Mevcut çözüm bileşeni:
- anket etkisi bu adaylar arasında bazı dersleri öne çıkarmaya yardımcı oluyor

Gelecekte planlanan çözüm:
- ikinci bir etken olarak NLP tabanlı ders ilişkisi eklenecek
- amaç ceza vermek değil, pozitif katkı sağlamak
- eğer müfredatta yüksek puan alan bir ders ile havuzdaki başka bir ders arasında anlamlı benzerlik veya ilişki varsa
- bu ilişki oranı kadar havuzdaki derse pozitif kesinleşme puanı katkısı verilecek
- yani benzer ve güçlü bir dersle ilişkili olmak, havuzdaki dersi seçilme açısından öne çıkaracak
- negatif ceza olmayacak

Bu NLP bölümünü mevcutta çalışıyormuş gibi anlatma.
Onu açıkça “gelecekte yapmayı planladığım geliştirme” olarak konumlandır.
Ama teknik olarak güçlü, mantıklı ve ürün değeri yüksek bir gelecek vizyonu gibi anlat.

Şimdi iki gerçek ders örneğini sunuma zorunlu olarak dahil et.
Bu iki örneği karşılaştırmalı kullan.
Buradaki sayıları değiştirme.
Bu iki örneği slaytlaştırırken hem tablo hem yorum hem de konuşma notu üret.

ORNEK DERS 1
- Yıl: 2022
- Fakülte: Güzel Sanatlar Fakültesi
- Ders: 568 — Antik Mutfaklar
- Toplam Öğrenci: 100
- Geçen Öğrenci: 76
- Not Ortalaması: 56.0
- Kontenjan: 120
- Kayıtlı (Talep): 100
- Başarı Oranı: %76.0
- Doluluk Oranı: %83.3
- Anket Oranı: %0.5

AHP:
- Başarı: 0.5859 (%58.6)
- Trend: 0.2297 (%23.0)
- Popülerlik: 0.1371 (%13.7)
- Anket: 0.0473 (%4.7)
- CR = 0.0269
- lambda_max = 4.0727

Trend / LR:
- Yöntem: Ağırlıklı Ortalama
- Yıllık geçmiş: 2022: %76.0 x 100.0% (re-scaled, varsayılan 50%) -> Trend: 0.7600
- Tahmin (0-1): 0.7600
- Tahmin (0-100): 76.00

TOPSIS:
- Girişler (normalize): Başarı 0.7600, Trend 0.7600, Doluluk 0.8333, Anket 0.0051
- Yakınlık (0-1): 0.309900
- Kesinleşme (0-100): 30.99

RF Tahmini:
- Yöntem: sklearn RandomForest
- Tahmin statü: 0 (Havuzda)
- Kural: RF skoru (39.4) baraj (40.0) altında
- RF Skor: 39.38

DT Tahmini:
- Yöntem: sklearn DecisionTree
- DT statü tahmini: 1 (Müfredatta)

Karar Gerekçesi:
- Ders havuzdan müfredata alındı.
- Başarı: %76.0
- Doluluk: %83.3
- Ortalama not: 56.0
- Kesinleşme: 31.0

Bu örnekte özellikle şu yorumları yap:
- AHP ağırlıkları aynı olsa da anket katkısı çok düşük kaldığında TOPSIS skoru ciddi biçimde düşebilir.
- RF ile nihai kararın farklılaşabilmesi, makine öğrenmesinin tek belirleyici değil destekleyici olduğunun güçlü bir göstergesidir.
- Nihai karar, sistemin sadece tek bir modelle değil birleşik mantıkla çalıştığını göstermektedir.

ORNEK DERS 2
- Yıl: 2022
- Fakülte: Güzel Sanatlar Fakültesi
- Ders: 559 — İçecek Bilgisi ve Miksoloji
- Toplam Öğrenci: 82
- Geçen Öğrenci: 63
- Not Ortalaması: 61.0
- Kontenjan: 100
- Kayıtlı (Talep): 82
- Başarı Oranı: %76.8
- Doluluk Oranı: %82.0
- Anket Oranı: %27.7

AHP:
- Başarı: 0.5859 (%58.6)
- Trend: 0.2297 (%23.0)
- Popülerlik: 0.1371 (%13.7)
- Anket: 0.0473 (%4.7)
- CR = 0.0269
- lambda_max = 4.0727

Trend / LR:
- Yöntem: Ağırlıklı Ortalama
- Yıllık geçmiş: 2022: %76.8 x 100.0% (re-scaled, varsayılan 50%) -> Trend: 0.7683
- Tahmin (0-1): 0.7683
- Tahmin (0-100): 76.83

TOPSIS:
- Girişler (normalize): Başarı 0.7683, Trend 0.7683, Doluluk 0.8200, Anket 0.2769
- Yakınlık (0-1): 0.599000
- Kesinleşme (0-100): 59.90

RF Tahmini:
- Yöntem: sklearn RandomForest
- Tahmin statü: 1 (Müfredatta)
- Kural: RF skoru (56.4) baraj (40.0) üzerinde
- RF Skor: 56.38

DT Tahmini:
- Yöntem: sklearn DecisionTree
- DT statü tahmini: 1 (Müfredatta)

Karar Gerekçesi:
- Ders havuzdan müfredata alındı.
- Başarı: %76.8
- Doluluk: %82.0
- Ortalama not: 61.0
- Kesinleşme: 59.9

Bu örnekte özellikle şu yorumları yap:
- AHP ağırlıkları değişmeden, anket oranındaki fark TOPSIS sonucunu ciddi biçimde yukarı taşıyabiliyor.
- Aynı çekirdek algoritma yapısı içinde sadece belirli girdilerin değişmesi, nihai sonucu nasıl etkiliyor açıkça göster.
- Bu örneği bir önceki ders ile karşılaştır ve “anket etkisinin havuzdan müfredata alınma ihtimalini nasıl güçlendirdiğini” sezgisel olarak anlat.

Bu iki örnek için ayrıca şu özel karşılaştırma slaytlarını üret:
- Ders 1 ve Ders 2 karşılaştırma tablosu
- Hangi girdiler aynı kaldı, hangileri değişti?
- AHP neden aynı kaldı?
- TOPSIS neden değişti?
- RF neden farklılaştı?
- DT neden her iki durumda da müfredat yönünde kaldı?
- Nihai karar mekanizması neden tek modelden ibaret değil?

Sunumda, algoritmaların girdi-çıktı mantığını çok net ver.
Özellikle şu ayrımı açıkça kur:
- girdi verileri
- ara hesaplamalar
- model çıktıları
- nihai karar

Örneğin açıkça göster:
- AHP girdi olarak kriter önem ilişkilerini alır, çıktı olarak ağırlık üretir
- Trend geçmiş yıl performanslarını alır, çıktı olarak geleceğe taşınan başarı eğilimi üretir
- re-scaling eksik geçmiş yıl verilerinde ağırlıkları yeniden dağıtır
- TOPSIS normalize edilmiş kriterleri ve ağırlıkları alır, çıktı olarak yakınlık ve kesinleşme puanı üretir
- RF istatistiksel örüntü üzerinden bir destek tahmini üretir
- DT karar yolu ve açıklanabilir bir tahmin sunar
- nihai karar ise bu yapıların ve iş kurallarının birlikte değerlendirilmesiyle oluşur

Sunumun bir bölümünde şunu çok güçlü şekilde anlat:

“Bu projede makine öğrenmesi vardır, ancak sistemin çekirdek kararı salt kara kutu bir yapay zekâya teslim edilmemiştir. Çekirdek karar hattı açıklanabilir ve denetlenebilir kalmıştır.”

Yani şu mesajı ver:
- AHP ve TOPSIS ana çekirdek karar mantığını kurar
- kurallar ve durum makinesi operasyonel gerçekliği sağlar
- RF ve DT destekleyici analitik katmandır
- bu da projeyi hem teknik hem savunulabilir kılar

Şimdi sana placeholder kurallarını veriyorum.
Sunumda eksik veya benim sonradan düzenlemek isteyeceğim yerlere bu biçimde alan bırak:
- [DERS_ADI]
- [FAKULTE]
- [BOLUM]
- [YIL]
- [AHP_BASARI]
- [AHP_TREND]
- [AHP_POPULERLIK]
- [AHP_ANKET]
- [CR_DEGERI]
- [LAMBDA_MAX]
- [TREND_0_100]
- [TOPSIS_YAKINLIK]
- [KESINLESME_PUANI]
- [RF_SKOR]
- [DT_STATU]
- [ORTALAMA_NOT]
- [DOLULUK]
- [ANKET_ORANI]
- [BURAYA_SAYISAL_VERI_EKLE]
- [BURAYA_KENDI_YORUMUMU_EKLE]
- [BURAYA_GELECEK_PLANI_EKLE]

Sunumun en sonunda mutlaka özel bir sayfa olsun:

Başlık:
“Gelecekte Yapmayı Planladıklarım”

Bu sayfada benim sonradan doldurabilmem için bilinçli boş alanlar bırak:
- [BURAYA_GELECEK_PLANI_EKLE]
- [BURAYA_NLP_VIZYON_NOTU_EKLE]
- [BURAYA_UYGULAMA_HEDEFLERIMI_EKLE]
- [BURAYA_KENDI_SON_SOZLERIMI_EKLE]

Bu sayfa tam dolu olmasın.
Gerçekten bana sonradan ekleme alanı bırakacak biçimde tasarlansın.

Sunumun içinde ayrıca şu vurguları yap:
- proje bir bütün olarak tasarlanmıştır
- veri girişi olmadan karar üretilmez
- algoritma kontrol merkezi veri ile karar arasındaki köprüdür
- ders analiz laboratuvarı kararın adım adım şeffaf şekilde okunabildiği yerdir
- havuz yönetimi karar öncesi ve karar sonrası farkı görünür kılar
- belge tabanlı kriter yönetimi, gerçek hayatta izlenebilirlik sağlar

Şimdi çıktı formatını kesin olarak belirliyorum. Buna birebir uy:

Her slayt için şu alanları sırayla yaz:

Slayt No:
Başlık:
Amaç:
Slayta Yazılacak İçerik:
Konuşma Notu:
Canlı Demo Geçişi:
Boş Bırakılacak Sayısal Alanlar:

Ek kurallar:
- “Slayta Yazılacak İçerik” bölümü kısa, net ve slayta uygun olsun
- “Konuşma Notu” bölümü sahnede okuyabileceğim doğal anlatım şeklinde olsun
- “Canlı Demo Geçişi” sadece varsa yazılsın; yoksa “Yok” yaz
- “Boş Bırakılacak Sayısal Alanlar” kısmına yalnızca o slaytta sonradan değiştirebileceğim alanları yaz

Sunumda şu özel bölümler kesin olsun:
- Örnek Ders Hesaplama 1
- Örnek Ders Hesaplama 2
- İki Dersin Karşılaştırmalı Analizi
- Gelecek Geliştirmeler / NLP Entegrasyonu
- Benim Sonradan Dolduracağım Boş Not Alanı

Slaytların önerilen akış mantığı şu omurgayı izlesin:
- problem
- çözüm fikri
- proje özeti
- mimari
- veri kaynakları
- ekran akışı
- canlı demo başlangıcı
- kriter girişi mantığı
- algoritma kontrol merkezi
- AHP
- Trend / weighted average / re-scaling
- TOPSIS
- RF / DT
- kural tabanlı karar ve durum makinesi
- örnek ders 1
- örnek ders 2
- iki dersin karşılaştırması
- havuzdaki 50 puan problemi
- anket katkısı
- gelecekte NLP katkısı
- güçlü yönler ve sınırlılıklar
- boş gelecek planı sayfası
- kapanış

Ama bu iskeleti doğrudan kopyalamak zorunda değilsin; daha iyi bir anlatı kurabiliyorsan aynı zorunlu içerikleri koruyarak daha güçlü bir akış kur.

Şimdi çok önemli kalite kuralları:
- Sadece başlık listesi üretme; gerçekten konuşma notu üret
- Slaytlar arasında mantıksal akış kur
- Bir slaytta söylenen şey sonraki canlı gösterim ile bağlansın
- Teknik terimleri sadeleştir ama yüzeyselleştirme
- Öğretici ama çocukça olmayan bir dil kullan
- Jüri karşısında savunulabilir cümleler kur
- Özellikle “neden bu algoritma seçildi?” sorusuna güçlü cevaplar ver
- “bu algoritma olmasaydı ne eksik kalırdı?” sorusunu görünür kıl
- Proje sanki tek bir algoritmadan ibaretmiş gibi davranma

Son olarak, bu sunumu şu hedefe göre optimize et:

Ben bu sunumda hem projeyi anlatmak hem de karşımdaki kişilere gerçekten sistemi anladığımı göstermek istiyorum.
Bu yüzden sadece içerik değil, anlatım akışı da beni güçlü gösterecek biçimde kurgulansın.

Şimdi yukarıdaki tüm kurallara uyarak, eksiksiz, bütünlüklü, güçlü bir sunum çıktısı üret.
```
