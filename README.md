# Adil Secmeli - Fakult e Bazli Secmeli Ders Sistemi

Universitelerde secmeli ders secimini veriye dayali ve izlenebilir hale getiren masaustu uygulama + REST API.

## Kurulum

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Konfigurasyon

1. `.env.example` dosyasini `.env` olarak kopyala
2. `DB_PATH` ve `DATABASE_URL` degerlerini ortamina gore guncelle

Opsiyonel: `config.json` ile ayni anahtarlar override edilebilir.

## Migration

```bash
alembic upgrade head
```

## Calistirma

Masaustu:
```bash
python -m app.main
```

API:
```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

## Kritik Dokumanlar

- [Production Gap Closure](docs/PRODUCTION_GAP_CLOSURE.md)
- [Migration Strategy](docs/MIGRATION_STRATEGY.md)
- [Runbook](docs/RUNBOOK_PRODUCTION.md)
