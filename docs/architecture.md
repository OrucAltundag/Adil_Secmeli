# Adil Seçmeli Katmanlı Mimari

Bu doküman Tkinter masaüstü uygulaması ve FastAPI API yüzeyinin aynı servis, validasyon, hata, permission ve veri erişim katmanlarını kullanması için getirilen mimari standardı açıklar.

## Katmanlar

`app/ui`
: Tkinter ekranlarıdır. Kullanıcı etkileşimi, form/tablo gösterimi ve buton olaylarından sorumludur. Yeni kodda iş kuralı ve doğrudan SQL yazılmamalıdır.

`app/api`
: FastAPI adapter katmanıdır. HTTP request/response dönüşümü, schema doğrulama ve permission kontrolü yapar. İş kuralını servis katmanına devreder.

`app/services`
: Application service ve domain service katmanıdır. Kriter tamlığı, import governance, decision governance, havuz state machine, raporlama ve validasyon kuralları burada tutulur.

`app/repositories`
: Veritabanı erişim katmanıdır. Ham SQL gerekiyorsa burada izole edilir. UI ve API doğrudan SQL yazmak yerine repository kullanan servisleri çağırmalıdır.

`app/db`
: SQLite bağlantısı, SQLAlchemy modelleri, session yönetimi, migration ve runtime schema compatibility katmanıdır.

`app/core`
: Config, ServiceResult, AppError, permission ve logging gibi ortak altyapıdır.

`app/schemas`
: Pydantic API request/response modelleridir.

`app/viewmodels`
: Tkinter ekranlarına özel sade veri modelleridir.

## UI Sorumluluğu

UI sınıfları:

- Servis bağımlılığını constructor veya `service_factory` üzerinden almalıdır.
- Hata durumunda `AppError.to_user_message()` veya `ServiceResult` mesajını kullanıcıya göstermelidir.
- DB sorgusu, hesaplama veya karar kuralı içermemelidir.

Geçiş örneği:

```python
service = service_factory.get_criteria_service()
result = service.completion_summary(...)
```

## API Sorumluluğu

API route fonksiyonları:

- Request parametrelerini alır.
- Gerekirse Pydantic schema ile temel tip doğrulaması yapar.
- Permission kontrolünü çağırır.
- Servis sonucunu JSON’a çevirir.

Yeni endpointlerde standart response formatı kullanılır:

```json
{
  "success": true,
  "data": {},
  "message": null,
  "warnings": [],
  "meta": {}
}
```

Hata formatı:

```json
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Bu işlem için yetkiniz yok.",
    "details": {},
    "suggestion": "Yetkili kullanıcı ile tekrar deneyin.",
    "severity": "error"
  }
}
```

## ServiceResult ve AppError

`app/core/result.py` içindeki `ServiceResult`, servislerden UI/API adapterlarına ortak sonuç taşır.

`app/core/errors.py` içinde:

- `AppError`
- `ValidationAppError`
- `NotFoundAppError`
- `BusinessRuleAppError`
- `PermissionAppError`
- `DatabaseAppError`
- `ConflictAppError`

tanımlıdır.

FastAPI `AppError` hatalarını standart JSON response’a çevirir. UI aynı hataları kullanıcı dostu messagebox metnine dönüştürebilir.

## Validation Mimarisi

Ortak validasyon modeli `app/services/validation.py` içindedir:

- `ValidationIssue`
- `ValidationResult`

Yeni validation servisleri:

- `criteria_validation_service.py`
- `import_validation_service.py`
- `decision_validation_service.py`
- `pool_state_validation_service.py`
- `curriculum_validation_service.py`

API schema yalnızca temel tip/zorunlu alan kontrolü yapmalıdır. İş kuralı validasyonu servislerde kalmalıdır.

## Repository Katmanı

Eklenen repository örnekleri:

- `CourseRepository`
- `CriteriaRepository`
- `CurriculumRepository`
- `PoolRepository`
- `DecisionRepository`
- `ImportRepository`
- `ReportRepository`
- `SystemRepository`

Repository iş kuralı üretmez; yalnızca veri okuma/yazma ve güvenli SQL izolasyonu yapar.

## DB / Session Yönetimi

`app/db/session.py` merkezi giriş noktasıdır:

- `open_sqlite_connection()`
- `db_session()`
- `get_db()`
- `init_database()`
- `close_database()`
- `get_engine()`
- `get_session_factory()`

SQLite bağlantısı kısa ömürlü transaction context manager ile açılır. Hata durumunda rollback yapılır.

Resmi veri erişim akışı:

```text
UI / API
  -> Service Layer
  -> Repository Layer
  -> SQLAlchemy ORM / merkezi DB Session
  -> Database
```

