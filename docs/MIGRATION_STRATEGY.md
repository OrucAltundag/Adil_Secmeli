# Migration Strategy

## Source of Truth

1. ORM model: `app/db/models.py`
2. Revision history: `alembic/versions/*.py`
3. Runtime safety net: `app/db/schema_compat.py`

## Revision Flow

1. Model degisikligi yap
2. Yeni revision olustur
3. Staging DB'de `alembic upgrade head`
4. Regression test calistir
5. Production rollout

## Legacy Normalization (Mevcut daginik sema)

- `havuz.donem` olmayan DB:
  - kolon eklenir
  - donem normalize edilir (`Guz`/`Bahar`)
  - duplicate satirlar tekillestirilir
  - composite unique index olusturulur

## Rollback Policy

- SQLite'da kolon drop riskli oldugu icin:
  - bu faz rollback'te indexleri geri alir
  - veri rollback ihtiyacinda backup restore kullanilir

