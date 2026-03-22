# Proje Yapisi ve Dosya Referansi

> **Proje:** Adil Secmeli — Fakulte Bazli Secmeli Ders Oneri ve Atama Sistemi
> **Tarih:** Mart 2026
> **Amac:** Bu belge, projede bulunan **her klasor ve dosyanin** ne ise yaradigini, neden var oldugunu ve sistemin butununde hangi role sahip oldugunu aciklar.

---

## Icindekiler

1. [Genel Bakis](#1-genel-bakis)
2. [Dizin Agaci](#2-dizin-agaci)
3. [Kok Dizin Dosyalari](#3-kok-dizin-dosyalari)
4. [app/ — Ana Uygulama Paketi](#4-app--ana-uygulama-paketi)
   - 4.1 [app/core/ — Cekirdek Altyapi](#41-appcore--cekirdek-altyapi)
   - 4.2 [app/db/ — Veritabani Katmani](#42-appdb--veritabani-katmani)
   - 4.3 [app/services/ — Is Mantigi ve Algoritmalar](#43-appservices--is-mantigi-ve-algoritmalar)
   - 4.4 [app/ui/ — Kullanici Arayuzu (Tkinter)](#44-appui--kullanici-arayuzu-tkinter)
   - 4.5 [app/api/ — REST API (FastAPI)](#45-appapi--rest-api-fastapi)
   - 4.6 [app/etl/ — Veri Aktarim Betikleri](#46-appetl--veri-aktarim-betikleri)
   - 4.7 [app/scripts/ — Yardimci ve Bakim Betikleri](#47-appscripts--yardimci-ve-bakim-betikleri)
   - 4.8 [app/utils/ — Genel Yardimci Araclar](#48-apputils--genel-yardimci-araclar)
   - 4.9 [app/tests/ — Birim ve Entegrasyon Testleri](#49-apptests--birim-ve-entegrasyon-testleri)
5. [data/ — Veritabani, Sema ve Kaynak Veriler](#5-data--veritabani-sema-ve-kaynak-veriler)
6. [docs/ — Proje Dokumantasyonu](#6-docs--proje-dokumantasyonu)
7. [exports/ — Disa Aktarim Ciktilari](#7-exports--disa-aktarim-ciktilari)
8. [logs/ — Uygulama Log Kayitlari](#8-logs--uygulama-log-kayitlari)
9. [reports/ — Olusturulan Raporlar](#9-reports--olusturulan-raporlar)
10. [_arsiv/ — Arsivlenmis / Eski Dosyalar](#10-_arsiv--arsivlenmis--eski-dosyalar)
11. [.github/ — GitHub Yapilandirmasi](#11-github--github-yapilandirmasi)
12. [.vscode/ — VS Code / Cursor Ayarlari](#12-vscode--vs-code--cursor-ayarlari)
13. [Mimari Ozet ve Veri Akisi](#13-mimari-ozet-ve-veri-akisi)

---

## 1. Genel Bakis

**Adil Secmeli**, universitelerde secmeli ders secim surecini **veriye dayali ve adil** hale getirmeyi amaclar. Sistem su bilesenlerden olusur:

| Bilesen | Teknoloji | Gorev |
|---------|-----------|-------|
| Masaustu Uygulamasi | Tkinter (Python) | Kriter girisi, algoritma calistirma, havuz yonetimi, raporlama |
| Karar Motorlari | AHP, TOPSIS, LR, RF, DT (scikit-learn) | Ders skorlama, siralama, gelecek tahmini |
| NLP Motoru | TF-IDF + Cosine Similarity (scikit-learn) | Dersler arasi benzerlik analizi |
| Veritabani | SQLite + SQLAlchemy | Ders, mufredat, kriter, performans, populerlik, havuz verileri |
| REST API | FastAPI | Universite OBS/kayit sistemi entegrasyonu |
| ETL | pandas + openpyxl | Excel'den toplu veri aktarimi |

---

## 2. Dizin Agaci

```
Adil_Secmeli_Python/
│
├── app/                          # Ana uygulama paketi
│   ├── __init__.py
│   ├── main.py                   # Masaustu uygulama giris noktasi
│   │
│   ├── core/                     # Cekirdek yapilandirma ve durum
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── state.py
│   │
│   ├── db/                       # Veritabani erisim katmani
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── sqlite_db.py
│   │
│   ├── services/                 # Is mantigi ve algoritmalar
│   │   ├── ai_engine.py
│   │   ├── calculation.py
│   │   ├── course_analyzer.py
│   │   ├── db.py
│   │   ├── havuz_karar.py
│   │   ├── rules_engine.py
│   │   ├── similarity.py
│   │   └── similarity_engine.py
│   │
│   ├── ui/                       # Tkinter kullanici arayuzu
│   │   ├── __init__.py
│   │   ├── style.py
│   │   └── tabs/
│   │       ├── __init__.py
│   │       ├── analysis_tab.py
│   │       ├── calc_tab.py
│   │       ├── course_analysis_tab.py
│   │       ├── criteria_page.py
│   │       ├── pool_tab.py
│   │       ├── relations_tab.py
│   │       ├── tools_tab.py
│   │       └── view_tab.py
│   │
│   ├── api/                      # REST API (FastAPI)
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── routes.py
│   │
│   ├── etl/                      # Excel veri aktarim betikleri
│   │   ├── import_dersler_master.py
│   │   ├── import_kriterler_excel.py
│   │   └── import_mufredat_excel.py
│   │
│   ├── scripts/                  # Yardimci / tek seferlik betikler
│   │   ├── analyze_duplicates.py
│   │   ├── cleanup_duplicate_ders.py
│   │   ├── export_missing_criteria_workbook.py
│   │   ├── fill_pool_manual.py
│   │   ├── fix_havuz_table.py
│   │   ├── havuz_2022_doldur.py
│   │   ├── havuz_kumulatif_doldur.py
│   │   ├── import_real_data.py
│   │   ├── init_script.py
│   │   ├── merge_duplicate_ders.py
│   │   ├── migrate_anket_columns.py
│   │   ├── reset.py
│   │   ├── seed_criteria_from_workbook.py
│   │   ├── smart_data_generator.py
│   │   └── update_db_for_pool.py
│   │
│   ├── utils/                    # Ortak yardimci fonksiyonlar
│   │   ├── etl.py
│   │   ├── import_excel.py
│   │   └── logger.py
│   │
│   └── tests/                    # Birim ve entegrasyon testleri
│       ├── check_db_results.py
│       ├── reset_counters.py
│       ├── test_assignment_engine.py
│       ├── test_curriculum_generation.py
│       ├── test_db.py
│       ├── test_etl.py
│       ├── test_havuz_karar.py
│       ├── test_score_engine.py
│       ├── test_similarity.py
│       └── test_single_analysis.py
│
├── data/                         # Veritabani ve kaynak veriler
│   ├── adil_secmeli.db
│   ├── config.json
│   ├── schema.sql
│   ├── schema_updated.sql
│   ├── seed.sql
│   ├── 2022_Mufredat.xlsx
│   ├── dersler_master.xlsx
│   ├── README.md
│   ├── KRITER_EXCEL_KULLANIM.md
│   └── MUFREDAT_EXCEL_KULLANIM.md
│
├── docs/                         # Proje dokumantasyonu
│   ├── MODUL_HARITASI.md
│   ├── ALGORITMA_KARSILASTIRMA_RAPORU.md
│   ├── ALGORITMA_KONTROL_DERS_LAB_DOSYALARI.md
│   ├── KESINLESME_NEXT_YEAR_ANALIZ.md
│   ├── PROJE_ANALIZ_RAPORU.md
│   ├── PROJE_YAPISI.md              ← Bu belge
│   ├── PROJE_YENIDEN_YAPILANDIRMA_PLANI.md
│   ├── system_roles.md
│   ├── terminology.md
│   ├── UNIVERSITE_ENTEGRASYON_PLANI.md
│   └── egitim/
│       ├── ALGORITMA_DOKUMANTASYONU.md
│       └── KAYNAK_KOD_REFERANSI.md
│
├── exports/                      # CSV/Excel disa aktarim ciktilari
│   └── .gitkeep
│
├── logs/                         # Calisma zamani log dosyalari
│   └── app.log
│
├── reports/                      # Olusturulan raporlar (PDF, HTML, XLSX)
│   ├── course_cards.pdf
│   ├── ders_performans_raporu.xlsx
│   └── fairness_dashboard.html
│
├── _arsiv/                       # Arsivlenmis / artik kullanilmayan dosyalar
│   ├── yedek/
│   ├── gecici/
│   ├── ornekler/
│   └── eski_ciktilar/
│
├── .github/
│   └── copilot-instructions.md
│
├── .vscode/
│   └── settings.json
│
├── .editorconfig                 # Editor format kurallari
├── .gitignore                    # Git tarafindan yoksayilan dosyalar
├── config.json                   # Kok yapilandirma (DB yolu)
├── main.py                       # Kisayol giris noktasi
├── README.md                     # Proje tanitimi ve kurulum
└── requirements.txt              # Python bagimliliklari
```

---

## 3. Kok Dizin Dosyalari

| Dosya | Amac | Neden Var? |
|-------|------|------------|
| `main.py` | Proje kokunden `python main.py` ile baslatma kisayolu. `sys.path`'i ayarlayip `app.main.AdilSecmeliApp`'i calistirir. | Kullanicinin kok dizinden tek komutla uygulamayi baslatabilmesi icin. `python -m app.main` alternatifi de calisir. |
| `README.md` | Proje tanitimi, kurulum adimlari, calistirma komutlari ve dokumantasyon baglantilari. | Her projenin ihtiyac duydugu "ilk okunan" belge. Yeni gelistiricinin hizla baslamasi icin. |
| `requirements.txt` | Python bagimliliklarinin listesi (`pip install -r requirements.txt`). scikit-learn, pandas, openpyxl, SQLAlchemy, FastAPI, matplotlib, seaborn vb. | Sanal ortam kurarken tum paketlerin tek komutla yuklenmesini saglar. Surum uyumunu garanti eder. |
| `config.json` | Veritabani dosya yolunu icerir (`db_path`). | Uygulama baslarken veritabaninin nerede oldugunu `app/core/config.py` buradan okur. Yol degistiginde sadece bu dosya guncellenir. |
| `.gitignore` | Git'in izlememesi gereken dosya/klasorleri tanimlar: `__pycache__`, `venv/`, `*.db` (opsiyonel), `logs/`, `_arsiv/` vb. | Depo boyutunu kucuk tutar, gereceksiz dosyalarin commit edilmesini engeller. |
| `.editorconfig` | Editor geneli format kurallari: UTF-8, LF satir sonu, Python icin 4 bosluk girinti. | Farkli editorlerde (VS Code, PyCharm, Vim) tutarli kod formati saglar. |

---

## 4. app/ — Ana Uygulama Paketi

`app/` altindaki her sey uygulamanin calisma zamani kodudur. Python paket yapisini takip eder (`__init__.py` dosyalari ile).

| Dosya | Amac |
|-------|------|
| `app/__init__.py` | `app` klasorunu Python paketi yapar. Icerik bos olabilir. |
| `app/main.py` | **Ana giris noktasi.** Tkinter penceresi olusturur, veritabani baglar, sekmeleri yukler. `AdilSecmeliApp` sinifi burada tanimlidir. |

### 4.1 app/core/ — Cekirdek Altyapi

Uygulamanin omurgasini olusturan, UI veya veritabanindan bagimsiz yapilandirma modulleri.

| Dosya | Amac | Neden Var? |
|-------|------|------------|
| `config.py` | `config.json` dosyasini okur, `DB_PATH` gibi sabitleri proje geneline sunar. | Yapilandirma tek noktadan yonetilsin, hardcoded yol kalmasin diye. |
| `state.py` | `AppState` sinifi: secili fakulte, yil, donem gibi UI durumlarini merkezi tutar. Degisiklikleri dinleyicilere (listener) bildirir. | Sekmeler arasi iletisimi saglar. Bir sekmede fakulte degistiginde diger sekmeler otomatik guncellenir. |
| `exceptions.py` | Ozel hata siniflari: `StudentNotFoundError`, `CourseQuotaExceededError` vb. | Anlamli hata mesajlari ve hata turune gore farkli islem yapabilme icin. Genel `Exception` yerine spesifik hatalar firlatilir. |

### 4.2 app/db/ — Veritabani Katmani

SQLite veritabanina erisim icin iki farkli yaklasim sunar.

| Dosya | Amac | Neden Var? |
|-------|------|------------|
| `models.py` | SQLAlchemy ORM modelleri: `Fakulte`, `Ders`, `Mufredat`, `Havuz`, `DersKriterleri`, `Performans`, `Populerlik`, `Skor` vb. | Veritabani tablolarini Python siniflari olarak tanimlar. Tip guvenligi, iliski tanimlari ve ORM islemleri icin. |
| `database.py` | SQLAlchemy `engine`, `SessionFactory`, `scoped_session` yonetimi. `config.json`'dan DB yolunu okur, baglanti havuzu olusturur. | Thread-safe veritabani oturumu saglar. Birden fazla sekme/thread ayni anda DB'ye eristiginde cakisma olmaz. |
| `sqlite_db.py` | Hafif `sqlite3` sarmalayici: `connect()`, tablo listeleme, `read_df()` (pandas DataFrame olarak okuma), `run_sql()` (serbest SQL). | Tkinter tarafindaki bazi islemler (view_tab, pool_tab) icin SQLAlchemy yerine daha hafif ve hizli dogrudan erisim gerektiginde kullanilir. |

### 4.3 app/services/ — Is Mantigi ve Algoritmalar

Projenin "beyni". Tum karar verme, puanlama ve tahmin algoritmalari burada.

| Dosya | Amac | Neden Var? |
|-------|------|------------|
| `calculation.py` | **Karar Motoru.** AHP agirlik hesabi, TOPSIS siralama, ders basari puani hesaplama, mufredat uretim pipeline'i. | Projenin en kritik dosyasi. "Hangi ders havuza alinmali, hangisi dusurulmeli?" sorusuna cevap verir. |
| `ai_engine.py` | **Makine Ogrenmesi Motoru.** scikit-learn tabanli Linear Regression (trend), Random Forest (siniflandirma/regresyon) ve Decision Tree modelleri. | Gecmis yil verilerinden gelecek basari/populerlik tahmini yapar. Hesaplama motorunun tahmin bilesenini saglar. |
| `course_analyzer.py` | **Tek Ders Analiz Servisi.** Secilen bir ders icin tum algoritmalari (AHP, TOPSIS, LR, RF, DT) sirayla calistirir, sonuclari birlestirir. | UI'dan "Bu dersi analiz et" denildiginde tek noktadan tum sonuclari toplar. Thread-safe tasarlanmistir. |
| `havuz_karar.py` | **Durum Makinesi (State Machine).** Havuz kayitlarinin statu gecislerini yonetir: `ADAY → AKTIF → DUSEN → CIKARILAN`. Sayac ve skor esik kontrolu. | Bir dersin havuzdaki yasam dongusunu belirler. "3 donem ust uste dusuk skor alan ders havuzdan cikarilir" gibi kurallari uygular. |
| `rules_engine.py` | **Is Kurallari Motoru.** Ogrenci yeterlilik kontrolu, ders kontenjani, ders cakismasi, onkosul dogrulama. | Ders atamasi sirasinda is kurallarini (business rules) kontrol eder. Ornegin: "Ogrenci bu dersi daha once almis mi?" |
| `similarity.py` | **NLP Benzerlik Motoru (SQLAlchemy versiyonu).** TF-IDF + Cosine Similarity ile ders icerikleri arasindaki benzerligi hesaplar. Sonuclari `ders_iliski` tablosuna yazar. | "Matematik I ile Matematik II ne kadar benzer?" sorusuna NLP tabanli cevap verir. Iliskiler sekmesinde kullanilir. |
| `similarity_engine.py` | **NLP Benzerlik Motoru (sqlite3 versiyonu).** Ayni TF-IDF + Cosine Similarity algoritmasi, ancak dogrudan `sqlite3` kullanir. | `similarity.py`'nin daha hafif alternatifi. Bazi UI bilesenleri SQLAlchemy yerine dogrudan sqlite3 ile calisir. |
| `db.py` | Thread-safe `db_session` context manager'i. SQLAlchemy oturumunu acar, commit/rollback yapar ve kapatir. | Tum servisler veritabanina bu context manager uzerinden erisir. Her islem icin ayri oturum acar, islem bitince kapatir. |

### 4.4 app/ui/ — Kullanici Arayuzu (Tkinter)

Masaustu uygulamasinin tum gorsel bilesenleri.

| Dosya | Amac | Neden Var? |
|-------|------|------------|
| `style.py` | Merkezi gorsel tema: renk paleti, fontlar, `apply_style()` fonksiyonu. ttk widgetlarina tutarli gorunum verir. | Tum sekmeler ayni gorunumu paylasir. Renk degisikligi tek noktadan yapilir. |

#### app/ui/tabs/ — Sekmeler

Her sekme, uygulamanin ana penceresinde bir "tab" olarak gorunur.

| Dosya | Sekme Adi | Amac | Neden Var? |
|-------|-----------|------|------------|
| `calc_tab.py` | **Hesaplama & Test** | Ana kontrol sekmesi. Kriter girisi, algoritma lab, iliskiler ve havuz alt sekmelerini bir arada sunar. | Diger alt sekmeleri (criteria_page, course_analysis_tab, relations_tab, pool_tab) barindiran ust seviye konteyner. |
| `criteria_page.py` | **Kriter Girisi** | Ders bazli kriter verisi girisi: toplam ogrenci, gecen ogrenci, ortalama, kontenjan. Veritabanina kaydeder. | Algoritmalarin calisabilmesi icin giris verisini saglar. Kullanici buradan yil/donem bazinda kriter girer. |
| `course_analysis_tab.py` | **Algoritma Lab** | Tek ders secip tum algoritmalari (AHP, TOPSIS, LR, RF, DT) calistirma. Aranabilir ders listesi, tam ekran modu. | Bir dersin detayli analizini gorsellestirmeyi saglar. "SearchableCombo" arama ozellikli ders secimi burada. |
| `relations_tab.py` | **Iliskiler** | Secilen ders icin NLP tabanli benzerlik analizi, NetworkX grafi, en benzer dersler tablosu. | Dersler arasi iliskileri gorsellestirerek karar vericiye ek bilgi saglar. |
| `pool_tab.py` | **Havuz** | Havuz yonetimi: fakulte/bolum/yil/donem bazli havuz gorunumu, saglik kontrolu, ogrenci simulasyonu. | Havuzdaki derslerin durumunu izleme, mufredat olusturma ve simulasyon yapma. |
| `analysis_tab.py` | **Analiz / Dashboard** | KPI kartlari (toplam ders, ortalama skor vb.) ve matplotlib/seaborn grafikleri. | Yoneticiye genel bakis saglayan gorsel ozet paneli. |
| `tools_tab.py` | **Rapor & Araclari** | Filtreli ozetler, CSV/Excel disa aktarim, yedekleme, mufredat yukleme, statu esitleme. | Toplu islemleri ve raporlamayi merkezi bir yerden yapmayi saglar. |
| `view_tab.py` | **Tablo Goruntule (Admin)** | Tum veritabani tablolarini listeleme, sutun bazli filtreleme, sayfalama, serbest SQL calistirma. | Veritabanini dogrudan inceleme ve hata ayiklama icin guclu admin paneli. |

### 4.5 app/api/ — REST API (FastAPI)

Universite OBS/kayit sistemi ile entegrasyon icin dis arayuz.

| Dosya | Amac | Neden Var? |
|-------|------|------------|
| `main.py` | FastAPI uygulama tanimlamasi. `uvicorn` ile calistirilir. | REST API sunucusunun giris noktasi. Swagger UI dokumantasyonu otomatik olusur (`/docs`). |
| `routes.py` | API endpoint'leri: ders listeleme, skor sorgulama, havuz durumu, mufredat bilgisi. | Dis sistemlerin (OBS, kayit sistemi) projedeki verilere HTTP uzerinden erisebilmesini saglar. |

### 4.6 app/etl/ — Veri Aktarim Betikleri

Excel dosyalarindan veritabanina toplu veri aktarimi icin ozel modüller.

| Dosya | Amac | Neden Var? |
|-------|------|------------|
| `import_dersler_master.py` | `dersler_master.xlsx` dosyasindan fakulte, bolum ve ders kayitlarini SQLite'a yukler. | Ilk kurulumda ders veritabanini olusturmak icin. Yeni ders eklendiginde toplu yukleme yapar. |
| `import_kriterler_excel.py` | Excel'den ders kriterlerini toplu olarak `ders_kriterleri`, `performans` ve `populerlik` tablolarina yazar. | Her donem yuz lerce kriter girisini tek tek yapmak yerine Excel'den toplu aktarim saglar. |
| `import_mufredat_excel.py` | Excel'den mufredat ve `mufredat_ders` iliskilerini SQLite'a aktarir. | Guz/Bahar mufredat listelerini toplu olarak sisteme girmeyi saglar. |

### 4.7 app/scripts/ — Yardimci ve Bakim Betikleri

Cogu **tek seferlik** veya **gerektiginde calistirilan** yardimci betiklerdir. Uygulamanin normal calismasinda kullanilmazlar.

| Dosya | Amac | Ne Zaman Kullanilir? |
|-------|------|---------------------|
| `init_script.py` | Gecmis yil secim ozetine gore havuz durumlarini simule eden prototip `DecisionEngine`. | Ilk kurulumda havuz verisi olusturmak icin. |
| `smart_data_generator.py` | Performans, populerlik ve skor tablolari icin rastgele test verisi uretir. | Gelistirme/test asamasinda gercek veri yokken sistem denemek icin. |
| `havuz_kumulatif_doldur.py` | Havuzu tum yillar icin kumulatif doldurur; onceki yilin durumu sonraki yilin kaydini uretir. | Ilk kurulumda veya yeniden baslatmada tum yillarin havuz verisini olusturmak icin. |
| `havuz_2022_doldur.py` | 2022 akademik yili mufredat referansina gore havuz kayitlarini olusturur. | 2022 yili icin spesifik havuz verisi gerektiginde. |
| `fill_pool_manual.py` | Belirli bir fakulte icin havuz tablosunu temizleyip elle havuz kaydi olusturur. | Tek bir fakultenin havuz verisini sifirdan olusturmak gerektiginde. |
| `import_real_data.py` | Excel/CSV kaynakli gercek ders verisini SQLite'a aktarir. | Gercek universite verileri geldiginde toplu yukleme icin. |
| `seed_criteria_from_workbook.py` | Excel/CSV'den kriter, performans ve populerlik verisini yukler. `--apply` parametresi ile gercek yazim yapar (varsayilan: dry-run). | Toplu kriter verisi aktariminda. Dry-run oncelikle kontrollu calisir. |
| `export_missing_criteria_workbook.py` | Mufredatta olup kriteri eksik dersleri Excel ve CSV olarak disa aktarir. | Hangi derslerin kriter girisinin eksik oldugunu tespit etmek icin. |
| `analyze_duplicates.py` | Veritabaninda mukerrer (duplicate) ders kayitlarini analiz eder, rapor uretir. | Veri temizligi oncesi durum tespiti. |
| `cleanup_duplicate_ders.py` | Ayni isim/ozellikteki yinelenen derslerde kucuk ID'yi birakip digerlerini siler, yabanci anahtarlari gunceller. | Mukerrer kayit temizliginde. |
| `merge_duplicate_ders.py` | Ayni isimde (ayni fakultede) birden fazla ders kaydini en kucuk ID'de birlestirir. | `cleanup_duplicate_ders.py`'ye benzer, farkli birlestirme stratejisi uygular. |
| `fix_havuz_table.py` | Havuz tablosunu kaldirip guncel sema ile yeniden olusturur. | Sema degisikligi sonrasi havuz tablosunu yenilemek icin. |
| `migrate_anket_columns.py` | Veritabanina anket sutunlarini ekler. | Yeni anket alanlari eklenmesi gerektiginde (migrasyon). |
| `update_db_for_pool.py` | Havuz ve ders tablolarina havuz yonetimine ozel yeni sutunlar ekler. | Havuz ozelliginin ilk entegrasyonunda sema guncelleme. |
| `reset.py` | Havuz tablosundaki statu, sayac ve skor alanlarini topluca sifirlar. | Test/gelistirme sirasinda havuzu basa almak icin. |

### 4.8 app/utils/ — Genel Yardimci Araclar

| Dosya | Amac | Neden Var? |
|-------|------|------------|
| `logger.py` | Merkezi loglama altyapisi. Dosya (`logs/app.log`) ve konsola (stdout) cift kanalli log yazar. `log_operation()` ile islem bazli yapisal kayit. | Hata ayiklama ve islem takibi icin. Tum modüller bu logger'i kullanir. |
| `import_excel.py` | Excel veri aktarim yardimcilari: temizlik, upsert, fakulte/bolum eslestirmesi, hata loglama. | ETL betiklerinin ortaklasa kullandigi alt seviye fonksiyonlar. |
| `etl.py` | Excel'den ogrenci kayitlarini okuma gibi ek ETL yardimcilari. | Kucuk, tekrar eden veri aktarim islemleri icin. |

### 4.9 app/tests/ — Birim ve Entegrasyon Testleri

Algoritma ve servislerin dogrulugunu kontrol eden test dosyalari.

| Dosya | Ne Test Eder? |
|-------|---------------|
| `test_havuz_karar.py` | Havuz durum makinesi (statu gecisleri, sayac artisi, esik kontrolleri). |
| `test_score_engine.py` | Skor hesaplama motorunun dogrulugu. |
| `test_similarity.py` | NLP benzerlik motorunun (TF-IDF + Cosine) dogrulugu. |
| `test_assignment_engine.py` | Ders atama motorunun is kurallarini dogru uygulayip uygulamadigi. |
| `test_curriculum_generation.py` | Mufredat uretim pipeline'inin beklenen sonuclari uretip uretmedigi. |
| `test_single_analysis.py` | Tek ders analiz servisinin (course_analyzer) entegrasyon testi. |
| `test_db.py` | Veritabani baglantisi ve temel CRUD islemleri. |
| `test_etl.py` | ETL aktarim betiklerinin dogrulugu. |
| `check_db_results.py` | Veritabanindaki sonuclari hizli kontrol etmek icin yardimci betik. |
| `reset_counters.py` | Test sirasinda sayaclari sifirlamak icin yardimci betik. |

---

## 5. data/ — Veritabani, Sema ve Kaynak Veriler

Bu klasor, uygulamanin calismasi icin gerekli veri dosyalarini icerir.

| Dosya | Amac | Neden Var? |
|-------|------|------------|
| `adil_secmeli.db` | **Ana SQLite veritabani.** Tum fakulte, ders, mufredat, kriter, performans, havuz vb. veriler burada. | Uygulamanin tek veri kaynagi. |
| `config.json` | `data/` icindeki alternatif yapilandirma (DB yolunu icermez, kok dizindeki `config.json` kullanilir). | Eski surum artigi; kok dizindeki `config.json` aktif yapilandirmadir. |
| `schema.sql` | Veritabani sema tanimlamasi (CREATE TABLE ifadeleri). | Veritabanini sifirdan olusturmak veya semayi incelemek icin referans. |
| `schema_updated.sql` | Guncellenenmis sema (havuz, anket vb. yeni alanlar dahil). | `schema.sql`'in genisletilmis surumu. Migrasyon sonrasi guncel yapi. |
| `seed.sql` | Ornek veriler (INSERT ifadeleri): ornek fakulteler, dersler, ogrenciler. | Ilk kurulumda veya demo icin baslangic verisi saglar. |
| `2022_Mufredat.xlsx` | 2022 akademik yili mufredat verileri (Excel). | ETL betikleri ile mufredat tablosunu doldurmak icin kaynak veri. |
| `dersler_master.xlsx` | Tum derslerin ana listesi (Excel): kod, ad, kredi, AKTS, fakulte. | `import_dersler_master.py` ile ders tablosunu doldurmak icin kaynak veri. |
| `README.md` | `data/` klasorunun icerigi ve projenin vizyon aciklamasi. | Klasorun amacini anlatan rehber belge. |
| `KRITER_EXCEL_KULLANIM.md` | Kriter Excel toplu yukleme kilavuzu: gerekli/opsiyonel kolonlar, ornek format. | Kullanicinin dogru formatta Excel hazirlayabilmesi icin kullanim rehberi. |
| `MUFREDAT_EXCEL_KULLANIM.md` | Mufredat Excel formati kilavuzu: guz/bahar sutunlari, ornek yapi. | Mufredat Excel'inin dogru hazirlanmasi icin kullanim rehberi. |

---

## 6. docs/ — Proje Dokumantasyonu

Projenin teknik ve egitimsel dokumanlari.

### Kok docs/ Dosyalari

| Dosya | Amac | Neden Var? |
|-------|------|------------|
| `MODUL_HARITASI.md` | Projedeki tum `.py` dosyalarinin listesi ve kisa aciklamalari. | Hangi dosyanin ne ise yaradigini hizla bulmak icin harita. |
| `PROJE_YAPISI.md` | **Bu belge.** Proje yapisinin ve tum dosyalarin detayli aciklamasi. | Projeyi yeni taniyan birinin tum yapıyı anlaması icin. |
| `ALGORITMA_KARSILASTIRMA_RAPORU.md` | AHP, TOPSIS, RF, DT gibi algoritmalarin karsilastirilmasi ve projeye uygunluk degerlendirmesi. | Neden bu algoritmalarin secildigini aciklarken akademik gerekce saglar. |
| `ALGORITMA_KONTROL_DERS_LAB_DOSYALARI.md` | "Algoritma Kontrol & Ders Lab" sekmesi ile ilgili dosyalarin envanteri. | Bu sekmenin hangi dosyalara bagimli oldugunu dokumante eder. |
| `KESINLESME_NEXT_YEAR_ANALIZ.md` | Kesinlesme puani hesabi ve gelecek yil mufredat uretiminde ilgili dosyalarin rolleri. | Karmasik pipeline'in hangi dosyalardan gectigini aciklarken yol haritasi. |
| `PROJE_ANALIZ_RAPORU.md` | Projeyi tamamlamak ve universiteye entegre etmek icin eksiklik/oncelik analizi. | Gelistirme yol haritasi ve onceliklendirme. |
| `PROJE_YENIDEN_YAPILANDIRMA_PLANI.md` | Veri akisini merkezilestirme ve gercek senaryoya uyum icin yeniden yapilandirma plani. | Gelecek refactoring calismalari icin mimari plan. |
| `system_roles.md` | Ogrenci, ogretim uyesi, yonetici gibi paydas rolleri ve sorumluluk haritasi. | Sistemin kimlere hizmet ettigini ve her rolun ne yapabildigini tanimlar. |
| `terminology.md` | Skor, basari, populerlik, anket gibi sistem terimlerinin sozlugu. | Proje genelinde tutarli terminoloji kullanimi icin referans. |
| `UNIVERSITE_ENTEGRASYON_PLANI.md` | Universite ortamina entegrasyon icin adim adim plan ve test stratejisi. | Gercek ortama gecis sureci icin yol haritasi. |

### docs/egitim/ — Egitim Belgeleri

| Dosya | Amac | Neden Var? |
|-------|------|------------|
| `ALGORITMA_DOKUMANTASYONU.md` | AHP, TOPSIS, Trend/LR, RF, DT, State Machine, NLP ve is kurallari algoritmalarinin detayli aciklamasi. Teori, kod ornekleri ve adim adim yurume. | Ogrencilerin projedeki algoritmalari ogrenebilmesi icin egitim belgesi. |
| `KAYNAK_KOD_REFERANSI.md` | 10 kritik servis dosyasinin tam kaynak kodu, kisa ozetleri ve bagimlilik haritasi. | Tum onemli kodlara tek belgeden erismek isteyen kisiler icin referans. |

---

## 7. exports/ — Disa Aktarim Ciktilari

Uygulama icerisindeki "Rapor & Araclar" sekmesinden olusturulan CSV/Excel dosyalari burada birikir.

| Dosya | Amac |
|-------|------|
| `.gitkeep` | Bos klasorun Git'te izlenebilmesi icin yer tutucu. Klasorun kendisi gerekli, icerik dinamik olusur. |

> Disa aktarim dosyalari kullaniciya ozeldir ve `.gitignore` ile izlenmez.

---

## 8. logs/ — Uygulama Log Kayitlari

| Dosya | Amac |
|-------|------|
| `app.log` | Calisma zamani log kayitlari. `app/utils/logger.py` tarafindan yazilir. Hata ayiklama, islem gecmisi ve performans izleme icin. |

> Log dosyalari `.gitignore` ile izlenmez. Her calistirmada eklenerek buyur.

---

## 9. reports/ — Olusturulan Raporlar

Uygulama tarafindan uretilen gorsel raporlar.

| Dosya | Amac |
|-------|------|
| `course_cards.pdf` | Ders bilgi kartlari (PDF formati). Her dersin ozet bilgilerini icerir. |
| `ders_performans_raporu.xlsx` | Ders performans verileri (Excel). Yillara gore basari, populerlik, trend bilgileri. |
| `fairness_dashboard.html` | Adalet gostergesi (HTML). Secmeli ders dagiliminun ne kadar adil oldugunu gorsellestiren interaktif sayfa. |

---

## 10. _arsiv/ — Arsivlenmis / Eski Dosyalar

Artik aktif olarak kullanilmayan ancak referans veya yedekleme amacli saklanan dosyalar.

| Alt Klasor | Icerik | Neden Var? |
|------------|--------|------------|
| `yedek/` | `adil_secmeli_backup_before_merge.db` (birlesme oncesi yedek DB), `adil_secmeli.sqbpro` (DB Browser projesi), `schema_original.sql` (orijinal sema) | Veri kaybi riski icin yedekler. Geri donulmesi gerekirse referans. |
| `gecici/` | `ders_listesi.xlsx` (gecici ders listesi Excel'i) | Gecici veri dosyalari. Silmek yerine arsivde tutulur. |
| `ornekler/` | `missing_criteria_placeholder.json`, `README_missing_criteria.md` | Eksik kriter verisi icin ornek yapilar ve aciklama. Test/dokumantasyon amaclı. |
| `eski_ciktilar/` | `missing_criteria_2022_*.csv`, `missing_criteria_2022_*.xlsx` | Eski disa aktarim dosyalari. Gecmis karsilastirmasi icin saklanir. |

> `_arsiv/` klasoru `.gitignore` ile izlenmez.

---

## 11. .github/ — GitHub Yapilandirmasi

| Dosya | Amac |
|-------|------|
| `copilot-instructions.md` | GitHub Copilot icin proje ozeti, mimari ve veri akisi yonergeleri (Ingilizce). | Copilot'un projeye ozel oneriler uretebilmesi icin. |

---

## 12. .vscode/ — VS Code / Cursor Ayarlari

| Dosya | Amac |
|-------|------|
| `settings.json` | VS Code / Cursor IDE'ye ozel yapilandirma: Python yorumlayici yolu, format ayarlari, uzanti ayarlari. | Gelistirici deneyimini tutarli kilar. |

---

## 13. Mimari Ozet ve Veri Akisi

### Katmanli Mimari

```
┌─────────────────────────────────────────────────────────┐
│                    KULLANICI ARAYUZU                     │
│  ┌──────────┬──────────┬──────────┬──────────┬────────┐ │
│  │ Kriter   │ Alg. Lab │ Iliskiler│  Havuz   │ Admin  │ │
│  │ Girisi   │ (Analiz) │ (NLP)    │ Yonetimi │ Panel  │ │
│  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴───┬────┘ │
│       │          │          │          │         │       │
│  ┌────▼──────────▼──────────▼──────────▼─────────▼────┐ │
│  │              SERVIS KATMANI                        │ │
│  │  ┌────────────┬─────────────┬────────────────────┐ │ │
│  │  │ KararMotoru│ AI Engine   │ Havuz Karar        │ │ │
│  │  │ (AHP,      │ (LR, RF,   │ (State Machine)    │ │ │
│  │  │  TOPSIS)   │  DT)        │                    │ │ │
│  │  ├────────────┼─────────────┼────────────────────┤ │ │
│  │  │ Benzerlik  │ Is Kurallari│ Ders Analizci      │ │ │
│  │  │ (TF-IDF)   │ (Rules)     │ (Orkestrator)      │ │ │
│  │  └────────────┴─────────────┴────────────────────┘ │ │
│  └────────────────────────┬───────────────────────────┘ │
│                           │                              │
│  ┌────────────────────────▼───────────────────────────┐ │
│  │              VERITABANI KATMANI                     │ │
│  │  SQLAlchemy ORM + sqlite3  →  adil_secmeli.db      │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
         │                              ▲
         ▼                              │
┌─────────────────┐           ┌─────────────────┐
│  REST API       │           │  ETL Betikleri   │
│  (FastAPI)      │           │  (Excel → DB)    │
│  Dis sistemler  │           │  Toplu veri      │
│  entegrasyonu   │           │  aktarimi        │
└─────────────────┘           └─────────────────┘
```

### Veri Akis Ozeti

1. **Veri Girisi:** Excel dosyalari (`data/*.xlsx`) → ETL betikleri (`app/etl/`) → SQLite DB
2. **Kriter Girisi:** UI Kriter Sayfasi → `ders_kriterleri`, `performans`, `populerlik` tablolari
3. **Hesaplama:** Servisler (`calculation.py`, `ai_engine.py`) → `skor`, `havuz` tablolari
4. **Karar:** `havuz_karar.py` state machine → Havuz statu gecisleri
5. **Cikti:** UI goruntuleme + `reports/` + `exports/` + REST API

### Dosya Sayisi Ozeti

| Kategori | Dosya Sayisi |
|----------|-------------|
| Uygulama kodu (`app/`) | ~40 |
| Veri ve sema (`data/`) | 10 |
| Dokumantasyon (`docs/`) | 12 |
| Raporlar (`reports/`) | 3 |
| Arsiv (`_arsiv/`) | 6 |
| Yapilandirma (kok) | 6 |
| **Toplam** | **~77** |

---

> **Not:** Bu belge, projenin Mart 2026 itibarıyla guncel yapisini yansitmaktadir. Yeni dosya eklendikce veya yapisal degisiklikler yapildikca bu belgenin de guncellenmesi onerilir.