Geçiş döneminde bazı legacy servisler SQLite connection adapterı kullanmaya devam edebilir. Yeni kodda DB sorgusu repository katmanına, iş kuralı service katmanına yazılmalıdır.

## Alembic ve Schema Compatibility

SQLAlchemy modelleri ve Alembic migration dosyaları resmi şema değişiklik yoludur. `app/db/schema_compat.py` yalnızca eski/demo SQLite dosyalarını güvenli açmak için controlled fallback olarak çalışır.

`app/core/database_policy.py` şu sınırları tanımlar:

- UI ve API içinde doğrudan DB erişimi yeni kod için yasaktır.
- `sqlite3` kullanımı repository, schema_compat, migration helper ve admin SQL Console ile sınırlıdır.
- Production ortamında SQL Console varsayılan kapalıdır.
- Production ortamında runtime schema mutation varsayılan kapalıdır.

Schema compatibility çalıştığında `schema_compat_logs` tablosuna özet audit kaydı yazılır. SQL Console kullanımları `sql_console_audit_logs` tablosunda izlenir.

## Permission Service

`app/core/permissions.py` temel rolleri ve action izinlerini tanımlar.

Roller:

- `admin`
- `developer`
- `faculty_coordinator`
- `department_coordinator`
- `viewer`
- `api_client`

Önemli action’lar:

- `view_data`
- `edit_criteria`
- `import_data`
- `approve_import`
- `run_algorithm`
- `approve_cancel`
- `override_decision`
- `use_sql_console`
- `manage_settings`

SQL Console için hem rol hem de config üzerinden developer/debug izni gerekir.

## Config Yönetimi

`app/core/config.py` merkezi konfigürasyonu sağlar:

- `APP_MODE`
- `DATABASE_URL`
- `SQLITE_DB_PATH`
- `DEBUG`
- `ENABLE_SQL_CONSOLE`
- `ENABLE_DEVELOPER_TOOLS`
- `API_AUTH_ENABLED`
- `API_HOST`
- `API_PORT`
- `LOG_LEVEL`
- `ENVIRONMENT`

Production ortamında SQL Console varsayılan olarak kapalıdır.

## Başlatma Modları

`main.py` ve `app/main.py` şu modları destekler:

- `python main.py --mode gui`
- `python main.py --mode api`
- `python main.py --mode benchmark`
- `python main.py --mode migrate`
- `python main.py --mode auto`

`auto` modunda headless ortamda API, display olan ortamda GUI başlar.

## SQL Console Güvenliği

`ViewTab` SQL Console düğmesi artık permission/config kontrolünden geçer. `ENABLE_SQL_CONSOLE=false` veya developer tools kapalıysa düğme disabled olur. `open_sql_runner` çağrısı doğrudan yapılsa bile permission kontrolü tekrar yapılır.

`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE` ve benzeri sorgular için ek kullanıcı onayı istenir. Her çalıştırma başarı/hata bilgisiyle audit log’a yazılır.

## Sistem Sağlığı Paneli

Tkinter içinde `Sistem Sağlığı` sekmesi:

- Uygulama modu
- DB yolu
- DB bağlantı durumu
- Schema compatibility sonucu
- Developer tools durumu
- SQL Console durumu
- Mimari denetim bulguları

bilgilerini gösterir.

Ek olarak `/api/v1/system/schema-health`, `/api/v1/system/architecture-audit`, `/api/v1/system/config-summary` ve `/api/v1/system/sql-console/audit-logs` endpointleri aynı servis katmanını kullanarak sistem durumunu döndürür.

API tarafında:

- `GET /api/v1/health`
- `GET /api/v1/system/info`

standart response formatıyla sağlık bilgisi döndürür.

## Yeni Kod Yazma Kuralları

1. UI içine SQL yazma.
2. API route içine iş kuralı yazma.
3. Önce service yaz, sonra UI/API adapterlarını bağla.
4. Yeni DB sorgusunu repository’ye koy.
5. Yeni iş kuralı validasyonunu ortak validation service’e koy.
6. Kullanıcıya traceback gösterme; `AppError` veya `ServiceResult` kullan.
7. Tehlikeli/geliştirici araçlarını permission + config arkasına al.

## Aşamalı Geçiş Notu

Mevcut büyük UI ekranlarında çok sayıda `self.db.run_sql` kullanımı vardır. Bu görevde kırıcı taşımadan kaçınmak için yeni mimari omurga kurulmuş, `ViewTab` ve health/API girişleri bu yapıya bağlanmıştır. Kalan legacy sorgular mimari denetim panelinde raporlanır ve sonraki refactor dilimlerinde repository/service arkasına alınmalıdır.
