# PostgreSQL Migration Runbook

Bu gecis veri ve hesaplama sonuclarini korumak icin iki asamali tasarlandi.

## 1. Baglanti Ayari

`.env` icinde PostgreSQL URL kullan:

```bash
DATABASE_URL=postgresql+psycopg://adil:strong_password@localhost:5432/adil_secmeli
```

SQLite yolu yalnizca kaynak veri dosyasi olarak kalir:

```bash
DB_PATH=./data/adil_secmeli.db
```

## 2. Hedef Semayi Olustur

```bash
python -m app.main --mode migrate
```

PostgreSQL aktifken bu komut SQLAlchemy modellerinden tablo semasini olusturur.

## 3. Kopyalama Plani

Once yazmadan satir sayilarini kontrol et:

```bash
python -m app.scripts.migrate_sqlite_to_postgres --dry-run --json
```

## 4. Veri Kopyalama

Bos PostgreSQL hedefine kopyala:

```bash
python -m app.scripts.migrate_sqlite_to_postgres --json
```

Hedef daha once denenmis ve temizlenecekse:

```bash
python -m app.scripts.migrate_sqlite_to_postgres --truncate-target --json
```

Varsayilan davranis bos olmayan hedef tablo gorurse durur. Bu, skor, karar,
kalite ve import tablolarinin yanlislikla ciftlenmesini onlemek icindir.

## 5. Gecis Siniri

Eski `sqlite3` tabanli UI/API yollarinda PostgreSQL aktifken islem bilerek
durdurulur. Boylece ayar PostgreSQL'e gecmisken uygulama eski SQLite dosyasina
sessizce veri yazmaz. Yeni kalici isler SQLAlchemy repository yoluna tasinmalidir.
