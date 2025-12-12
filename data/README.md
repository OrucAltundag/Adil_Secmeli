# Adil Seçmeli (Python Sürümü)

## 🎯 Proje Başlığı
**Adil Seçmeli: Fakülte Bazlı Seçmeli Ders Öneri ve Atama Sistemi**

---

## 🧩 1. Proje Vizyonu
Üniversitelerde seçmeli ders seçimi çoğu zaman öğrencinin tercihinden ziyade öğretim üyesi, kontenjan veya sistem kısıtları tarafından şekillenmektedir.  
Bu durum, öğrencinin ilgisi dışında dersler almasına, düşük motivasyon ve başarısızlık oranlarının artmasına neden olur.  

**Adil Seçmeli**, bu sorunu veriye dayalı ve şeffaf bir yaklaşımla çözmeyi hedefler:  
Her dönem açılan seçmeli dersler **Başarı (B)**, **Popülerlik (P)** ve **Anket (A)** bileşenleriyle puanlanır; sistem bu skorları analiz ederek her öğrenciye adil, dengeli ve açıklanabilir bir şekilde **otomatik öneri ve atama** yapar.

Sonuç olarak:  
- Öğrenciler ilgilerine uygun dersleri seçebilir,  
- Yönetimler müfredatı veriyle şekillendirebilir,  
- Fakülteler performansa dayalı ders planlaması yapabilir.

---

## 🧠 2. Problem Tanımı
Geleneksel seçmeli ders süreçlerinde:
- Öğrenci talepleri sistematik biçimde toplanmıyor,  
- Başarısız derslerin tekrarında adalet sorunları doğuyor,  
- “Popülerlik” ve “başarı oranı” veriye dayalı değerlendirilmiyor,  
- Hangi dersin neden önerildiği açıklanamıyor.

Bu proje, bu eksikleri gidermek üzere **matematiksel bir skor motoru + Python tabanlı atama sistemi** geliştirir.  
Her dersin puanı aşağıdaki formülle hesaplanır:

> **S = wB·B_norm + wP·P_norm + wA·A_norm**

Burada:
- **B_norm:** Başarı bileşeni (ortalama not veya başarı oranı)  
- **P_norm:** Popülerlik bileşeni (tercih oranı)  
- **A_norm:** Anket bileşeni (öğrenci oylaması)  
- **wB, wP, wA:** Ağırlık parametreleri (config.json’dan okunur)

Sistemin hedefi, öğrencinin 4 seçmeli hakkının:
- **2’sini otomatik olarak** (en uygun & yüksek puanlı derslerden),
- **2’sini serbest seçimle** yapmasına izin vererek hibrit bir adalet modeli oluşturmaktır.

---

## 🧩 3. Proje Hedefleri
| No | Hedef | Çıktı |
|----|--------|--------|
| 1 | Adil ders öneri ve atama sistemi | `assignment_engine.py` |
| 2 | Veriye dayalı skor motoru | `score_engine.py` |
| 3 | Müfredat öneri sistemi | `mufredat_taslak.py` |
| 4 | Otomatik dinlendirme (engel) kontrolü | `cooldown_trigger.py` |
| 5 | Görsel ve sayısal raporlama | `report_generator.py`, PDF/HTML |
| 6 | Web arayüzü (öğrenci, danışman, yönetici) | `FastAPI + Jinja2` tabanlı web panel |
| 7 | Denetim & şeffaflık raporları | `logs/`, “Kim, neyi, neden atadı?” ekranı |

---

## ⚙️ 4. Teknolojik Altyapı
| Katman | Teknoloji | Açıklama |
|--------|------------|-----------|
| Veritabanı | SQLite + SQLAlchemy | Hafif, portatif, test dostu |
| Analitik | pandas, numpy, scikit-learn | Skor ve normalizasyon işlemleri |
| API & UI | FastAPI, Jinja2, Swagger | REST API + kullanıcı arayüzü |
| Raporlama | reportlab, plotly | PDF ve interaktif grafikler |
| Zamanlama | apscheduler | Dönemsel görev yönetimi |
| Test | pytest, faker | Otomatik test ve sahte veri üretimi |
| Versiyonlama | Git, mkdocs | Kod ve dokümantasyon yönetimi |

---

## 🔐 5. Şeffaflık ve Etik İlkeler
- Tüm parametreler (`wB`, `wP`, `wA`, eşikler, kontenjanlar) **versiyonlanır**.  
- Her atama kararı **gerekçeli ve açıklanabilir** olur.  
- Öğrenci verileri yalnızca anonimleştirilmiş raporlamada kullanılır.  
- Ağırlık veya kural değişiklikleri sistem tarafından otomatik loglanır.  

---

## 🧾 6. Beklenen Sonuçlar
- Öğrenci memnuniyetinde artış (%10–20 arası iyileşme hedefi)  
- Ders tekrar oranında azalma  
- Fakülte içi adalet skorlarında dengelenme  
- Dönem sonu geri bildirimlerinde veri temelli analizler

---

## 🗂️ 7. Proje Klasör Yapısı
```
adil_secmeli/
├── data/
│   ├── schema.sql
│   ├── seed.sql
│   └── config.json
├── src/
│   ├── etl/
│   │   ├── import_ubys.py
│   │   └── validate_data.py
│   ├── core/
│   │   ├── score_engine.py
│   │   ├── assignment_engine.py
│   │   └── normalization.py
│   ├── ui/
│   │   ├── api.py
│   │   └── templates/
│   └── utils/
│       ├── logger.py
│       └── scheduler.py
├── reports/
│   ├── course_cards.pdf
│   └── fairness_dashboard.html
└── tests/
    ├── test_score_engine.py
    ├── test_assignment_engine.py
    └── test_etl.py
```

---

## 📅 8. Geliştirme Takvimi
Proje, 3 fazda 12 haftada tamamlanacak:  
1. **Temeller ve veri modeli** (Hafta 1–4)  
2. **Skor ve atama motoru** (Hafta 5–8)  
3. **Anket, arayüz, raporlama** (Hafta 9–12)

---

## 👤 9. Yazar ve Danışman
- **Proje Sahibi:** _(Ad Soyad)_  
- **Danışman:** _(Danışman Adı)_  
- **Üniversite:** _(Üniversite Adı) Fakülte Adı_  
- **Yıl:** 2025  
