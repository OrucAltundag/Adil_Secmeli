# Database Schema Policy

Bu doküman Adil Seçmeli projesinde veritabanı erişimi, migration ve runtime schema compatibility sınırlarını tanımlar.

## Resmi Yol

Resmi veri erişim akışı:

```text
UI / API -> Service -> Repository -> SQLAlchemy ORM / DB Session -> Database
```

Yeni iş kodu UI veya API içinde doğrudan SQL çalıştırmamalıdır. Yeni sorgular repository katmanına, yeni iş kuralları service katmanına eklenir.

## SQLAlchemy ve Alembic

SQLAlchemy modelleri projenin resmi şema tanımıdır. Yeni tablo veya kolon eklendiğinde:

1. SQLAlchemy model güncellenir.
2. Alembic migration eklenir.
3. Gerekirse `schema_compat.py` içinde idempotent legacy fallback eklenir.
4. Test eklenir.

Alembic production ve kalıcı ortamlar için resmi migration yoludur.

## schema_compat Rolü

`app/db/schema_compat.py` migration alternatifi değildir. Eski/demo SQLite dosyalarını açarken eksik kritik tablo ve kolonları tamamlayan kontrollü güvenlik ağıdır.

Konfigürasyon:

- `ENABLE_SCHEMA_COMPAT`
- `ALLOW_RUNTIME_SCHEMA_MUTATION`
- `ALLOW_RUNTIME_SCHEMA_MUTATION_IN_PRODUCTION`

Production ortamında runtime schema mutation varsayılan olarak kapalıdır. Mutation kapalıyken schema health endpointleri eksikleri raporlar, otomatik değişiklik yapmaz.

schema_compat yaptığı işlemleri `schema_compat_logs` tablosuna yazar.

## sqlite3 ve Raw SQL

İzinli alanlar:

- `app/db/schema_compat.py`
- `app/db/session.py` ve bağlantı adapterları
- `app/repositories/`
- Alembic migration dosyaları
- Admin/developer SQL Console

Kaçınılacak alanlar:

- Normal Tkinter ekranları
- FastAPI route gövdeleri
- Service iş kuralı fonksiyonları

Raw SQL gerekiyorsa parametreli yazılmalı ve repository içinde tutulmalıdır.

## SQL Console Güvenliği

SQL Console yalnızca `admin` veya `developer` rolü, `ENABLE_DEVELOPER_TOOLS=true` ve `ENABLE_SQL_CONSOLE=true` olduğunda kullanılabilir. Production modda varsayılan kapalıdır.

Veri veya şema değiştiren sorgularda kullanıcıya uyarı gösterilir. Her çalıştırma `sql_console_audit_logs` tablosuna yazılır.

## Sağlık Kontrolleri

`SchemaHealthService` şunları raporlar:

- Kritik tablo ve kolon eksikleri
- Alembic version durumu
- schema_compat logları
- runtime mutation durumu
- SQLAlchemy model tabloları ile DB karşılaştırması

API endpointleri:

- `GET /api/v1/system/schema-health`
- `GET /api/v1/system/architecture-audit`
- `GET /api/v1/system/config-summary`
- `GET /api/v1/system/sql-console/audit-logs`

## Net İlke

Projede resmi veri erişim yolu SQLAlchemy model + repository/service katmanıdır. Alembic resmi schema migration aracıdır. Runtime schema compatibility yalnızca eski SQLite dosyalarıyla geriye dönük uyumluluk için kontrollü bir güvenlik ağıdır. UI ve API doğrudan veritabanına erişmez; ortak servisleri kullanır.
