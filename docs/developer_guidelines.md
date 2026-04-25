# Developer Guidelines

Bu rehber Adil Seçmeli projesinde yeni kod yazarken uygulanacak mimari kuralları özetler.

## UI

- Tkinter ekranları servis çağırmalıdır.
- UI içinde `sqlite3.connect`, `cursor.execute`, ham `SELECT/INSERT/UPDATE/DELETE` kullanılmamalıdır.
- Kullanıcı hataları `AppError` veya `ServiceResult` üzerinden gösterilmelidir.
- UI sınıfları servis bağımlılığını constructor’dan alabilir olmalıdır.

## API

- FastAPI endpointleri adapter gibi davranmalıdır.
- İş kuralı endpoint içinde yazılmamalıdır.
- Yeni endpointlerde standart `ApiResponse` formatı kullanılmalıdır.
- Permission kontrolü servis çağrısından önce yapılmalıdır.

## Service

- İş kuralları service katmanında tutulur.
- Servisler mümkün olduğunca `ServiceResult` döner veya `AppError` fırlatır.
- UI ve API aynı servisi çağırmalıdır.

## Repository

- Ham SQL repository içinde kalmalıdır.
- Repository iş kuralı üretmemelidir.
- SQLite uyumluluğu korunmalıdır.
- Yeni tablo/kolon için SQLAlchemy model + Alembic migration eklenmelidir.
- `schema_compat.py` yalnızca legacy SQLite uyumluluk fallback’i için güncellenmelidir.

## Validation

- Tip/zorunlu alan kontrolü API schema’da olabilir.
- İş kuralı validasyonu ortak validation servislerinde olmalıdır.
- UI ve API aynı validation fonksiyonunu kullanmalıdır.

## Config ve Permission

- DB path, API host/port, debug ve SQL Console ayarları `app/core/config.py` üzerinden okunmalıdır.
- SQL Console sadece `admin` veya `developer` rolü ve developer/debug config açıkken kullanılmalıdır.
- Production’da runtime schema mutation ve SQL Console varsayılan kapalı kalmalıdır.

## Schema ve Migration

- Alembic resmi migration yoludur.
- Runtime schema compatibility production migration alternatifi değildir.
- schema_compat değişiklikleri `schema_compat_logs` tablosuna yazılmalıdır.
- Mimari borç için `ArchitectureAuditService` raporu ve architecture guard testleri güncel tutulmalıdır.

## Test

- Yeni service için doğrudan unit test yaz.
- Yeni API endpointi için smoke test ekle.
- Yeni UI paneli için en az import/fake service smoke testi ekle.
