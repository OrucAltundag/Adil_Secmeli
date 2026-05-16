# Fonksiyon ve Sınıf Envanteri - 2026-05-16

Bu dosya AST tabanlı otomatik envanterdir. Amaç, proje raporunda anlatılan modül sorumluluklarını fonksiyon/sınıf düzeyinde izlenebilir hale getirmektir.

## Kapsam
- Taranan Python dosyası: 356
- Üst seviye fonksiyon: 1754
- Sınıf: 431
- Sınıf metodu: 1008
- Hariç tutulanlar: `env`, `_arsiv`, `.git`, `__pycache__`.
- Docstring olmayan fonksiyonlarda açıklama imza ve modül konumundan ayrıca okunmalıdır; bu dosya kaynak kod yerine geçmez.

## Alembic Migration

### `alembic/env.py`
  - Fonksiyonlar:
    - `_resolve_sqlalchemy_url() -> str` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `run_migrations_offline() -> None` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `run_migrations_online() -> None` (satır 59): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `alembic/versions/20260324_0001_havuz_semester_axis.py`
  - Fonksiyonlar:
    - `upgrade() -> None` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `downgrade() -> None` (satır 66): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `alembic/versions/20260325_0002_yearly_workflow_state.py`
  - Fonksiyonlar:
    - `upgrade() -> None` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `downgrade() -> None` (satır 89): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `alembic/versions/20260503_0003_decision_governance.py`
  - Fonksiyonlar:
    - `upgrade() -> None` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `downgrade() -> None` (satır 269): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `alembic/versions/20260504_0004_import_governance.py`
  - Fonksiyonlar:
    - `_table_exists(table_name: str) -> bool` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_column_names(table_name: str) -> set[str]` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_add_column_if_missing(table_name: str, column_name: str, ddl: str) -> None` (satır 36): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `upgrade() -> None` (satır 43): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `downgrade() -> None` (satır 280): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `alembic/versions/20260505_0005_criteria_completion_governance.py`
  - Fonksiyonlar:
    - `_table_exists(table_name: str) -> bool` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_column_names(table_name: str) -> set[str]` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_add_column_if_missing(table_name: str, column_name: str, ddl: str) -> None` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `upgrade() -> None` (satır 42): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `downgrade() -> None` (satır 248): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `alembic/versions/20260506_0006_pool_state_governance.py`
  - Fonksiyonlar:
    - `_table_exists(bind, table_name: str) -> bool` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_add_column_if_missing(bind, table_name: str, column: sa.Column) -> None` (satır 25): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `upgrade() -> None` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `downgrade() -> None` (satır 178): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `alembic/versions/20260507_0007_ml_governance.py`
  - Fonksiyonlar:
    - `_create_table_if_missing(table_name: str, *columns, **kwargs) -> None` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `upgrade() -> None` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `downgrade() -> None` (satır 145): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `alembic/versions/20260508_0008_algorithm_governance.py`
  - Fonksiyonlar:
    - `_create_table_if_missing(table_name: str, *columns) -> None` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `upgrade() -> None` (satır 25): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `downgrade() -> None` (satır 187): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `alembic/versions/20260509_0009_ahp_governance.py`
  - Fonksiyonlar:
    - `_tables() -> set[str]` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_columns(table_name: str) -> set[str]` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_create_table_if_missing(table_name: str, *columns) -> None` (satır 30): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_add_column_if_missing(table_name: str, column: sa.Column) -> None` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `upgrade() -> None` (satır 40): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `downgrade() -> None` (satır 171): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `alembic/versions/20260510_0010_semester_planning_governance.py`
  - Fonksiyonlar:
    - `_tables() -> set[str]` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_columns(table_name: str) -> set[str]` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_create_table_if_missing(table_name: str, *columns) -> None` (satır 30): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_add_column_if_missing(table_name: str, column: sa.Column) -> None` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `upgrade() -> None` (satır 40): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `downgrade() -> None` (satır 96): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `alembic/versions/20260511_0011_architecture_schema_policy.py`
  - Fonksiyonlar:
    - `_tables() -> set[str]` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_create_table_if_missing(table_name: str, *columns) -> None` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `upgrade() -> None` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `downgrade() -> None` (satır 57): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `alembic/versions/20260512_0012_security_data_quality_schema.py`
  - Fonksiyonlar:
    - `_tables() -> set[str]` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_columns(table_name: str) -> set[str]` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_create_table_if_missing(table_name: str, *columns) -> None` (satır 30): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_add_column_if_missing(table_name: str, column: sa.Column) -> None` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_add_columns(table_name: str, columns: list[sa.Column]) -> None` (satır 40): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `upgrade() -> None` (satır 45): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `downgrade() -> None` (satır 366): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `alembic/versions/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

## Giriş Noktası

### `main.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/api/main.py`
  - Fonksiyonlar:
    - `root()` (satır 59): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `async app_error_handler(_request: Request, exc: AppError)` (satır 64): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `async unexpected_error_handler(_request: Request, exc: Exception)` (satır 69): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/main.py`
  - Fonksiyonlar:
    - `is_headless_environment() -> bool` (satır 29): Tkinter gibi GUI araçları bir "display" ister.
    - `_default_api_port() -> int` (satır 41): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `load_config()` (satır 78): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `build_headless_message(host: str, port: int) -> str` (satır 92): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `run_api_server(host: str, port: int) -> int` (satır 104): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `run_gui() -> int` (satır 118): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `run_migrate() -> int` (satır 132): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `run_schema_check() -> int` (satır 142): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `run_benchmark_mode() -> int` (satır 153): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `main(argv=None) -> int` (satır 158): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `AdilSecmeliApp(tk.Tk)` (satır 211): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self)` (satır 213): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `auto_connect(self)` (satır 337): Uygulama acilisinda otomatik veritabani baglantisi kurar.
      - `cmd_open_db(self)` (satır 416): Kullanicidan yeni veritabani dosyasi secmesini ister ve baglantıyı yeniler.
      - `fill_pool_table_for_years(self)` (satır 468): Havuz tablosunu mevcut mufredat yillari icin doldurur.
      - `open_sql_runner(self)` (satır 514): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `refresh_all(self)` (satır 561): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `on_tab_change(self, event)` (satır 606): Ana sekme degistiginde ilgili sekmenin refresh() metodunu cagırır.
      - `ensure_pool_initialized_once(self)` (satır 635): Havuz tablosu bos ise ilk kez mufredat yillarindan seed olusturur.

## Kök Testler

### `tests/test_auth.py`
  - Fonksiyonlar:
    - `test_permission_service_rbac_disabled()` (satır 7): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_permission_service_rbac_enabled()` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_permission_service_faculty_scoping()` (satır 30): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `tests/test_import_security.py`
  - Fonksiyonlar:
    - `test_file_upload_extension_validation()` (satır 7): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_file_upload_mime_type_validation()` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_sanitize_filename()` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

## Proje Scriptleri

### `scripts/run_tests.py`
  - Fonksiyonlar:
    - `run_pytest(args: list[str], capture: bool=False) -> subprocess.CompletedProcess` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `main()` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

## Testler

### `app/tests/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/tests/api/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/tests/api/test_api_smoke.py`
  - Fonksiyonlar:
    - `client()` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `TestAPISmokeEndpoints` (satır 25): Temel API endpoint'lerinin 500 vermeden yanit donmesi.
      - `test_root(self, client)` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_health(self, client)` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_system_health(self, client)` (satır 39): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_dersler(self, client)` (satır 43): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_skorlar(self, client)` (satır 50): DB schema eksik oldugunda exception olabilir — smoke test.
      - `test_fakulteler(self, client)` (satır 58): DB schema eksik oldugunda exception olabilir — smoke test.
      - `test_response_is_json(self, client)` (satır 66): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_docs_endpoint(self, client)` (satır 70): Swagger UI erisilebilir mi.

### `app/tests/benchmark/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/tests/benchmark/test_ml_minimum_sample_guard.py`
  - Sınıflar:
    - `TestMinimumSampleGuard` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_find(self, key)` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_random_forest_min_sample(self)` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_xgboost_min_sample(self)` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_logistic_regression_needs_per_class(self)` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `TestAlgorithmGovernanceRoles` (satır 25): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_find(self, key)` (satır 26): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_ahp_production(self)` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_topsis_production(self)` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_xgboost_benchmark_only(self)` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_no_ml_in_production(self)` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_all_have_metrics(self)` (satır 43): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/check_db_results.py`
  - Fonksiyonlar:
    - `kontrol_et()` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/conftest.py`
  - Fonksiyonlar:
    - `_create_base_schema(conn: sqlite3.Connection) -> None` (satır 22): Temel veritabani şemasını oluşturur (minimal).
    - `empty_db(tmp_path)` (satır 94): Temiz, bos SQLite veritabani (gecici dosya).
    - `memory_db()` (satır 105): In-memory SQLite DB fixture.
    - `golden_db(tmp_path)` (satır 115): Golden dataset ile seed edilmis DB.
    - `state_machine_db(tmp_path)` (satır 125): Pool state machine testleri icin hazir DB.

### `app/tests/db/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/tests/db/test_schema_compat.py`
  - Sınıflar:
    - `TestFreshDBSchema` (satır 12): Sifirdan DB olusturuldiginda gerekli tablolar var mi.
      - `test_base_tables_exist(self, empty_db)` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `TestSchemaCompat` (satır 25): schema_compat fonksiyonlari — eksik kolon ekleme.
      - `test_ensure_criteria_import_schema(self, empty_db)` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_ensure_survey_import_schema(self, empty_db)` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_ensure_skor_schema(self, empty_db)` (satır 43): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_ensure_havuz_semester_schema(self, empty_db)` (satır 48): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_ensure_architecture_schema(self, empty_db)` (satır 53): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_ensure_decision_governance_schema(self, empty_db)` (satır 62): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `TestTransactionRollback` (satır 68): Hata durumunda transaction rollback ediyor mu.
      - `test_rollback_on_error(self, empty_db)` (satır 71): Bozuk SQL sonrasi onceki commit korunur.

### `app/tests/e2e/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/tests/e2e/test_full_decision_pipeline.py`
  - Sınıflar:
    - `TestFullDecisionPipeline` (satır 18): Tam karar pipeline: veri → trend → skor → karar → aciklama.
      - `test_pipeline_produces_decisions_for_all_courses(self)` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_pipeline_scores_in_range(self)` (satır 71): Pipeline ciktisi tum skorlar gecerli aralikta.

### `app/tests/fixtures/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/tests/fixtures/test_db_builders.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_create_base_schema(conn: sqlite3.Connection) -> None` (satır 21): Minimum tablo yapisi.
    - `create_empty_test_db(db_path: str | None=None) -> sqlite3.Connection` (satır 164): Bos test DB olusturur.
    - `seed_golden_dataset(conn: sqlite3.Connection) -> dict[str, Any]` (satır 172): Golden dataset ile DB'yi doldurur.
    - `create_golden_db(db_path: str | None=None) -> sqlite3.Connection` (satır 208): Golden dataset ile hazir DB olusturur.
    - `seed_minimal_academic_structure(conn: sqlite3.Connection) -> None` (satır 215): Minimum fakulte/bolum/ders yapisi olusturur.
    - `seed_edge_case_dataset(conn: sqlite3.Connection) -> None` (satır 227): Uc durum verileri seed eder.
    - `seed_large_synthetic_dataset(conn: sqlite3.Connection, size: int=1000) -> None` (satır 244): Buyuk sentetik veri seti olusturur (performans testleri icin).
    - `create_state_machine_db(db_path: str | None=None) -> sqlite3.Connection` (satır 270): Pool state machine testleri icin DB. Governance tablolari da olusturulur.

### `app/tests/integration/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/tests/performance/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/tests/performance/test_performance_smoke.py`
  - Sınıflar:
    - `TestPerformanceSmoke` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_1000_courses_topsis_under_5_seconds(self)` (satır 12): 1000 derslik TOPSIS 5 saniye altinda tamamlanmali.
      - `test_5000_courses_no_crash(self)` (satır 28): 5000 derslik veri crash etmemeli.

### `app/tests/regression/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/tests/regression/test_deterministic_decision_runs.py`
  - Sınıflar:
    - `TestDeterministicRuns` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_df(self)` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_topsis_deterministic_five_runs(self)` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_ahp_deterministic_three_runs(self)` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_tiebreak_is_deterministic(self)` (satır 50): Ayni skorlu dersler deterministik siralanmali.

### `app/tests/regression/test_golden_dataset_decisions.py`
  - Sınıflar:
    - `TestGoldenDatasetDecisions` (satır 15): Golden dataset ile beklenen kararlar dogrulanir.
      - `_build_topsis_input(self)` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_topsis_ranking_deterministic(self)` (satır 35): Ayni golden dataset → ayni TOPSIS siralamasi.
      - `test_high_score_course_ranks_first(self)` (satır 46): En yuksek skorlu ders (Ders 1) ilk sirada olmali.
      - `test_low_score_course_ranks_last(self)` (satır 53): En dusuk skorlu ders (Ders 5) son siralarda olmali.
      - `test_trend_labels_match_expected(self)` (satır 61): Golden dataset trend etiketleri beklenenlerle uyusmali.
      - `test_scores_in_valid_range(self)` (satır 70): Tum TOPSIS skorlari 0-1 arasinda olmali.

### `app/tests/reset_counters.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/tests/test_ahp_governance.py`
  - Fonksiyonlar:
    - `conn()` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_default_criteria_are_seeded(conn)` (satır 39): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_ahp_matrix_validation_rules()` (satır 46): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_weight_calculation_and_consistency()` (satır 57): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_default_profile_is_active(conn)` (satır 72): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_profile_resolution_priority(conn)` (satır 80): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_profile_lifecycle_and_policy(conn)` (satır 109): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_decision_run_stores_ahp_snapshot_and_staleness(conn)` (satır 125): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_impact_and_sensitivity(conn)` (satır 162): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_ahp_api_smoke(monkeypatch, tmp_path)` (satır 207): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_ahp_ui_importable()` (satır 233): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_ai_engine.py`
  - Fonksiyonlar:
    - `_build_ai_test_db(total_rows: int, curriculum_rows: int) -> str` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_predict_all_courses_falls_back_to_faculty_training_scope_when_curriculum_too_small()` (satır 133): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_predict_all_courses_returns_fallback_columns_when_training_still_insufficient()` (satır 162): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_algorithm_governance.py`
  - Fonksiyonlar:
    - `conn()` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_algorithm_governance_registry_roles(conn)` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_task_mapping_blocks_wrong_algorithm(conn)` (satır 48): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_data_guard_minimum_samples_and_class_rules(conn)` (satır 57): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_metric_router_classification_regression_clustering_allocation()` (satır 71): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_validation_strategy_selection()` (satır 89): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_statistical_comparison_and_ci()` (satır 100): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_leakage_detector()` (satır 108): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_model_diagnostics()` (satır 116): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_clustering_evaluation_dbscan_noise_and_warnings()` (satır 125): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_baseline_comparison()` (satır 132): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_governed_benchmark_run_persists_results(conn)` (satır 141): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_api_smoke(monkeypatch, tmp_path)` (satır 160): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_ui_smoke_import_and_create(monkeypatch)` (satır 188): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_architecture_foundation.py`
  - Fonksiyonlar:
    - `_tmp_db() -> str` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_config_defaults_and_production_sql_console(monkeypatch, tmp_path)` (satır 77): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_postgresql_config_blocks_legacy_sqlite_default(monkeypatch, tmp_path)` (satır 86): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_service_result_and_app_error_formats()` (satır 95): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_db_session_commit_and_rollback()` (satır 107): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_repository_and_service_reuse()` (satır 132): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_shared_validation_services()` (satır 144): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_permission_rules(monkeypatch, tmp_path)` (satır 151): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_api_health_and_system_service(monkeypatch)` (satır 163): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_ui_imports_and_architecture_scan()` (satır 177): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_architecture_guards.py`
  - Fonksiyonlar:
    - `_minimal_db(path: Path) -> None` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_database_policy_production_defaults_are_safe()` (satır 39): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_schema_compat_creates_audit_tables_and_logs(tmp_path)` (satır 55): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_schema_health_reports_required_tables(tmp_path)` (satır 82): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_architecture_audit_service_reports_layers()` (satır 94): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_ui_direct_sqlite_connect_guard_allowlist()` (satır 102): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_repository_layer_contains_required_modules()` (satır 118): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_system_api_smoke_endpoints(monkeypatch, tmp_path)` (satır 133): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_assignment_engine.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/tests/test_calc_tab.py`
  - Fonksiyonlar:
    - `test_next_year_batch_runs_all_individual_algorithms_in_order()` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `_DummyStatus` (satır 4): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, text='Bekliyor...')` (satır 5): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `cget(self, key)` (satır 8): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_course_code_service.py`
  - Fonksiyonlar:
    - `_build_db() -> str` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_build_course_code_normalizes_turkish_initials()` (satır 57): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_apply_missing_course_codes_updates_only_blank_rows()` (satır 62): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_criteria_completion_governance.py`
  - Fonksiyonlar:
    - `_db() -> tuple[str, sqlite3.Connection]` (satır 26): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_insert_criteria(conn: sqlite3.Connection, course_id: int, total: int | None=100, passed: int | None=80, average: float | None=82.0, capacity: int | None=50, enrolled: int | None=45)` (satır 96): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_completion_ratio_and_levels()` (satır 117): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_completed_matrix_and_algorithm_gate()` (satır 144): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_validation_invalid_values_block_completion()` (satır 162): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_policy_priority_and_default_creation()` (satır 179): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_missing_data_risk_tasks_and_history()` (satır 209): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_override_pending_and_approved_gate()` (satır 230): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_criteria_completion_api_smoke(monkeypatch)` (satır 258): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_criteria_page_completion_panel_importable()` (satır 278): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_criteria_import_service.py`
  - Fonksiyonlar:
    - `_build_db() -> str` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_write_criteria_excel(rows: list[dict], *, meta_department: str | None=None, note: str | None=None) -> str` (satır 163): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_cleanup(*paths)` (satır 188): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_import_criteria_tracks_document_and_report_summary()` (satır 198): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_faculty_reimport_preserves_department_override_metrics()` (satır 298): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_write_criteria_template_scopes_department_courses()` (satır 484): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `_DummyDB` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, conn)` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run_sql(self, query, params=())` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_criteria_page.py`
  - Fonksiyonlar:
    - `test_fetch_saved_criteria_uses_named_columns_with_aktif_mi_present()` (satır 51): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_manual_fields_locked_after_import()` (satır 88): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_preference_ratio_computed_correctly()` (satır 100): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `_DummyDB` (satır 6): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, conn)` (satır 7): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run_sql(self, query, params=())` (satır 10): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_DummyEntry` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, value='0', state='normal')` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `delete(self, _start, _end=None)` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `insert(self, _index, value)` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get(self)` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `config(self, **kwargs)` (satır 30): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `cget(self, key)` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_DummyLabel` (satır 40): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self)` (satır 41): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `config(self, **kwargs)` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `cget(self, key)` (satır 47): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_curriculum_generation.py`
  - Fonksiyonlar:
    - `_build_generation_db() -> str` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_single_and_bulk_topsis_consistency()` (satır 172): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_drop_rule_reasons_and_state_machine()` (satır 195): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_auto_and_manual_generation_and_year_based_scores()` (satır 232): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_curriculum_import_service.py`
  - Fonksiyonlar:
    - `_build_db() -> str` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_write_excel(rows: list[dict]) -> str` (satır 54): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_import_curriculum_excel_insert_and_compare_same()` (satır 63): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_import_curriculum_excel_rejects_cross_semester_duplicate()` (satır 91): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_data_quality.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 26): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_db_memory()` (satır 31): In-memory SQLite veritabanı oluştur
  - Sınıflar:
    - `TestDataCoverage` (satır 123): Veri kapsama hesaplama testleri
      - `test_empty_database(self, test_db_memory)` (satır 126): Boş veritabanında kapsama hesapla
      - `test_coverage_with_partial_data(self, test_db_memory)` (satır 134): Kısmi verilerle kapsama hesapla
    - `TestDataReadiness` (satır 169): Veri olgunluğu değerlendirme testleri
      - `test_readiness_not_ready(self, test_db_memory)` (satır 172): Hazır olmayan veri için seviye kontrolü
      - `test_readiness_decision_ready(self, test_db_memory)` (satır 190): Karar almaya hazır veri için seviye kontrolü
    - `TestMissingDataDetection` (satır 233): Eksik veri tespiti testleri
      - `test_detect_missing_criteria(self, test_db_memory)` (satır 236): Eksik kriter verisi tespiti
      - `test_insert_missing_data_item(self, test_db_memory)` (satır 256): Eksik veri öğesi kayıt
    - `TestValidationIssues` (satır 275): Doğrulama sorunları testleri
      - `test_record_validation_issue(self, test_db_memory)` (satır 278): Doğrulama sorununu kaydet
      - `test_resolve_validation_issue(self, test_db_memory)` (satır 298): Doğrulama sorununu çöz
    - `TestCoverageReportPersistence` (satır 327): Kapsama raporu kalıcılığı testleri
      - `test_save_coverage_report(self, test_db_memory)` (satır 330): Kapsama raporunu kaydet

### `app/tests/test_data_quality_api.py`
  - Fonksiyonlar:
    - `test_data_coverage_endpoint_stub()` (satır 13): API coverage endpoint testi (stub)
    - `test_data_readiness_endpoint_stub()` (satır 20): API readiness endpoint testi (stub)
    - `test_data_confidence_endpoint_stub()` (satır 27): API confidence endpoint testi (stub)
    - `test_missing_data_endpoint_stub()` (satır 34): API missing data endpoint testi (stub)
    - `test_validation_issues_endpoint_stub()` (satır 41): API validation issues endpoint testi (stub)
    - `test_decisions_outcomes_endpoint_stub()` (satır 48): API decisions outcomes endpoint testi (stub)
    - `test_collection_priorities_endpoint_stub()` (satır 55): API collection priorities endpoint testi (stub)
    - `test_missing_resolve_endpoint_stub()` (satır 62): API missing data resolve endpoint testi (stub)
    - `test_validation_resolve_endpoint_stub()` (satır 69): API validation issue resolve endpoint testi (stub)
    - `test_collection_priority_complete_endpoint_stub()` (satır 76): API collection priority complete endpoint testi (stub)
  - Sınıflar:
    - `TestDataQualityAPIIntegration` (satır 83): Veri kalitesi API entegrasyon testleri
      - `test_coverage_endpoint_response_structure(self)` (satır 86): Coverage endpoint yanıt yapısı kontrolü
      - `test_readiness_endpoint_response_structure(self)` (satır 94): Readiness endpoint yanıt yapısı kontrolü
      - `test_error_handling_missing_parameters(self)` (satır 102): Eksik parametreler için hata yönetimi
      - `test_api_pagination_support(self)` (satır 108): Sayfalandırma desteği
    - `TestDataQualityDataValidation` (satır 115): Veri kalitesi API veri doğrulama testleri
      - `test_confidence_score_range(self)` (satır 118): Güven skorunun 0-1 aralığında olması
      - `test_readiness_level_valid_values(self)` (satır 123): Hazırlık seviyesi geçerli değerler
      - `test_severity_valid_values(self)` (satır 130): Sorun şiddeti geçerli değerler
      - `test_timestamp_format_iso8601(self)` (satır 136): Zaman damgası ISO 8601 formatı

### `app/tests/test_db.py`
  - Fonksiyonlar:
    - `_get_db_path() -> str` (satır 22): config.json'dan veya varsayılandan DB yolunu al.
    - `test_db_connection()` (satır 39): Veritabanı bağlantısı ve temel okuma testi (raw SQLite).

### `app/tests/test_decision_governance.py`
  - Fonksiyonlar:
    - `_tmp_conn()` (satır 26): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_create_integration_db()` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_ahp_default_profile_and_scope_resolution()` (satır 145): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_decision_policy_defaults_and_scope_resolution()` (satır 168): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_data_confidence_levels()` (satır 189): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_trend_labels()` (satır 197): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_explanation_for_low_score_trend_and_confidence()` (satır 205): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_governance_blocks_automatic_cancel_for_manual_new_and_strategic()` (satır 225): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_decision_run_integration_writes_core_records()` (satır 241): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_etl.py`
  - Fonksiyonlar:
    - `_build_etl_db()` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_collect_curriculum_rows_normalized_layout()` (satır 81): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_run_import_replaces_only_target_scope()` (satır 104): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_havuz_karar.py`
  - Fonksiyonlar:
    - `test_s1_kalici_iptal_degismez()` (satır 28): S1: prev=-2 → her koşulda -2, sayaç değişmez.
    - `test_s2_dinlenmede_0_olur_mufredat_yok_sayilir()` (satır 35): S2: prev=-1 → her koşulda 0 (in_mufredat True olsa bile).
    - `test_s3_mufredatta_kalir()` (satır 42): S3: prev=1 + in_mufredat=True → (1, sayaç değişmez).
    - `test_s4_mufredattan_ilk_dusus()` (satır 48): S4: prev=1 + in_mufredat=False + prev_sayac=0 → (-1, 1).
    - `test_s5_mufredattan_ikinci_dusus_kalici_iptal()` (satır 53): S5: prev=1 + in_mufredat=False + prev_sayac=1 → (-2, 2).
    - `test_s6_havuzdan_mufredata()` (satır 58): S6: prev=0 + in_mufredat=True → (1, sayaç aynı).
    - `test_s7_havuzda_kalir()` (satır 64): S7: prev=0 + in_mufredat=False → (0, sayaç aynı).
    - `test_zincir_tam_yasam_dongusu()` (satır 74): A dersi tam yaşam döngüsü:
    - `test_zincir_iki_dusus_direkt_iptal()` (satır 108): B dersi:
    - `test_havuzda_sayac_artmaz()` (satır 126): Havuzdayken (statu=0) sayaç kesinlikle artmamalı.
    - `test_dinlenmedeyken_sayac_artmaz()` (satır 133): Dinlenmedeyken (statu=-1) sayaç kesinlikle artmamalı.
    - `test_none_girdi_guvenliyol()` (satır 140): None/bozuk girdi → güvenli varsayılan (0, 0).
    - `test_maks_dusme_sayaci_sabiti()` (satır 147): MAKS_DUSME_SAYACI 2 olmalı.
    - `test_onar_2022_ground_truth_cok_fakulteli()` (satır 152): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_sayac_tam_esik()` (satır 231): Sayaç tam eşikte (prev_sayac=1) düşünce → -2.
    - `test_iptal_sonrasi_mufredata_girme_denemesi()` (satır 238): -2 durumundaki ders müfredata alınmak istense de -2 kalır.

### `app/tests/test_import_governance.py`
  - Fonksiyonlar:
    - `_db() -> tuple[str, sqlite3.Connection]` (satır 23): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_insert_criteria_row(conn, batch_id, row_no, course_id, code, value)` (satır 48): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_file_hash_same_content_same_hash()` (satır 82): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_duplicate_import_same_scope_detected()` (satır 87): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_import_quality_high_and_low()` (satır 99): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_row_issue_classification_has_user_friendly_suggestion()` (satır 125): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_import_diff_added_removed_changed_unchanged()` (satır 142): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_rollback_reactivates_previous_and_logs()` (satır 160): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_value_source_manual_override_deactivates_previous()` (satır 181): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_import_api_smoke(monkeypatch)` (satır 195): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_real_criteria_import_creates_audit_batch()` (satır 215): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_data_management_page_importable()` (satır 255): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_ml_governance.py`
  - Fonksiyonlar:
    - `_temp_db(rows: int=24) -> str` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_conn(path: str)` (satır 121): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_algorithm_registry_defaults_and_roles()` (satır 128): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_readiness_blocks_small_random_forest_and_warns_imbalance()` (satır 143): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_readiness_high_when_sample_count_is_sufficient_but_advisory_not_production()` (satır 158): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_feature_pipeline_normalizes_and_handles_zero_capacity()` (satır 172): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_model_run_skipped_when_data_insufficient_and_trained_when_sufficient()` (satır 188): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_evaluation_overfit_and_small_cv_warning()` (satır 214): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_confidence_low_with_low_sample_and_never_influences()` (satır 221): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_prediction_fallback_is_logged_and_advisory_only()` (satır 228): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_explainability_tree_path_and_low_data_limitation()` (satır 243): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_benchmark_registry_marks_ml_roles()` (satır 253): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_ml_api_smoke(monkeypatch)` (satır 261): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_ml_readiness_page_importable()` (satır 275): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_pool_rules.py`
  - Fonksiyonlar:
    - `_build_pool_db() -> str` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_pool_only_elective_courses()` (satır 201): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_required_courses_not_visible_in_pool(monkeypatch)` (satır 220): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_cross_department_faculty_pool_candidate_selection()` (satır 252): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_same_course_not_used_in_both_semesters()` (satır 269): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_pool_filtering_by_faculty_department_year(monkeypatch)` (satır 325): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_pool_sorted_by_kesinlesme_score_desc(monkeypatch)` (satır 365): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_pool_state_machine_governance.py`
  - Fonksiyonlar:
    - `_db() -> tuple[str, sqlite3.Connection]` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_base_context(**overrides)` (satır 83): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_pool_policy_resolution_priority()` (satır 104): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_protected_courses_are_not_cancelled()` (satır 127): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_new_course_grace_and_low_confidence_block_hard_decisions()` (satır 148): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_cancel_approval_and_transition_history()` (satır 166): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_override_and_reactivation_rules()` (satır 192): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_backward_compatibility_and_api_smoke(monkeypatch)` (satır 227): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_decision_center_pool_lifecycle_importable()` (satır 248): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_reporting.py`
  - Fonksiyonlar:
    - `_build_reporting_db()` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_build_report_snapshot_respects_faculty_and_term()` (satır 113): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_build_report_snapshot_counts_statuses()` (satır 140): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `DummyDB` (satır 10): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, db_path: str)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run_sql(self, query, params=None)` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_score_engine.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/tests/test_semester_planning_governance.py`
  - Fonksiyonlar:
    - `_conn(path: str=':memory:') -> sqlite3.Connection` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_default_policy_seed_and_validation()` (satır 84): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_policy_resolution_priority()` (satır 103): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_planning_engine_default_policy_generates_4_plus_4_and_audit()` (satır 137): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_course_availability_blocks_forbidden_semester()` (satır 152): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_instructor_availability_and_capacity_constraint()` (satır 162): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_resource_and_prerequisite_violations_are_reported()` (satır 182): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_demand_capacity_balance_and_same_course_repeat_policy()` (satır 207): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_api_smoke(monkeypatch)` (satır 218): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_ui_smoke_import_and_widget()` (satır 246): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_semester_support.py`
  - Fonksiyonlar:
    - `_build_dual_semester_db() -> str` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_rebuild_school_curricula_dual_semester_balances_4_plus_4()` (satır 172): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_cross_semester_state_machine_conflict_guard()` (satır 228): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_havuz_semester_schema_backward_compat()` (satır 242): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_skor_schema_adds_missing_hesap_tarih()` (satır 285): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_similarity.py`
  - Fonksiyonlar:
    - `_make_similarity_db() -> str` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_get_similar_courses_returns_ranked_list()` (satır 52): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_compute_and_save_persists_relations()` (satır 68): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_single_analysis.py`
  - Fonksiyonlar:
    - `test_sm_kalici_iptal_degismez()` (satır 38): S1: -2 her kosulda -2 kalir.
    - `test_sm_dinlenmede_havuza_donus()` (satır 45): S2: -1 her kosulda 0 olur (in_mufredat True olsa bile).
    - `test_sm_mufredatta_kalir()` (satır 51): S3: 1 + in_mufredat=True -> (1, sayac degismez).
    - `test_sm_ilk_dusus()` (satır 57): S4: 1 + in_mufredat=False + sayac=0 -> (-1, 1).
    - `test_sm_ikinci_dusus_kalici_iptal()` (satır 62): S5: 1 + in_mufredat=False + sayac=1 -> (-2, 2).
    - `test_sm_havuzdan_mufredata()` (satır 67): S6: 0 + in_mufredat=True -> (1, sayac ayni).
    - `test_sm_havuzda_kalir()` (satır 73): S7: 0 + in_mufredat=False -> (0, sayac ayni).
    - `test_sm_maks_sayac_sabiti()` (satır 79): MAKS_DUSME_SAYACI = 2 olmali.
    - `test_sm_zincir_tam()` (satır 84): 2022->2023->2024->2025 tam zincir.
    - `test_sm_havuzda_sayac_artmaz()` (satır 104): Havuzdayken sayac artmamali.
    - `test_sm_none_guvenli()` (satır 111): None girdi -> (0, 0).
    - `test_ahp_agirliklar_toplami()` (satır 121): AHP agirlik toplami 1.0 olmali.
    - `test_ahp_saaty_matrisi_kurallari()` (satır 133): Saaty ikili karsilastirma matrisi is kurallarina uygun olmali.
    - `test_ahp_cr_gecerli()` (satır 149): AHP tutarlilik orani < 0.10 olmali.
    - `test_topsis_skor_aralik()` (satır 155): TOPSIS skoru 0-100 arasinda olmali.
    - `test_topsis_hesaplanamadi_guvenli()` (satır 181): Fakulte baglami yoksa kontrollu sekilde hesaplanamadi donmeli.
    - `test_trend_bos_gecmis()` (satır 205): Gecmis veri yoksa hesaplama guvenli sekilde sifir donmeli.
    - `test_trend_uclu_agirlik()` (satır 212): 3 yil verisi -> agirlikli ortalama hesaplamali.
    - `test_trend_rescaling_eksik_orta_yil()` (satır 225): 1. ve 3. yil varsa agirliklar 0.50/0.20 -> 0.70 uzerinden normalize edilmeli.
    - `test_trend_rescaling_sifiri_eksik_sayar()` (satır 239): 0 degeri de eksik veri kabul edilmeli ve yeniden agirliklandirilmali.
    - `test_trend_tum_yillar_gecersizse_sifir_doner()` (satır 251): Tum veriler null/0 ise islem guvenli sekilde sifirla sonlanmali.
    - `test_rf_yuksek_basari_mufredatta()` (satır 263): Yuksek basari + yuksek doluluk -> Mufredatta tahmini.
    - `test_rf_dusuk_basari_dinlenmede()` (satır 271): Dusuk basari -> Dinlenmede tahmini.
    - `test_rf_maks_sayac_iptal()` (satır 279): Sayac >= MAKS_DUSME_SAYACI -> Kalici Iptal.
    - `_make_mock_db_path(ders_id: int=99, yil: int=2023, basari_orani: float=0.7, doluluk_orani: float=0.6, prev_statu: int=0, prev_sayac: int=0, add_criteria: bool=True, include_curriculum: bool=True, current_havuz_statu: int=None, gt_statu: int=None) -> str` (satır 291): Gecici dosyada mock SQLite veritabani olusturur; yol dondurur (thread-safe test icin).
    - `test_analiz_veri_eksik_hata()` (satır 462): Kriter verisi olmayan ders -> kismi analiz donmeli, fatal error donmemeli.
    - `test_analiz_havuz_dersi_kriter_yok_status_gosterir()` (satır 480): Havuzda bekleyen kriter eksik ders de analiz ekranina durumuyla donmeli.
    - `test_analiz_dict_formati_dogru()` (satır 500): Basarili analizde donus dict'i dogru anahtarlara sahip olmali.
    - `test_analiz_statu_kodlari()` (satır 519): Yuksek basari + yuksek doluluk -> statu 1 (Mufredatta) bekleniyor.
    - `test_analiz_dusuk_performans_dinlenmede()` (satır 537): Dusuk basari + prev statu=1 -> -1 (Dinlenmede).
    - `test_analiz_ikinci_dusus_kalici_iptal()` (satır 556): Prev sayac=1 + dusuyor -> statu -2 (Kalici Iptal).
    - `test_analiz_2022_ground_truth()` (satır 574): year=2022 ise state machine calismamali, mevcut havuz kaydi donmeli.
    - `test_analiz_db_yok()` (satır 589): Olmayan / bos veritabani yolu -> error donmeli (veya bos DB icin ders bulunamadi).
    - `test_analiz_ders_yok()` (satır 604): Olmayan ders_id -> error donmeli.
    - `test_analiz_skor_aralik()` (satır 617): score_final 0-100 arasinda olmali.

### `app/tests/test_survey_import_service.py`
  - Fonksiyonlar:
    - `_build_db() -> str` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_build_legacy_db_without_kod() -> str` (satır 128): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_write_survey_excel(meta: dict, rows: list[dict]) -> str` (satır 185): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_write_flat_survey_excel(rows: list[dict], sheet_name: str=SURVEY_TEMPLATE_SHEET_NAME) -> str` (satır 194): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_import_survey_replaces_previous_data()` (satır 202): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_total_participants_computed()` (satır 254): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_write_survey_template_prefills_active_pool_courses()` (satır 265): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_write_survey_template_handles_legacy_ders_schema_without_kod()` (satır 328): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_import_survey_supports_flat_template_format()` (satır 366): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_import_survey_ignores_template_total_row()` (satır 412): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_course_matching_by_code_then_name()` (satır 466): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_unmatched_rows_reported()` (satır 501): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_survey_values_written_to_criteria()` (satır 531): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/test_yearly_criteria_workflow.py`
  - Fonksiyonlar:
    - `_create_db() -> str` (satır 25): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_insert_curriculum(conn, fakulte_id: int, bolum_id: int, yil: int, ders_ids: list[int], donem: str='Guz')` (satır 112): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_insert_complete_metrics(conn, ders_id: int, yil: int, donem: str='Guz', toplam: int=100, gecen: int=80, ortalama: float=75.0, kontenjan: int=50, kayitli: int=40)` (satır 129): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_insert_pool_row(conn, ders_id: int, yil: int, fakulte_id: int, bolum_id: int, statu: int, skor: float | None=None, donem: str='Guz')` (satır 177): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_write_import_excel(rows: list[dict]) -> str` (satır 206): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_import_resets_criteria_status()` (satır 215): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_department_completion_status()` (satır 277): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_faculty_completion_status()` (satır 310): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_no_auto_calculation_after_criteria_entry()` (satır 343): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_build_two_faculty_algorithm_db() -> str` (satır 373): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_algorithm_runs_only_for_completed_faculty()` (satır 411): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_next_year_created_after_algorithm_run()` (satır 426): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_new_year_visible_but_scores_empty_until_new_criteria()` (satır 450): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_ai_engine_filters_to_selected_faculty_year_curriculum()` (satır 477): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_import_api_requires_explicit_target_year()` (satır 532): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `test_only_one_cross_department_course_allowed()` (satır 540): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/ui/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/tests/ui/test_ui_smoke.py`
  - Sınıflar:
    - `TestUIModuleImport` (satır 11): UI modulleri import edilebiliyor mu.
      - `test_import_app_main(self)` (satır 14): app.main import edilebilmeli (GUI baslatmadan).
      - `test_import_ui_style(self)` (satır 21): UI stil modulu import edilebilmeli.
      - `test_import_security_readiness_page(self)` (satır 28): Guvenlik hazirlik sekmesi API/requests bagimliligi olmadan import edilebilmeli.
      - `test_import_api_routes(self)` (satır 33): API route modulu import edilebilmeli.
      - `test_import_algorithms(self)` (satır 38): Algoritma modulleri import edilebilmeli.
      - `test_import_services(self)` (satır 44): Temel servisler import edilebilmeli.

### `app/tests/unit/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/tests/unit/test_ahp.py`
  - Sınıflar:
    - `TestAHPMatrixValidation` (satır 20): AHP ikili karsilastirma matrisi dogruluk kontrolleri.
      - `test_identity_matrix_equal_weights(self)` (satır 23): Birim matris → tum agirliklar esit olmali.
      - `test_weight_sum_is_one(self)` (satır 44): Uretilen agirliklar toplami 1 olmali.
      - `test_known_3x3_weights(self)` (satır 62): Bilinen 3x3 Saaty matrisi icin agirliklar dogrulama.
      - `test_known_4x4_weights(self)` (satır 86): 4x4 matris icin bilinen agirliklar.
    - `TestAHPConsistency` (satır 109): Tutarlilik orani kontrolleri.
      - `test_consistent_matrix_cr_below_threshold(self)` (satır 112): Tutarli matris → CR <= 0.10.
      - `test_inconsistent_matrix_cr_above_threshold(self)` (satır 124): Tutarsiz matris → CR > 0.10.
      - `test_n1_safe(self)` (satır 137): n=1 matriste hata yok.
      - `test_n2_safe(self)` (satır 145): n=2 matriste CR = 0 (RI=0).
    - `TestAHPRanking` (satır 158): AHP siralama/skor dogrulama.
      - `test_ranking_order_with_known_data(self)` (satır 161): Bilinen agirliklarla siralama dogrulamasi.
      - `test_criteria_count_mismatch_raises_error(self)` (satır 184): Matris boyutu != kriter sayisi → ValueError.
      - `test_confidence_decreases_with_high_cr(self)` (satır 196): Yuksek CR → dusuk confidence.
      - `test_explain_returns_nonempty_string(self)` (satır 215): explain() bos string donmemeli.
      - `test_score_method_returns_valid_float(self)` (satır 225): score() 0-1 arasinda float donmeli.
    - `TestAHPRITable` (satır 238): Random Index tablosu dogrulama.
      - `test_ri_table_known_values(self)` (satır 241): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_ri_table_has_entries_1_to_10(self)` (satır 248): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/unit/test_edge_cases.py`
  - Sınıflar:
    - `TestEdgeCasesTOPSIS` (satır 19): TOPSIS uc durumlari.
      - `test_all_topsis_values_identical(self)` (satır 22): Tum TOPSIS degerleri ayni → NaN/ZeroDivision yok.
      - `test_single_criterion(self)` (satır 36): Tek kriter ile calismali.
    - `TestEdgeCasesAHP` (satır 44): AHP uc durumlari.
      - `test_ahp_cr_very_high(self)` (satır 47): Cok yuksek CR → sistem cokmez, uyari uretilir.
    - `TestEdgeCasesTrend` (satır 63): Trend uc durumlari.
      - `test_no_performance_data(self)` (satır 66): Hic performans verisi yok.
      - `test_single_year_trend(self)` (satır 71): Tek yil veri → dusuk guven.
    - `TestEdgeCasesConfidence` (satır 77): Data confidence uc durumlari.
      - `test_zero_survey_still_works(self)` (satır 80): Anket katilimi 0 ise sistem cokmez.
      - `test_no_data_at_all(self)` (satır 89): Hic veri yok → en dusuk guven.
    - `TestEdgeCasesScoreCalculation` (satır 100): Skor hesaplama uc durumlari.
      - `test_division_by_zero_capacity(self)` (satır 103): Kontenjan 0 ise division by zero olmamali.
      - `test_none_input_safe(self)` (satır 111): None girdiler guvenli sonuc donmeli.

### `app/tests/unit/test_explainability.py`
  - Sınıflar:
    - `TestExplainability` (satır 14): Karar aciklanabilirligi.
      - `test_explanation_not_empty(self)` (satır 17): Her karar icin aciklama uretilmeli.
      - `test_low_score_explains_reason(self)` (satır 26): Dusuk skor → aciklamada skor bilgisi olmali.
      - `test_falling_trend_in_explanation(self)` (satır 34): Falling trend → aciklamada trend etiketi olmali.
      - `test_low_confidence_in_explanation(self)` (satır 46): Dusuk veri guveni → aciklamada guven bilgisi olmali.
      - `test_strategic_protection_in_explanation(self)` (satır 58): Stratejik ders → aciklamada koruma bilgisi olmali.
      - `test_approval_required_in_explanation(self)` (satır 70): Onay gerekli → aciklamada onay bilgisi olmali.
      - `test_high_score_positive_reason(self)` (satır 83): Yuksek skor → olumlu ana neden.

### `app/tests/unit/test_fairness_metrics.py`
  - Fonksiyonlar:
    - `_setup_decision_tables(conn)` (satır 14): decision_runs ve course_decisions tablolarini gercek semayla olustur.
  - Sınıflar:
    - `TestFairnessMetrics` (satır 45): Fairness report icerigi dogrulama.
      - `test_fairness_report_has_required_fields(self, memory_db)` (satır 48): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_low_confidence_count_detected(self, memory_db)` (satır 71): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/unit/test_state_machine.py`
  - Fonksiyonlar:
    - `_eval(conn, **ctx)` (satır 19): Kisa yardimci: state transition evaluate et.
  - Sınıflar:
    - `TestStateMachineTransitions` (satır 26): Havuz state machine — 11 governance transition senaryosu.
      - `test_s01_curriculum_low_score_one_year(self, state_machine_db)` (satır 29): Mufredatta + 1 yil dusuk skor → havuz/dinlenme, kalici iptal degil.
      - `test_s02_pool_two_years_low_score(self, state_machine_db)` (satır 38): Havuzda + 2 yil dusuk skor → dinlenme veya revizyon onerisi.
      - `test_s03_resting_three_years_low_high_confidence(self, state_machine_db)` (satır 47): Dinlenmede + 3 yil dusuk skor + yuksek veri guveni → cancel_candidate.
      - `test_s04_resting_low_confidence_blocks_cancel(self, state_machine_db)` (satır 59): Dinlenmede + dusuk veri guveni → cancel engellenir.
      - `test_s05_strategic_course_no_auto_cancel(self, state_machine_db)` (satır 68): Stratejik ders + dusuk skor → otomatik iptal yok.
      - `test_s06_accreditation_no_auto_cancel(self, state_machine_db)` (satır 78): Akreditasyon dersi + dusuk skor → otomatik iptal yok.
      - `test_s07_new_course_grace_period(self, state_machine_db)` (satır 88): Yeni ders + dusuk skor → grace period, kalici iptal onerilmez.
      - `test_s08_revised_course_grace(self, state_machine_db)` (satır 97): Revize ders + dusuk skor → revision grace period.
      - `test_s09_pool_high_score_rising_reactivation(self, state_machine_db)` (satır 106): Havuzdaki ders + yuksek skor + rising trend → reactivation_candidate.
      - `test_s10_cancelled_no_auto_return(self, state_machine_db)` (satır 115): Kalici iptal edilmis ders + yuksek skor → otomatik donus yok.
      - `test_s11_override_changes_final(self, state_machine_db)` (satır 123): Manuel override → final_status override ile degisir.
      - `test_explanation_never_empty(self, state_machine_db)` (satır 141): Her transition icin explanation bos olmamali.
      - `test_rule_applied_never_empty(self, state_machine_db)` (satır 149): Her transition icin rule_applied dolu olmali.
      - `test_statuses_are_valid_ints(self, state_machine_db)` (satır 156): old/recommended/final status gecerli integer olmali.
    - `TestLegacyStateMachine` (satır 167): Eski/basit state machine — calculate_next_status geriye uyumluluk.
      - `test_curriculum_stays_when_selected(self)` (satır 170): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_curriculum_drops_to_rest(self)` (satır 173): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_second_drop_cancels(self)` (satır 176): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_pool_to_curriculum(self)` (satır 179): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_cancelled_stays_cancelled(self)` (satır 182): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_resting_returns_to_pool(self)` (satır 185): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/tests/unit/test_topsis.py`
  - Sınıflar:
    - `TestTOPSISNormalization` (satır 16): Normalizasyon ve agirlik uygulamasi.
      - `test_closeness_in_0_1_range(self)` (satır 19): Closeness coefficient 0-1 arasinda olmali.
      - `test_equal_weights_produce_uniform_weighting(self)` (satır 31): Esit agirliklar normalizeye esit etki etmeli.
      - `test_weight_normalization(self)` (satır 45): Agirliklar toplami 1'e normalize edilmeli.
    - `TestTOPSISRanking` (satır 56): Siralama dogrulamasi.
      - `test_known_ranking_order(self)` (satır 59): Bilinen veriyle beklenen siralama.
      - `test_best_item_has_highest_score(self)` (satır 76): Her kriterde en iyi olan en yuksek skoru almali.
      - `test_worst_item_has_lowest_score(self)` (satır 90): Her kriterde en kotu olan 0'a yakin skor almali.
    - `TestTOPSISEdgeCases` (satır 105): Uc durumlar.
      - `test_all_values_equal_no_crash(self)` (satır 108): Tum degerler ayni → NaN/ZeroDivision olmamali.
      - `test_single_item(self)` (satır 122): Tek alternatifle calismali.
      - `test_weight_length_mismatch_raises(self)` (satır 134): Agirlik sayisi != kriter sayisi → ValueError.
      - `test_zero_column_no_crash(self)` (satır 144): Bir kolon tamamen 0 olsa bile crash etmemeli.
      - `test_missing_values_handled(self)` (satır 155): NaN/None degerleri fillna(0) ile islenmeli.
      - `test_explain_returns_nonempty(self)` (satır 166): explain() bos olmamali.
      - `test_artifacts_contain_ideal_values(self)` (satır 173): Cikti artifacts ideal_best/ideal_worst icermeli.
    - `TestTOPSISDeterministic` (satır 187): Deterministiklik kontrolu.
      - `test_same_input_same_output(self)` (satır 190): Ayni veri → ayni sonuc.

### `app/tests/unit/test_trend.py`
  - Sınıflar:
    - `TestWeightedTrendScore` (satır 18): 50/30/20 agirlikli trend skoru.
      - `test_default_weights_are_50_30_20(self)` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_single_year_only(self)` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_three_year_weighted(self)` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_missing_middle_year_renormalizes(self)` (satır 35): 2 yil veri → kalan agirliklar yeniden normalize ediliyor mu.
      - `test_empty_returns_zero(self)` (satır 41): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_zero_values_return_zero(self)` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `TestAnalyzeTrendValues` (satır 48): Trend etiketleme ve senaryo testleri.
      - `test_no_data_insufficient(self)` (satır 51): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_single_point_insufficient_or_new(self)` (satır 56): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_single_point_not_new(self)` (satır 61): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_rising_trend(self)` (satır 65): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_falling_trend(self)` (satır 70): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_stable_trend(self)` (satır 75): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_volatile_trend(self)` (satır 80): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_extreme_outlier_no_crash(self)` (satır 85): Aykiri deger sistemi cokmemeli.
      - `test_values_clamped_to_0_1(self)` (satır 92): Aralik disi degerler 0-1 bandina cekiliyor mu.
      - `test_explanation_not_empty(self)` (satır 99): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `TestDataConfidence` (satır 104): Veri guveni hesaplama.
      - `test_all_sources_high_confidence(self)` (satır 107): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_no_data_low_confidence(self)` (satır 121): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_partial_data_medium_confidence(self)` (satır 134): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `test_score_between_0_and_1(self)` (satır 146): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

## app/__init__.py

### `app/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

## app/algorithms

### `app/algorithms/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/algorithms/allocation/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/algorithms/allocation/allocators.py`
  - Sınıflar:
    - `AllocationInput` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `BaseAllocator(IAllocator)` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, name: str, parameters: dict[str, Any] | None=None) -> None` (satır 23): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `fit(self, X: Any, y: Any | None=None) -> 'BaseAllocator'` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `predict(self, X: Any) -> AlgorithmOutput` (satır 30): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `recommend(self, X: Any, top_k: int=5) -> AlgorithmOutput` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `score(self, X: Any, y: Any | None=None) -> float` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `explain(self, X: Any | None=None) -> str` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_prepare(self, students: pd.DataFrame, courses: pd.DataFrame, preferences: pd.DataFrame) -> tuple[list[int], dict[int, int], dict[int, list[tuple[int, int]]]]` (satır 50): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_format_assignments(self, student_ids: list[int], assigned_course: dict[int, int | None], received_rank: dict[int, int | None]) -> list[dict[str, Any]]` (satır 75): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_output(self, started: float, assignments: list[dict[str, Any]], explanation: str, artifacts: dict[str, Any] | None=None) -> AlgorithmOutput` (satır 89): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `RandomAllocator(BaseAllocator)` (satır 101): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, random_seed: int=42) -> None` (satır 102): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `allocate(self, students: pd.DataFrame, courses: pd.DataFrame, preferences: pd.DataFrame) -> AlgorithmOutput` (satır 106): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `FCFSAllocator(BaseAllocator)` (satır 127): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self) -> None` (satır 128): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `allocate(self, students: pd.DataFrame, courses: pd.DataFrame, preferences: pd.DataFrame) -> AlgorithmOutput` (satır 131): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `GreedyAllocator(BaseAllocator)` (satır 149): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self) -> None` (satır 150): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `allocate(self, students: pd.DataFrame, courses: pd.DataFrame, preferences: pd.DataFrame) -> AlgorithmOutput` (satır 153): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MinimumRegretAllocator(BaseAllocator)` (satır 172): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self) -> None` (satır 173): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `allocate(self, students: pd.DataFrame, courses: pd.DataFrame, preferences: pd.DataFrame) -> AlgorithmOutput` (satır 176): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `GaleShapleyAllocator(BaseAllocator)` (satır 207): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self) -> None` (satır 208): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `allocate(self, students: pd.DataFrame, courses: pd.DataFrame, preferences: pd.DataFrame) -> AlgorithmOutput` (satır 211): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/algorithms/base.py`
  - Sınıflar:
    - `AlgorithmOutput` (satır 12): Normalized output schema shared by all algorithms.
      - `as_dict(self) -> dict[str, Any]` (satır 26): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `IAlgorithm(ABC)` (satır 41): Base contract for all algorithm families.
      - `__init__(self, name: str, task_type: str, parameters: Mapping[str, Any] | None=None) -> None` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `fit(self, X: Any, y: Any | None=None) -> 'IAlgorithm'` (satır 50): Fit internal state using training data.
      - `predict(self, X: Any) -> AlgorithmOutput` (satır 54): Produce predictions for supervised tasks.
      - `recommend(self, X: Any, top_k: int=5) -> AlgorithmOutput` (satır 58): Produce ranked recommendations.
      - `score(self, X: Any, y: Any | None=None) -> float` (satır 62): Return a scalar quality score.
      - `explain(self, X: Any | None=None) -> str` (satır 66): Return human-readable explanation metadata.
      - `_start_timer(self) -> float` (satır 69): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_output(self, started_at: float, *, predictions: list[Any] | None=None, recommendations: list[Any] | None=None, assignments: list[dict[str, Any]] | None=None, confidence: float=0.0, explanation: str='', artifacts: Mapping[str, Any] | None=None) -> AlgorithmOutput` (satır 72): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `IPredictor(IAlgorithm, ABC)` (satır 97): Contract for predictive models.
      - `predict_proba(self, X: Any) -> list[list[float]]` (satır 101): Return class probabilities.
    - `IRanker(IAlgorithm, ABC)` (satır 105): Contract for ranking/recommendation models.
      - `rank(self, X: Any, top_k: int=5) -> AlgorithmOutput` (satır 109): Return ranked items for each input entity.
    - `IAllocator(IAlgorithm, ABC)` (satır 113): Contract for allocation/optimization models.
      - `allocate(self, students: Any, courses: Any, preferences: Any) -> AlgorithmOutput` (satır 117): Allocate students to courses under constraints.
    - `IClusterer(IAlgorithm, ABC)` (satır 121): Contract for clustering models.
      - `cluster(self, X: Any) -> AlgorithmOutput` (satır 125): Return cluster labels and clustering artifacts.

### `app/algorithms/clustering/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/algorithms/clustering/models.py`
  - Sınıflar:
    - `_ClustererBase(IClusterer)` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, name: str, estimator: Any, parameters: dict[str, Any] | None=None) -> None` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `fit(self, X: pd.DataFrame, y: None=None) -> '_ClustererBase'` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `cluster(self, X: pd.DataFrame) -> AlgorithmOutput` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `predict(self, X: pd.DataFrame) -> AlgorithmOutput` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `recommend(self, X: pd.DataFrame, top_k: int=5) -> AlgorithmOutput` (satır 47): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `score(self, X: pd.DataFrame, y: pd.Series | None=None) -> float` (satır 56): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `explain(self, X: pd.DataFrame | None=None) -> str` (satır 63): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_as_dataframe(self, X: Any) -> pd.DataFrame` (satır 69): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `KMeansClusterer(_ClustererBase)` (satır 75): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, n_clusters: int=5, random_seed: int=42) -> None` (satır 76): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `HierarchicalClusterer(_ClustererBase)` (satır 84): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, n_clusters: int=5, linkage: str='ward') -> None` (satır 85): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DBSCANClusterer(_ClustererBase)` (satır 93): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, eps: float=0.5, min_samples: int=5) -> None` (satır 94): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/algorithms/mcdm/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/algorithms/mcdm/ahp.py`
  - Sınıflar:
    - `AHPFitState` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AHPRanker(IRanker)` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, pairwise_matrix: np.ndarray | list[list[float]] | None=None) -> None` (satır 36): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `fit(self, X: pd.DataFrame, y: None=None) -> 'AHPRanker'` (satır 41): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_rank(self, X: pd.DataFrame, top_k: int) -> AlgorithmOutput` (satır 64): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `rank(self, X: pd.DataFrame, top_k: int=5) -> AlgorithmOutput` (satır 110): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `predict(self, X: pd.DataFrame) -> AlgorithmOutput` (satır 113): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `recommend(self, X: pd.DataFrame, top_k: int=5) -> AlgorithmOutput` (satır 116): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `score(self, X: pd.DataFrame, y: pd.Series | None=None) -> float` (satır 119): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `explain(self, X: pd.DataFrame | None=None) -> str` (satır 125): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/algorithms/mcdm/promethee.py`
  - Sınıflar:
    - `PROMETHEERanker(IRanker)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, weights: list[float] | None=None) -> None` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `fit(self, X: pd.DataFrame, y: None=None) -> 'PROMETHEERanker'` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_rank(self, X: pd.DataFrame, top_k: int) -> AlgorithmOutput` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `rank(self, X: pd.DataFrame, top_k: int=5) -> AlgorithmOutput` (satır 76): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `predict(self, X: pd.DataFrame) -> AlgorithmOutput` (satır 79): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `recommend(self, X: pd.DataFrame, top_k: int=5) -> AlgorithmOutput` (satır 82): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `score(self, X: pd.DataFrame, y: pd.Series | None=None) -> float` (satır 85): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `explain(self, X: pd.DataFrame | None=None) -> str` (satır 89): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/algorithms/mcdm/topsis.py`
  - Sınıflar:
    - `TOPSISRanker(IRanker)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, weights: list[float] | None=None) -> None` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `fit(self, X: pd.DataFrame, y: None=None) -> 'TOPSISRanker'` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_rank(self, X: pd.DataFrame, top_k: int) -> AlgorithmOutput` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `rank(self, X: pd.DataFrame, top_k: int=5) -> AlgorithmOutput` (satır 71): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `predict(self, X: pd.DataFrame) -> AlgorithmOutput` (satır 74): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `recommend(self, X: pd.DataFrame, top_k: int=5) -> AlgorithmOutput` (satır 77): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `score(self, X: pd.DataFrame, y: pd.Series | None=None) -> float` (satır 80): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `explain(self, X: pd.DataFrame | None=None) -> str` (satır 84): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/algorithms/mcdm/vikor.py`
  - Sınıflar:
    - `VIKORRanker(IRanker)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, weights: list[float] | None=None, v: float=0.5) -> None` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `fit(self, X: pd.DataFrame, y: None=None) -> 'VIKORRanker'` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_rank(self, X: pd.DataFrame, top_k: int) -> AlgorithmOutput` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `rank(self, X: pd.DataFrame, top_k: int=5) -> AlgorithmOutput` (satır 71): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `predict(self, X: pd.DataFrame) -> AlgorithmOutput` (satır 74): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `recommend(self, X: pd.DataFrame, top_k: int=5) -> AlgorithmOutput` (satır 77): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `score(self, X: pd.DataFrame, y: pd.Series | None=None) -> float` (satır 80): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `explain(self, X: pd.DataFrame | None=None) -> str` (satır 84): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/algorithms/ml/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/algorithms/ml/baselines.py`
  - Sınıflar:
    - `RandomPredictor(IPredictor)` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, classes: list[Any] | None=None, random_seed: int=42) -> None` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `fit(self, X: pd.DataFrame, y: pd.Series | np.ndarray | list[Any] | None=None) -> 'RandomPredictor'` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `predict_proba(self, X: pd.DataFrame) -> list[list[float]]` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `predict(self, X: pd.DataFrame) -> AlgorithmOutput` (satır 37): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `recommend(self, X: pd.DataFrame, top_k: int=5) -> AlgorithmOutput` (satır 49): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `score(self, X: pd.DataFrame, y: pd.Series | None=None) -> float` (satır 64): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `explain(self, X: pd.DataFrame | None=None) -> str` (satır 71): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MajorityClassPredictor(IPredictor)` (satır 75): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self) -> None` (satır 76): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `fit(self, X: pd.DataFrame, y: pd.Series | np.ndarray | list[Any] | None=None) -> 'MajorityClassPredictor'` (satır 81): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `predict_proba(self, X: pd.DataFrame) -> list[list[float]]` (satır 91): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `predict(self, X: pd.DataFrame) -> AlgorithmOutput` (satır 97): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `recommend(self, X: pd.DataFrame, top_k: int=5) -> AlgorithmOutput` (satır 111): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `score(self, X: pd.DataFrame, y: pd.Series | None=None) -> float` (satır 123): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `explain(self, X: pd.DataFrame | None=None) -> str` (satır 129): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `PopularityRecommender(IRanker)` (satır 133): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self) -> None` (satır 134): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `fit(self, X: pd.DataFrame, y: pd.Series | None=None) -> 'PopularityRecommender'` (satır 138): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `rank(self, X: pd.DataFrame, top_k: int=5) -> AlgorithmOutput` (satır 150): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `predict(self, X: pd.DataFrame) -> AlgorithmOutput` (satır 164): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `recommend(self, X: pd.DataFrame, top_k: int=5) -> AlgorithmOutput` (satır 167): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `score(self, X: pd.DataFrame, y: pd.Series | None=None) -> float` (satır 170): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `explain(self, X: pd.DataFrame | None=None) -> str` (satır 177): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/algorithms/ml/classifiers.py`
  - Fonksiyonlar:
    - `_build_lr_estimator()` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `SklearnPredictorBase(IPredictor)` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, name: str, estimator: Any, *, task_type: str='prediction', parameters: dict[str, Any] | None=None) -> None` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `fit(self, X: pd.DataFrame, y: pd.Series | np.ndarray | list[Any] | None=None) -> 'SklearnPredictorBase'` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `predict_proba(self, X: pd.DataFrame) -> list[list[float]]` (satır 40): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `predict(self, X: pd.DataFrame) -> AlgorithmOutput` (satır 56): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `recommend(self, X: pd.DataFrame, top_k: int=5) -> AlgorithmOutput` (satır 73): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `score(self, X: pd.DataFrame, y: pd.Series | None=None) -> float` (satır 98): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `explain(self, X: pd.DataFrame | None=None) -> str` (satır 104): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_feature_importance(self) -> dict[str, float]` (satır 112): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_as_dataframe(self, X: Any) -> pd.DataFrame` (satır 123): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `NaiveBayesPredictor(SklearnPredictorBase)` (satır 133): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self) -> None` (satır 134): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `LogisticRegressionPredictor(SklearnPredictorBase)` (satır 138): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self) -> None` (satır 139): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `RandomForestPredictor(SklearnPredictorBase)` (satır 143): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, n_estimators: int=300, random_seed: int=42) -> None` (satır 144): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `XGBoostLikePredictor(SklearnPredictorBase)` (satır 157): Uses XGBoost when available, otherwise GradientBoosting fallback.
      - `__init__(self, random_seed: int=42) -> None` (satır 160): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

## app/api

### `app/api/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/api/middleware/rate_limit.py`
  - Fonksiyonlar:
    - `async rate_limit_middleware(request: Request, call_next)` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `RateLimiter` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self)` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_cleanup(self, key: str, window: int)` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `is_allowed(self, key: str, limit: int, window: int=60) -> bool` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/api/routes.py`
  - Fonksiyonlar:
    - `_normalize_donem(value: str | None) -> str` (satır 241): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_donem_key(value: str | None) -> str` (satır 248): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_get_db_path() -> str` (satır 252): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_open_connection() -> sqlite3.Connection` (satır 266): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_run_query(query: str, params: tuple=()) -> tuple[list[str], list[list]]` (satır 275): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_havuz_has_donem(conn: sqlite3.Connection) -> bool` (satır 287): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ders_listesi(fakulte_id: Optional[int]=None, secmeli_only: bool=False)` (satır 294): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `skor_listesi(akademik_yil: Optional[int]=None, donem: Optional[str]=None)` (satır 305): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_listesi(yil: int, fakulte_id: Optional[int]=None, bolum_id: Optional[int]=None, donem: Optional[str]=None)` (satır 326): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `mufredat_listesi(akademik_yil: int, bolum_id: Optional[int]=None, donem: Optional[str]=None)` (satır 376): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `akademik_plan(fakulte_id: int, yil: int)` (satır 397): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `fakulte_listesi()` (satır 435): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `health()` (satır 446): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `system_info()` (satır 456): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `system_health()` (satır 466): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `system_schema_health()` (satır 476): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `system_architecture_audit()` (satır 486): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `system_config_summary()` (satır 492): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `system_sql_console_audit_logs(limit: int=50)` (satır 498): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_durumu(fakulte_id: int, yil: int)` (satır 508): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_tamlik(year: int, faculty_id: Optional[int]=None, department_id: Optional[int]=None, semester: Optional[str]=None)` (satır 523): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_tamlik_matrix(year: int, faculty_id: Optional[int]=None, department_id: Optional[int]=None, semester: Optional[str]=None)` (satır 546): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_tamlik_issues(year: int, faculty_id: Optional[int]=None, department_id: Optional[int]=None, semester: Optional[str]=None)` (satır 571): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_tamlik_validate(payload: dict[str, Any]=Body(default_factory=dict))` (satır 596): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_tamlik_policies()` (satır 622): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_tamlik_policy_create(payload: dict[str, Any]=Body(default_factory=dict))` (satır 631): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_tamlik_policy_activate(policy_id: int)` (satır 663): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_tamlik_risk(year: int, faculty_id: Optional[int]=None, department_id: Optional[int]=None, semester: Optional[str]=None)` (satır 676): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_tamlik_tasks(year: Optional[int]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None, status: Optional[str]=None)` (satır 708): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_tamlik_task_create(payload: dict[str, Any]=Body(default_factory=dict))` (satır 722): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_tamlik_task_update(task_id: int, payload: dict[str, Any]=Body(default_factory=dict))` (satır 753): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_tamlik_overrides(scope_type: Optional[str]=None, year: Optional[int]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None, approval_status: Optional[str]=None)` (satır 773): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_tamlik_override_request(payload: dict[str, Any]=Body(default_factory=dict))` (satır 797): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_tamlik_override_approve(override_id: int, payload: dict[str, Any]=Body(default_factory=dict))` (satır 825): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_tamlik_override_reject(override_id: int, payload: dict[str, Any]=Body(default_factory=dict))` (satır 836): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_tamlik_history(scope_type: Optional[str]=None, year: Optional[int]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None, semester: Optional[str]=None)` (satır 855): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `kriter_tamlik_can_run(year: int, faculty_id: Optional[int]=None, department_id: Optional[int]=None, semester: Optional[str]=None)` (satır 879): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `aktif_yillar(fakulte_id: int)` (satır 900): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `algoritma_tumunu_calistir(yil: int, donem: Optional[str]='Guz', user: UserContext=Depends(require_action('run_algorithm')))` (satır 910): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `async mufredat_yukle(file: UploadFile=File(...), hedef_yil: int=Form(...), user: UserContext=Depends(require_action('import_data')))` (satır 922): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `async anket_yukle(file: UploadFile=File(...), fakulte_id: int=Form(...), hedef_yil: int=Form(...))` (satır 955): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `decision_ahp_profiles()` (satır 994): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `decision_ahp_profile_create(payload: dict[str, Any]=Body(default_factory=dict))` (satır 1003): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `decision_ahp_profile_activate(profile_id: int)` (satır 1027): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `decision_policies()` (satır 1038): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `decision_policy_create(payload: dict[str, Any]=Body(default_factory=dict))` (satır 1047): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `decision_policy_activate(policy_id: int)` (satır 1081): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `decision_runs()` (satır 1092): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `decision_runs_execute(payload: dict[str, Any]=Body(default_factory=dict))` (satır 1101): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `decision_run_detail(run_id: int)` (satır 1119): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `decision_run_courses(run_id: int)` (satır 1132): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `decision_course_explanation(decision_id: int)` (satır 1141): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `decision_run_fairness(run_id: int)` (satır 1156): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `decision_run_sensitivity(run_id: int)` (satır 1175): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `decision_run_data_confidence(run_id: int)` (satır 1196): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_history(import_type: Optional[str]=None, status: Optional[str]=None, year: Optional[int]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None, limit: int=200)` (satır 1216): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `async import_preview(file: UploadFile=File(...), import_type: str=Form('criteria'), faculty_id: Optional[int]=Form(None), department_id: Optional[int]=Form(None), year: Optional[int]=Form(None), semester: Optional[str]=Form(None))` (satır 1242): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_value_sources(course_id: Optional[int]=None, year: Optional[int]=None, field_name: Optional[str]=None, active_only: bool=True)` (satır 1269): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `course_value_sources(course_id: int, year: Optional[int]=None, active_only: bool=True)` (satır 1291): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_detail(import_batch_id: int)` (satır 1300): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_rows(import_batch_id: int, limit: int=500)` (satır 1314): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_issues(import_batch_id: int, limit: int=500)` (satır 1323): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_quality(import_batch_id: int)` (satır 1332): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_quality_recalculate(import_batch_id: int)` (satır 1341): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_validate(import_batch_id: int)` (satır 1352): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_approve(import_batch_id: int, payload: dict[str, Any]=Body(default_factory=dict))` (satır 1363): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_reject(import_batch_id: int, payload: dict[str, Any]=Body(default_factory=dict))` (satır 1374): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_activate(import_batch_id: int, payload: dict[str, Any]=Body(default_factory=dict))` (satır 1388): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_diff(import_batch_id: int)` (satır 1399): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_diff_recalculate(import_batch_id: int, payload: dict[str, Any]=Body(default_factory=dict))` (satır 1412): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_rollback_plan(import_batch_id: int)` (satır 1427): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_rollback(import_batch_id: int, payload: dict[str, Any]=Body(default_factory=dict))` (satır 1436): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_impact(import_batch_id: int)` (satır 1450): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_impact_recalculate(import_batch_id: int, payload: dict[str, Any]=Body(default_factory=dict))` (satır 1463): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_state_policies()` (satır 1479): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_state_policy_create(payload: dict[str, Any]=Body(default_factory=dict))` (satır 1488): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_state_policy_activate(policy_id: int)` (satır 1510): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_course_governance(course_id: int)` (satır 1521): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_course_governance_update(course_id: int, payload: dict[str, Any]=Body(default_factory=dict))` (satır 1531): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_state_transition_list(year: Optional[int]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None, course_id: Optional[int]=None, status: Optional[int]=None, approval_status: Optional[str]=None)` (satır 1542): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_course_state_history(course_id: int)` (satır 1568): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_evaluate(payload: dict[str, Any]=Body(default_factory=dict))` (satır 1577): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_approvals(year: Optional[int]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None, status: Optional[str]='pending')` (satır 1607): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_approval_approve(approval_id: int, payload: dict[str, Any]=Body(default_factory=dict))` (satır 1629): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_approval_reject(approval_id: int, payload: dict[str, Any]=Body(default_factory=dict))` (satır 1645): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_overrides(year: Optional[int]=None, course_id: Optional[int]=None, active_only: bool=False)` (satır 1661): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_override_create(payload: dict[str, Any]=Body(default_factory=dict))` (satır 1670): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_override_update(override_id: int, payload: dict[str, Any]=Body(default_factory=dict))` (satır 1696): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_lifecycle_summary(year: int, faculty_id: Optional[int]=None, department_id: Optional[int]=None, semester: Optional[str]=None)` (satır 1714): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_reactivation_candidates(year: Optional[int]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None)` (satır 1734): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `havuz_protected_courses(faculty_id: Optional[int]=None, department_id: Optional[int]=None)` (satır 1754): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_api_response(*, data: Any, message: str | None=None, warnings: list[Any] | None=None, meta: dict[str, Any] | None=None) -> dict` (satır 1762): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_payload_dict(payload: Any) -> dict[str, Any]` (satır 1769): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_criteria()` (satır 1778): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_criteria_create(payload: AHPCriterionRequest)` (satır 1789): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_criteria_update(criterion_key: str, payload: AHPCriterionRequest)` (satır 1800): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_criteria_deactivate(criterion_key: str)` (satır 1813): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_profiles(scope_type: Optional[str]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None, year: Optional[int]=None, semester: Optional[str]=None, status: Optional[str]=None, is_active: Optional[int]=None)` (satır 1824): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_profiles_active(year: Optional[int]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None, semester: Optional[str]=None)` (satır 1852): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_profile_detail(profile_id: int)` (satır 1874): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_profile_create(payload: AHPProfileCreateRequest)` (satır 1886): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_profile_update(profile_id: int, payload: AHPProfileUpdateRequest)` (satır 1899): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_profile_validate(profile_id: int)` (satır 1912): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_profile_submit(profile_id: int, payload: AHPApprovalRequest=Body(default_factory=AHPApprovalRequest))` (satır 1924): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_profile_approve(profile_id: int, payload: AHPApprovalRequest=Body(default_factory=AHPApprovalRequest))` (satır 1936): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_profile_reject(profile_id: int, payload: AHPRejectRequest)` (satır 1948): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_profile_activate(profile_id: int, payload: AHPApprovalRequest=Body(default_factory=AHPApprovalRequest))` (satır 1960): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_profile_archive(profile_id: int, payload: AHPApprovalRequest=Body(default_factory=AHPApprovalRequest))` (satır 1972): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_profile_clone(profile_id: int, payload: AHPCloneRequest)` (satır 1984): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_calculate(payload: AHPCalculateRequest)` (satır 1996): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_consistency_check(payload: AHPCalculateRequest)` (satır 2005): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_profile_impact(profile_id: int)` (satır 2014): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_decision_run_impact(run_id: int, course_id: Optional[int]=None)` (satır 2025): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_decision_run_sensitivity(run_id: int, payload: AHPSensitivityRequest=Body(default_factory=AHPSensitivityRequest))` (satır 2042): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_decision_run_sensitivity_get(run_id: int)` (satır 2054): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_stale_decisions(unresolved_only: bool=True)` (satır 2064): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ahp_stale_decision_resolve(stale_id: int, payload: AHPApprovalRequest=Body(default_factory=AHPApprovalRequest))` (satır 2073): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_policies(scope_type: Optional[str]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None, year: Optional[int]=None, active_only: bool=False)` (satır 2083): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_policy_create(payload: SemesterPlanningPolicyRequest)` (satır 2100): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_policy_update(policy_id: int, payload: SemesterPlanningPolicyRequest)` (satır 2113): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_policy_activate(policy_id: int)` (satır 2126): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_course_availability(year: Optional[int]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None, course_id: Optional[int]=None)` (satır 2139): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_course_availability_create(payload: CourseAvailabilityRequest)` (satır 2156): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_course_availability_patch(availability_id: int, payload: CourseAvailabilityRequest)` (satır 2167): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_instructors(faculty_id: Optional[int]=None, department_id: Optional[int]=None)` (satır 2173): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_instructor_create(payload: InstructorRequest)` (satır 2182): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_instructor_availability(year: Optional[int]=None, semester: Optional[str]=None, instructor_id: Optional[int]=None)` (satır 2193): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_instructor_availability_create(payload: InstructorAvailabilityRequest)` (satır 2202): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_resources(resource_type: Optional[str]=None)` (satır 2213): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_resource_create(payload: TeachingResourceRequest)` (satır 2222): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_resource_requirements(course_id: Optional[int]=None)` (satır 2233): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_resource_requirement_create(payload: ResourceRequirementRequest)` (satır 2242): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_prerequisites(course_id: Optional[int]=None)` (satır 2253): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_prerequisite_create(payload: PrerequisiteRequest)` (satır 2262): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_generate(payload: SemesterPlanGenerateRequest)` (satır 2273): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_generate_alternatives(payload: SemesterPlanGenerateRequest)` (satır 2286): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_runs(year: Optional[int]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None)` (satır 2293): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_run_detail(run_id: int)` (satır 2302): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_run_assignments(run_id: int)` (satır 2314): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_run_violations(run_id: int)` (satır 2323): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_run_scenarios(run_id: int)` (satır 2332): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `semester_planning_run_report(run_id: int)` (satır 2341): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `algorithms_governance(usage_role: Optional[str]=None)` (satır 2350): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `algorithms_governance_report()` (satır 2361): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `algorithms_governance_detail(algorithm_key: str)` (satır 2372): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `algorithms_governance_update(algorithm_key: str, payload: AlgorithmGovernanceUpdateRequest)` (satır 2381): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `algorithms_tasks()` (satır 2399): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `algorithms_for_task(task_key: str)` (satır 2410): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `algorithms_data_guard_check(payload: DataGuardCheckRequest)` (satır 2419): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `benchmark_governed_run_execute(payload: GovernedBenchmarkRunRequest)` (satır 2439): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `benchmark_governed_runs(limit: int=100)` (satır 2450): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `benchmark_governed_run_metrics(run_id: int)` (satır 2459): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `benchmark_governed_run_validation(run_id: int)` (satır 2468): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `benchmark_governed_run_statistics(run_id: int)` (satır 2477): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `benchmark_governed_run_diagnostics(run_id: int)` (satır 2486): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `benchmark_governed_run_leakage(run_id: int)` (satır 2495): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `benchmark_governed_run_clustering(run_id: int)` (satır 2504): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `benchmark_governed_run_report(run_id: int)` (satır 2513): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `benchmark_governed_run_statistical_report(run_id: int)` (satır 2522): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `benchmark_governed_run_clustering_report(run_id: int)` (satır 2531): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `benchmark_governed_run_detail(run_id: int)` (satır 2540): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ml_algorithms()` (satır 2552): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ml_algorithm_update(algorithm_key: str, payload: MLAlgorithmUpdateRequest)` (satır 2563): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ml_readiness(year: Optional[int]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None, algorithm_key: Optional[str]=None)` (satır 2582): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ml_readiness_report_create(payload: MLReadinessReportRequest)` (satır 2605): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ml_features_summary(year: Optional[int]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None)` (satır 2622): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ml_features_build_snapshot(payload: MLFeatureSnapshotRequest)` (satır 2647): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ml_model_runs(algorithm_key: Optional[str]=None, status: Optional[str]=None, limit: int=100)` (satır 2672): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ml_model_run_train(payload: MLTrainRequest)` (satır 2681): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ml_model_run_detail(run_id: int)` (satır 2699): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ml_model_run_deprecate(run_id: int, payload: dict[str, Any]=Body(default_factory=dict))` (satır 2711): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ml_prediction_list(course_id: Optional[int]=None, algorithm_key: Optional[str]=None, limit: int=100)` (satır 2722): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ml_predict_course(payload: MLPredictCourseRequest)` (satır 2735): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ml_predict_batch(payload: MLPredictBatchRequest)` (satır 2754): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ml_prediction_explanation(prediction_id: int)` (satır 2772): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ml_readiness_reports(limit: int=100)` (satır 2784): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ml_readiness_report_detail(report_id: int)` (satır 2793): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_safe_json(value: Any, default: Any) -> Any` (satır 2804): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `data_coverage(year: int, faculty_id: Optional[int]=None, department_id: Optional[int]=None, semester: Optional[str]=None)` (satır 2820): Veri kapsama raporunu al
    - `data_readiness(year: int, faculty_id: Optional[int]=None, department_id: Optional[int]=None, semester: Optional[str]=None)` (satır 2844): Veri olgunluğu değerlendirmesini al
    - `data_confidence(year: Optional[int]=None, course_id: Optional[int]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None, level: Optional[str]=None, limit: int=500)` (satır 2868): Ders veri güveni kayıtlarını listele.
    - `data_coverage_generate(payload: dict[str, Any]=Body(default_factory=dict))` (satır 2925): Yeni kapsama raporu oluştur ve kaydet
    - `data_missing(year: int, course_id: Optional[int]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None, severity: Optional[str]=None, limit: int=500)` (satır 2962): Eksik veri öğelerini listele
    - `data_missing_resolve(item_id: int, payload: dict[str, Any]=Body(default_factory=dict))` (satır 3008): Eksik veri öğesini çözüldü olarak işaretle
    - `data_validation_issues(year: Optional[int]=None, severity: Optional[str]=None, is_resolved: Optional[int]=None, limit: int=500)` (satır 3032): Doğrulama sorunlarını listele
    - `data_validation_issue_resolve(issue_id: int, payload: dict[str, Any]=Body(default_factory=dict))` (satır 3074): Doğrulama sorununu çözüldü olarak işaretle
    - `data_collection_priorities(year: Optional[int]=None, is_completed: Optional[int]=None, limit: int=100)` (satır 3098): Veri toplama önceliklerini listele
    - `data_collection_priority_complete(priority_id: int)` (satır 3141): Veri toplama önceliğini tamamlandı olarak işaretle
    - `decisions_outcomes(run_id: Optional[int]=None, year: Optional[int]=None, course_id: Optional[int]=None, confidence_level: Optional[str]=None, limit: int=500)` (satır 3161): Karar sonuçlarını listele (outcome tracking)

### `app/api/security_routes.py`
  - Fonksiyonlar:
    - `security_health()` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `security_readiness()` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_api_client(data: ApiClientCreate, user: UserContext=Depends(require_action('manage_users')), auth_service: AuthService=Depends(get_auth_service))` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `execute_sql(sql_text: str, user: UserContext=Depends(require_action('use_sql_console')), db: Session=Depends(get_session))` (satır 41): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `async upload_secure_import(import_type: str, faculty_id: int=None, year: int=None, file: UploadFile=File(...), user: UserContext=Depends(require_action('import_data')), db: Session=Depends(get_session))` (satır 56): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `approve_secure_import(job_id: str, user: UserContext=Depends(require_action('approve_import')), db: Session=Depends(get_session))` (satır 73): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `verify_audit_chain(user: UserContext=Depends(require_action('view_audit_logs')), db: Session=Depends(get_session))` (satır 87): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_backup(snapshot_type: str='manual', user: UserContext=Depends(require_action('manage_schema')), db: Session=Depends(get_session))` (satır 96): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

## app/benchmark

### `app/benchmark/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/benchmark/registry.py`
  - Sınıflar:
    - `RegistryEntry` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AlgorithmRegistry` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self) -> None` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `register(self, name: str, group: str, factory: Callable[[], IAlgorithm], *, usage_role: str='benchmark_only', role_label: str='Sadece benchmark') -> None` (satır 37): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `create(self, name: str) -> IAlgorithm` (satır 48): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_algorithms(self, group: str | None=None) -> list[dict[str, str]]` (satır 55): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_register_defaults(self) -> None` (satır 64): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/benchmark/registry_temp.py`
  - Sınıflar:
    - `RegistryEntry` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `create(self, name: str) -> IAlgorithm` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_algorithms(self, group: str | None=None) -> list[dict[str, str]]` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_register_defaults(self) -> None` (satır 47): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/benchmark/result_store.py`
  - Fonksiyonlar:
    - `_json_default(value: Any)` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `ResultStore` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, root_dir: str='reports/benchmark_runs') -> None` (satır 36): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `save_run(self, run: BenchmarkRun, payload: dict[str, Any]) -> Path` (satır 40): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `load_run(self, run_id: str) -> dict[str, Any]` (satır 49): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_runs(self, limit: int=100) -> list[dict[str, Any]]` (satır 55): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/benchmark/runner.py`
  - Sınıflar:
    - `ExperimentRunner` (satır 26): Executes comparable multi-algorithm experiments on shared scenarios.
      - `__init__(self, registry: AlgorithmRegistry | None=None, result_store: ResultStore | None=None) -> None` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, dataset: DatasetBundle, scenario: BenchmarkScenario, algorithm_names: list[str] | None=None) -> dict` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_run_algorithm(self, dataset: DatasetBundle, scenario: BenchmarkScenario, algorithm)` (satır 76): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_get_table(self, dataset: DatasetBundle, scenario: BenchmarkScenario) -> pd.DataFrame` (satır 87): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_run_prediction(self, dataset: DatasetBundle, scenario: BenchmarkScenario, algorithm)` (satır 98): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_run_ranking(self, dataset: DatasetBundle, scenario: BenchmarkScenario, algorithm)` (satır 144): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_run_clustering(self, dataset: DatasetBundle, scenario: BenchmarkScenario, algorithm)` (satır 183): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_run_allocation(self, dataset: DatasetBundle, scenario: BenchmarkScenario, algorithm)` (satır 204): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/benchmark/scenarios.py`
  - Sınıflar:
    - `BenchmarkScenario` (satır 10): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

## app/core

### `app/core/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/core/config.py`
  - Fonksiyonlar:
    - `_bool(value: Any, default: bool=False) -> bool` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_int(value: Any, default: int) -> int` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_load_json(path: str='config.json') -> dict[str, Any]` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `load_app_config(config_path: str='config.json') -> AppConfig` (satır 118): config.json + environment değerlerini tek yerde birleştirir.
  - Sınıflar:
    - `AppConfig` (satır 46): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `db_path(self) -> str` (satır 90): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `db_backend(self) -> str` (satır 94): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_legacy_dict(self) -> dict[str, Any]` (satır 97): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `Settings` (satır 215): Eski importları kırmamak için korunan uyumluluk sınıfı.

### `app/core/database_policy.py`
  - Fonksiyonlar:
    - `runtime_schema_mutation_allowed(config: AppConfig | None=None) -> bool` (satır 46): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `sql_console_allowed_by_policy(config: AppConfig | None=None) -> bool` (satır 55): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `database_policy_summary(config: AppConfig | None=None) -> dict[str, Any]` (satır 62): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `DatabasePolicySummary` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/core/errors.py`
  - Fonksiyonlar:
    - `app_error_from_exception(exc: Exception) -> AppError` (satır 101): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `ErrorPayload` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `to_dict(self) -> dict[str, Any]` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AppError(Exception)` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, message: str, *, code: str | None=None, details: dict[str, Any] | None=None, suggestion: str | None=None, severity: str='error') -> None` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `code(self) -> str` (satır 51): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `to_dict(self) -> dict[str, Any]` (satır 54): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `to_api_response(self) -> dict[str, Any]` (satır 57): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `to_user_message(self) -> str` (satır 60): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ValidationAppError(AppError)` (satır 66): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `NotFoundAppError(AppError)` (satır 71): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `BusinessRuleAppError(AppError)` (satır 76): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `PermissionAppError(AppError)` (satır 81): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DatabaseAppError(AppError)` (satır 86): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SchemaAppError(AppError)` (satır 91): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ConflictAppError(AppError)` (satır 96): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/core/exceptions.py`
  - Sınıflar:
    - `BaseError(Exception)` (satır 9): Tum proje hatalarinin taban sinifi.
    - `StudentNotFoundError(BaseError)` (satır 14): Ogrenci bulunamadiginda firlatilir.
    - `CourseQuotaExceededError(BaseError)` (satır 19): Ders kontenjani doldugunda firlatilir.

### `app/core/logging_config.py`
  - Fonksiyonlar:
    - `configure_logging(config: AppConfig | None=None) -> None` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_logger(name: str) -> logging.Logger` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/core/permissions.py`
  - Fonksiyonlar:
    - `can(user_context: UserContext | None, action: str, resource: Any | None=None, config: AppConfig | None=None) -> bool` (satır 50): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `require_permission(user_context: UserContext | None, action: str, resource: Any | None=None, config: AppConfig | None=None) -> None` (satır 64): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `UserContext` (satır 36): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `demo_admin(cls, config: AppConfig | None=None) -> 'UserContext'` (satır 45): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/core/result.py`
  - Sınıflar:
    - `ServiceWarning` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ServiceResult` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `ok(cls, data: Any=None, message: str | None=None, warnings: list[Any] | None=None, meta: dict[str, Any] | None=None) -> 'ServiceResult'` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `fail(cls, message: str, errors: list[Any] | None=None, data: Any=None, meta: dict[str, Any] | None=None) -> 'ServiceResult'` (satır 37): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `to_api(self) -> dict[str, Any]` (satır 46): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `unwrap(self) -> Any` (satır 58): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/core/security.py`
  - Fonksiyonlar:
    - `generate_api_key(prefix: str='ak') -> str` (satır 6): Generate a secure API key.
    - `hash_api_key(api_key: str) -> str` (satır 11): Hash an API key using SHA-256 for storage.
    - `verify_api_key(plain_key: str, hashed_key: str) -> bool` (satır 16): Constant-time comparison for API keys.
    - `generate_client_id() -> str` (satır 21): Generate a unique client ID.

### `app/core/settings.py`
  - Fonksiyonlar:
    - `load_settings(config_path: str='config.json') -> AppSettings` (satır 25): load_app_config() üzerinden AppSettings oluşturur (geriye uyumluluk).
  - Sınıflar:
    - `AppSettings` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/core/state.py`
  - Sınıflar:
    - `AppState` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `on(self, key: str, callback: Callable[[Any], None]) -> None` (satır 31): state.key değişince callback çalışsın.
      - `set(self, key: str, value: Any) -> None` (satır 35): state alanını güncelle + dinleyicileri tetikle.

## app/dashboard

### `app/dashboard/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/dashboard/api_routes.py`
  - Fonksiyonlar:
    - `list_scenarios()` (satır 50): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_algorithms(group: str | None=None)` (satır 55): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `load_dataset(request: DatasetLoadRequest)` (satır 60): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `run_scenario(request: ScenarioRunRequest)` (satır 80): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `compare_algorithms(request: CompareRequest)` (satır 99): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `recommend_algorithm(request: RecommendationRequest)` (satır 118): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_runs(limit: int=20)` (satır 128): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_run(run_id: str)` (satır 135): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `DatasetLoadRequest(BaseModel)` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ScenarioRunRequest(BaseModel)` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CompareRequest(BaseModel)` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `RecommendationRequest(BaseModel)` (satır 42): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/dashboard/serializers.py`
  - Fonksiyonlar:
    - `summarize_run(run_payload: dict[str, Any]) -> dict[str, Any]` (satır 8): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `build_comparison_table(run_payload: dict[str, Any]) -> list[dict[str, Any]]` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

## app/datasets

### `app/datasets/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/datasets/entities.py`
  - Sınıflar:
    - `Student` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `Course` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `Preference` (satır 37): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SurveyResponse` (satır 46): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `Allocation` (satır 56): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MetricResult` (satır 67): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict[str, Any]` (satır 75): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `BenchmarkRun` (satır 80): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict[str, Any]` (satır 91): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DatasetBundle` (satır 100): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `table(self, layer: str, name: str) -> pd.DataFrame` (satır 107): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/datasets/feature_engineering.py`
  - Fonksiyonlar:
    - `split_features_and_target(features_df: pd.DataFrame, *, target_column: str, drop_columns: list[str] | None=None) -> tuple[pd.DataFrame, pd.Series]` (satır 160): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `FeatureConfig` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `FeatureEngineer` (satır 51): Transforms raw tables into model-ready derived features.
      - `__init__(self, config: FeatureConfig | None=None) -> None` (satır 54): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `generate(self, bundle: DatasetBundle) -> DatasetBundle` (satır 57): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_student_course_matrix(self, students: pd.DataFrame, courses: pd.DataFrame, preferences: pd.DataFrame, survey: pd.DataFrame) -> pd.DataFrame` (satır 80): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_normalize_numeric(self, df: pd.DataFrame) -> pd.DataFrame` (satır 108): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_add_composite_scores(self, df: pd.DataFrame) -> pd.DataFrame` (satır 129): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_one_hot_encode(self, df: pd.DataFrame) -> pd.DataFrame` (satır 152): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/datasets/loaders.py`
  - Fonksiyonlar:
    - `ensure_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame` (satır 142): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ensure_non_negative(df: pd.DataFrame, columns: list[str], fill_value: float=0.0) -> pd.DataFrame` (satır 150): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `sanitize_dataset(bundle: DatasetBundle) -> DatasetBundle` (satır 159): Run minimal schema-safe clean-up before feature engineering.
  - Sınıflar:
    - `RealDatasetLoader` (satır 15): Load canonical tables from real data sources.
      - `__init__(self, dataset_name: str='real_dataset') -> None` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `from_csv_folder(self, folder_path: str | os.PathLike[str]) -> DatasetBundle` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `from_sqlite(self, db_path: str | os.PathLike[str]) -> DatasetBundle` (satır 45): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_validate_tables(self, tables: dict[str, pd.DataFrame]) -> None` (satır 70): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_students(self, conn: sqlite3.Connection) -> pd.DataFrame` (satır 75): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_courses(self, conn: sqlite3.Connection) -> pd.DataFrame` (satır 89): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_preferences(self, conn: sqlite3.Connection) -> pd.DataFrame` (satır 104): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_survey(self, conn: sqlite3.Connection) -> pd.DataFrame` (satır 118): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_allocations(self, conn: sqlite3.Connection) -> pd.DataFrame` (satır 130): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/datasets/preprocess.py`
  - Fonksiyonlar:
    - `save_dataset_layers(bundle: DatasetBundle, output_root: str | Path) -> None` (satır 75): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `PipelineConfig` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DataPipeline` (satır 27): Pipeline that materializes raw_real, derived, synthetic layers.
      - `__init__(self, loader: RealDatasetLoader | None=None, feature_engineer: FeatureEngineer | None=None, synthetic_generator: SyntheticDataGenerator | None=None) -> None` (satır 30): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, config: PipelineConfig) -> DatasetBundle` (satır 40): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load(self, config: PipelineConfig) -> DatasetBundle` (satır 68): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/datasets/synthetic_generator.py`
  - Sınıflar:
    - `SyntheticConfig` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SyntheticDataGenerator` (satır 32): Produces synthetic variants while preserving source distribution.
      - `__init__(self, default_seed: int=42) -> None` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `generate(self, bundle: DatasetBundle, table_name: str='student_course_features_unencoded', config: SyntheticConfig | None=None) -> pd.DataFrame` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `generate_scale_tiers(self, bundle: DatasetBundle, table_name: str='student_course_features_unencoded', noise_std: float=0.02, class_imbalance_alpha: float=0.0, capacity_scale: float=1.0) -> dict[str, pd.DataFrame]` (satır 55): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_resolve_base_table(self, bundle: DatasetBundle, table_name: str) -> pd.DataFrame` (satır 75): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_bootstrap_sample(self, base: pd.DataFrame, target_size: int, class_imbalance_alpha: float, rng: np.random.Generator) -> pd.DataFrame` (satır 82): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_inject_noise(self, df: pd.DataFrame, noise_std: float, rng: np.random.Generator) -> pd.DataFrame` (satır 104): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_apply_capacity_constraints(self, df: pd.DataFrame, capacity_scale: float, rng: np.random.Generator) -> pd.DataFrame` (satır 120): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

## app/db

### `app/db/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/db/backend.py`
  - Fonksiyonlar:
    - `database_backend(database_url: str | None) -> str` (satır 16): Return a stable backend name from a SQLAlchemy database URL.
    - `is_sqlite_url(database_url: str | None) -> bool` (satır 30): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `is_postgresql_url(database_url: str | None) -> bool` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `is_sqlite_connection(conn: Any) -> bool` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `require_sqlite_url(database_url: str | None, *, feature: str) -> None` (satır 42): Fail fast when a legacy sqlite3-only path is used with another backend.

### `app/db/database.py`
  - Fonksiyonlar:
    - `_load_db_url()` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_build_engine(url: str)` (satır 36): Verilen URL'ye uygun SQLAlchemy engine oluşturur.
    - `_fallback_sqlite_url() -> str` (satır 53): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_ensure_engine()` (satır 60): Engine oluştur veya URL değiştiyse yenile.
    - `get_engine()` (satır 96): Aktif engine'i döndürür.
    - `get_session()` (satır 102): Thread-safe session döndürür.
    - `dispose_session()` (satır 108): Mevcut thread'in session'ını temizler.
    - `create_all_tables()` (satır 114): ORM modellerinden tüm tabloları oluşturur (PostgreSQL migration için).

### `app/db/models.py`
  - Sınıflar:
    - `Okul(Base)` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `Bolum(Base)` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `Fakulte(Base)` (satır 49): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `Ogrenci(Base)` (satır 68): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `Ders(Base)` (satır 87): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `normalized_type(self) -> str` (satır 114): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DersKriterleri(Base)` (satır 128): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `Havuz(Base)` (satır 163): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `OgretimGorevlisi(Base)` (satır 207): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DersOgretim(Base)` (satır 234): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `Mufredat(Base)` (satır 262): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MufredatDers(Base)` (satır 281): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `Kayit(Base)` (satır 297): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `Performans(Base)` (satır 319): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `Populerlik(Base)` (satır 340): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AnketForm(Base)` (satır 364): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AnketCevap(Base)` (satır 385): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AnketSonuclari(Base)` (satır 408): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `Skor(Base)` (satır 429): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `OgrenciEngel(Base)` (satır 451): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CriteriaDepartmentStatus(Base)` (satır 469): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CriteriaFacultyStatus(Base)` (satır 490): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CurriculumGenerationAudit(Base)` (satır 513): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DecisionCriteriaDefinition(Base)` (satır 538): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AHPWeightProfile(Base)` (satır 558): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AHPProfilePolicy(Base)` (satır 594): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AHPProfileApprovalLog(Base)` (satır 615): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DecisionPolicy(Base)` (satır 631): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DecisionRun(Base)` (satır 664): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CourseDecision(Base)` (satır 695): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CourseScoreBreakdown(Base)` (satır 725): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CourseTrendAnalysis(Base)` (satır 748): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CourseDataConfidence(Base)` (satır 764): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CourseDecisionExplanation(Base)` (satır 785): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DecisionSensitivityResult(Base)` (satır 800): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DecisionFairnessReport(Base)` (satır 817): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CourseGovernanceFlag(Base)` (satır 830): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `PoolStatePolicy(Base)` (satır 853): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CourseStateTransition(Base)` (satır 893): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CourseStateApproval(Base)` (satır 926): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CourseStateOverride(Base)` (satır 949): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ImportBatch(Base)` (satır 971): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ImportQualityCheck(Base)` (satır 1015): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ImportRowIssue(Base)` (satır 1037): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ImportDiff(Base)` (satır 1054): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ImportDiffItem(Base)` (satır 1068): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ImportRollbackLog(Base)` (satır 1084): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DecisionRunImportSource(Base)` (satır 1098): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ImportImpactReport(Base)` (satır 1108): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DecisionStalenessFlag(Base)` (satır 1128): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AHPSensitivityResult(Base)` (satır 1143): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AHPCourseSensitivityItem(Base)` (satır 1157): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CriteriaValueSource(Base)` (satır 1174): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CriteriaCompletionMatrix(Base)` (satır 1196): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CriteriaValidationIssue(Base)` (satır 1219): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CriteriaCompletionPolicy(Base)` (satır 1238): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CriteriaMissingDataRisk(Base)` (satır 1265): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CriteriaCompletionTask(Base)` (satır 1284): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CriteriaCompletionOverride(Base)` (satır 1310): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CriteriaCompletionHistory(Base)` (satır 1337): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MLAlgorithmRegistry(Base)` (satır 1361): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MLFeatureSnapshot(Base)` (satır 1380): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MLModelRun(Base)` (satır 1397): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MLPrediction(Base)` (satır 1427): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MLPredictionExplanation(Base)` (satır 1452): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MLReadinessReport(Base)` (satır 1465): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AlgorithmGovernanceRegistry(Base)` (satır 1484): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AlgorithmTaskMapping(Base)` (satır 1511): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AlgorithmBenchmarkRun(Base)` (satır 1523): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `BenchmarkMetricResult(Base)` (satır 1546): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `BenchmarkValidationResult(Base)` (satır 1560): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `BenchmarkStatisticalComparison(Base)` (satır 1576): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `BenchmarkDataLeakageReport(Base)` (satır 1593): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `BenchmarkModelDiagnostic(Base)` (satır 1607): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ClusteringEvaluationResult(Base)` (satır 1624): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SemesterPlanningPolicy(Base)` (satır 1646): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CourseSemesterAvailability(Base)` (satır 1683): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `Instructor(Base)` (satır 1703): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CourseInstructorAssignment(Base)` (satır 1716): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `InstructorSemesterAvailability(Base)` (satır 1730): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `TeachingResource(Base)` (satır 1746): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CourseResourceRequirement(Base)` (satır 1763): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SemesterResourceCapacity(Base)` (satır 1777): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CoursePrerequisite(Base)` (satır 1791): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SemesterRequiredCourseLoad(Base)` (satır 1803): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CourseTimeConstraint(Base)` (satır 1820): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SemesterPlanRun(Base)` (satır 1835): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SemesterPlanCourseAssignment(Base)` (satır 1859): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SemesterPlanConstraintViolation(Base)` (satır 1875): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SemesterPlanScenario(Base)` (satır 1888): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SchemaCompatLog(Base)` (satır 1907): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DataCoverageReport(Base)` (satır 1924): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DataReadinessAssessment(Base)` (satır 1955): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MissingDataItem(Base)` (satır 1981): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DataValidationIssue(Base)` (satır 2003): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `LowConfidenceDecisionFlag(Base)` (satır 2030): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DataCollectionPriority(Base)` (satır 2049): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `PostDecisionOutcome(Base)` (satır 2072): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `FairnessMetricItem(Base)` (satır 2097): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MLDatasetSnapshot(Base)` (satır 2112): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ApiClient(Base)` (satır 2132): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SqlConsoleAuditLog(Base)` (satır 2150): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SecureImportJob(Base)` (satır 2173): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SecureImportJobRow(Base)` (satır 2209): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SecurityAuditLog(Base)` (satır 2226): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DataSnapshot(Base)` (satır 2256): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/db/schema_compat.py`
  - Fonksiyonlar:
    - `normalize_term(raw: str | None) -> str` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_table_exists(cur: sqlite3.Cursor, table_name: str) -> bool` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_column_names(cur: sqlite3.Cursor, table_name: str) -> set[str]` (satır 37): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_index_names(cur: sqlite3.Cursor, table_name: str) -> set[str]` (satır 42): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_table_sql(cur: sqlite3.Cursor, table_name: str) -> str` (satır 52): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_ensure_columns(cur: sqlite3.Cursor, table_name: str, columns: list[tuple[str, str]]) -> int` (satır 61): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_utc_now() -> str` (satır 74): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_schema_mutation_allowed() -> bool` (satır 78): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_log_schema_compat(conn: sqlite3.Connection, *, action_type: str, table_name: str, column_name: str | None=None, index_name: str | None=None, sql_text: str | None=None, success: bool=True, message: str | None=None) -> None` (satır 88): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_log_schema_compat_result(conn: sqlite3.Connection, name: str, result: dict[str, Any]) -> None` (satır 126): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ensure_architecture_schema(conn: sqlite3.Connection, commit: bool=True) -> dict[str, int]` (satır 152): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_criteria_term_case_sql(column_name: str) -> str` (satır 440): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_create_ders_kriterleri_table(cur: sqlite3.Cursor, table_name: str='ders_kriterleri') -> None` (satır 448): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_needs_ders_kriterleri_rebuild(cur: sqlite3.Cursor) -> bool` (satır 477): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_rebuild_ders_kriterleri_table(cur: sqlite3.Cursor) -> None` (satır 484): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ensure_criteria_import_schema(conn: sqlite3.Connection, commit: bool=True) -> dict[str, int]` (satır 551): Kriter belge import semasini hazirlar.
    - `ensure_ders_code_schema(conn: sqlite3.Connection) -> dict[str, int]` (satır 688): Legacy ders tablolarinda eksik ders kodu kolonunu tamamlar.
    - `ensure_havuz_semester_schema(conn: sqlite3.Connection) -> dict[str, int]` (satır 713): havuz tablosunu donem-aware hale getirir.
    - `ensure_skor_schema(conn: sqlite3.Connection) -> dict[str, int]` (satır 821): skor tablosundaki kritik kolon/index uyumlulugunu saglar.
    - `ensure_survey_import_schema(conn: sqlite3.Connection, commit: bool=True) -> dict[str, int]` (satır 938): Fakulte+yil bazli anket import semasini hazirlar.
    - `ensure_decision_governance_schema(conn: sqlite3.Connection, commit: bool=True) -> dict[str, int]` (satır 1055): Karar yonetisimi ve aciklanabilirlik tablolarini hazirlar.
    - `ensure_ahp_governance_schema(conn: sqlite3.Connection, commit: bool=True) -> dict[str, int]` (satır 1332): AHP profil, kriter, policy, staleness ve sensitivity semasini hazirlar.
    - `ensure_pool_state_governance_schema(conn: sqlite3.Connection, commit: bool=True) -> dict[str, int]` (satır 1529): Havuz yasam dongusu state machine semasini idempotent hazirlar.
    - `ensure_import_governance_schema(conn: sqlite3.Connection, commit: bool=True) -> dict[str, int]` (satır 1759): Import audit trail ve veri kokeni tablolarini hazirlar.
    - `ensure_criteria_completion_governance_schema(conn: sqlite3.Connection, commit: bool=True) -> dict[str, int]` (satır 2050): Gelismis kriter tamlik, validation, risk, gorev ve override semasini hazirlar.
    - `ensure_ml_governance_schema(conn: sqlite3.Connection, commit: bool=True) -> dict[str, int]` (satır 2329): ML algoritma konumlandırma, model run, tahmin ve readiness semasini hazirlar.
    - `ensure_algorithm_governance_schema(conn: sqlite3.Connection, commit: bool=True) -> dict[str, int]` (satır 2495): Algoritma yönetişimi, benchmark metrikleri ve istatistiksel değerlendirme semasını hazırlar.
    - `ensure_semester_planning_schema(conn: sqlite3.Connection, commit: bool=True) -> dict[str, int]` (satır 2674): Policy tabanli Guz/Bahar donem planlama semasini hazirlar.
    - `ensure_data_quality_schema(conn: sqlite3.Connection, commit: bool=True) -> dict[str, int]` (satır 2970): Data quality, readiness, confidence follow-up tablolarini hazirlar.
    - `ensure_reporting_schema(conn: sqlite3.Connection) -> dict[str, dict[str, int]]` (satır 3321): Raporlama icin gereken tum kritik tablolari synchronize eder.

### `app/db/session.py`
  - Fonksiyonlar:
    - `_resolve_sqlite_path(db_path: str | None=None, config: AppConfig | None=None) -> str` (satır 23): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_sqlite_url_for_path(db_path: str) -> str` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `open_sqlite_connection(db_path: str | None=None, *, row_factory: bool=True)` (satır 35): Legacy uyumluluk: Raw DBAPI connection döndürür.
    - `db_session(db_path: str | None=None) -> Iterator[sqlite3.Connection]` (satır 51): Kısa ömürlü legacy SQLite transaction context manager.
    - `get_db() -> Iterator[Session]` (satır 64): FastAPI dependency uyumlu SQLAlchemy session üretir.
    - `init_database(db_path: str | None=None) -> dict[str, object]` (satır 77): Veritabanı şemasını oluşturur/günceller.
    - `close_database() -> None` (satır 120): Engine'i temizler.
    - `get_alembic_head(config_path: str='alembic.ini') -> str | None` (satır 126): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `stamp_database_head(engine_obj: object, config_path: str='alembic.ini') -> str | None` (satır 137): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/db/sqlite_connection.py`
  - Fonksiyonlar:
    - `connect_sqlite(db_path: str='', *, row_factory: bool=False)` (satır 12): Legacy uyumluluk: Raw DBAPI connection döndürür.
    - `is_database_locked_error(exc: BaseException) -> bool` (satır 23): Veritabanı kilitli hatası mı kontrol eder.

### `app/db/sqlite_db.py`
  - Sınıflar:
    - `Database` (satır 19): UI tarafı için SQLAlchemy tabanlı küçük DB wrapper.
      - `__init__(self, db_path: Optional[str]=None)` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `connect(self, db_path: str | None=None) -> None` (satır 37): Veritabanı engine'ini hazırlar. PostgreSQL'de db_path yoksayılır.
      - `conn(self)` (satır 43): Legacy uyumluluk: raw DBAPI connection döndürür.
      - `ensure(self) -> None` (satır 50): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `tables(self) -> list[str]` (satır 60): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_columns(self, table: str) -> set[str]` (satır 66): Tablonun kolon isimlerini döndürür.
      - `head(self, table: str, limit: int=1000) -> tuple[list[str], list[Any]]` (satır 74): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `read_df(self, query: str, params=None)` (satır 82): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run_sql(self, query: str, params: Optional[Sequence[Any]]=None) -> tuple[list[str], list[Any]]` (satır 89): SELECT => (cols, rows)
      - `_adapt_params(query: str, params: Optional[Sequence[Any]]) -> tuple[str, dict[str, Any] | None]` (satır 117): SQLite ? parametrelerini SQLAlchemy :param formatına dönüştürür.

## app/etl

### `app/etl/import_dersler_master.py`
  - Fonksiyonlar:
    - `find_file(filename, search_paths)` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `run_import()` (satır 23): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/etl/import_kriterler_excel.py`
  - Fonksiyonlar:
    - `_normalize_col(s: str) -> str` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_find_col(df: pd.DataFrame, *names)` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_safe_int(val, default=0)` (satır 41): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_safe_float(val, default=0.0)` (satır 50): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_find_ders_id(cur, ders_adi: str=None, ders_id: int=None, kod: str=None)` (satır 59): Ders adı, ID veya kod ile ders_id bulur.
    - `_clean_year(val)` (satır 81): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `run_import(excel_path: str, db_path: str=None)` (satır 89): Excel'den ders kriterlerini toplu yükler.

### `app/etl/import_mufredat_excel.py`
  - Fonksiyonlar:
    - `normalize_col(s: str) -> str` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `find_col(df: pd.DataFrame, *names)` (satır 37): Kolon adını esnek şekilde bulur (Türkçe/İngilizce/underscore varyasyonları).
    - `clean_year(val, base_year_if_class=None)` (satır 46): - 2022, 2022.0, '2022/2023', '2022-2023 Güz' -> 2022
    - `get_fakulte_id(cur, fak_adi)` (satır 70): Fakülte adını kullanarak fakülte ID'sini bulur.
    - `get_bolum_id(cur, bol_adi, fakulte_id)` (satır 80): Bölüm adını kullanarak bölüm ID'sini bulur (fakülteye bağlı).
    - `find_course_id(cur, ders_adi: str)` (satır 90): Ders adını daha toleranslı eşleştirir:
    - `find_course_id_by_code_or_name(cur, ders_kodu=None, ders_adi=None)` (satır 115): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `collect_curriculum_rows(df: pd.DataFrame)` (satır 125): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `replace_scope_curriculum(cur, f_id, b_id, yil, donem, ders_ids)` (satır 222): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `run_import(excel_path=None, db_path=None)` (satır 264): Excel'den müfredat verisi aktarır.
    - `_main()` (satır 347): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

## app/health

### `app/health/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/health/checks/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/health/checks/ahp_check.py`
  - Sınıflar:
    - `AHPWeightSumCheck(BaseHealthCheck)` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AHPConsistencyRatioCheck(BaseHealthCheck)` (satır 67): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 73): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AHPMatrixShapeCheck(BaseHealthCheck)` (satır 111): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 116): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AHPReciprocalMatrixCheck(AHPMatrixShapeCheck)` (satır 120): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CriteriaCompletenessCheck(AHPMatrixShapeCheck)` (satır 124): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AlternativeCompletenessCheck(AHPMatrixShapeCheck)` (satır 128): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SensitivityReadinessCheck(AHPMatrixShapeCheck)` (satır 132): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/health/checks/analytics_check.py`
  - Sınıflar:
    - `AnalyticsDependencyCheck(BaseHealthCheck)` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ChartGenerationCheck(BaseHealthCheck)` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 39): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `NumericDataAvailabilityCheck(BaseHealthCheck)` (satır 54): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 59): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `EmptyDatasetHandlingCheck(BaseHealthCheck)` (satır 76): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 81): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/health/checks/base_check.py`
  - Sınıflar:
    - `BaseHealthCheck` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext) -> HealthCheckResult` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `safe_run(self, context: HealthContext) -> HealthCheckResult` (satır 23): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `result(self, status: HealthStatus | str, message: str, *, severity: HealthSeverity | str | None=None, detail: str='', suggestion: str='İşlem gerekmiyor.', metadata: dict[str, Any] | None=None) -> HealthCheckResult` (satır 51): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/health/checks/data_quality_check.py`
  - Fonksiyonlar:
    - `_existing_tables(repo: SQLiteRepository, candidates: tuple[str, ...]) -> list[str]` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `MissingValueCheck(BaseHealthCheck)` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DuplicateRecordCheck(BaseHealthCheck)` (satır 49): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 55): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `RangeValidationCheck(BaseHealthCheck)` (satır 95): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 101): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DataProfilingCheck(BaseHealthCheck)` (satır 133): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 139): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `OrphanRecordCheck(BaseHealthCheck)` (satır 153): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 158): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `OutlierDetectionCheck(BaseHealthCheck)` (satır 166): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 171): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/health/checks/database_check.py`
  - Sınıflar:
    - `SQLiteConnectionCheck(BaseHealthCheck)` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SQLiteIntegrityCheck(BaseHealthCheck)` (satır 49): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 55): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SQLiteForeignKeyCheck(BaseHealthCheck)` (satır 69): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 75): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SQLiteTableCountCheck(BaseHealthCheck)` (satır 90): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 97): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SQLiteWritePermissionCheck(BaseHealthCheck)` (satır 124): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 130): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/health/checks/function_check.py`
  - Sınıflar:
    - `ImportCheck(BaseHealthCheck)` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ServiceFunctionCheck(BaseHealthCheck)` (satır 43): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 48): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ContractCheck(BaseHealthCheck)` (satır 60): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 65): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ExceptionHandlingCheck(BaseHealthCheck)` (satır 73): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 78): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `BoundaryCheck(BaseHealthCheck)` (satır 86): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 91): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/health/checks/performance_check.py`
  - Sınıflar:
    - `DatabaseConnectionTimeCheck(BaseHealthCheck)` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `QueryPerformanceCheck(BaseHealthCheck)` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 50): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `FunctionExecutionTimeCheck(BaseHealthCheck)` (satır 83): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 88): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MemoryUsageCheck(BaseHealthCheck)` (satır 95): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 100): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SlowQueryDetectionCheck(BaseHealthCheck)` (satır 116): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 121): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/health/checks/reporting_check.py`
  - Sınıflar:
    - `ReportDirectoryCheck(BaseHealthCheck)` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ExportPermissionCheck(BaseHealthCheck)` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 39): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `PDFExportCheck(BaseHealthCheck)` (satır 55): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 60): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ExcelExportCheck(BaseHealthCheck)` (satır 72): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 77): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ImportFileValidationCheck(BaseHealthCheck)` (satır 84): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 89): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/health/checks/schema_check.py`
  - Sınıflar:
    - `SchemaValidationCheck(BaseHealthCheck)` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ExpectedTablesCheck(SchemaValidationCheck)` (satır 63): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ExpectedColumnsCheck(SchemaValidationCheck)` (satır 67): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SchemaCompatibilityCheck(BaseHealthCheck)` (satır 71): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 77): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ColumnTypeCheck(BaseHealthCheck)` (satır 90): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 95): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/health/checks/security_check.py`
  - Sınıflar:
    - `SQLConsolePermissionCheck(BaseHealthCheck)` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DeveloperModeCheck(BaseHealthCheck)` (satır 48): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 55): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `UnsafeSQLPatternCheck(BaseHealthCheck)` (satır 73): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 78): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `PathTraversalCheck(BaseHealthCheck)` (satır 89): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 94): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SensitiveLogCheck(BaseHealthCheck)` (satır 100): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 105): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/health/checks/table_view_check.py`
  - Sınıflar:
    - `TableListLoadCheck(BaseHealthCheck)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `TablePreviewCheck(BaseHealthCheck)` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 39): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `LargeTableSafetyCheck(BaseHealthCheck)` (satır 54): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run(self, context: HealthContext)` (satır 59): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/health/health_config.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/health/models.py`
  - Fonksiyonlar:
    - `now_iso() -> str` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `HealthStatus(str, Enum)` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `HealthSeverity(str, Enum)` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `HealthCheckResult` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `to_dict(self) -> dict[str, Any]` (satır 47): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `HealthReport` (satır 52): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `to_dict(self) -> dict[str, Any]` (satır 65): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `HealthContext` (satır 72): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

## app/metrics

### `app/metrics/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/metrics/academic.py`
  - Fonksiyonlar:
    - `ranking_similarity_with_ground_truth(predicted_ranking: list[Any], ground_truth_ranking: list[Any]) -> float` (satır 11): Computes Spearman rank correlation between predicted and known ranking.
    - `pattern_reproduction_score(observed: pd.DataFrame, expected_patterns: dict[str, dict[str, Any]]) -> float` (satır 35): Generic pattern-matching metric.

### `app/metrics/classification.py`
  - Fonksiyonlar:
    - `classification_metrics(y_true: list[Any] | np.ndarray, y_pred: list[Any] | np.ndarray, y_proba: np.ndarray | None=None, *, average: str='weighted') -> dict[str, float]` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `top_k_accuracy(y_true: list[Any] | np.ndarray, ranked_labels: list[list[Any]], k: int=3) -> float` (satır 39): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/metrics/clustering.py`
  - Fonksiyonlar:
    - `clustering_metrics(X: pd.DataFrame | np.ndarray, labels: list[int] | np.ndarray) -> dict[str, float]` (satır 10): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/metrics/fairness.py`
  - Fonksiyonlar:
    - `average_rank(assignments: pd.DataFrame) -> float` (satır 9): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `top_k_satisfaction(assignments: pd.DataFrame, k: int=3) -> float` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `envy_score(assignments: pd.DataFrame) -> float` (satır 24): Proxy envy:
    - `seat_fill_rate(assignments: pd.DataFrame, courses: pd.DataFrame) -> float` (satır 46): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `allocation_fairness_metrics(assignments: pd.DataFrame, courses: pd.DataFrame, top_k: int=3) -> dict[str, float]` (satır 61): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/metrics/performance.py`
  - Sınıflar:
    - `PerformanceSnapshot` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict[str, float]` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `PerformanceTracker` (satır 24): Tracks latency, throughput, and memory usage for benchmarked calls.
      - `__init__(self, workload_size: int=1) -> None` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__enter__(self) -> 'PerformanceTracker'` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__exit__(self, exc_type, exc, tb) -> None` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `snapshot(self) -> PerformanceSnapshot` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/metrics/ranking.py`
  - Fonksiyonlar:
    - `hit_at_k(actual_items: list[set], predicted_rankings: list[list], k: int=5) -> float` (satır 8): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ndcg_at_k(actual_items: list[set], predicted_rankings: list[list], k: int=5) -> float` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `map_at_k(actual_items: list[set], predicted_rankings: list[list], k: int=5) -> float` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `coverage(predicted_rankings: list[list], catalog_items: set) -> float` (satır 45): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `diversity(predicted_rankings: list[list]) -> float` (satır 52): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

## app/repositories

### `app/repositories/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/repositories/base.py`
  - Fonksiyonlar:
    - `row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None=None) -> dict[str, Any] | None` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `fetch_all_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `validate_identifier(name: str) -> str` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/repositories/benchmark_repository.py`
  - Sınıflar:
    - `BenchmarkRepository` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, conn: sqlite3.Connection)` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_algorithm_governance(self) -> list[dict[str, Any]]` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_benchmark_runs(self, limit: int=100) -> list[dict[str, Any]]` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_benchmark_run(self, run_id: int) -> dict[str, Any] | None` (satır 43): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/repositories/course_repository.py`
  - Sınıflar:
    - `CourseRepository` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, conn: sqlite3.Connection)` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_courses(self, faculty_id: int | None=None, elective_only: bool=False) -> list[dict[str, Any]]` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_faculties(self) -> list[dict[str, Any]]` (satır 42): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_departments(self, faculty_id: int | None=None) -> list[dict[str, Any]]` (satır 47): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_curriculum_years(self) -> list[int]` (satır 55): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/repositories/criteria_repository.py`
  - Sınıflar:
    - `CriteriaRepository` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, conn: sqlite3.Connection)` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `find_by_scope(self, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> list[dict[str, Any]]` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/repositories/curriculum_repository.py`
  - Sınıflar:
    - `CurriculumRepository` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, conn: sqlite3.Connection)` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_curricula(self, year: int | None=None, department_id: int | None=None, semester: str | None=None) -> list[dict[str, Any]]` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/repositories/decision_repository.py`
  - Sınıflar:
    - `DecisionRepository` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, conn: sqlite3.Connection)` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_runs(self, limit: int=100) -> list[dict[str, Any]]` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_course_decisions(self, decision_run_id: int) -> list[dict[str, Any]]` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/repositories/department_repository.py`
  - Sınıflar:
    - `DepartmentRepository(CourseRepository)` (satır 7): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/repositories/faculty_repository.py`
  - Sınıflar:
    - `FacultyRepository(CourseRepository)` (satır 7): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/repositories/import_repository.py`
  - Sınıflar:
    - `ImportRepository` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, conn: sqlite3.Connection)` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_batches(self, limit: int=200) -> list[dict[str, Any]]` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/repositories/pool_repository.py`
  - Sınıflar:
    - `PoolRepository` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, conn: sqlite3.Connection)` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_pool_rows(self, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> list[dict[str, Any]]` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/repositories/report_repository.py`
  - Sınıflar:
    - `ReportRepository` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, conn: sqlite3.Connection)` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_tables(self) -> list[str]` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `table_head(self, table: str, limit: int=1000) -> tuple[list[str], list[Any]]` (satır 25): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `table_count(self, table: str) -> int` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `select_query(self, query: str, params: tuple[Any, ...]=()) -> list[dict[str, Any]]` (satır 40): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/repositories/score_repository.py`
  - Sınıflar:
    - `ScoreRepository` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, conn: sqlite3.Connection)` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_scores(self, year: int | None=None, semester: str | None=None) -> list[dict[str, Any]]` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/repositories/sqlite_repository.py`
  - Fonksiyonlar:
    - `quote_identifier(name: str) -> str` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `SQLiteRepository` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, db_path: str)` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `connect(self) -> Iterator[sqlite3.Connection]` (satır 23): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `table_names(self) -> list[str]` (satır 30): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `table_count(self) -> int` (satır 37): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `columns(self, table_name: str) -> list[dict[str, Any]]` (satır 40): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `row_count(self, table_name: str) -> int` (satır 55): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `execute_scalar(self, sql: str, params: tuple[Any, ...]=()) -> Any` (satır 60): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `execute_rows(self, sql: str, params: tuple[Any, ...]=()) -> list[sqlite3.Row]` (satır 65): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `integrity_check(self) -> list[str]` (satır 69): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `foreign_key_check(self) -> list[dict[str, Any]]` (satır 73): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `write_permission_check(self) -> None` (satır 77): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `profile_tables(self, limit: int=40) -> list[dict[str, Any]]` (satır 87): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/repositories/system_repository.py`
  - Sınıflar:
    - `SystemRepository` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, conn: sqlite3.Connection)` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `ping(self) -> bool` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `table_count(self) -> int` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `database_info(self, db_path: str | None=None) -> dict[str, Any]` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `latest_schema_compat_logs(self, limit: int=20) -> list[dict[str, Any]]` (satır 36): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `latest_sql_console_audit_logs(self, limit: int=50) -> list[dict[str, Any]]` (satır 66): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

## app/schemas

### `app/schemas/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/schemas/ahp.py`
  - Sınıflar:
    - `AHPCriterionRequest(BaseModel)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AHPProfileCreateRequest(BaseModel)` (satır 26): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AHPProfileUpdateRequest(BaseModel)` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AHPRejectRequest(BaseModel)` (satır 60): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AHPApprovalRequest(BaseModel)` (satır 65): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AHPCloneRequest(BaseModel)` (satır 70): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AHPCalculateRequest(BaseModel)` (satır 76): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AHPSensitivityRequest(BaseModel)` (satır 82): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/schemas/algorithm_governance.py`
  - Sınıflar:
    - `AlgorithmGovernanceUpdateRequest(BaseModel)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DataGuardCheckRequest(BaseModel)` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `GovernedBenchmarkRunRequest(BaseModel)` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `to_payload(self) -> dict[str, Any]` (satır 57): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/schemas/auth.py`
  - Sınıflar:
    - `UserContext(BaseModel)` (satır 6): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ApiClientCreate(BaseModel)` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ApiClientResponse(BaseModel)` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ApiClientCreatedResponse(ApiClientResponse)` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/schemas/common.py`
  - Sınıflar:
    - `ServiceWarning(BaseModel)` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ErrorResponse(BaseModel)` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `PaginationMeta(BaseModel)` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ApiResponse(BaseModel, Generic[T])` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ApiErrorResponse(BaseModel)` (satır 41): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/schemas/course.py`
  - Sınıflar:
    - `CourseOut(BaseModel)` (satır 7): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/schemas/criteria.py`
  - Sınıflar:
    - `CriteriaScopeQuery(BaseModel)` (satır 7): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/schemas/curriculum.py`
  - Sınıflar:
    - `CurriculumScope(BaseModel)` (satır 7): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/schemas/decision.py`
  - Sınıflar:
    - `DecisionRunRequest(BaseModel)` (satır 7): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/schemas/import_schema.py`
  - Sınıflar:
    - `ImportPreviewRequest(BaseModel)` (satır 7): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/schemas/ml.py`
  - Sınıflar:
    - `MLAlgorithmUpdateRequest(BaseModel)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MLTrainRequest(BaseModel)` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MLPredictCourseRequest(BaseModel)` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MLPredictBatchRequest(BaseModel)` (satır 36): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MLReadinessReportRequest(BaseModel)` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MLFeatureSnapshotRequest(BaseModel)` (satır 51): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/schemas/pool.py`
  - Sınıflar:
    - `PoolTransitionRequest(BaseModel)` (satır 7): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/schemas/reporting.py`
  - Sınıflar:
    - `ReportExportRequest(BaseModel)` (satır 7): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/schemas/semester_planning.py`
  - Sınıflar:
    - `SemesterPlanningPolicyRequest(BaseModel)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CourseAvailabilityRequest(BaseModel)` (satır 42): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `InstructorRequest(BaseModel)` (satır 57): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `InstructorAvailabilityRequest(BaseModel)` (satır 65): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `TeachingResourceRequest(BaseModel)` (satır 76): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ResourceRequirementRequest(BaseModel)` (satır 87): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `PrerequisiteRequest(BaseModel)` (satır 96): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SemesterPlanGenerateRequest(BaseModel)` (satır 103): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

## app/scripts

### `app/scripts/ahp_weights_demo.py`
  - Fonksiyonlar:
    - `main() -> None` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/scripts/analyze_duplicates.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/scripts/cleanup_duplicate_ders.py`
  - Fonksiyonlar:
    - `main()` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/scripts/cleanup_pool_non_elective.py`
  - Fonksiyonlar:
    - `_build_non_elective_query(cur: sqlite3.Cursor) -> tuple[str, str]` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `run_cleanup(db_path: str, apply_changes: bool=False) -> dict` (satır 42): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `main() -> int` (satır 134): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/scripts/export_missing_criteria_workbook.py`
  - Fonksiyonlar:
    - `main()` (satır 25): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/scripts/fill_missing_course_codes.py`
  - Fonksiyonlar:
    - `main() -> int` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/scripts/fill_pool_manual.py`
  - Fonksiyonlar:
    - `havuzu_doldur()` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/scripts/fix_havuz_table.py`
  - Fonksiyonlar:
    - `recreate_havuz_table()` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/scripts/havuz_2022_doldur.py`
  - Fonksiyonlar:
    - `havuz_2022_doldur(fakulte_id=2)` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/scripts/havuz_kumulatif_doldur.py`
  - Fonksiyonlar:
    - `get_db_path()` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_havuz_columns(cur)` (satır 27): Havuz tablosundaki kolonları döner.
    - `get_mufredat_ders_ids_for_year(cur, yil, fakulte_id=None)` (satır 33): Belirtilen yılda müfredatta olan ders_id listesini döner.
    - `get_mevcut_yillar(cur, fakulte_id=None)` (satır 52): Havuz veya müfredattan sistemdeki tüm yılları döner.
    - `kumulatif_tum_yillar_doldur(db_path=None, fakulte_id=2, baslangic_yili=None, bitis_yili=None)` (satır 66): Havuz tablosunu tüm yıllar için döngüsel doldurur.
    - `get_mufredat_listeleri()` (satır 194): Örnek müfredat kataloğu (isteğe bağlı kullanım).

### `app/scripts/import_real_data.py`
  - Fonksiyonlar:
    - `get_paths()` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `run_import()` (satır 51): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/scripts/init_script.py`
  - Sınıflar:
    - `DecisionEngine` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, all_unique_course_ids)` (satır 12): Başlangıçta sistemdeki tüm tekil derslerin listesi verilir.
      - `log(self, msg)` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `simulate_history(self, history_map)` (satır 30): Geçmiş yılları sırayla işleyerek bugünkü durumu oluşturur.
      - `_apply_transition_rules(self, year_from, year_to, current_ids, next_ids)` (satır 61): İki yıl arasındaki geçiş kurallarını uygular.

### `app/scripts/integrate_dataset_bundle.py`
  - Fonksiyonlar:
    - `normalize_text(value: Any) -> str` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `clean_text(value: Any) -> str | None` (satır 48): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `clean_int(value: Any, default: int | None=None) -> int | None` (satır 57): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `clean_float(value: Any, default: float | None=None) -> float | None` (satır 66): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `normalize_term(value: Any) -> str` (satır 75): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `is_elective(value: Any) -> bool` (satır 82): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `parse_teaching_hours(value: Any) -> int | None` (satır 86): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `table_columns(cur: sqlite3.Cursor, table: str) -> set[str]` (satır 96): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `fetch_name_map(cur: sqlite3.Cursor, table: str, id_column: str, extra_where: str='', params: tuple[Any, ...]=()) -> dict[str, int]` (satır 100): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_or_create_faculty(cur: sqlite3.Cursor, name: str, stats: dict[str, int]) -> int` (satır 105): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_or_create_department(cur: sqlite3.Cursor, faculty_id: int, name: str, stats: dict[str, int]) -> int` (satır 115): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `find_course_id(cur: sqlite3.Cursor, code: str | None=None, name: str | None=None, department_id: int | None=None) -> int | None` (satır 125): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `upsert_course(cur: sqlite3.Cursor, *, faculty_id: int, department_id: int, code: str | None, name: str, credit: int | None, ects: int | None, course_type: str | None, content: str | None, stats: dict[str, int]) -> int` (satır 155): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `load_master_courses(cur: sqlite3.Cursor, source_dir: Path, stats: dict[str, int]) -> dict[str, int]` (satır 231): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `resolve_scope_and_course(cur: sqlite3.Cursor, row: pd.Series, stats: dict[str, int]) -> tuple[int, int, int] | None` (satır 263): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `replace_curriculum_scope(cur: sqlite3.Cursor, faculty_id: int, department_id: int, year: int, term: str, course_ids: list[int]) -> tuple[int, int]` (satır 291): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `upsert_pool_row(cur: sqlite3.Cursor, *, course_id: int, faculty_id: int, department_id: int, year: int, term: str, course_name: str | None, stats: dict[str, int]) -> None` (satır 336): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `load_curriculum(cur: sqlite3.Cursor, source_dir: Path, stats: dict[str, int]) -> None` (satır 384): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `upsert_by_key(cur: sqlite3.Cursor, table: str, key_where: str, key_params: tuple[Any, ...], insert_sql: str, insert_params: tuple[Any, ...], update_sql: str, update_params: tuple[Any, ...]) -> bool` (satır 431): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `load_criteria(cur: sqlite3.Cursor, source_dir: Path, stats: dict[str, int]) -> None` (satır 449): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_or_create_survey_form(cur: sqlite3.Cursor, faculty_id: int, year: int) -> int` (satır 579): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `load_survey_summary(cur: sqlite3.Cursor, source_dir: Path, stats: dict[str, int]) -> None` (satır 601): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `copy_benchmark_csvs(source_dir: Path, stats: dict[str, int]) -> None` (satır 667): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `make_backup(db_path: Path) -> Path` (satır 679): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `count_table(cur: sqlite3.Cursor, table: str) -> int` (satır 688): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `integrate(source_dir: Path, db_path: Path, *, backup: bool=True) -> dict[str, Any]` (satır 692): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `main() -> int` (satır 739): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/scripts/merge_duplicate_ders.py`
  - Fonksiyonlar:
    - `table_exists(cur, name)` (satır 42): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `column_exists(cur, table, col)` (satır 47): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_dup_groups(cur, by_name_only=False)` (satır 52): Tekrarlayan ders gruplarını döner. (ad, fakulte_id) veya sadece (ad) ile grupla.
    - `merge_duplicates(conn, dup_groups, dry_run=False, verbose=False)` (satır 68): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `main()` (satır 144): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/scripts/migrate_anket_columns.py`
  - Fonksiyonlar:
    - `main()` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/scripts/migrate_sqlite_to_postgres.py`
  - Fonksiyonlar:
    - `_quote_ident(name: str) -> str` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_sqlite_table_names(conn: sqlite3.Connection) -> set[str]` (satır 39): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_sqlite_column_names(conn: sqlite3.Connection, table_name: str) -> set[str]` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_sqlite_column_info(conn: sqlite3.Connection, table_name: str) -> list[sqlite3.Row]` (satır 49): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_sqlite_type_to_sa(type_name: str) -> sa.types.TypeEngine` (satır 53): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_legacy_table_from_sqlite(conn: sqlite3.Connection, table_name: str, metadata: sa.MetaData) -> sa.Table` (satır 66): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_target_count(conn: sa.Connection, table_name: str) -> int` (satır 84): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_source_count(conn: sqlite3.Connection, table_name: str) -> int` (satır 89): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_iter_sqlite_rows(conn: sqlite3.Connection, table_name: str, columns: list[str], *, batch_size: int=BATCH_SIZE)` (satır 94): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_coerce_value(column: sa.Column, value: Any) -> Any` (satır 110): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_coerce_batch(table: sa.Table, rows: list[dict[str, Any]]) -> list[dict[str, Any]]` (satır 140): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_reset_postgres_sequence(conn: sa.Connection, table: sa.Table) -> None` (satır 148): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `migrate(sqlite_path: str | Path, postgres_url: str, *, truncate_target: bool=False, append: bool=False, dry_run: bool=False) -> dict[str, Any]` (satır 178): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_parse_args() -> argparse.Namespace` (satır 265): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `main() -> int` (satır 277): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/scripts/reset.py`
  - Fonksiyonlar:
    - `reset_database_stats(db_path='proje_veritabani.db')` (satır 10): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/scripts/run_all_algorithms_and_save.py`
  - Fonksiyonlar:
    - `main() -> None` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/scripts/run_benchmark_example.py`
  - Fonksiyonlar:
    - `main() -> None` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/scripts/seed_criteria_from_workbook.py`
  - Fonksiyonlar:
    - `_norm(s)` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_col(df, *names)` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `main()` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/scripts/smart_data_generator.py`
  - Fonksiyonlar:
    - `baglanti_kur()` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `tablolari_yenile()` (satır 17): Performans, Popülerlik ve Skor tablolarını sıfırlar ve 4 kriterli yeni şemayı uygular.
    - `veri_uret_ve_hesapla()` (satır 80): Sadece Mühendislik Müfredatındaki dersler için veri üretir.

### `app/scripts/update_db_for_pool.py`
  - Fonksiyonlar:
    - `find_database_and_upgrade()` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

## app/services

### `app/services/ahp_calculation_service.py`
  - Fonksiyonlar:
    - `validate_pairwise_matrix(matrix: list[list[float]], criteria_keys: list[str] | None=None) -> ValidationResult` (satır 63): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_weights_from_pairwise_matrix(criteria_keys: list[str], matrix: list[list[float]], method: str='geometric_mean') -> AHPResult` (satır 101): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_consistency(criteria_keys: list[str], matrix: list[list[float]], weights: dict[str, float]) -> ConsistencyResult` (satır 131): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `normalize_weights(weights: dict[str, float], criteria_keys: list[str] | None=None) -> dict[str, float]` (satır 147): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `build_pairwise_matrix_from_weights(weights: dict[str, float], criteria_keys: list[str] | None=None) -> list[list[float]]` (satır 162): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_random_index(n: int) -> float` (satır 176): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_geometric_mean_weights(matrix: list[list[float]], criteria_keys: list[str]) -> dict[str, float]` (satır 180): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_eigenvector_weights(matrix: list[list[float]], criteria_keys: list[str]) -> tuple[dict[str, float], float]` (satır 191): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_lambda_max(matrix: list[list[float]], weights: list[float]) -> float` (satır 207): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_issue(code: str, message: str, suggestion: str) -> dict[str, str]` (satır 216): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `ValidationResult` (satır 26): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `to_dict(self) -> dict[str, Any]` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ConsistencyResult` (satır 37): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `to_dict(self) -> dict[str, Any]` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AHPResult` (satır 49): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `to_dict(self) -> dict[str, Any]` (satır 59): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/ahp_impact_explanation_service.py`
  - Fonksiyonlar:
    - `explain_weight_profile(conn: sqlite3.Connection, profile_id: int) -> dict[str, Any]` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_ahp_human_readable_summary(profile: dict[str, Any]) -> str` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_weight_impact_table(score_breakdown: dict[str, Any]) -> list[dict[str, Any]]` (satır 52): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `explain_course_weight_contribution(conn: sqlite3.Connection, course_id: int, decision_run_id: int) -> dict[str, Any]` (satır 69): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_load(value: Any, default: Any) -> Any` (satır 124): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_safe_float(value: Any) -> float` (satır 133): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/ahp_profile_policy_service.py`
  - Fonksiyonlar:
    - `seed_default_policy(conn: sqlite3.Connection) -> dict[str, Any]` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `resolve_policy(conn: sqlite3.Connection, *, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> dict[str, Any]` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `can_activate_profile(profile: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]` (satır 81): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `can_use_profile_for_decision(profile: dict[str, Any], policy: dict[str, Any], *, draft_run: bool=False) -> dict[str, Any]` (satır 94): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `should_mark_decisions_stale(policy: dict[str, Any]) -> bool` (satır 106): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_dict(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]` (satır 110): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_now() -> str` (satır 146): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/ahp_profile_service.py`
  - Fonksiyonlar:
    - `seed_default_profile(conn: sqlite3.Connection) -> dict[str, Any]` (satır 37): Global varsayılan AHP profilini idempotent oluşturur.
    - `create_profile(conn: sqlite3.Connection, *, profile_name: str | None=None, name: str | None=None, profile_code: str | None=None, scope_type: str='global', faculty_id: int | None=None, department_id: int | None=None, year: int | None=None, semester: str | None=None, criteria_keys: list[str] | None=None, pairwise_matrix: list[list[float]] | None=None, weights: dict[str, float] | None=None, source: str='manual', status: str='draft', created_by: str | None=None, notes: str | None=None, parent_profile_id: int | None=None, activate: bool=False, bypass_activation_policy: bool=False) -> dict[str, Any]` (satır 103): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_ahp_profile(conn: sqlite3.Connection, name: str, scope_type: str='global', faculty_id: int | None=None, department_id: int | None=None, year: int | None=None, criteria_keys: list[str] | None=None, pairwise_matrix: list[list[float]] | None=None, weights: dict[str, float] | None=None, source: str='manual', created_by: str | None=None, notes: str | None=None, activate: bool=True) -> dict[str, Any]` (satır 197): Eski Decision Center/API çağrıları için geriye dönük uyumlu wrapper.
    - `update_profile(conn: sqlite3.Connection, profile_id: int, **updates) -> dict[str, Any]` (satır 232): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `validate_profile(conn: sqlite3.Connection, profile_id: int) -> dict[str, Any]` (satır 305): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `submit_for_approval(conn: sqlite3.Connection, profile_id: int, actor: str | None=None) -> dict[str, Any]` (satır 341): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `approve_profile(conn: sqlite3.Connection, profile_id: int, approved_by: str | None=None) -> dict[str, Any]` (satır 349): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `reject_profile(conn: sqlite3.Connection, profile_id: int, reason: str, rejected_by: str | None=None) -> dict[str, Any]` (satır 367): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `activate_profile(conn: sqlite3.Connection, profile_id: int, actor: str | None=None, *, bypass_policy: bool=False) -> dict[str, Any]` (satır 393): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `archive_profile(conn: sqlite3.Connection, profile_id: int, actor: str | None=None) -> dict[str, Any]` (satır 473): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `clone_profile(conn: sqlite3.Connection, profile_id: int, new_scope: dict[str, Any] | None=None, new_year: int | None=None, actor: str | None=None) -> dict[str, Any]` (satır 486): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `resolve_active_profile(conn: sqlite3.Connection, *, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None, draft_run: bool=False) -> dict[str, Any]` (satır 516): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `resolve_ahp_profile(conn: sqlite3.Connection, faculty_id: int | None=None, department_id: int | None=None, year: int | None=None, semester: str | None=None) -> dict[str, Any]` (satır 551): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_profile_for_decision_run(conn: sqlite3.Connection, decision_run_id: int) -> dict[str, Any] | None` (satır 567): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_profiles(conn: sqlite3.Connection, filters: dict[str, Any] | None=None) -> list[dict[str, Any]]` (satır 585): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_profile(conn: sqlite3.Connection, profile_id: int) -> dict[str, Any] | None` (satır 606): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_stale_decisions(conn: sqlite3.Connection, unresolved_only: bool=True) -> list[dict[str, Any]]` (satır 615): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `resolve_stale_decision(conn: sqlite3.Connection, stale_id: int, resolved_by: str | None=None) -> dict[str, Any]` (satır 629): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `mark_decisions_stale_for_profile_change(conn: sqlite3.Connection, *, old_profile_id: int, new_profile_id: int, actor: str | None=None, commit: bool=True) -> int` (satır 647): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_set_status(conn: sqlite3.Connection, profile_id: int, new_status: str, action: str, actor: str | None, message: str | None) -> None` (satır 697): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_active_profile_rows(conn: sqlite3.Connection, scope_type: str, faculty_id: int | None, department_id: int | None, year: int | None, semester: str | None) -> list[sqlite3.Row]` (satır 716): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_next_profile_version(conn: sqlite3.Connection, scope_type: str, faculty_id: int | None, department_id: int | None, year: int | None, semester: str | None) -> int` (satır 744): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_profile(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]` (satır 767): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_dict(row: sqlite3.Row | tuple[Any, ...] | None) -> dict[str, Any]` (satır 792): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json(value: Any) -> str` (satır 800): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_load(value: Any, default: Any) -> Any` (satır 804): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_bool(value: Any) -> bool` (satır 815): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_optional_float(value: Any) -> float | None` (satır 824): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_log_profile_action(cur: sqlite3.Cursor, profile_id: int, action: str, old_status: str | None, new_status: str | None, actor: str | None, message: str | None) -> None` (satır 833): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_now() -> str` (satır 853): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/ahp_reporting_service.py`
  - Fonksiyonlar:
    - `get_ahp_profile_report(conn: sqlite3.Connection, profile_id: int) -> dict[str, Any]` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_active_ahp_profile_summary(conn: sqlite3.Connection, *, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> dict[str, Any]` (satır 52): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_decision_run_ahp_summary(conn: sqlite3.Connection, run_id: int) -> dict[str, Any]` (satır 70): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `compare_ahp_profiles(conn: sqlite3.Connection, profile_a_id: int, profile_b_id: int) -> dict[str, Any]` (satır 89): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_ahp_profile_matrix(conn: sqlite3.Connection, profile_id: int, format: str='csv') -> str` (satır 111): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_ahp_sensitivity_report(conn: sqlite3.Connection, run_id: int, format: str='csv') -> str` (satır 125): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_dict(row: sqlite3.Row) -> dict[str, Any]` (satır 146): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/ahp_sensitivity_service.py`
  - Fonksiyonlar:
    - `perturb_weights(weights: dict[str, float], criterion_key: str, delta: float) -> dict[str, float]` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `run_weight_sensitivity_analysis(conn: sqlite3.Connection, decision_run_id: int, variation_percent: float=0.05) -> dict[str, Any]` (satır 23): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_sensitivity_result(conn: sqlite3.Connection, result_id: int) -> dict[str, Any]` (satır 144): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_latest_sensitivity_for_run(conn: sqlite3.Connection, decision_run_id: int) -> dict[str, Any] | None` (satır 164): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_weighted_score(raw_values: dict[str, Any], weights: dict[str, float]) -> float` (satır 176): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_decision_bucket(score: float) -> str` (satır 186): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json(value: Any) -> str` (satır 196): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_load(value: Any, default: Any) -> Any` (satır 200): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_dict(row: sqlite3.Row) -> dict[str, Any]` (satır 209): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_safe_float(value: Any) -> float` (satır 213): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_now() -> str` (satır 220): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/ai_engine.py`
  - Fonksiyonlar:
    - `_sf(val, default=0.0)` (satır 29): Guvenli float donusumu. None/NaN/Inf icin varsayilan deger doner.
  - Sınıflar:
    - `HavuzAIEngine` (satır 42): Havuz + performans + populerlik verileri uzerinde ML modelleri.
      - `__init__(self, db_session: Session)` (satır 51): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_training_data(self, fakulte_id=None, yil=None, curriculum_only: bool=False)` (satır 59): performans + populerlik + havuz + ders_kriterleri tablolarindan
      - `_feature_cols(self)` (satır 140): ML modelleri icin kullanilan ozellik (feature) sutun listesini doner.
      - `_resolve_training_frames(self, fakulte_id=None, yil=None, curriculum_only: bool=False)` (satır 144): Tahmin gosterimi ve egitim kapsamlarini ayirir.
      - `_train_from_dataframe(self, df: pd.DataFrame) -> bool` (satır 183): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_last_training_meta(self) -> dict` (satır 213): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `train(self, fakulte_id=None, yil=None, curriculum_only: bool=False)` (satır 216): LR, RF ve DT modellerini havuz verisi uzerinde egitir. Basarili ise True, veri yetersizse False doner.
      - `predict_basari(self, features: dict) -> float` (satır 235): LR: gelecek yil basari orani tahmini (0-100).
      - `predict_kesinlesme(self, features: dict) -> float` (satır 242): RF: kesinlesme puani tahmini (0-100).
      - `predict_statu(self, features: dict) -> int` (satır 249): DT: statu tahmini (1/0/-1/-2).
      - `_dict_to_X(self, features: dict) -> np.ndarray` (satır 256): Feature dictionary'yi numpy array'e cevirir (sklearn uyumlu).
      - `predict_all_courses(self, fakulte_id=None, yil=None, curriculum_only: bool=False)` (satır 261): Tum dersler icin toplu tahmin yapar; DataFrame doner.
      - `run_kfold(self, algorithm_type='rf', k=5, fakulte_id=None, yil=None, curriculum_only: bool=False)` (satır 304): K-Fold cross-validation sonucu doner (string).
    - `AIEngine` (satır 422): calc_tab.py tarafindan kullanilan ust duzey arayuz. HavuzAIEngine'i sarar.
      - `__init__(self, db_session: Session)` (satır 427): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run_kfold_test(self, algorithm_type='rf', k=5)` (satır 431): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/algorithm_data_guard_service.py`
  - Fonksiyonlar:
    - `check_data_requirements(conn: sqlite3.Connection, algorithm_key: str, X: Any=None, y: Iterable[Any] | None=None, task_type: str | None=None, *, sample_count: int | None=None, feature_count: int | None=None, n_clusters: int | None=None) -> DataGuardResult` (satır 43): Registry kurallarına göre algoritmanın veriyle çalıştırılabilirliğini değerlendir.
    - `check_minimum_sample_count(sample_count: int, required: int) -> bool` (satır 148): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `check_min_samples_per_class(y: Iterable[Any], required: int) -> dict[str, int]` (satır 152): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_class_distribution(y: Iterable[Any]) -> dict[str, int]` (satır 156): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `check_feature_count(X: Any, min_features: int=1) -> bool` (satır 164): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `check_class_balance(y: Iterable[Any], imbalance_ratio: float=0.2) -> str | None` (satır 168): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `check_scaling_required(algorithm_key: str) -> bool` (satır 181): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `check_target_required(task_type: str) -> bool` (satır 185): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `check_missing_values(X: Any) -> int` (satır 189): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `check_algorithm_specific_requirements(algorithm_key: str, *, sample_count: int, n_clusters: int | None=None) -> list[str]` (satır 204): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_allowed_mode(role: str, sample_count: int, required: int, blocking: list[str], algorithm_key: str) -> str` (satır 216): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_shape(X: Any) -> tuple[int, int]` (satır 234): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_as_rows(X: Any) -> list[Any]` (satır 253): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `DataGuardResult` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `to_dict(self) -> dict[str, Any]` (satır 37): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/algorithm_governance_report_service.py`
  - Fonksiyonlar:
    - `generate_algorithm_role_report(conn: sqlite3.Connection) -> dict[str, Any]` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_benchmark_statistical_report(conn: sqlite3.Connection, benchmark_run_id: int) -> dict[str, Any]` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_algorithm_data_guard_report(conn: sqlite3.Connection, benchmark_run_id: int) -> dict[str, Any]` (satır 39): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_clustering_report(conn: sqlite3.Connection, benchmark_run_id: int) -> dict[str, Any]` (satır 53): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_benchmark_report(conn: sqlite3.Connection, benchmark_run_id: int, format: str='json') -> str` (satır 62): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_algorithm_governance_matrix(conn: sqlite3.Connection, format: str='json') -> str` (satır 81): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/algorithm_governance_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 49): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json(value: Any) -> str` (satır 53): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `seed_default_algorithm_registry(conn: sqlite3.Connection) -> list[dict]` (satır 114): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_algorithm_governance(conn: sqlite3.Connection, usage_role: str | None=None) -> list[dict]` (satır 178): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_algorithm_governance(conn: sqlite3.Connection, algorithm_key: str) -> dict` (satır 194): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_algorithms_by_role(conn: sqlite3.Connection, usage_role: str) -> list[dict]` (satır 207): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `can_algorithm_affect_final_decision(conn: sqlite3.Connection, algorithm_key: str) -> bool` (satır 211): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `validate_algorithm_usage(conn: sqlite3.Connection, algorithm_key: str, requested_usage_role: str) -> dict` (satır 215): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `update_algorithm_role(conn: sqlite3.Connection, algorithm_key: str, *, usage_role: str | None=None, can_affect_final_decision: bool | None=None, minimum_sample_count: int | None=None, user_facing_warning: str | None=None) -> dict` (satır 234): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_user_facing_algorithm_label(conn: sqlite3.Connection, algorithm_key: str) -> str` (satır 266): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_allowed_algorithms_for_task(conn: sqlite3.Connection, task_key: str) -> list[dict]` (satır 277): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `validate_algorithm_for_task(conn: sqlite3.Connection, algorithm_key: str, task_key: str) -> dict` (satır 304): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_task_description(task_key: str) -> str` (satır 318): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_task_mappings(conn: sqlite3.Connection) -> list[dict]` (satır 331): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `normalize_algorithm_key(value: str) -> str` (satır 338): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_governance_dict(row: sqlite3.Row | tuple, keys: list[str]) -> dict` (satır 362): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `AlgorithmGovernance` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict` (satır 45): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/algorithm_manager.py`
  - Sınıflar:
    - `AlgorithmRecommendation` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict[str, Any]` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `AlgorithmManager` (satır 30): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, result_store: ResultStore | None=None) -> None` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `recommend(self, *, problem_type: str, data_size: int, explainability_priority: bool=False, use_history: bool=True) -> AlgorithmRecommendation` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_rule_based(self, *, problem_type: str, data_size: int, explainability_priority: bool) -> AlgorithmRecommendation` (satır 49): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_history_based(self, *, problem_type: str) -> AlgorithmRecommendation | None` (satır 117): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_objective_score(self, problem_type: str, metric_groups: dict[str, dict[str, float]]) -> float` (satır 147): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/architecture_audit_service.py`
  - Fonksiyonlar:
    - `_iter_py_files(relative_dir: str) -> Iterable[Path]` (satır 54): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_relative(path: Path) -> str` (satır 61): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_scan_patterns(relative_dir: str, patterns: tuple[str, ...], *, layer: str, allowlist: dict[str, str] | None=None, severity: str='warning') -> list[ArchitectureFinding]` (satır 65): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `scan_ui_direct_db_access() -> list[dict[str, Any]]` (satır 102): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `scan_api_raw_sql() -> list[dict[str, Any]]` (satır 107): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `scan_service_sqlite_usage() -> list[dict[str, Any]]` (satır 112): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `scan_schema_mutation_usage() -> list[dict[str, Any]]` (satır 120): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_architecture_audit_report() -> dict[str, Any]` (satır 138): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_architecture_audit_report(format: str='json') -> str` (satır 160): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `ArchitectureFinding` (satır 40): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `to_dict(self) -> dict[str, Any]` (satır 50): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/auth_service.py`
  - Fonksiyonlar:
    - `get_auth_service(db: Session=Depends(get_session)) -> AuthService` (satır 115): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_current_user(request: Request, auth_service: AuthService=Depends(get_auth_service)) -> UserContext` (satır 119): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `AuthService` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, db: Session, config: AppConfig)` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `create_api_client(self, data: ApiClientCreate) -> ApiClientCreatedResponse` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `verify_request(self, request: Request) -> Optional[ApiClient]` (satır 53): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_current_user_context(self, request: Request) -> UserContext` (satır 81): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/backup_restore_service.py`
  - Sınıflar:
    - `BackupRestoreService` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, db: Session, config: AppConfig)` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `create_sqlite_backup(self, snapshot_type: str, scope_type: str='global', faculty_id: int=None, department_id: int=None, year: int=None, related_import_job_id: str=None, related_decision_run_id: int=None, created_by: str='system') -> DataSnapshot` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `create_pre_import_backup(self, import_job_id: str, created_by: str) -> DataSnapshot` (satır 66): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `restore_from_snapshot(self, snapshot_id: str) -> bool` (satır 71): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/baseline_benchmark_service.py`
  - Fonksiyonlar:
    - `build_dummy_classifier(strategy: str='most_frequent', random_state: int=42)` (satır 59): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `build_dummy_regressor(strategy: str='mean')` (satır 68): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `compare_with_baseline(model_metrics: dict[str, Any], baseline_metrics: dict[str, Any], primary_metric: str) -> dict[str, Any]` (satır 77): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_num(value: Any) -> float | None` (satır 101): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `RuleBasedBaseline` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `predict(self, scores: Iterable[float]) -> list[int]` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MajorityClassPredictor` (satır 30): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self) -> None` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `fit(self, _X: Any, y: Iterable[Any])` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `predict(self, X: Sequence[Any]) -> list[Any]` (satır 39): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `RandomPredictor` (satır 43): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, random_state: int=42) -> None` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `fit(self, _X: Any, y: Iterable[Any])` (satır 48): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `predict(self, X: Sequence[Any]) -> list[Any]` (satır 52): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/benchmark_metric_router.py`
  - Fonksiyonlar:
    - `get_metrics_for_task(task_type: str) -> list[str]` (satır 10): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_metrics(task_type: str, *, y_true: Sequence[Any] | None=None, y_pred: Sequence[Any] | None=None, y_score: Sequence[Any] | None=None, rankings: Sequence[Sequence[Any]] | None=None, relevant_items: Sequence[set[Any] | list[Any]] | None=None, clusters: Sequence[int] | None=None, X: Any=None, allocations: Sequence[dict[str, Any]] | None=None, k: int=10) -> dict[str, Any]` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `validate_metric_inputs(task_type: str, data: dict[str, Any]) -> dict[str, Any]` (satır 75): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `summarize_metrics(metrics: dict[str, Any]) -> str` (satır 91): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_classification_metrics(y_true: Sequence[Any] | None, y_pred: Sequence[Any] | None, y_score: Sequence[Any] | None, warnings: list[str]) -> dict[str, Any]` (satır 105): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_regression_metrics(y_true: Sequence[Any] | None, y_pred: Sequence[Any] | None, warnings: list[str]) -> dict[str, Any]` (satır 158): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_ranking_metrics(rankings: Sequence[Sequence[Any]], relevant_items: Sequence[set[Any] | list[Any]], *, k: int) -> dict[str, Any]` (satır 192): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_allocation_metrics(allocations: Sequence[dict[str, Any]]) -> dict[str, Any]` (satır 227): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_basic_classification_metrics(y_true: list[Any], y_pred: list[Any]) -> dict[str, Any]` (satır 251): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_binary_scores(y_score: Sequence[Any]) -> list[float]` (satır 256): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_std(values: Sequence[float]) -> float` (satır 266): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/calculation.py`
  - Fonksiyonlar:
    - `ders_cakisma_kontrolu(ders_listesi, conn=None)` (satır 290): AynÄ± gÃ¼n ve saatte Ã§akÄ±ÅŸan dersleri tespit eder.
    - `yukle_gercek_2022_mufredati(conn, excel_path)` (satır 337): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `run_automatic_scoring(db_path='data/adil_secmeli.db')` (satır 470): Acilis veya manuel tetikleme: base_year sonrasi mufredati sifirlar,
    - `_normalize_mufredat_faculty_ids(cur)` (satır 485): Legacy veri setlerinde mufredat.fakulte_id yanlis yazilmis olabiliyor.
    - `_safe_float2(value, default=0.0)` (satır 518): None, NaN, Inf ve string degerleri guvenli float'a cevirir. Gecersiz degerlerde default doner.
    - `_resolve_elective_col(cur)` (satır 533): Legacy helper: ders tablosunda secmeli/zorunlu tip sutununun ilk bulunan adini dondurur.
    - `_normalize_term_key(value)` (satır 541): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_table_has_column(cur, table_name, column_name)` (satır 545): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_table_exists(cur, table_name)` (satır 550): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_havuz_has_donem_col(cur)` (satır 558): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_havuz_unique_includes_donem(cur)` (satır 562): Return True only when havuz uniqueness is term-scoped.
    - `_fetch_other_term_curriculum_map(cur, fakulte_id, akademik_yil, current_term)` (satır 585): Next-year generation sirasinda, diger donemde zaten secili dersleri bolum bazli getirir.
    - `_has_generation_criteria(cur, ders_id, yil, donem)` (satır 611): Yeni yil mufredat uretimi icin zorunlu kriter kontrolu.
    - `_has_full_criteria(cur, ders_id, yil, donem)` (satır 646): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_read_course_metrics(cur, ders_id, yil, donem, motor)` (satır 749): Tek ders icin AHP/TOPSIS girdilerini derler: basari, trend, populerlik, anket, ortalama_not.
    - `evaluate_drop_reasons(score_100, average_grade, score_threshold=DROP_SCORE_THRESHOLD, average_grade_threshold=DROP_AVERAGE_GRADE_THRESHOLD)` (satır 933): Dersin mufredattan dusme nedenlerini degerlendirip neden listesi doner.
    - `should_drop_course(score_100, average_grade, score_threshold=DROP_SCORE_THRESHOLD, average_grade_threshold=DROP_AVERAGE_GRADE_THRESHOLD)` (satır 950): Dersin dusup dusmeyecegini ve nedenlerini doner. (drop_flag, reasons) tuple.
    - `_pool_course_score_anket_only(anket)` (satır 968): Mufredat disi dersler icin kesinlesme puani. TOPSIS'e girmez.
    - `get_faculty_year_topsis_results(cur, fakulte_id, akademik_yil, donem='G', include_course_ids=None)` (satır 987): Bir fakulte+yil icin tum adaylarin TOPSIS skorlarini hesaplar. Mufredattaki dersler TOPSIS pipeline'ina girer;
    - `_get_curriculum_course_ids(cur, fakulte_id, akademik_yil, donem='G')` (satır 1220): Fakulte + yil (+ donem ilk harf) icin mufredatta bulunan ders_id kumesini dondurur.
    - `persist_faculty_year_topsis_scores(cur, fakulte_id, akademik_yil, skor_map, ders_meta, donem='G')` (satır 1299): Hesaplanan TOPSIS skorlarini havuz tablosuna yazar. Mevcut kayit varsa UPDATE, yoksa INSERT yapar.
    - `ensure_pool_visibility_for_curriculum(cur, fakulte_id, akademik_yil, donem='G')` (satır 1386): Havuz ekraninda gorunurluk ve kural tutarliligi icin:
    - `generate_next_year_curricula(db_path='data/adil_secmeli.db', fakulte_id=None, akademik_yil=None, donem='G', drop_score_threshold=DROP_SCORE_THRESHOLD, drop_average_grade_threshold=DROP_AVERAGE_GRADE_THRESHOLD)` (satır 1489): Faculty + year + term icin bolum bazli sonraki yil mufredati olusturur.
    - `run_all_algorithms_for_year(yil: int, db_path: str='data/adil_secmeli.db', donem: str='G', fakulte_id: int | None=None) -> dict` (satır 2357): Algoritma kontrol merkezi icin yil bazli manuel calistirma.
    - `auto_generate_next_year_curricula(db_path='data/adil_secmeli.db', donem='G')` (satır 2560): Tum fakulteler icin otomatik sonraki yil mufredat uretimini tetikler. Her fakultenin en son mufredatli yilini bulur ve bir sonraki yili uretir.
    - `reset_future_curricula(db_path='data/adil_secmeli.db', base_year=2022)` (satır 2684): Sadece base_year ve onceki yillari birakir.
    - `_ensure_curriculum_log_table(cur)` (satır 2743): Mufredat uretim log tablosu yoksa olusturur.
    - `_write_curriculum_generation_log(db_path, overall)` (satır 2758): Pipeline sonucu ozetini kalici log tablosuna yazar.
    - `generate_curricula_until_stable(db_path='data/adil_secmeli.db', donem='G', max_rounds=8)` (satır 2803): Otomatik uretimi birden fazla tur calistirir.
    - `rebuild_school_curricula(db_path='data/adil_secmeli.db', base_year=2022, donem='G', max_rounds=8)` (satır 2883): 1) base_year sonrasi mufredatlari sifirlar
    - `rebuild_school_curricula_dual_semester(db_path='data/adil_secmeli.db', base_year=2022, max_rounds=8, block_size=4)` (satır 2904): Production-grade dual semester wrapper.
  - Sınıflar:
    - `KararMotoru` (satır 78): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, db=None)` (satır 79): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `ahp_matrisi(self)` (satır 82): Saaty kurallarina gore kurulan 4x4 ikili karsilastirma matrisini doner.
      - `ahp_calistir(self, profile=None)` (satır 86): AHP agirliklarini ozvektor yontemi ile hesaplar.
      - `ahp_tutarlilik_kontrolu(self, matris=None, agirliklar=None)` (satır 114): TutarlÄ±lÄ±k OranÄ± (CR) hesaplar. CR < 0.10 kabul edilebilir.
      - `gecmis_trend_hesapla(self, gecmis_list)` (satır 136): Gecmis yillarin agirlikli ortalamasini hesaplar.
      - `topsis_calistir(self, df, agirliklar, criteria_keys=None, benefit_map=None)` (satır 212): TOPSIS: Veri akÄ±ÅŸÄ± AHP'den gelen aÄŸÄ±rlÄ±klarla.

### `app/services/clustering_evaluation_service.py`
  - Fonksiyonlar:
    - `evaluate_clustering(X: Any, labels: Iterable[Any], algorithm_key: str, *, dbscan_params: dict[str, Any] | None=None) -> ClusteringEvaluation` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_cluster_size_distribution(labels: Iterable[Any]) -> dict[str, int]` (satır 79): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_noise_ratio(labels: Iterable[Any]) -> float` (satır 87): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_cluster_stability(*_args, **_kwargs) -> dict[str, Any]` (satır 94): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `recommend_dbscan_eps(X: Any, min_samples: int=5) -> dict[str, Any]` (satır 98): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_k_distance_data(X: Any, min_samples: int=5) -> dict[str, Any]` (satır 107): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `dbscan_sensitivity_analysis(X: Any, eps_values: Iterable[float], min_samples_values: Iterable[int]) -> list[dict[str, Any]]` (satır 124): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `ClusteringEvaluation` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `metrics(self) -> dict[str, Any]` (satır 25): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `to_dict(self) -> dict[str, Any]` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/course_analyzer.py`
  - Fonksiyonlar:
    - `_safe_float(val, default: float=0.0) -> float` (satır 72): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_statu_label(statu: int) -> str` (satır 82): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_not_calculated_step(message: str) -> dict` (satır 91): Algoritma adimi calismadiginda UI'nin gosterebilecegi standart paket.
    - `_missing_criteria(reason: str) -> dict` (satır 100): Kriter bulunamadiginda analiz akisini kesmemek icin guvenli bos kriter paketi.
    - `_fetch_course_meta(cur: sqlite3.Cursor, course_id: int) -> dict` (satır 122): ders tablosundan ders_id, ad, tip, fakulte_id, bolum_id bilgilerini okur.
    - `_fetch_criteria(cur: sqlite3.Cursor, course_id: int, year: int) -> dict` (satır 156): ders_kriterleri -> performans -> populerlik sırasıyla okur.
    - `_fetch_prev_pool(cur: sqlite3.Cursor, course_id: int, year: int) -> dict` (satır 243): Bir önceki yılın havuz kaydını döner.
    - `_fetch_observed_state(cur: sqlite3.Cursor, course_id: int, year: int) -> dict` (satır 258): Secili yil icin eldeki gercek durumu okur.
    - `_resolve_course_faculty_id(cur: sqlite3.Cursor, course_meta: dict, course_id: int, year: int) -> Optional[int]` (satır 328): Dersin fakulte_id'sini cozumler: ders.fakulte_id > havuz > mufredat sirasiyla bakar.
    - `_fetch_gecmis_trend(cur: sqlite3.Cursor, course_id: int, base_year: int) -> list` (satır 380): Son 3 yılın başarı oranını döner (en yeni önce).
    - `_run_ahp(criteria: dict) -> dict` (satır 393): AHP ağırlıklarını ve CR'yi döner.
    - `_run_topsis_single(cur: sqlite3.Cursor, course_id: int, year: int, fakulte_id: Optional[int], donem: str='G') -> dict` (satır 419): Tek ders puanini, ilgili fakulte+yil evreninde toplu TOPSIS calistirarak
    - `_run_trend_lr(gecmis_list: list) -> dict` (satır 494): Trend/LR: yeterli veri varsa sklearn LinearRegression,
    - `_run_rf(criteria: dict, prev_pool: dict, db_path: str=None) -> dict` (satır 569): RF tahmini: yeterli havuz verisi varsa sklearn RandomForest,
    - `_run_rf_simple(criteria: dict, prev_pool: dict) -> dict` (satır 664): Hafif/kural tabanli RF yardimcisi.
    - `_run_dt(criteria: dict, prev_pool: dict) -> dict` (satır 698): DT tahmini: yeterli havuz verisi varsa sklearn DecisionTree,
    - `_build_dt_reason(criteria: dict, topsis: dict, in_mufredat: bool, next_statu: int, next_sayac: int, prev_pool: dict) -> str` (satır 767): Karar aciklamasini insan dilinde uretir.
    - `analyze_single_course(course_id: int, year: int, db_path: Optional[str]=None) -> dict` (satır 840): Tek ders analiz servisi (thread-safe).
  - Sınıflar:
    - `VeriEksikHatasi(Exception)` (satır 65): Seçilen dersin o yıl için yeterli kriter verisi yoksa fırlatılır.

### `app/services/course_code_service.py`
  - Fonksiyonlar:
    - `normalize_ascii_upper(value: str | None) -> str` (satır 45): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `build_name_initial(value: str | None, fallback: str='X') -> str` (satır 54): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `build_course_code(fakulte_adi: str | None, bolum_adi: str | None, ders_id: int) -> str` (satır 62): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_missing_course_code_rows(conn: sqlite3.Connection) -> list[MissingCourseCodeRow]` (satır 68): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `preview_missing_course_codes(db_path: str) -> dict[str, Any]` (satır 118): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `apply_missing_course_codes(db_path: str) -> dict[str, Any]` (satır 134): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `MissingCourseCodeRow` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict[str, Any]` (satır 41): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/course_matcher.py`
  - Fonksiyonlar:
    - `normalize_course_text(value: str | None) -> str` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `normalize_course_key(value: str | None) -> str` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_load_candidates(cur: sqlite3.Cursor, faculty_id: int, year: int, use_elective_filter: bool) -> list[CourseCandidate]` (satır 49): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `load_faculty_course_candidates(cur: sqlite3.Cursor, faculty_id: int, year: int) -> list[CourseCandidate]` (satır 122): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_select_candidate(matches: list[CourseCandidate]) -> tuple[CourseCandidate | None, str | None]` (satır 137): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `match_course_row(candidates: list[CourseCandidate], ders_kodu: str | None, ders_adi: str | None) -> CourseMatchResult` (satır 151): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `CourseCandidate` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CourseMatchResult` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/course_semester_availability_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_bool(value: Any) -> bool` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `normalize_semester(value: str | None) -> str` (satır 23): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `display_semester(value: str | None) -> str` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None=None) -> dict[str, Any] | None` (satır 36): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_one_dict(cur: sqlite3.Cursor) -> dict[str, Any] | None` (satır 49): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_all_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]` (satır 54): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `default_availability(course_id: int, year: int | None=None) -> dict[str, Any]` (satır 59): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_course_availability(conn: sqlite3.Connection, course_id: int, year: int | None=None, department_id: int | None=None, faculty_id: int | None=None) -> dict[str, Any]` (satır 75): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `validate_course_semester(conn: sqlite3.Connection, course_id: int, semester: str, year: int | None=None, department_id: int | None=None, faculty_id: int | None=None) -> dict[str, Any]` (satır 111): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `upsert_course_availability(conn: sqlite3.Connection, course_id: int, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None, allowed_fall: bool=True, allowed_spring: bool=True, preferred_semester: str='either', availability_type: str='always', unavailable_reason: str | None=None, effective_from_year: int | None=None, effective_to_year: int | None=None, notes: str | None=None) -> dict[str, Any]` (satır 142): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_availability_by_scope(conn: sqlite3.Connection, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None, course_id: int | None=None) -> list[dict[str, Any]]` (satır 189): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/course_service.py`
  - Sınıflar:
    - `CourseService` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, conn: sqlite3.Connection | None=None, db_path: str | None=None)` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_repo(self, conn: sqlite3.Connection) -> CourseRepository` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_courses(self, faculty_id: int | None=None, elective_only: bool=False) -> ServiceResult` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_faculties(self) -> ServiceResult` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_departments(self, faculty_id: int | None=None) -> ServiceResult` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_curriculum_years(self) -> ServiceResult` (satır 40): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/course_type.py`
  - Fonksiyonlar:
    - `_normalize_text(value: str | None) -> str` (satır 37): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `is_elective_value(value: str | None) -> bool` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `is_required_value(value: str | None) -> bool` (satır 49): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_existing_type_columns(cur, table_name: str='ders') -> list[str]` (satır 54): Tablodaki kolon isimlerini alır (PostgreSQL ve SQLite uyumlu).
    - `get_existing_type_columns_from_names(column_names: Iterable[str]) -> list[str]` (satır 73): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `build_course_type_expr(cur: sqlite3.Cursor, alias: str='d') -> str` (satır 78): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `build_course_type_expr_from_columns(column_names: Iterable[str], alias: str='d') -> str` (satır 83): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_build_normalized_sql_text_expr(expr: str) -> str` (satır 96): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `build_elective_predicate(cur: sqlite3.Cursor, alias: str='d') -> str` (satır 103): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `build_elective_predicate_from_columns(column_names: Iterable[str], alias: str='d') -> str` (satır 107): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `build_required_predicate(cur: sqlite3.Cursor, alias: str='d') -> str` (satır 121): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `build_required_predicate_from_columns(column_names: Iterable[str], alias: str='d') -> str` (satır 125): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `filter_elective_course_ids(cur, course_ids: Iterable[int]) -> set[int]` (satır 141): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/criteria_completion_policy_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_normalize_semester(value: str | None) -> str | None` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dumps(value: Any) -> str` (satır 37): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_loads(value: str | None, default: Any) -> Any` (satır 41): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None=None) -> dict[str, Any] | None` (satır 50): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_default_policy(conn: sqlite3.Connection) -> dict[str, Any]` (satır 72): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_policy(conn: sqlite3.Connection, policy_id: int) -> dict[str, Any] | None` (satır 111): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_completion_policy(conn: sqlite3.Connection, name: str, scope_type: str='global', faculty_id: int | None=None, department_id: int | None=None, year: int | None=None, semester: str | None=None, required_completion_ratio: float=1.0, required_fields: list[str] | None=None, optional_fields: list[str] | None=None, allow_new_course_missing_history: bool=True, new_course_grace_period_years: int=2, min_survey_response_count: int | None=None, block_on_invalid_numeric: bool=True, block_on_critical_issues: bool=True, allow_override: bool=True, override_requires_reason: bool=True, override_requires_approval: bool=True, notes: str | None=None, activate: bool=True) -> dict[str, Any]` (satır 118): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `resolve_policy(conn: sqlite3.Connection, scope_type: str, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> dict[str, Any]` (satır 198): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_completion_policies(conn: sqlite3.Connection) -> list[dict[str, Any]]` (satır 248): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `activate_completion_policy(conn: sqlite3.Connection, policy_id: int) -> dict[str, Any]` (satır 255): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/criteria_completion_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 74): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dumps(value: Any) -> str` (satır 78): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_loads(value: str | None, default: Any) -> Any` (satır 82): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None=None) -> dict[str, Any] | None` (satır 91): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetchone_dict(cur: sqlite3.Cursor) -> dict[str, Any] | None` (satır 101): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetchall_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]` (satır 109): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_ensure_schema(conn: sqlite3.Connection) -> None` (satır 115): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_normalize_semester(value: str | None) -> str | None` (satır 120): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_legacy_status_from_level(level: str, ratio: float) -> str` (satır 129): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_completion_level(ratio: float, warning_count: int, invalid_required_fields: int, blocking: bool) -> str` (satır 137): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_semester_sql(alias: str) -> str` (satır 160): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_course_scope(conn: sqlite3.Connection, scope_type: str, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> list[dict[str, Any]]` (satır 164): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_latest_criteria_row(conn: sqlite3.Connection, course_id: int, year: int, semester: str | None) -> dict[str, Any] | None` (satır 209): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_history_count(conn: sqlite3.Connection, course_id: int, year: int) -> int` (satır 236): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_first_curriculum_year(conn: sqlite3.Connection, course_id: int) -> int | None` (satır 254): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_matrix_row_for_field(conn: sqlite3.Connection, course: dict[str, Any], criteria_row: dict[str, Any] | None, field: str, required: bool, policy: dict[str, Any], year: int, semester: str | None) -> tuple[dict[str, Any], list[dict[str, Any]]]` (satır 269): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_delete_scope_rows(conn: sqlite3.Connection, table_name: str, scope_type: str, year: int, faculty_id: int | None, department_id: int | None, semester: str | None) -> None` (satır 411): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_persist_matrix_and_issues(conn: sqlite3.Connection, result: dict[str, Any], issues: list[dict[str, Any]]) -> None` (satır 436): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_criterion_summary(matrix: list[dict[str, Any]]) -> dict[str, dict[str, Any]]` (satır 517): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_course_counts(matrix: list[dict[str, Any]]) -> dict[str, int]` (satır 540): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_blocking_reason(result: dict[str, Any]) -> str | None` (satır 564): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_completion(conn: sqlite3.Connection, scope_type: str, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> dict[str, Any]` (satır 581): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_status_previous(conn: sqlite3.Connection, table_name: str, faculty_id: int | None, department_id: int | None, year: int) -> dict[str, Any] | None` (satır 695): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `log_completion_change(conn: sqlite3.Connection, result: dict[str, Any], old_status: str | None=None, old_ratio: float | None=None, old_level: str | None=None, changed_by: str | None=None, change_reason: str | None=None) -> bool` (satır 726): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_upsert_department_status(conn: sqlite3.Connection, result: dict[str, Any], old: dict[str, Any] | None) -> None` (satır 781): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_upsert_faculty_status(conn: sqlite3.Connection, result: dict[str, Any], old: dict[str, Any] | None) -> None` (satır 856): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `refresh_completion_status(conn: sqlite3.Connection, scope_type: str, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None, commit: bool=True) -> dict[str, Any]` (satır 931): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_completion_summary(conn: sqlite3.Connection, scope_type: str, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None, refresh: bool=True) -> dict[str, Any]` (satır 991): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_blocking_reason(conn: sqlite3.Connection, scope_type: str, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> str | None` (satır 1005): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `can_run_algorithm(conn: sqlite3.Connection, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None, scope_type: str | None=None) -> dict[str, Any]` (satır 1017): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_completion_matrix(conn: sqlite3.Connection, scope_type: str, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None, refresh: bool=True) -> list[dict[str, Any]]` (satır 1052): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_validation_issues(conn: sqlite3.Connection, scope_type: str, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None, refresh: bool=True) -> list[dict[str, Any]]` (satır 1065): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_completion_history(conn: sqlite3.Connection, scope_type: str | None=None, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None, limit: int=200) -> list[dict[str, Any]]` (satır 1078): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/criteria_definition_service.py`
  - Fonksiyonlar:
    - `seed_default_decision_criteria(conn: sqlite3.Connection) -> list[dict[str, Any]]` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_active_criteria(conn: sqlite3.Connection, include_inactive: bool=False) -> list[dict[str, Any]]` (satır 51): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_criterion(conn: sqlite3.Connection, criterion_key: str) -> dict[str, Any] | None` (satır 64): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_or_update_criterion(conn: sqlite3.Connection, *, criterion_key: str, display_name: str, description: str | None=None, criterion_type: str='score', is_benefit: bool=True, default_enabled: bool=True, min_value: float | None=None, max_value: float | None=None, normalization_method: str | None='minmax', source_type: str | None='manual', sort_order: int=100, is_active: bool=True) -> dict[str, Any]` (satır 71): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `deactivate_criterion(conn: sqlite3.Connection, criterion_key: str) -> dict[str, Any]` (satır 133): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `criteria_direction_map(conn: sqlite3.Connection) -> dict[str, bool]` (satır 143): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_dict(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]` (satır 147): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_now() -> str` (satır 176): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/criteria_import_service.py`
  - Fonksiyonlar:
    - `_now_utc() -> str` (satır 85): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `normalize_term_label(value: str | None) -> str` (satır 89): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `term_key(value: str | None) -> str` (satır 96): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `normalize_department_scope_name(value: str | None) -> str | None` (satır 100): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_find_col(columns: list[str], *candidates) -> str | None` (satır 109): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_parse_year(value: Any) -> int | None` (satır 118): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_safe_int(value: Any) -> int | None` (satır 136): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_safe_float(value: Any) -> float | None` (satır 145): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_clean_text(value: Any) -> str | None` (satır 154): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_excel_column_letter(index_1_based: int) -> str` (satır 161): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_is_summary_row(ders_kodu: str | None, ders_adi: str | None) -> bool` (satır 172): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_read_meta_sheet(xls: pd.ExcelFile) -> dict[str, Any]` (satır 179): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `parse_criteria_excel(excel_path: str) -> dict[str, Any]` (satır 197): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `validate_criteria_rows(rows: list[CriteriaRow], faculty_name: str | None=None, department_name: str | None=None, year: int | None=None, term: str | None=None) -> dict[str, Any]` (satır 294): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_resolve_faculty_name(cur: sqlite3.Cursor, faculty_id: int) -> str | None` (satır 359): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_resolve_department_name(cur: sqlite3.Cursor, department_id: int | None) -> str | None` (satır 365): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_table_exists(cur: sqlite3.Cursor, table_name: str) -> bool` (satır 373): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_elective_predicate(cur: sqlite3.Cursor, alias: str) -> str` (satır 381): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_get_scope_courses(cur: sqlite3.Cursor, faculty_id: int, year: int, term: str, department_id: int | None=None) -> list[dict[str, Any]]` (satır 389): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `load_criteria_template_context(db_path: str, faculty_id: int, year: int, term: str, department_id: int | None=None) -> dict[str, Any]` (satır 437): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `write_criteria_template_excel(target_path: str, faculty_name: str | None=None, department_name: str | None=None, year: int | None=None, term: str | None=None, db_path: str | None=None, faculty_id: int | None=None, department_id: int | None=None) -> str` (satır 480): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_load_scope_candidates(cur: sqlite3.Cursor, faculty_id: int, year: int, term: str, department_id: int | None=None) -> tuple[list[CourseCandidate], list[dict[str, Any]]]` (satır 569): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `match_criteria_rows(conn: sqlite3.Connection, rows: list[CriteriaRow], faculty_id: int, year: int, term: str, department_id: int | None=None) -> dict[str, Any]` (satır 606): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_iter_chunks(values: list[int], chunk_size: int=800) -> list[list[int]]` (satır 694): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_exact_scope_import_ids(cur: sqlite3.Cursor, faculty_id: int, year: int, term: str, department_id: int | None=None, only_applied: bool=True) -> list[int]` (satır 698): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_delete_metrics_for_courses(cur: sqlite3.Cursor, course_ids: set[int], year: int, term: str) -> dict[str, int]` (satır 740): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `replace_existing_criteria_scope(conn: sqlite3.Connection, faculty_id: int, year: int, term: str, department_id: int | None=None) -> dict[str, int]` (satır 775): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_next_scope_version(cur: sqlite3.Cursor, faculty_id: int, year: int, term: str, department_id: int | None=None) -> int` (satır 868): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_find_criteria_row_id(cur: sqlite3.Cursor, ders_id: int, year: int, term: str) -> int | None` (satır 905): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_has_active_department_override(cur: sqlite3.Cursor, criteria_row_id: int) -> bool` (satır 927): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_active_department_override_course_ids(cur: sqlite3.Cursor, course_ids: set[int], year: int, term: str) -> set[int]` (satır 943): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `apply_criteria_import(conn: sqlite3.Connection, faculty_id: int, year: int, term: str, rows: list[CriteriaImportRowResult], source_filename: str | None=None, department_id: int | None=None, template_version: str=CRITERIA_TEMPLATE_VERSION, notes: str | None=None, import_batch_id: int | None=None) -> dict[str, Any]` (satır 971): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_criteria_excel(db_path: str, excel_path: str, faculty_id: int, year: int, term: str, department_id: int | None=None, source_filename: str | None=None, auto_activate: bool=True, uploaded_by: str | None=None) -> dict[str, Any]` (satır 1278): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_criteria_import_row_to_summary(row: sqlite3.Row | tuple[Any, ...] | None) -> dict[str, Any] | None` (satır 1542): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_criteria_import_by_id(conn: sqlite3.Connection, import_id: int) -> dict[str, Any] | None` (satır 1562): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_active_criteria_import(conn: sqlite3.Connection, faculty_id: int, year: int, term: str, department_id: int | None=None) -> dict[str, Any] | None` (satır 1592): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `format_criteria_import_summary(summary: dict[str, Any] | None) -> str` (satır 1666): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `summarize_report_criteria_scope(conn: sqlite3.Connection, faculty_id: int, year: int, term: str, department_id: int | None=None) -> dict[str, Any]` (satır 1679): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `CriteriaRow` (satır 45): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `CriteriaImportRowResult` (satır 62): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict[str, Any]` (satır 81): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/criteria_override_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_normalize_semester(value: str | None) -> str | None` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dumps(value: Any) -> str` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_loads(value: str | None, default: Any) -> Any` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None) -> dict[str, Any] | None` (satır 41): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `request_override(conn: sqlite3.Connection, scope_type: str, year: int, reason: str, faculty_id: int | None=None, department_id: int | None=None, course_id: int | None=None, semester: str | None=None, missing_fields: list[str] | None=None, validation_issues: list[dict[str, Any]] | None=None, requested_by: str | None=None, expires_at: str | None=None) -> dict[str, Any]` (satır 50): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_override(conn: sqlite3.Connection, override_id: int) -> dict[str, Any] | None` (satır 105): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `approve_override(conn: sqlite3.Connection, override_id: int, approved_by: str | None=None) -> dict[str, Any]` (satır 112): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `reject_override(conn: sqlite3.Connection, override_id: int, rejection_reason: str, rejected_by: str | None=None) -> dict[str, Any]` (satır 126): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_active_override(conn: sqlite3.Connection, scope_type: str, year: int, faculty_id: int | None=None, department_id: int | None=None, course_id: int | None=None, semester: str | None=None) -> dict[str, Any] | None` (satır 145): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_overrides(conn: sqlite3.Connection, scope_type: str | None=None, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None, approval_status: str | None=None) -> list[dict[str, Any]]` (satır 178): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `mark_override_used(conn: sqlite3.Connection, override_id: int, run_id: int | None=None) -> None` (satır 207): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/criteria_service.py`
  - Sınıflar:
    - `CriteriaService` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, conn: sqlite3.Connection | None=None, db_path: str | None=None)` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_criteria(self, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> ServiceResult` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `completion_summary(self, scope_type: str, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> ServiceResult` (satır 25): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/criteria_task_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dumps(value: Any) -> str` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_loads(value: str | None, default: Any) -> Any` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None) -> dict[str, Any] | None` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_priority(missing_fields: list[str], validation_issues: list[dict[str, Any]]) -> str` (satır 40): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_tasks_for_missing_criteria(conn: sqlite3.Connection, completion_result: dict[str, Any], assigned_role: str | None=None, created_by: str | None=None) -> list[dict[str, Any]]` (satır 50): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_task(conn: sqlite3.Connection, task_id: int) -> dict[str, Any] | None` (satır 124): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_tasks(conn: sqlite3.Connection, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None, status: str | None=None) -> list[dict[str, Any]]` (satır 131): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `assign_task(conn: sqlite3.Connection, task_id: int, assigned_to: str | None=None, assigned_role: str | None=None, due_date: str | None=None) -> dict[str, Any]` (satır 153): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `update_task_status(conn: sqlite3.Connection, task_id: int, status: str, notes: str | None=None, approved_by: str | None=None) -> dict[str, Any]` (satır 175): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `close_completed_tasks(conn: sqlite3.Connection, completion_result: dict[str, Any]) -> int` (satır 198): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/criteria_validation_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 36): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_normalize_number(value: Any) -> tuple[bool, float | None]` (satır 40): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_missing(field_name: str, value: Any, required: bool) -> ValidationResult` (satır 52): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `validate_criterion_value(field_name: str, value: Any, context: dict[str, Any] | None=None) -> ValidationResult` (satır 74): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_table_exists(cur: sqlite3.Cursor, table_name: str) -> bool` (satır 172): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_semester_clause(alias: str='dk') -> str` (satır 177): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `validate_course_criteria(conn: sqlite3.Connection, course_id: int, year: int, semester: str | None=None, required_fields: list[str] | None=None) -> dict[str, Any]` (satır 181): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `record_validation_issues(conn: sqlite3.Connection, scope_type: str, year: int, issues: list[dict[str, Any]], faculty_id: int | None=None, department_id: int | None=None, course_id: int | None=None, semester: str | None=None) -> None` (satır 249): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `validate_scope_criteria(conn: sqlite3.Connection, scope_type: str, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None, required_fields: list[str] | None=None) -> dict[str, Any]` (satır 288): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `ValidationResult` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `is_valid(self) -> bool` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict[str, Any]` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/curriculum_import_service.py`
  - Fonksiyonlar:
    - `normalize_term(raw: str | None) -> str` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_normalize_text(value: str | None) -> str` (satır 39): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_find_col(columns: list[str], *candidates) -> str | None` (satır 55): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_extract_rows_from_df(df: pd.DataFrame, sheet_name: str) -> tuple[list[dict[str, Any]], list[str]]` (satır 64): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_parse_year(raw: Any) -> int | None` (satır 150): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `parse_curriculum_excel(excel_path: str) -> tuple[list[dict[str, Any]], list[str]]` (satır 164): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `parse_excel(excel_path: str) -> tuple[list[dict[str, Any]], list[str]]` (satır 178): Backward-compatible alias:
    - `_table_exists(cur: sqlite3.Cursor, table_name: str) -> bool` (satır 186): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_find_faculty_id(cur: sqlite3.Cursor, faculty_name: str) -> int | None` (satır 194): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_find_department_id(cur: sqlite3.Cursor, faculty_id: int, department_name: str) -> int | None` (satır 204): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_find_course_id(cur: sqlite3.Cursor, ders_adi: str | None, ders_kodu: str | None) -> int | None` (satır 230): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_get_or_create_scope_mufredat_id(cur: sqlite3.Cursor, faculty_id: int, department_id: int, year: int, term: str) -> int` (satır 252): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_scope_courses(cur: sqlite3.Cursor, mufredat_id: int) -> set[int]` (satır 291): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `reset_criteria_for_import(conn: sqlite3.Connection, target_year: int, scope_courses: dict[tuple[int, int, int, str], set[int]]) -> dict[str, int]` (satır 296): Import sonrasi ilgili yil/fakulte/bolum kapsaminda kriter ve skor verilerini sifirlar.
    - `import_curriculum_excel(db_path: str, excel_path: str, target_year: int=2022, auto_activate: bool=True, uploaded_by: str | None=None) -> dict[str, Any]` (satır 450): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_curriculum_2022(db_path: str, excel_path: str) -> dict[str, Any]` (satır 794): Backward-compatible helper:
  - Sınıflar:
    - `ImportResult` (satır 425): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict[str, Any]` (satır 446): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/curriculum_validation_service.py`
  - Fonksiyonlar:
    - `validate_curriculum_scope(year: int | None, department_id: int | None=None, semester: str | None=None) -> ValidationResult` (satır 9): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/data_collection_priority_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dump(value) -> str` (satır 26): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_collection_priorities(year: int, faculty_id: Optional[int]=None, department_id: Optional[int]=None, session: Optional[Session]=None) -> list[DataCollectionPriority]` (satır 30): Veri toplama öncelikleri üret.
    - `mark_priority_completed(priority_id: int, session: Optional[Session]=None) -> Optional[DataCollectionPriority]` (satır 175): Veri toplama görevini tamamlandı olarak işaretle.
    - `get_open_priorities(year: int, faculty_id: Optional[int]=None, session: Optional[Session]=None) -> list[dict]` (satır 204): Açık (yapılmamış) veri toplama öncelikleri.

### `app/services/data_confidence_service.py`
  - Fonksiyonlar:
    - `_safe_float(value: Any, default: float=0.0) -> float` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dump(value: Any) -> str` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `confidence_level(score: float) -> str` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_data_confidence(has_success_data: bool, has_popularity_data: bool, has_survey_data: bool, has_trend_data: bool, has_recent_data: bool, survey_count: int | None=None, data_points_count: int=0, min_survey_count: int | None=None) -> dict[str, Any]` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_course_data_confidence(cur: sqlite3.Cursor, course_id: int, year: int, semester: str | None=None, policy: dict[str, Any] | None=None) -> dict[str, Any]` (satır 97): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `save_data_confidence(cur: sqlite3.Cursor, decision_run_id: int | None, course_id: int, year: int, confidence: dict[str, Any]) -> int` (satır 202): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/data_coverage_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 25): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dump(value) -> str` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_coverage_ratios(session: Session, year: int, faculty_id: Optional[int]=None, department_id: Optional[int]=None) -> dict` (satır 33): Veri kapsama oranlarını hesapla.
    - `generate_coverage_report(year: int, faculty_id: Optional[int]=None, department_id: Optional[int]=None, session: Optional[Session]=None) -> DataCoverageReport` (satır 180): Veri kapsama raporu oluştur ve kaydet.
    - `get_coverage_table(year: int, scope_type: str='department', session: Optional[Session]=None) -> list[dict]` (satır 255): Fakülte/bölüm bazında coverage table.

### `app/services/data_leakage_detector.py`
  - Fonksiyonlar:
    - `detect_target_leakage(feature_names: Iterable[str], target_name: str | None) -> dict[str, Any]` (satır 9): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `detect_future_leakage(dataset_meta: dict[str, Any] | None) -> dict[str, Any]` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `detect_duplicate_entity_leakage(entity_ids: dict[str, Iterable[Any]] | Iterable[Any], splits: dict[str, Iterable[Any]] | None=None) -> dict[str, Any]` (satır 26): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `detect_score_leakage(feature_names: Iterable[str]) -> dict[str, Any]` (satır 43): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `detect_mcdm_output_as_feature(feature_names: Iterable[str]) -> dict[str, Any]` (satır 51): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_leakage_report(*, feature_names: Iterable[str], target_name: str | None=None, dataset_meta: dict[str, Any] | None=None, entity_ids: dict[str, Iterable[Any]] | None=None) -> dict[str, Any]` (satır 58): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_report(detected: bool, level: str, warnings: list[str], blocked: bool, details: dict[str, Any] | None=None) -> dict[str, Any]` (satır 97): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_norm(value: str) -> str` (satır 108): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/data_quality_integration_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dump(value: Any) -> str` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `assess_data_readiness_cursor(cur: sqlite3.Cursor, year: int, faculty_id: Optional[int]=None, department_id: Optional[int]=None, semester: Optional[str]=None) -> dict[str, Any]` (satır 25): Veri olgunluğunu değerlendir (cursor tabanlı).
    - `generate_coverage_report_cursor(cur: sqlite3.Cursor, year: int, faculty_id: Optional[int]=None, department_id: Optional[int]=None, semester: Optional[str]=None) -> dict[str, Any]` (satır 163): Veri kapsama raporunu hesapla (cursor tabanlı).
    - `save_data_coverage_report(cur: sqlite3.Cursor, year: int, faculty_id: Optional[int]=None, department_id: Optional[int]=None, semester: Optional[str]=None, coverage_data: Optional[dict[str, Any]]=None) -> int` (satır 261): Kapsama raporunu data_coverage_reports tablosuna kaydet.

### `app/services/data_quality_reporting_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 26): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dump(value) -> str` (satır 30): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_data_quality_dashboard(year: int, faculty_id: Optional[int]=None, session: Optional[Session]=None) -> dict` (satır 34): Kapsamlı veri kalitesi dashboard'u.
    - `generate_missing_data_report(year: int, faculty_id: Optional[int]=None, session: Optional[Session]=None) -> dict` (satır 122): Eksik veri raporu.
    - `generate_validation_issues_report(year: int, faculty_id: Optional[int]=None, session: Optional[Session]=None) -> dict` (satır 184): Data validation issues raporu.
    - `generate_readiness_report(year: int, faculty_id: Optional[int]=None, session: Optional[Session]=None) -> dict` (satır 252): Data readiness değerlendirme raporu.

### `app/services/data_readiness_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dump(value) -> str` (satır 26): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_readiness_score(session: Session, year: int, faculty_id: Optional[int]=None, department_id: Optional[int]=None) -> dict` (satır 30): Veri olgunluğu skorunu hesapla (0-100).
    - `assess_data_readiness(year: int, faculty_id: Optional[int]=None, department_id: Optional[int]=None, session: Optional[Session]=None) -> DataReadinessAssessment` (satır 143): Veri olgunluğu değerlendirmesi yap ve kaydet.
    - `get_readiness_level(score: float) -> str` (satır 211): Score'dan readiness level'ı belirle.
    - `get_blocking_reasons(year: int, faculty_id: Optional[int]=None, department_id: Optional[int]=None, session: Optional[Session]=None) -> list[str]` (satır 225): Readiness'i bloklayan sebepleri listele.

### `app/services/database_service.py`
  - Sınıflar:
    - `DatabaseService` (satır 10): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, db_path: str | None=None, config: AppConfig | None=None)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `table_names(self) -> list[str]` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `table_count(self) -> int` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `database_profile(self) -> list[dict[str, object]]` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/db.py`
  - Fonksiyonlar:
    - `db_session(db_path: Optional[str]=None) -> Generator[object, None, None]` (satır 25): Thread-safe legacy SQLite oturumu.
    - `get_raw_connection(db_path: Optional[str]=None)` (satır 39): Raw DBAPI connection döndürür.
    - `get_conn(db_path: Optional[str]=None)` (satır 51): Legacy uyumluluk: Raw DBAPI connection döndürür.

### `app/services/decision_outcome_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `record_post_decision_outcome(course_id: int, decision_year: int, outcome_year: int, actual_enrollment: Optional[int]=None, actual_capacity: Optional[int]=None, actual_success_rate: Optional[float]=None, actual_average_grade: Optional[float]=None, actual_survey_demand: Optional[int]=None, decision_run_id: Optional[int]=None, course_decision_id: Optional[int]=None, session: Optional[Session]=None) -> PostDecisionOutcome` (satır 25): Karar sonrası outcome kaydedilir.
    - `evaluate_decision_effectiveness(course_decision_id: int, session: Optional[Session]=None) -> dict` (satır 74): Bir kararın sonraki yıl ne kadar etkili olduğunu değerlendir.
    - `compare_predicted_vs_actual(course_id: int, decision_year: int, outcome_year: int, session: Optional[Session]=None) -> dict` (satır 180): Tahmin edilen vs gerçekleşen sonuçları karşılaştır.
    - `generate_outcome_report(year: int, session: Optional[Session]=None) -> dict` (satır 244): Bir karar yılı için outcome raporu.

### `app/services/decision_policy_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_bool(value: Any) -> bool` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_policy(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]` (satır 42): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_deactivate_same_scope(cur: sqlite3.Cursor, scope_type: str, faculty_id: int | None, department_id: int | None, year: int | None) -> None` (satır 82): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ensure_default_decision_policy(conn: sqlite3.Connection) -> dict[str, Any]` (satır 102): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_decision_policy(conn: sqlite3.Connection, name: str, scope_type: str='global', faculty_id: int | None=None, department_id: int | None=None, year: int | None=None, mode: str='static_threshold', curriculum_keep_threshold: float=70.0, pool_threshold: float=50.0, rest_threshold: float=40.0, cancel_candidate_threshold: float | None=30.0, min_success_rate: float | None=None, min_survey_count: int | None=None, min_enrollment_rate: float | None=None, new_course_grace_period_years: int=2, low_data_confidence_threshold: float=0.5, sensitivity_margin: float=3.0, top_percent_curriculum: float | None=None, middle_percent_pool: float | None=None, bottom_percent_rest: float | None=None, require_manual_approval_for_cancel: bool=True, notes: str | None=None, activate: bool=True) -> dict[str, Any]` (satır 125): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `resolve_decision_policy(conn: sqlite3.Connection, faculty_id: int | None=None, department_id: int | None=None, year: int | None=None) -> dict[str, Any]` (satır 202): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_decision_policies(conn: sqlite3.Connection) -> list[dict[str, Any]]` (satır 244): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `activate_decision_policy(conn: sqlite3.Connection, policy_id: int) -> dict[str, Any]` (satır 252): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `classify_score(score: float | None, policy: dict[str, Any]) -> dict[str, Any]` (satır 277): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `status_label(status: int | None) -> str` (satır 311): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/decision_run_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dump(value: Any) -> str` (satır 37): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_load(value: str | None, default: Any) -> Any` (satır 41): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_hash_payload(value: Any) -> str` (satır 50): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_normalize_semester(value: str | None) -> str` (satır 55): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_term_key(value: str | None) -> str` (satır 59): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_dict(row: sqlite3.Row | tuple[Any, ...], columns: list[str] | None=None) -> dict[str, Any]` (satır 63): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_governance_flags(cur: sqlite3.Cursor, course_id: int) -> dict[str, Any]` (satır 69): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_first_seen_year(cur: sqlite3.Cursor, course_id: int) -> int | None` (satır 103): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_old_status(cur: sqlite3.Cursor, course_id: int, year: int, faculty_id: int | None, semester: str | None) -> int | None` (satır 122): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_course_meta(cur: sqlite3.Cursor, course_ids: list[int]) -> dict[int, dict[str, Any]]` (satır 143): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_apply_governance(recommended_status: int, old_status: int | None, year: int, policy: dict[str, Any], governance: dict[str, Any], confidence: dict[str, Any], first_seen_year: int | None, sensitivity: dict[str, Any] | None=None) -> dict[str, Any]` (satır 169): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_decision_run(cur: sqlite3.Cursor, run_name: str, year: int, faculty_id: int | None, department_id: int | None, semester: str | None, ahp_profile_id: int | None, decision_policy_id: int | None, input_data_hash: str | None, created_by: str | None=None, status: str='started', ahp_profile_version: int | None=None, ahp_weights_snapshot: dict[str, Any] | None=None, ahp_consistency_ratio: float | None=None, ahp_profile_status_at_run: str | None=None, ahp_profile_source: str | None=None) -> int` (satır 231): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `mark_decision_run_completed(cur: sqlite3.Cursor, run_id: int, summary: dict[str, Any]) -> None` (satır 286): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `mark_decision_run_failed(cur: sqlite3.Cursor, run_id: int, error_message: str, summary: dict[str, Any] | None=None) -> None` (satır 297): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `record_decision_run_for_faculty_year(conn: sqlite3.Connection, year: int, faculty_id: int | None, semester: str | None='Guz', department_id: int | None=None, generation_result: dict[str, Any] | None=None, created_by: str | None=None) -> dict[str, Any]` (satır 308): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `record_failed_decision_run(db_path: str, year: int, faculty_id: int | None, semester: str | None, error_message: str, department_id: int | None=None) -> dict[str, Any]` (satır 543): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_decision_runs(conn: sqlite3.Connection, limit: int=100) -> list[dict[str, Any]]` (satır 582): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_decision_run(conn: sqlite3.Connection, run_id: int) -> dict[str, Any] | None` (satır 600): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_course_decisions(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]` (satır 609): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_course_decision_explanation(conn: sqlite3.Connection, decision_id: int) -> dict[str, Any] | None` (satır 628): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `execute_decision_run(db_path: str, year: int, faculty_id: int, semester: str | None='Guz') -> dict[str, Any]` (satır 646): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `safe_record_decision_run(conn: sqlite3.Connection, year: int, faculty_id: int | None, semester: str | None, generation_result: dict[str, Any] | None=None) -> dict[str, Any]` (satır 666): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/decision_validation_service.py`
  - Fonksiyonlar:
    - `validate_decision_run_request(year: int | None, faculty_id: int | None=None) -> ValidationResult` (satır 9): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/dual_semester.py`
  - Fonksiyonlar:
    - `_term_token(term: str) -> str` (satır 43): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_havuz_has_donem(cur: sqlite3.Cursor) -> bool` (satır 48): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_or_create_curriculum_id(cur: sqlite3.Cursor, faculty_id: int, department_id: int, year: int, term: str) -> int` (satır 53): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_curriculum_courses(cur: sqlite3.Cursor, department_id: int, year: int, term: str) -> list[int]` (satır 92): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_candidate_courses(cur: sqlite3.Cursor, faculty_id: int, department_id: int) -> list[int]` (satır 113): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_scores_for_term(cur: sqlite3.Cursor, faculty_id: int, year: int, term: str, include_ids: list[int]) -> dict[int, float]` (satır 131): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_sort_by_score(courses: list[int], score_map: dict[int, float]) -> list[int]` (satır 152): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fill_block(current: list[int], ranking: list[int], blocked: set[int], block_size: int) -> list[int]` (satır 160): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_rebalance_department(cur: sqlite3.Cursor, faculty_id: int, department_id: int, year: int, block_size: int=4) -> tuple[dict[str, list[int]], int]` (satır 177): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_persist_department_curricula(cur: sqlite3.Cursor, faculty_id: int, department_id: int, year: int, assignments: dict[str, list[int]]) -> None` (satır 244): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_sync_havuz_dual_semester_state(cur: sqlite3.Cursor, faculty_id: int, year: int) -> int` (satır 267): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `rebuild_school_curricula_dual_semester(db_path: str='data/adil_secmeli.db', base_year: int=2022, max_rounds: int=8, block_size: int=4) -> dict[str, Any]` (satır 394): Tum okul icin dual-semester (Guz+Bahar) rebuild.
  - Sınıflar:
    - `RebalanceResult` (satır 36): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/experiment_service.py`
  - Sınıflar:
    - `ExperimentService` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, data_pipeline: DataPipeline | None=None, registry: AlgorithmRegistry | None=None, result_store: ResultStore | None=None) -> None` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_scenarios(self) -> list[dict[str, Any]]` (satır 26): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_algorithms(self, group: str | None=None) -> list[dict[str, str]]` (satır 37): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `build_dataset(self, *, source_type: str, source_path: str, dataset_name: str='benchmark_dataset', synth_noise_std: float=0.02, synth_class_imbalance_alpha: float=0.0, synth_capacity_scale: float=1.0)` (satır 40): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run_scenario(self, dataset, scenario_name: str, *, algorithm_names: list[str] | None=None, synthetic_tier: str | None=None, top_k: int | None=None) -> dict` (satır 60): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `compare_algorithms(self, dataset, *, scenario_name: str, algorithm_names: list[str], synthetic_tier: str | None=None, top_k: int | None=None) -> dict` (satır 80): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `recommend_algorithm(self, *, problem_type: str, data_size: int, explainability_priority: bool=False, use_history: bool=True) -> dict[str, Any]` (satır 99): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/explanation_engine.py`
  - Fonksiyonlar:
    - `_json_dump(value: Any) -> str` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `build_decision_explanation(course_code: str | None, course_name: str | None, decision: dict[str, Any], breakdown: dict[str, Any] | None=None, trend: dict[str, Any] | None=None, confidence: dict[str, Any] | None=None, governance: dict[str, Any] | None=None) -> dict[str, Any]` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `save_decision_explanation(cur: sqlite3.Cursor, course_decision_id: int, explanation: dict[str, Any]) -> int` (satır 106): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/fairness_report_service.py`
  - Fonksiyonlar:
    - `_json_dump(value: Any) -> str` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_fairness_report(cur: sqlite3.Cursor, decision_run_id: int, year: int, faculty_id: int | None=None, department_id: int | None=None) -> dict[str, Any]` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `save_fairness_report(cur: sqlite3.Cursor, decision_run_id: int, faculty_id: int | None, department_id: int | None, year: int, report_pack: dict[str, Any]) -> int` (satır 135): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/file_upload_security_service.py`
  - Sınıflar:
    - `FileUploadSecurityService` (satır 10): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, config: AppConfig)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `sanitize_filename(self, filename: str) -> str` (satır 14): Secure the filename and remove path traversal artifacts.
      - `validate_extension(self, filename: str) -> None` (satır 23): Validate file extension against allowlist.
      - `validate_mime_type(self, content_type: str) -> None` (satır 30): Validate MIME type.
      - `async validate_size_and_hash(self, file: UploadFile) -> tuple[str, int]` (satır 36): Validate file size and compute hash in chunks.
      - `async validate_upload(self, file: UploadFile) -> tuple[str, int]` (satır 55): Perform all file security validations and return hash + byte size.

### `app/services/governed_benchmark_service.py`
  - Fonksiyonlar:
    - `execute_governed_benchmark_run(conn: sqlite3.Connection, payload: dict[str, Any]) -> dict[str, Any]` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_governed_benchmark_runs(conn: sqlite3.Connection, limit: int=100) -> list[dict[str, Any]]` (satır 201): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_governed_benchmark_run(conn: sqlite3.Connection, run_id: int) -> dict[str, Any] | None` (satır 207): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_governed_run_metrics(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]` (satır 214): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_governed_run_validation(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]` (satır 218): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_governed_run_statistics(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]` (satır 222): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_governed_run_diagnostics(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]` (satır 226): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_governed_run_leakage(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]` (satır 230): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_governed_run_clustering(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]` (satır 234): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_governed_run_report(conn: sqlite3.Connection, run_id: int) -> dict[str, Any]` (satır 238): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_save_metrics(conn: sqlite3.Connection, run_id: int, row: dict[str, Any]) -> None` (satır 254): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_save_validation(conn: sqlite3.Connection, run_id: int, algorithm_key: str, row: dict[str, Any]) -> None` (satır 265): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_save_leakage(conn: sqlite3.Connection, run_id: int, algorithm_key: str, report: dict[str, Any]) -> None` (satır 287): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_save_diagnostics(conn: sqlite3.Connection, run_id: int, diagnostics: dict[str, Any]) -> None` (satır 298): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_save_clustering(conn: sqlite3.Connection, run_id: int, evaluation: dict[str, Any]) -> None` (satır 322): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_save_statistics(conn: sqlite3.Connection, stats: dict[str, Any]) -> None` (satır 349): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_build_statistical_comparison(run_id: int, task_type: str, primary_metric: str, fold_metric_map: dict[str, list[float]]) -> dict[str, Any]` (satır 373): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_prediction_for_algorithm(payload: dict[str, Any], algorithm_key: str, y_true: list[Any]) -> list[Any] | None` (satır 398): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_synthetic_fold_metrics(primary_value: float | None) -> list[dict[str, float]]` (satır 408): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_rows(conn: sqlite3.Connection, table: str, run_id: int) -> list[dict[str, Any]]` (satır 418): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_dict(row: sqlite3.Row | tuple) -> dict[str, Any]` (satır 424): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_mean_metrics(rows: list[dict[str, Any]]) -> dict[str, float]` (satır 435): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_std_metrics(rows: list[dict[str, Any]]) -> dict[str, float]` (satır 446): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_default_task_key(task_type: str) -> str` (satır 457): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_primary_metric(task_type: str) -> str` (satır 468): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_feature_names(X: Any) -> list[str]` (satır 478): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_sample_count(X: Any, y: list[Any]) -> int` (satır 490): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_class_distribution(y: list[Any]) -> dict[str, int]` (satır 498): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_float_or_none(value: Any) -> float | None` (satır 505): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json(value: Any) -> str` (satır 512): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_loads(value: Any) -> Any` (satır 516): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_now() -> str` (satır 525): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/havuz_karar.py`
  - Fonksiyonlar:
    - `normalize_semester(raw: str | None) -> str` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_next_status(prev_statu: int, prev_sayac: int, in_mufredat_this_year: bool) -> tuple[int, int]` (satır 37): Bir onceki yilin (prev_statu, prev_sayac) durumuna ve bu yil mufredatta
    - `calculate_next_status_semester(prev_statu: int, prev_sayac: int, selected_in_current_semester: bool, selected_in_other_semester: bool=False) -> tuple[int, int]` (satır 75): Donem-aware durum guncellemesi.
    - `calculate_next_status_governed(prev_statu: int, prev_sayac: int, in_mufredat_this_year: bool, conn: sqlite3.Connection | None=None, context: dict | None=None) -> tuple[int, int, dict]` (satır 97): Geriye uyumlu adapter.
    - `enforce_cross_semester_constraints(assignments: dict[str, set[int] | list[int]]) -> dict[str, list[int]]` (satır 130): Guz/Bahar listelerinde ayni dersi tekillestirir.
    - `_get_muhendislik_fakulte_id(imlec) -> int` (satır 149): Mühendislik fakültesinin ID'sini döner; bulunamazsa 2 varsayar.
    - `_canonical_course_scope(imlec, ders_id: int)` (satır 156): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_pool_row_priority(row, canonical_fakulte_id)` (satır 176): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_dedupe_havuz_year(imlec, yil: int)` (satır 188): Ayni yil + ders icin birden fazla havuz satiri varsa tekilleştirir.
    - `_get_year_curriculum_pairs(imlec, yil: int)` (satır 245): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `onar_2022_ground_truth(vt_yolu: str='data/adil_secmeli.db')` (satır 280): 2022 yılı havuz kayıtlarını müfredat verisiyle senkronize eder.
    - `muhendislik_mufredat_durumunu_esitle(vt_yolu: str='data/adil_secmeli.db', baslangic_yili: int=2022, bitis_yili: int=2025)` (satır 332): 2022 yılını dokunmadan bırakır; 2023, 2024, 2025'i zincirleme hesaplar.
    - `mufredat_durumunu_esitle(vt_yolu: str='data/adil_secmeli.db', baslangic_yili: int=2022, bitis_yili: int=2025)` (satır 468): Tum fakulte ve bolumler icin zincirleme statu/sayac esitlemesi.

### `app/services/import_audit_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dumps(value: Any) -> str` (satır 39): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_loads(value: str | None, default: Any=None) -> Any` (satır 43): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_table_exists(cur: sqlite3.Cursor, table_name: str) -> bool` (satır 52): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_column_names(cur: sqlite3.Cursor, table_name: str) -> set[str]` (satır 57): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None=None) -> dict[str, Any]` (satır 64): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_file_hash(file_path_or_bytes: str | os.PathLike[str] | bytes | bytearray | BinaryIO) -> str` (satır 74): Dosya yolu, byte dizisi veya file-like obje icin SHA256 hesaplar.
    - `calculate_column_signature(columns: list[str] | tuple[str, ...] | None) -> str` (satır 102): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_row_hash(row_payload: dict[str, Any]) -> str` (satır 107): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `extract_excel_metadata(excel_path: str) -> dict[str, Any]` (satır 111): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `detect_duplicate_import(conn: sqlite3.Connection, file_hash: str | None, import_type: str, faculty_id: int | None=None, department_id: int | None=None, year: int | None=None, semester: str | None=None, exclude_batch_id: int | None=None) -> dict[str, Any]` (satır 126): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_scope_type(faculty_id: int | None, department_id: int | None, school_id: int | None, semester: str | None) -> str | None` (satır 173): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_previous_active_batch(conn: sqlite3.Connection, import_type: str, faculty_id: int | None, department_id: int | None, year: int | None, semester: str | None, exclude_batch_id: int | None=None) -> int | None` (satır 185): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_import_batch(conn: sqlite3.Connection, import_type: str, original_filename: str | None=None, stored_filename: str | None=None, file_path: str | None=None, file_bytes: bytes | None=None, sheet_names: list[str] | None=None, columns: list[str] | None=None, row_count: int=0, column_count: int | None=None, school_id: int | None=None, faculty_id: int | None=None, department_id: int | None=None, year: int | None=None, semester: str | None=None, uploaded_by: str | None=None, source_table: str | None=None, source_import_id: int | None=None, validation_summary: dict[str, Any] | None=None, notes: str | None=None, status: str='uploaded') -> dict[str, Any]` (satır 219): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `link_source_import(conn: sqlite3.Connection, import_batch_id: int, source_table: str, source_import_id: int, file_hash_sha256: str | None=None, file_size: int | None=None) -> None` (satır 331): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `update_import_status(conn: sqlite3.Connection, import_batch_id: int, status: str, error_message: str | None=None, user: str | None=None, reason: str | None=None, validation_summary: dict[str, Any] | None=None) -> dict[str, Any]` (satır 370): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `validate_import(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any]` (satır 406): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `approve_import(conn: sqlite3.Connection, import_batch_id: int, approved_by: str | None=None) -> dict[str, Any]` (satır 419): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `reject_import(conn: sqlite3.Connection, import_batch_id: int, reason: str, rejected_by: str | None=None) -> dict[str, Any]` (satır 423): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `activate_import(conn: sqlite3.Connection, import_batch_id: int, user: str | None=None) -> dict[str, Any]` (satır 432): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `classify_issue(message: str | None, row_status: str | None=None, field_name: str | None=None) -> tuple[str, str, str]` (satır 473): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `record_import_issue(conn: sqlite3.Connection, import_batch_id: int, row_number: int, message: str, source_row_id: int | None=None, severity: str | None=None, issue_type: str | None=None, field_name: str | None=None, raw_value: Any=None, normalized_value: Any=None, suggestion: str | None=None) -> dict[str, Any]` (satır 527): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_import_batch(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any] | None` (satır 572): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_import_batches(conn: sqlite3.Connection, import_type: str | None=None, status: str | None=None, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None, limit: int=200) -> list[dict[str, Any]]` (satır 580): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_source_row_table(import_type: str | None) -> str | None` (satır 616): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_import_rows(conn: sqlite3.Connection, import_batch_id: int, limit: int=500) -> list[dict[str, Any]]` (satır 624): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_import_issues(conn: sqlite3.Connection, import_batch_id: int, limit: int=500) -> list[dict[str, Any]]` (satır 645): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `mark_batch_failed_by_path(db_path: str, file_path: str, import_type: str, error_message: str, **scope) -> dict[str, Any]` (satır 666): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `preview_import(db_path: str, file_path: str, import_type: str, faculty_id: int | None=None, department_id: int | None=None, year: int | None=None, semester: str | None=None, uploaded_by: str | None=None) -> dict[str, Any]` (satır 695): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `save_upload_to_temp(upload: Any) -> str` (satır 732): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/import_diff_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dumps(value: Any) -> str` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_normalize_value(value: Any) -> Any` (satır 36): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_load_normalized_row(row: dict[str, Any]) -> dict[str, Any]` (satır 51): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_entity_key(row: dict[str, Any]) -> str` (satır 63): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `find_previous_import_batch(conn: sqlite3.Connection, import_batch_id: int) -> int | None` (satır 73): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `recalculate_import_diff(conn: sqlite3.Connection, import_batch_id: int, compared_to_import_batch_id: int | None=None) -> dict[str, Any]` (satır 104): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_import_diff(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any] | None` (satır 253): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/import_impact_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dumps(value: Any) -> str` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_table_exists(cur: sqlite3.Cursor, table_name: str) -> bool` (satır 23): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `link_decision_run_import_source(conn: sqlite3.Connection, decision_run_id: int | None, import_batch_id: int, import_type: str | None=None) -> int` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_decision_map(cur: sqlite3.Cursor, run_id: int | None) -> dict[int, dict[str, Any]]` (satır 53): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `recalculate_import_impact(conn: sqlite3.Connection, import_batch_id: int, previous_decision_run_id: int | None=None, new_decision_run_id: int | None=None) -> dict[str, Any]` (satır 76): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_import_impact(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any] | None` (satır 193): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/import_lineage_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `record_value_source(conn: sqlite3.Connection, course_id: int, year: int, field_name: str, value: Any, source_type: str, faculty_id: int | None=None, department_id: int | None=None, source_import_batch_id: int | None=None, source_row_id: int | None=None, is_locked: bool=False, created_by: str | None=None, deactivate_existing: bool=True) -> int` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `apply_manual_override(conn: sqlite3.Connection, course_id: int, year: int, field_name: str, value: Any, override_reason: str, user: str | None=None, faculty_id: int | None=None, department_id: int | None=None) -> dict[str, Any]` (satır 76): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_value_sources(conn: sqlite3.Connection, course_id: int | None=None, year: int | None=None, field_name: str | None=None, active_only: bool=True, limit: int=500) -> list[dict[str, Any]]` (satır 135): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/import_quality_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dumps(value: Any) -> str` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_quality_level(score: float) -> str` (satır 46): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `evaluate_row_quality(row_result: dict[str, Any]) -> float` (satır 54): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `evaluate_import_quality(conn: sqlite3.Connection, import_batch_id: int) -> ImportQualityResult` (satır 65): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `summarize_quality(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any]` (satır 210): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `ImportQualityResult` (satır 25): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict[str, Any]` (satır 42): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/import_rollback_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dumps(value: Any) -> str` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_table_exists(cur: sqlite3.Cursor, table_name: str) -> bool` (satır 23): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_column_names(cur: sqlite3.Cursor, table_name: str) -> set[str]` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_log(cur: sqlite3.Cursor, import_batch_id: int, action: str, table: str, message: str, affected_record_id: int | None=None, before: Any=None, after: Any=None) -> None` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `can_rollback(conn: sqlite3.Connection, import_batch_id: int) -> bool` (satır 66): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_rollback_plan(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any]` (satır 71): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `rollback_import(conn: sqlite3.Connection, import_batch_id: int, reason: str, user: str | None=None) -> dict[str, Any]` (satır 109): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/import_validation_service.py`
  - Fonksiyonlar:
    - `validate_import_request(import_type: str | None, filename: str | None=None) -> ValidationResult` (satır 9): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/instructor_planning_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None=None) -> dict[str, Any] | None` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_all_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]` (satır 26): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_instructor(conn: sqlite3.Connection, name: str, email: str | None=None, faculty_id: int | None=None, department_id: int | None=None, is_active: bool=True) -> dict[str, Any]` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_instructors(conn: sqlite3.Connection, faculty_id: int | None=None, department_id: int | None=None) -> list[dict[str, Any]]` (satır 53): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `assign_course_instructor(conn: sqlite3.Connection, course_id: int, instructor_id: int, priority: int=1, can_teach: bool=True, preferred: bool=False, notes: str | None=None) -> dict[str, Any]` (satır 68): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `upsert_instructor_availability(conn: sqlite3.Connection, instructor_id: int, year: int, semester: str, available: bool=True, max_elective_courses: int=2, current_assigned_elective_count: int | None=None, unavailable_reason: str | None=None, notes: str | None=None) -> dict[str, Any]` (satır 92): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_instructor_availability(conn: sqlite3.Connection, year: int | None=None, semester: str | None=None, instructor_id: int | None=None) -> list[dict[str, Any]]` (satır 132): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_available_instructors(conn: sqlite3.Connection, course_id: int, year: int, semester: str, assigned_counts: dict[tuple[int, str], int] | None=None) -> list[dict[str, Any]]` (satır 158): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `check_instructor_feasibility(conn: sqlite3.Connection, course_id: int, year: int, semester: str, assigned_counts: dict[tuple[int, str], int] | None=None) -> dict[str, Any]` (satır 193): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_instructor_load(assignments: list[dict[str, Any]]) -> dict[str, Any]` (satır 217): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/missing_data_risk_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 25): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dumps(value: Any) -> str` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_risk_level(score: float) -> str` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_missing_data_risk(matrix_rows: list[dict[str, Any]], policy: dict[str, Any], scope_type: str, year: int, faculty_id: int | None=None, department_id: int | None=None, course_id: int | None=None, semester: str | None=None) -> dict[str, Any]` (satır 43): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `persist_missing_data_risk(conn: sqlite3.Connection, risk: dict[str, Any]) -> dict[str, Any]` (satır 109): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_missing_data_risk_report(conn: sqlite3.Connection, scope_type: str, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> dict[str, Any] | None` (satır 160): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/missing_data_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `detect_missing_data_for_course(course_id: int, year: int, semester: str='Güz', session: Optional[Session]=None) -> list[MissingDataItem]` (satır 26): Bir ders için eksik veriyi tespit et.
    - `record_low_confidence_decision(decision_run_id: int, course_decision_id: Optional[int], course_id: int, year: int, confidence_score: float, confidence_level: str, reason: str, session: Optional[Session]=None) -> LowConfidenceDecisionFlag` (satır 196): Düşük güven kararını işaretle.
    - `record_validation_issue(source_type: str, issue_type: str, severity: str, message: str, source_id: Optional[int]=None, source_row_id: Optional[int]=None, course_id: Optional[int]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None, year: Optional[int]=None, field_name: Optional[str]=None, raw_value: Optional[str]=None, session: Optional[Session]=None) -> DataValidationIssue` (satır 235): Veri validation issue'sunu kaydet.
    - `get_missing_data_matrix(year: int, faculty_id: Optional[int]=None, session: Optional[Session]=None) -> list[dict]` (satır 284): Eksik veri matrisini döndür.

### `app/services/ml_algorithm_registry_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 50): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_bool(value) -> bool` (satır 54): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_config(row: sqlite3.Row | tuple) -> MLAlgorithmConfig` (satır 58): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `seed_default_algorithm_registry(conn: sqlite3.Connection) -> list[dict]` (satır 83): Varsayılan ML algoritma konumlandırmasını idempotent şekilde oluşturur.
    - `list_algorithm_registry(conn: sqlite3.Connection, usage_role: str | None=None) -> list[dict]` (satır 126): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_algorithm_config(conn: sqlite3.Connection, algorithm_key: str) -> MLAlgorithmConfig` (satır 151): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `update_algorithm_usage_role(conn: sqlite3.Connection, algorithm_key: str, *, usage_role: str | None=None, default_enabled: bool | None=None, min_training_samples: int | None=None, min_samples_per_class: int | None=None, notes: str | None=None) -> dict` (satır 175): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `is_algorithm_allowed_for_role(conn: sqlite3.Connection, algorithm_key: str, role: str) -> bool` (satır 214): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_normalize_algorithm_key(value: str) -> str` (satır 225): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `MLAlgorithmConfig` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/ml_confidence_service.py`
  - Fonksiyonlar:
    - `confidence_from_sample_size(sample_count: int, required_min_samples: int) -> tuple[float, list[str]]` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `confidence_from_validation_metrics(metrics: dict | None, task_type: str='classification') -> tuple[float, list[str]]` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `confidence_from_model_probability(probability: float | None) -> tuple[float, list[str]]` (satır 50): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `combine_confidence_signals(signals: list[tuple[float, list[str]]], *, readiness_level: str | None=None, overfit_warning: bool=False) -> ConfidenceResult` (satır 59): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `estimate_prediction_confidence(model, prediction, X_row, context: dict[str, Any]) -> ConfidenceResult` (satır 92): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_to_float(value: Any, default: float | None) -> float | None` (satır 118): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `ConfidenceResult` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/ml_evaluation_service.py`
  - Fonksiyonlar:
    - `evaluate_regression_model(model, X, y) -> EvaluationResult` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `evaluate_classification_model(model, X, y) -> EvaluationResult` (satır 63): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `run_cross_validation(model, X, y, *, task_type: str='classification', max_folds: int=5) -> dict` (satır 98): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `detect_overfitting(train_metrics: dict, validation_metrics: dict, *, metric_name: str='accuracy') -> dict` (satır 138): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_evaluation_report(result: EvaluationResult) -> dict` (satır 161): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_regression_metrics(y_true, y_pred) -> dict` (satır 165): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_classification_metrics(y_true, y_pred, y_proba=None) -> dict` (satır 177): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_metric(metrics: dict, name: str) -> float | None` (satır 197): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `EvaluationResult` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/ml_explainability_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json(value: Any) -> str` (satır 36): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_feature_importance(model, feature_names: list[str]) -> dict[str, float]` (satır 40): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_decision_path_if_tree(model, X_row, feature_names: list[str]) -> list[dict[str, Any]] | None` (satır 58): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `explain_model_prediction(model, X_row, feature_names: list[str], algorithm_key: str, *, readiness_level: str | None=None, sample_count: int | None=None) -> MLExplanation` (satır 86): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_human_readable_ml_explanation(*, algorithm_key: str, top_features: list[dict[str, Any]], limitations: list[str]) -> str` (satır 124): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `save_prediction_explanation(conn: sqlite3.Connection, prediction_id: int, explanation: MLExplanation) -> int` (satır 141): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_prediction_explanation(conn: sqlite3.Connection, prediction_id: int) -> dict | None` (satır 165): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `MLExplanation` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/ml_feature_pipeline.py`
  - Fonksiyonlar:
    - `get_feature_schema_version() -> str` (satır 60): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_now() -> str` (satır 64): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json(value: Any) -> str` (satır 68): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_table_exists(conn: sqlite3.Connection, table_name: str) -> bool` (satır 72): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_safe_float(value: Any, default: float=0.0) -> float` (satır 78): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `build_course_feature_dataset(conn: sqlite3.Connection, *, scope: dict | None=None, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None, save_snapshot: bool=False) -> MLFeatureDataset` (satır 88): Ders-yıl seviyesinde ML feature veri seti üretir.
    - `_load_raw_course_rows(conn: sqlite3.Connection, *, year: int | None, faculty_id: int | None, department_id: int | None) -> pd.DataFrame` (satır 147): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `normalize_features(raw_df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]` (satır 236): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `impute_missing_values(df: pd.DataFrame, strategy: str='median') -> tuple[pd.DataFrame, dict[str, Any]]` (satır 285): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `validate_feature_schema(df: pd.DataFrame) -> list[str]` (satır 303): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_missing_summary(df: pd.DataFrame) -> dict[str, Any]` (satır 314): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `save_feature_snapshot(conn: sqlite3.Connection, dataset: MLFeatureDataset, *, scope: dict | None=None, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None) -> int` (satır 325): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `extract_features_for_course(conn: sqlite3.Connection, course_id: int, year: int) -> dict` (satır 362): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `MLFeatureDataset` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/ml_model_registry_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json(value: Any) -> str` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_loads(value: Any, default: Any) -> Any` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_model_run(conn: sqlite3.Connection, *, algorithm_key: str, model_name: str, model_type: str, usage_role: str, model_version: str, feature_schema_version: str, training_sample_count: int, target_column: str | None=None, training_scope: dict | None=None, class_distribution: dict | None=None, parameters: dict | None=None, readiness_level: str | None=None, readiness_warnings: list | None=None, status: str='created', created_by: str | None=None, notes: str | None=None) -> int` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `mark_trained(conn: sqlite3.Connection, run_id: int, *, train_metrics: dict | None=None, validation_metrics: dict | None=None, cross_validation: dict | None=None, overfitting_report: dict | None=None, artifact_path: str | None=None) -> dict` (satır 86): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `mark_skipped(conn: sqlite3.Connection, run_id: int, reason: str) -> dict` (satır 122): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `mark_failed(conn: sqlite3.Connection, run_id: int, reason: str) -> dict` (satır 130): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `deprecate_model_run(conn: sqlite3.Connection, run_id: int, reason: str | None=None) -> dict` (satır 138): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_latest_model_run(conn: sqlite3.Connection, algorithm_key: str, trained_only: bool=False) -> dict | None` (satır 146): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_model_run(conn: sqlite3.Connection, run_id: int) -> dict | None` (satır 159): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_model_runs(conn: sqlite3.Connection, *, algorithm_key: str | None=None, status: str | None=None, limit: int=100) -> list[dict]` (satır 167): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_dict(row: sqlite3.Row | tuple, keys: list[str]) -> dict` (satır 191): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/ml_prediction_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json(value: Any) -> str` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `predict_course(conn: sqlite3.Connection, *, algorithm_key: str, course_id: int, year: int, faculty_id: int | None=None, department_id: int | None=None, prediction_type: str='status') -> dict` (satır 35): Tek ders için destekleyici ML tahmini üretir ve ml_predictions tablosuna yazar.
    - `predict_batch(conn: sqlite3.Connection, *, algorithm_key: str, course_ids: list[int], year: int, faculty_id: int | None=None, department_id: int | None=None) -> list[dict]` (satır 192): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `fallback_prediction(conn: sqlite3.Connection, *, algorithm_key: str, course_id: int, year: int, faculty_id: int | None=None, department_id: int | None=None, prediction_type: str='status', fallback_method: str='no_prediction', fallback_reason: str='Model readiness koşulları sağlanmadı.') -> dict` (satır 214): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `save_prediction(conn: sqlite3.Connection, *, model_run_id: int | None, algorithm_key: str, course_id: int, year: int, faculty_id: int | None, department_id: int | None, prediction_type: str, predicted_value_text: str | None, predicted_value_numeric: float | None, confidence_score: float | None, confidence_level: str | None, uncertainty_reasons: list[str] | None, fallback_used: bool, fallback_method: str | None=None, fallback_reason: str | None=None, advisory_only: bool=True, should_influence_decision: bool=False, explanation: str | None=None) -> int` (satır 255): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_prediction(conn: sqlite3.Connection, prediction_id: int) -> dict` (satır 315): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_predictions(conn: sqlite3.Connection, *, course_id: int | None=None, algorithm_key: str | None=None, limit: int=100) -> list[dict]` (satır 324): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_predictions_for_course(conn: sqlite3.Connection, course_id: int, year: int | None=None) -> list[dict]` (satır 348): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_build_model(algorithm_key: str)` (satır 361): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_dataset_missing_ratio(dataset) -> float` (satır 379): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fallback_value(conn: sqlite3.Connection, course_id: int, year: int, method: str) -> tuple[str | None, float | None]` (satır 387): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_prediction_row(row: sqlite3.Row | tuple, keys: list[str]) -> dict` (satır 424): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/ml_readiness_report_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json(value: Any) -> str` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_ml_readiness_report(conn: sqlite3.Connection, *, scope: dict | None=None, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None, save: bool=True) -> dict` (satır 25): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_algorithm_readiness_table(conn: sqlite3.Connection, *, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None, algorithm_key: str | None=None) -> list[dict]` (satır 65): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `estimate_required_additional_samples(readiness_rows: list[dict]) -> list[dict]` (satır 78): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `save_readiness_report(conn: sqlite3.Connection, report: dict) -> int` (satır 90): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_readiness_reports(conn: sqlite3.Connection, limit: int=100) -> list[dict]` (satır 117): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_readiness_report(conn: sqlite3.Connection, report_id: int) -> dict | None` (satır 125): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_summary(sample_count: int, rows: list[dict], recommendations: list[dict]) -> str` (satır 133): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_report_row(row: sqlite3.Row | tuple, keys: list[str]) -> dict` (satır 143): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/ml_readiness_service.py`
  - Fonksiyonlar:
    - `_as_dataframe(dataset: Any) -> pd.DataFrame` (satır 42): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_class_distribution(y: Any) -> dict[str, int]` (satır 56): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_sample_requirements(conn: sqlite3.Connection, algorithm_key: str) -> dict` (satır 63): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `check_model_readiness(conn: sqlite3.Connection, algorithm_key: str, dataset: Any, target_column: str | None=None) -> MLReadinessResult` (satır 73): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_readiness_report(conn: sqlite3.Connection, dataset: Any, *, target_column: str | None=None, algorithm_key: str | None=None) -> dict` (satır 159): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_summary_text(sample_count: int, rows: list[dict]) -> str` (satır 180): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `MLReadinessResult` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/ml_training_service.py`
  - Fonksiyonlar:
    - `train_model_run(conn: sqlite3.Connection, *, algorithm_key: str, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None, created_by: str | None=None) -> dict` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_build_model(algorithm_key: str)` (satır 80): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/model_diagnostics_service.py`
  - Fonksiyonlar:
    - `detect_overfitting(train_metrics: dict[str, float], validation_metrics: dict[str, float], task_type: str) -> dict[str, Any]` (satır 10): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `detect_class_imbalance(y: Iterable[Any], threshold: float=0.2) -> dict[str, Any]` (satır 30): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `detect_high_variance_across_folds(fold_metrics: list[dict[str, Any]], metric_name: str | None=None, threshold: float=0.1) -> dict[str, Any]` (satır 46): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_model_diagnostics(*, algorithm_key: str, task_type: str, train_metrics: dict[str, float] | None=None, validation_metrics: dict[str, float] | None=None, y: Iterable[Any] | None=None, fold_metrics: list[dict[str, Any]] | None=None) -> dict[str, Any]` (satır 65): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_primary_metric(task_type: str, train: dict[str, Any], valid: dict[str, Any]) -> str | None` (satır 97): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_std(values: list[float]) -> float` (satır 104): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/permission_service.py`
  - Fonksiyonlar:
    - `get_permission_service() -> PermissionService` (satır 100): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `require_action(action: str)` (satır 105): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `PermissionService` (satır 61): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, config: AppConfig)` (satır 62): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `has_permission(self, user: UserContext, action: str) -> bool` (satır 65): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `can_access_faculty(self, user: UserContext, faculty_id: int) -> bool` (satır 79): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `can_access_department(self, user: UserContext, department_id: int) -> bool` (satır 84): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `require_permission(self, user: UserContext, action: str)` (satır 93): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/pool_state_machine_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 41): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json(data: Any) -> str` (satır 45): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_load_json(raw: str | None, default: Any=None) -> Any` (satır 49): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_bool(value: Any) -> bool` (satır 58): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_int(value: Any, default: int=0) -> int` (satır 64): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_float(value: Any, default: float | None=None) -> float | None` (satır 73): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_score100(value: Any) -> float | None` (satır 82): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_confidence01(value: Any) -> float | None` (satır 91): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None=None) -> dict[str, Any] | None` (satır 100): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_all_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]` (satır 110): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_one_dict(cur: sqlite3.Cursor) -> dict[str, Any] | None` (satır 115): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_table_columns(conn: sqlite3.Connection, table: str) -> set[str]` (satır 120): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_status_label(status: int | None) -> str` (satır 126): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_lifecycle_for_status(status: int, *, protected: bool=False) -> str` (satır 133): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_is_required_course_type(value: str | None) -> bool` (satır 147): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_is_service_course_type(value: str | None) -> bool` (satır 152): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_course_metadata(conn: sqlite3.Connection, course_id: int) -> dict[str, Any]` (satır 157): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_governance_flags(conn: sqlite3.Connection, course_id: int) -> dict[str, Any]` (satır 172): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `upsert_governance_flags(conn: sqlite3.Connection, course_id: int, **fields) -> dict[str, Any]` (satır 203): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_active_override(conn: sqlite3.Connection, course_id: int, year: int, semester: str | None=None) -> dict[str, Any] | None` (satır 246): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_course_state_override(conn: sqlite3.Connection, course_id: int, year: int, overridden_final_status: int, reason: str, semester: str | None=None, recommended_status: int | None=None, requested_by: str | None=None, approved_by: str | None=None, expires_at: str | None=None, transition_id: int | None=None) -> dict[str, Any]` (satır 274): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_overrides(conn: sqlite3.Connection, year: int | None=None, course_id: int | None=None, active_only: bool=False) -> list[dict[str, Any]]` (satır 318): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_is_protected(flags: dict[str, Any], policy: dict[str, Any], year: int) -> tuple[bool, list[str]]` (satır 352): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_in_grace_period(flags: dict[str, Any], policy: dict[str, Any], year: int) -> tuple[bool, list[str]]` (satır 370): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `evaluate_course_state_transition(conn: sqlite3.Connection, context: dict[str, Any]) -> dict[str, Any]` (satır 390): Tek ders icin cok faktorlü havuz state transition sonucu üretir.
    - `_approval_type_for_result(result: dict[str, Any]) -> str` (satır 701): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ensure_pending_approval(conn: sqlite3.Connection, result: dict[str, Any], transition_id: int | None=None) -> dict[str, Any]` (satır 709): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `save_state_transition(conn: sqlite3.Connection, result: dict[str, Any], *, trigger: str | None=None, created_by: str | None=None, decision_run_id: int | None=None) -> int` (satır 771): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `update_havuz_lifecycle(conn: sqlite3.Connection, result: dict[str, Any], transition_id: int | None=None) -> int` (satır 837): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `approve_state_approval(conn: sqlite3.Connection, approval_id: int, reviewed_by: str | None=None, review_note: str | None=None) -> dict[str, Any]` (satır 873): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `reject_state_approval(conn: sqlite3.Connection, approval_id: int, reviewed_by: str | None=None, review_note: str | None=None) -> dict[str, Any]` (satır 918): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_state_transitions(conn: sqlite3.Connection, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None, course_id: int | None=None, status: int | None=None, approval_status: str | None=None, limit: int=500) -> list[dict[str, Any]]` (satır 949): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_course_state_history(conn: sqlite3.Connection, course_id: int) -> list[dict[str, Any]]` (satır 1006): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_pending_approvals(conn: sqlite3.Connection, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None, status: str | None='pending') -> list[dict[str, Any]]` (satır 1010): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_pool_lifecycle_summary(conn: sqlite3.Connection, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> dict[str, Any]` (satır 1046): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_reactivation_candidates(conn: sqlite3.Connection, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None) -> list[dict[str, Any]]` (satır 1105): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_protected_courses(conn: sqlite3.Connection, faculty_id: int | None=None, department_id: int | None=None) -> list[dict[str, Any]]` (satır 1115): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `evaluate_scope_transitions(conn: sqlite3.Connection, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None, save: bool=False) -> list[dict[str, Any]]` (satır 1150): Mevcut havuz satırları üzerinden kapsam bazlı güvenli değerlendirme yapar.

### `app/services/pool_state_policy_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `normalize_semester(value: str | None) -> str | None` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_bool(value: Any) -> bool` (satır 41): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None=None) -> dict[str, Any] | None` (satır 47): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_policy(conn: sqlite3.Connection, policy_id: int) -> dict[str, Any] | None` (satır 60): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_default_policy(conn: sqlite3.Connection) -> dict[str, Any]` (satır 67): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_pool_state_policy(conn: sqlite3.Connection, name: str, scope_type: str='global', faculty_id: int | None=None, department_id: int | None=None, year: int | None=None, semester: str | None=None, activate: bool=True, notes: str | None=None, **values) -> dict[str, Any]` (satır 111): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `resolve_policy(conn: sqlite3.Connection, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> dict[str, Any]` (satır 228): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_pool_state_policies(conn: sqlite3.Connection) -> list[dict[str, Any]]` (satır 272): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `activate_pool_state_policy(conn: sqlite3.Connection, policy_id: int) -> dict[str, Any]` (satır 279): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `validate_policy(policy: dict[str, Any]) -> dict[str, Any]` (satır 301): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/pool_state_validation_service.py`
  - Fonksiyonlar:
    - `validate_pool_transition_context(context: dict) -> ValidationResult` (satır 10): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/prerequisite_planning_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None=None) -> dict[str, Any] | None` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_all_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_prerequisite(conn: sqlite3.Connection, course_id: int, prerequisite_course_id: int, prerequisite_type: str='hard', relation_note: str | None=None) -> dict[str, Any]` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_prerequisites(conn: sqlite3.Connection, course_id: int | None=None) -> list[dict[str, Any]]` (satır 56): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `check_prerequisite_order(assignments: list[dict[str, Any]], prerequisites: list[dict[str, Any]] | None=None) -> list[dict[str, Any]]` (satır 68): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_prerequisite_penalty(assignments: list[dict[str, Any]], prerequisites: list[dict[str, Any]]) -> float` (satır 96): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `explain_prerequisite_decision(course_id: int, semester: str, prerequisites: list[dict[str, Any]]) -> str | None` (satır 101): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/report_table_service.py`
  - Sınıflar:
    - `ReportTableService` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, conn: sqlite3.Connection)` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `list_tables(self) -> ServiceResult` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `table_head(self, table: str, limit: int=1000) -> ServiceResult` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `statement_type(query: str) -> str` (satır 26): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `is_dangerous_sql(cls, query: str) -> bool` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_audit_sql_console(self, *, query: str, statement_type: str, success: bool, user_id: str | None=None, error_message: str | None=None, row_count: int | None=None) -> None` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run_admin_sql(self, query: str, params: tuple[Any, ...]=(), *, user_id: str | None=None) -> ServiceResult` (satır 58): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/reporting.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/services/reporting_service.py`
  - Fonksiyonlar:
    - `normalize_term(term: str | None) -> str` (satır 51): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `term_key(term: str | None) -> str` (satır 58): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `status_label(status: int | None) -> str` (satır 62): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_conn_from_db(db)` (satır 73): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]` (satır 77): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ensure_score_source_schema(db) -> None` (satır 86): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_persist_score_source(db, year: int, term: str, score_map: dict[int, float]) -> None` (satır 93): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ensure_report_scores(db, faculty_id: int, year: int, term: str) -> dict[str, Any]` (satır 128): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `fetch_curriculum_course_ids(db, faculty_id: int, year: int, term: str) -> set[int]` (satır 182): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_score_source_map(db, year: int, term: str) -> dict[int, float]` (satır 198): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_pool_rows(db, faculty_id: int, year: int, term: str)` (satır 216): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `build_report_snapshot(db, faculty_id: int, faculty_name: str, year: int, term: str, department_name: str | None=None) -> dict[str, Any]` (satır 255): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_import_history(conn: sqlite3.Connection, filters: dict[str, Any] | None=None) -> list[dict[str, Any]]` (satır 418): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_import_quality_summary(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any]` (satır 432): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_import_diff_summary(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any] | None` (satır 437): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_import_impact_summary(conn: sqlite3.Connection, import_batch_id: int) -> dict[str, Any] | None` (satır 442): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_import_issues(conn: sqlite3.Connection, import_batch_id: int) -> str` (satır 447): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_import_audit_report(conn: sqlite3.Connection, import_batch_id: int, format: str='csv') -> str` (satır 467): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_criteria_completion_report(conn: sqlite3.Connection, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> dict[str, Any]` (satır 498): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_criteria_completion_matrix_report(conn: sqlite3.Connection, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> list[dict[str, Any]]` (satır 538): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_criteria_validation_report(conn: sqlite3.Connection, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> list[dict[str, Any]]` (satır 558): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_missing_data_risk_report(conn: sqlite3.Connection, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> dict[str, Any] | None` (satır 578): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_csv_from_dicts(rows: list[dict[str, Any]], fieldnames: list[str]) -> str` (satır 609): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_criteria_completion_matrix(conn: sqlite3.Connection, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None, format: str='csv') -> str` (satır 618): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_validation_issues(conn: sqlite3.Connection, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None, format: str='csv') -> str` (satır 645): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_completion_tasks(conn: sqlite3.Connection, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None, status: str | None=None, format: str='csv') -> str` (satır 660): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_pool_lifecycle_summary(conn: sqlite3.Connection, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> dict[str, Any]` (satır 690): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_course_state_history(conn: sqlite3.Connection, course_id: int) -> list[dict[str, Any]]` (satır 707): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_pending_approvals(conn: sqlite3.Connection, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None) -> list[dict[str, Any]]` (satır 712): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_reactivation_candidates(conn: sqlite3.Connection, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None) -> list[dict[str, Any]]` (satır 728): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_protected_courses(conn: sqlite3.Connection, faculty_id: int | None=None, department_id: int | None=None) -> list[dict[str, Any]]` (satır 738): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_pool_lifecycle_report(conn: sqlite3.Connection, year: int, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None, format: str='csv') -> str` (satır 747): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_state_transition_history(conn: sqlite3.Connection, course_id: int | None=None, year: int | None=None, format: str='csv') -> str` (satır 788): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_ahp_profile_report(conn: sqlite3.Connection, profile_id: int) -> dict[str, Any]` (satır 821): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_active_ahp_profile_summary(conn: sqlite3.Connection, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None, semester: str | None=None) -> dict[str, Any]` (satır 828): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_decision_run_ahp_summary(conn: sqlite3.Connection, run_id: int) -> dict[str, Any]` (satır 841): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_ahp_profile_matrix(conn: sqlite3.Connection, profile_id: int, format: str='csv') -> str` (satır 848): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_ahp_sensitivity_report(conn: sqlite3.Connection, run_id: int, format: str='csv') -> str` (satır 855): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `compare_ahp_profiles(conn: sqlite3.Connection, profile_a_id: int, profile_b_id: int) -> dict[str, Any]` (satır 862): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_semester_plan_summary(conn: sqlite3.Connection, run_id: int) -> dict[str, Any]` (satır 869): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_semester_plan_assignments(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]` (satır 876): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_semester_plan_constraint_violations(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]` (satır 883): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `compare_semester_plan_scenarios(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]` (satır 890): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_semester_plan(conn: sqlite3.Connection, run_id: int, format: str='csv') -> str` (satır 897): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_semester_plan_constraint_violations(conn: sqlite3.Connection, run_id: int, format: str='csv') -> str` (satır 904): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_human_readable_semester_plan_report(conn: sqlite3.Connection, run_id: int) -> str` (satır 911): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/resource_planning_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None=None) -> dict[str, Any] | None` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_all_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]` (satır 26): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_resource(conn: sqlite3.Connection, resource_name: str, resource_type: str, faculty_id: int | None=None, department_id: int | None=None, capacity: int | None=None, available_fall: bool=True, available_spring: bool=True, notes: str | None=None) -> dict[str, Any]` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_resources(conn: sqlite3.Connection, resource_type: str | None=None) -> list[dict[str, Any]]` (satır 59): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_resource_requirement(conn: sqlite3.Connection, course_id: int, resource_type: str, required_capacity: int | None=None, required_hours: float | None=None, hard_requirement: bool=True, notes: str | None=None) -> dict[str, Any]` (satır 71): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_resource_requirements(conn: sqlite3.Connection, course_id: int | None=None) -> list[dict[str, Any]]` (satır 95): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_course_resource_requirements(conn: sqlite3.Connection, course_id: int) -> list[dict[str, Any]]` (satır 107): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_resource_capacity_for_type(conn: sqlite3.Connection, resource_type: str, year: int, semester: str) -> tuple[int, float]` (satır 111): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `check_resource_feasibility(conn: sqlite3.Connection, course_id: int, year: int, semester: str, usage: dict[tuple[str, str], dict[str, float]] | None=None) -> dict[str, Any]` (satır 137): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_resource_usage(assignments: list[dict[str, Any]]) -> dict[str, Any]` (satır 167): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `find_resource_conflicts(plan: list[dict[str, Any]]) -> list[dict[str, Any]]` (satır 176): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/rules_engine.py`
  - Fonksiyonlar:
    - `is_course_eligible_for_student(ogrenci_id: int, ders_id: int, secilen_dersler: list, db, yil: int=None) -> tuple` (satır 9): Öğrencinin bir dersi alıp alamayacağını kurallara göre kontrol eder.
    - `_get_ders_saatleri(db, ders_id: int) -> list` (satır 86): Dersin gün ve saat bilgilerini getirir.

### `app/services/schema_health_service.py`
  - Fonksiyonlar:
    - `_unwrap_sqlite_connection(conn: Any) -> Any` (satır 39): SQLAlchemy raw connection proxy nesnelerinden gerçek sqlite bağlantısını al.
    - `_managed_connection(conn: sqlite3.Connection | Any | None, db_path: str | None, config: AppConfig | None=None) -> Iterator[Any]` (satır 54): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_table_names(conn: Any) -> set[str]` (satır 77): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_column_names(conn: Any, table_name: str) -> set[str]` (satır 85): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `check_required_tables(conn: sqlite3.Connection) -> dict[str, Any]` (satır 95): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `check_required_columns(conn: sqlite3.Connection) -> dict[str, Any]` (satır 101): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `check_alembic_version(conn: Any) -> dict[str, Any]` (satır 115): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `check_schema_compat_status(conn: sqlite3.Connection, config: AppConfig | None=None) -> dict[str, Any]` (satır 130): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `compare_models_to_database(conn: sqlite3.Connection) -> dict[str, Any]` (satır 166): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `check_schema_health(conn: sqlite3.Connection | None=None, db_path: str | None=None, config: AppConfig | None=None) -> dict[str, Any]` (satır 177): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_schema_health_report(conn: sqlite3.Connection | None=None, db_path: str | None=None, config: AppConfig | None=None) -> str` (satır 212): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/secure_import_service.py`
  - Sınıflar:
    - `SecureImportService` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, db: Session, config: AppConfig, upload_security: FileUploadSecurityService, audit_service: SecurityAuditService)` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `async create_import_job(self, import_type: str, file: UploadFile, user: UserContext, faculty_id: int=None, year: int=None) -> SecureImportJob` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `validate_import_job(self, job_id: str, summary_data: dict, rows: list) -> SecureImportJob` (satır 58): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `approve_import_job(self, job_id: str, user: UserContext) -> SecureImportJob` (satır 80): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `mark_applied(self, job_id: str, user: UserContext) -> SecureImportJob` (satır 106): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/security_audit_service.py`
  - Sınıflar:
    - `SecurityAuditService` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, db: Session, config: AppConfig)` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `log_event(self, event_type: str, actor_type: str, action: str, message: str, actor_id: Optional[str]=None, role: Optional[str]=None, faculty_id: Optional[int]=None, department_id: Optional[int]=None, resource_type: Optional[str]=None, resource_id: Optional[str]=None, success: bool=True, severity: str='info', before_data: Optional[Dict[str, Any]]=None, after_data: Optional[Dict[str, Any]]=None, metadata: Optional[Dict[str, Any]]=None, request_id: Optional[str]=None, ip_address: Optional[str]=None, user_agent: Optional[str]=None) -> SecurityAuditLog` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `verify_audit_chain(self) -> Dict[str, Any]` (satır 76): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_recent_logs(self, limit: int=100) -> List[SecurityAuditLog]` (satır 100): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/security_health_service.py`
  - Sınıflar:
    - `SecurityHealthService` (satır 5): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, config: AppConfig)` (satır 6): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `check_security_configuration(self) -> Dict[str, Any]` (satır 9): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/semester_balance_metrics_service.py`
  - Fonksiyonlar:
    - `_float(value: Any, default: float=0.0) -> float` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `estimate_course_demand(conn: sqlite3.Connection, course_id: int, year: int) -> float` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `estimate_course_capacity(conn: sqlite3.Connection, course_id: int, year: int) -> float` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_semester_balance_metrics(plan: list[dict[str, Any]]) -> dict[str, Any]` (satır 57): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_plan_score(plan: list[dict[str, Any]], policy: dict[str, Any]) -> float` (satır 81): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_balance_warnings(metrics: dict[str, Any], policy: dict[str, Any]) -> list[str]` (satır 105): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/semester_planning_engine.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json(data: Any) -> str` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_load_json(raw: str | None, default: Any=None) -> Any` (satır 42): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_float(value: Any, default: float=0.0) -> float` (satır 51): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None=None) -> dict[str, Any] | None` (satır 60): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_all_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]` (satır 68): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_table_columns(conn: sqlite3.Connection, table: str) -> set[str]` (satır 73): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_course_name_map(conn: sqlite3.Connection, course_ids: list[int]) -> dict[int, dict[str, Any]]` (satır 82): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_candidate_courses(conn: sqlite3.Connection, year: int, faculty_id: int | None=None, department_id: int | None=None) -> list[dict[str, Any]]` (satır 106): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_latest_scores(conn: sqlite3.Connection, year: int) -> dict[int, float]` (satır 152): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_existing_tables(conn: sqlite3.Connection) -> set[str]` (satır 178): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_prepare_candidates(conn: sqlite3.Connection, year: int, candidate_courses: list[Any] | None, faculty_id: int | None, department_id: int | None) -> list[dict[str, Any]]` (satır 184): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_semester_allowed(candidate: dict[str, Any], semester: str) -> bool` (satır 221): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_semester_capacity(assignments: list[dict[str, Any]], semester: str) -> int` (satır 226): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_choose_semester(candidate: dict[str, Any], assignments: list[dict[str, Any]], policy: dict[str, Any], scenario_type: str) -> list[str]` (satır 230): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_can_repeat(course_id: int, candidate: dict[str, Any], assignments: list[dict[str, Any]], policy: dict[str, Any]) -> tuple[bool, str | None]` (satır 244): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fits_semester_counts(assignments: list[dict[str, Any]], semester: str, policy: dict[str, Any]) -> bool` (satır 261): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_assignment_explanation(candidate: dict[str, Any], semester: str, extra: list[str] | None=None) -> str` (satır 266): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_semester_plan(conn: sqlite3.Connection, year: int, faculty_id: int | None=None, department_id: int | None=None, candidate_courses: list[Any] | None=None, policy: dict[str, Any] | None=None, curriculum_year: int | None=None, persist: bool=True, run_name: str | None=None, created_by: str | None=None, scenario_type: str='score_priority', generate_alternatives: bool=True) -> dict[str, Any]` (satır 279): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_repair_prerequisites(assignments: list[dict[str, Any]], violations: list[dict[str, Any]], policy: dict[str, Any]) -> None` (satır 487): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_persist_plan(conn: sqlite3.Connection, *, year: int, faculty_id: int | None, department_id: int | None, policy: dict[str, Any], candidates: list[dict[str, Any]], assignments: list[dict[str, Any]], violations: list[dict[str, Any]], metrics: dict[str, Any], warnings: list[str], plan_score: float, run_name: str | None, created_by: str | None) -> int` (satır 502): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_build_alternative_scenarios(conn: sqlite3.Connection, year: int, faculty_id: int | None, department_id: int | None, candidates: list[dict[str, Any]], policy: dict[str, Any], run_id: int | None) -> list[dict[str, Any]]` (satır 592): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_persist_scenarios(conn: sqlite3.Connection, run_id: int, scenarios: list[dict[str, Any]]) -> None` (satır 634): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_plan_run(conn: sqlite3.Connection, run_id: int) -> dict[str, Any] | None` (satır 662): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_plan_runs(conn: sqlite3.Connection, year: int | None=None, faculty_id: int | None=None, department_id: int | None=None) -> list[dict[str, Any]]` (satır 674): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/semester_planning_policy_service.py`
  - Fonksiyonlar:
    - `_now() -> str` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_bool(value: Any) -> bool` (satır 42): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json(data: Any) -> str` (satır 48): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_load_json(raw: str | None, default: Any=None) -> Any` (satır 52): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None=None) -> dict[str, Any] | None` (satır 61): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_one_dict(cur: sqlite3.Cursor) -> dict[str, Any] | None` (satır 76): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_all_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]` (satır 81): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `normalize_soft_weights(weights: dict[str, Any] | None) -> dict[str, float]` (satır 86): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `validate_policy(policy: dict[str, Any]) -> dict[str, Any]` (satır 97): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_policy(conn: sqlite3.Connection, policy_id: int) -> dict[str, Any] | None` (satır 125): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `seed_default_policy(conn: sqlite3.Connection) -> dict[str, Any]` (satır 132): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `create_policy(conn: sqlite3.Connection, name: str, scope_type: str='global', faculty_id: int | None=None, department_id: int | None=None, year: int | None=None, curriculum_year: int | None=None, activate: bool=True, notes: str | None=None, **values) -> dict[str, Any]` (satır 172): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_deactivate_same_scope(conn: sqlite3.Connection, scope_type: str, faculty_id: int | None, department_id: int | None, year: int | None, curriculum_year: int | None) -> None` (satır 271): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `update_policy(conn: sqlite3.Connection, policy_id: int, **values) -> dict[str, Any]` (satır 299): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `activate_policy(conn: sqlite3.Connection, policy_id: int) -> dict[str, Any]` (satır 352): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `list_policies(conn: sqlite3.Connection, scope_type: str | None=None, faculty_id: int | None=None, department_id: int | None=None, year: int | None=None, active_only: bool=False) -> list[dict[str, Any]]` (satır 374): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `resolve_policy(conn: sqlite3.Connection, year: int, faculty_id: int | None=None, department_id: int | None=None, curriculum_year: int | None=None) -> dict[str, Any]` (satır 408): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/semester_planning_reporting_service.py`
  - Fonksiyonlar:
    - `_load_json(raw: str | None, default: Any=None) -> Any` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None=None) -> dict[str, Any] | None` (satır 25): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_fetch_all_dicts(cur: sqlite3.Cursor) -> list[dict[str, Any]]` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_csv_from_dicts(rows: list[dict[str, Any]], columns: list[str]) -> str` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_semester_plan_summary(conn: sqlite3.Connection, run_id: int) -> dict[str, Any]` (satır 47): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_semester_plan_assignments(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]` (satır 61): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_constraint_violations(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]` (satır 78): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `compare_plan_scenarios(conn: sqlite3.Connection, run_id: int) -> list[dict[str, Any]]` (satır 94): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_semester_plan(conn: sqlite3.Connection, run_id: int, format: str='csv') -> str` (satır 108): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `export_constraint_violations(conn: sqlite3.Connection, run_id: int, format: str='csv') -> str` (satır 128): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_human_readable_plan_report(conn: sqlite3.Connection, run_id: int) -> str` (satır 133): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/semester_workload_service.py`
  - Fonksiyonlar:
    - `_row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None=None) -> dict[str, Any] | None` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_required_course_load(conn: sqlite3.Connection, department_id: int, year: int, semester: str) -> dict[str, Any] | None` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_semester_workload(plan: list[dict[str, Any]]) -> dict[str, Any]` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `adjust_targets_by_required_load(policy: dict[str, Any], required_loads: dict[str, dict[str, Any]] | None=None) -> tuple[dict[str, Any], list[str]]` (satır 48): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `explain_workload_effect(policy: dict[str, Any], adjusted_policy: dict[str, Any]) -> str` (satır 61): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/sensitivity_analysis_service.py`
  - Fonksiyonlar:
    - `_json_dump(value: Any) -> str` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_thresholds(policy: dict[str, Any]) -> list[tuple[str, float]]` (satır 17): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `analyze_decision_sensitivity(score: float, policy: dict[str, Any], weights: dict[str, float] | None=None, raw_values: dict[str, float] | None=None) -> dict[str, Any]` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `save_sensitivity_result(cur: sqlite3.Cursor, decision_run_id: int, course_id: int, sensitivity: dict[str, Any]) -> int` (satır 98): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/service_factory.py`
  - Fonksiyonlar:
    - `get_service_factory(conn: sqlite3.Connection | None=None, db_path: str | None=None, config: AppConfig | None=None) -> ServiceFactory` (satır 36): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_course_service(conn: sqlite3.Connection | None=None, db_path: str | None=None) -> CourseService` (satır 40): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_criteria_service(conn: sqlite3.Connection | None=None, db_path: str | None=None) -> CriteriaService` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_reporting_service(conn: sqlite3.Connection | None=None, db_path: str | None=None) -> ReportTableService` (satır 48): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_system_service(conn: sqlite3.Connection | None=None, db_path: str | None=None, config: AppConfig | None=None) -> SystemService` (satır 52): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_curriculum_service(*args, **kwargs)` (satır 56): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_pool_service(*args, **kwargs)` (satır 60): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_decision_service(*args, **kwargs)` (satır 64): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_import_service(*args, **kwargs)` (satır 68): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `ServiceFactory` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, conn: sqlite3.Connection | None=None, db_path: str | None=None, config: AppConfig | None=None)` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_course_service(self) -> CourseService` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_criteria_service(self) -> CriteriaService` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_reporting_table_service(self) -> ReportTableService` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_system_service(self) -> SystemService` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/similarity.py`
  - Sınıflar:
    - `SimilarityEngine` (satır 25): SQLAlchemy ORM tabanli ders benzerlik hesaplama motoru.
      - `__init__(self, db_session: Session)` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_related_courses(self, target_course_id, top_n=10)` (satır 31): TF-IDF ve Cosine Similarity kullanarak benzer dersleri bulur.

### `app/services/similarity_engine.py`
  - Sınıflar:
    - `SimilarityEngine` (satır 22): sqlite3 tabanli ders benzerlik hesaplama motoru.
      - `__init__(self, db_path: str)` (satır 25): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_get_connection(self)` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `load_courses(self)` (satır 31): Veritabanindan bilgi alani dolu tum dersleri DataFrame olarak doner.
      - `compute_similarity(self)` (satır 47): Tum dersler icin TF-IDF matrisi olusturur ve cosine similarity hesaplar.
      - `get_similar_courses(self, target_ders_id: int, top_n: int=10)` (satır 66): Verilen ders icin en benzer top_n dersi skor ile doner.
      - `compute_and_save(self, target_ders_id: int, top_n: int=10)` (satır 88): Benzerlikleri hesaplayip ders_iliski tablosuna kaydeder.

### `app/services/sql_console_service.py`
  - Sınıflar:
    - `SqlConsoleService` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, db: Session, config: AppConfig, audit_service: SecurityAuditService)` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `is_sql_console_enabled(self, user: UserContext) -> bool` (satır 25): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `is_dangerous_sql(self, sql_text: str) -> bool` (satır 37): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `is_read_only_sql(self, sql_text: str) -> bool` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `execute_sql(self, sql_text: str, user: UserContext, skip_dangerous_check: bool=False) -> Dict[str, Any]` (satır 47): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_log_audit(self, user: UserContext, sql_text: str, dangerous: bool=False, read_only: bool=True, success: bool=False, allowed: bool=False, error_msg: str=None, row_count: int=None)` (satır 95): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/statistical_comparison_service.py`
  - Fonksiyonlar:
    - `bootstrap_confidence_interval(values: Iterable[float], confidence: float=0.95, n_bootstrap: int=1000) -> dict[str, Any]` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `compare_two_models(metric_values_a: Iterable[float], metric_values_b: Iterable[float], test_type: str='auto') -> dict[str, Any]` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `compare_classifiers_mcnemar(y_true: Iterable[Any], pred_a: Iterable[Any], pred_b: Iterable[Any]) -> dict[str, Any]` (satır 73): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `wilcoxon_signed_rank(values_a: Iterable[float], values_b: Iterable[float]) -> dict[str, Any]` (satır 98): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `paired_t_test(values_a: Iterable[float], values_b: Iterable[float]) -> dict[str, Any]` (satır 102): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `friedman_test(results_matrix: list[list[float]]) -> dict[str, Any]` (satır 106): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `nemenyi_posthoc_if_available(results_matrix: list[list[float]]) -> dict[str, Any]` (satır 118): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_effect_size(values_a: Iterable[float], values_b: Iterable[float]) -> float` (satır 122): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_statistical_summary(comparison: dict[str, Any]) -> str` (satır 134): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_comparison_summary(a: list[float], b: list[float], p_value: float | None, significant: bool) -> str` (satır 138): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/survey_import_service.py`
  - Fonksiyonlar:
    - `_now_utc() -> str` (satır 71): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_normalize_text(value: str | None) -> str` (satır 75): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_find_col(columns: list[str], *candidates) -> str | None` (satır 79): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_parse_year(value: Any) -> int | None` (satır 88): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_safe_int(value: Any, default: int | None=None) -> int | None` (satır 106): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_clean_text(value: Any) -> str | None` (satır 115): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_excel_column_letter(index_1_based: int) -> str` (satır 122): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_is_summary_row(ders_kodu: str | None, ders_adi: str | None) -> bool` (satır 133): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_read_meta_sheet(xls: pd.ExcelFile) -> dict[str, Any]` (satır 140): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `parse_survey_excel(excel_path: str) -> dict[str, Any]` (satır 157): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `validate_survey_rows(rows: list[SurveyRow], faculty_name: str | None=None, year: int | None=None, declared_total_participants: int | None=None) -> dict[str, Any]` (satır 250): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `compute_total_participants(rows: list[SurveyImportRowResult] | list[SurveyRow]) -> int` (satır 303): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `match_courses(conn: sqlite3.Connection, rows: list[SurveyRow], faculty_id: int, year: int) -> dict[str, Any]` (satır 307): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_resolve_faculty_name(cur: sqlite3.Cursor, faculty_id: int) -> str | None` (satır 370): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_table_exists(cur: sqlite3.Cursor, table_name: str) -> bool` (satır 376): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_load_template_courses(cur: sqlite3.Cursor, faculty_id: int, year: int) -> list[dict[str, Any]]` (satır 384): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `load_survey_template_context(db_path: str, faculty_id: int, year: int) -> dict[str, Any]` (satır 432): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_get_faculty_year_course_scope(cur: sqlite3.Cursor, faculty_id: int, year: int) -> set[int]` (satır 463): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `replace_existing_survey_data(conn: sqlite3.Connection, faculty_id: int, year: int, scope_course_ids: set[int] | None=None) -> dict[str, int]` (satır 514): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `apply_survey_to_criteria(conn: sqlite3.Connection, faculty_id: int, year: int, rows: list[SurveyImportRowResult], source_filename: str | None=None, template_version: str=SURVEY_TEMPLATE_VERSION, notes: str | None=None, import_batch_id: int | None=None) -> dict[str, Any]` (satır 577): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `import_survey_excel(db_path: str, excel_path: str, faculty_id: int, year: int, source_filename: str | None=None, auto_activate: bool=True, uploaded_by: str | None=None) -> dict[str, Any]` (satır 768): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `write_survey_template_excel(target_path: str, faculty_name: str | None=None, year: int | None=None, db_path: str | None=None, faculty_id: int | None=None) -> str` (satır 1046): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `SurveyRow` (satır 42): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `SurveyImportRowResult` (satır 54): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict[str, Any]` (satır 67): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/system_service.py`
  - Fonksiyonlar:
    - `_unwrap_sqlite_connection(conn: Any) -> Any` (satır 30): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `SystemService` (satır 43): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, conn: sqlite3.Connection | None=None, db_path: str | None=None, config: AppConfig | None=None)` (satır 44): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `health(self) -> ServiceResult` (satır 49): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_health_with_conn(self, conn: sqlite3.Connection) -> dict[str, Any]` (satır 57): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_postgresql_health(self) -> dict[str, Any]` (satır 89): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `view_model(self, user_context: UserContext | None=None) -> SystemHealthViewModel` (satır 96): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `architecture_findings(self, ui_dir: str='app/ui/tabs') -> ServiceResult` (satır 111): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `schema_health(self) -> ServiceResult` (satır 121): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `architecture_audit(self) -> ServiceResult` (satır 131): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `config_summary(self) -> ServiceResult` (satır 134): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `sql_console_audit_logs(self, limit: int=50) -> ServiceResult` (satır 151): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `backup_database(self, target_path: str, source_path: str | None=None) -> ServiceResult` (satır 157): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/time_conflict_planning_service.py`
  - Fonksiyonlar:
    - `_row_to_dict(row: sqlite3.Row | tuple[Any, ...] | None, columns: list[str] | None=None) -> dict[str, Any] | None` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_time_constraints(conn: sqlite3.Connection, course_id: int | None=None) -> list[dict[str, Any]]` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `estimate_conflict_risk(conn: sqlite3.Connection, plan: list[dict[str, Any]]) -> dict[str, Any]` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `generate_conflict_warnings(conn: sqlite3.Connection, plan: list[dict[str, Any]]) -> list[dict[str, Any]]` (satır 51): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/topsis_explainability_service.py`
  - Fonksiyonlar:
    - `_safe_float(value: Any, default: float=0.0) -> float` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dump(value: Any) -> str` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_normalize_weights(weights: dict[str, float], criteria_keys: list[str]) -> dict[str, float]` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `calculate_topsis_breakdowns(course_rows: list[dict[str, Any]], weights: dict[str, float], criteria_keys: list[str] | None=None) -> dict[int, dict[str, Any]]` (satır 34): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `save_score_breakdown(cur: sqlite3.Cursor, decision_run_id: int | None, course_id: int, year: int, faculty_id: int | None, department_id: int | None, breakdown: dict[str, Any], ahp_profile_id: int | None=None) -> int` (satır 91): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `short_score_explanation(breakdown: dict[str, Any]) -> str` (satır 153): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/trend_analysis_service.py`
  - Fonksiyonlar:
    - `_safe_float(value: Any, default: float=0.0) -> float` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_json_dump(value: Any) -> str` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `weighted_trend_score(values_by_year: dict[int, float]) -> float` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `analyze_trend_values(values_by_year: dict[int, float], target_year: int | None=None, first_seen_year: int | None=None, rising_threshold: float=0.08, stable_threshold: float=0.04, volatility_threshold: float=0.18) -> dict[str, Any]` (satır 49): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `analyze_course_trend(cur: sqlite3.Cursor, course_id: int, year: int) -> dict[str, Any]` (satır 126): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `save_trend_analysis(cur: sqlite3.Cursor, decision_run_id: int | None, course_id: int, year: int, trend: dict[str, Any]) -> int` (satır 169): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/validation.py`
  - Sınıflar:
    - `ValidationIssue` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict[str, Any]` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ValidationResult` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `as_dict(self) -> dict[str, Any]` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/validation_strategy_service.py`
  - Fonksiyonlar:
    - `choose_validation_strategy(task_type: str, dataset_meta: dict[str, Any] | None=None) -> ValidationStrategy` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `run_validation_strategy(model: Any, X: Any, y: Iterable[Any] | None, strategy: ValidationStrategy) -> dict[str, Any]` (satır 68): Basit, güvenli validation yürütücüsü. Model sklearn uyumluysa fold metrikleri döner.
    - `time_based_split(years: Iterable[int]) -> dict[str, Any]` (satır 103): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `group_k_fold_split(groups: Iterable[Any], fold_count: int=5) -> dict[str, Any]` (satır 110): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `stratified_k_fold_split(y: Iterable[Any], fold_count: int=5) -> dict[str, Any]` (satır 117): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `repeated_k_fold_split(sample_count: int, fold_count: int=5, repeats: int=3) -> dict[str, Any]` (satır 127): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `leave_one_out_if_needed(sample_count: int) -> dict[str, Any]` (satır 131): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_safe_fold_count(sample_count: int, class_distribution: dict[str, int]) -> int` (satır 135): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_make_splits(strategy: ValidationStrategy, X: Any, y: Any)` (satır 141): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_is_numeric(values: Any) -> bool` (satır 152): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `ValidationStrategy` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `to_dict(self) -> dict[str, Any]` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/services/yearly_workflow.py`
  - Fonksiyonlar:
    - `is_yearly_workflow_enabled() -> bool` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_now_utc() -> str` (satır 43): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_table_exists(cur: sqlite3.Cursor, table_name: str) -> bool` (satır 47): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ensure_yearly_workflow_schema(conn: sqlite3.Connection, auto_commit: bool=True) -> dict[str, int]` (satır 55): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_faculty_name(cur: sqlite3.Cursor, fakulte_id: int) -> str` (satır 146): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_department_name(cur: sqlite3.Cursor, bolum_id: int) -> str` (satır 152): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_departments_for_faculty_year(cur: sqlite3.Cursor, fakulte_id: int, yil: int) -> list[tuple[int, str]]` (satır 158): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_required_department_course_ids(cur: sqlite3.Cursor, fakulte_id: int, bolum_id: int, yil: int) -> set[int]` (satır 177): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_criteria_table_available(cur: sqlite3.Cursor) -> bool` (satır 199): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_latest_criteria_row(cur: sqlite3.Cursor, ders_id: int, yil: int) -> tuple[Any, ...] | None` (satır 203): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_as_float(value: Any, default: float=0.0) -> float` (satır 222): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_is_criteria_complete_row(row: tuple[Any, ...] | None) -> bool` (satır 231): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_missing_criteria(conn: sqlite3.Connection, yil: int, fakulte_id: int | None=None, bolum_id: int | None=None) -> list[dict[str, Any]]` (satır 248): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_department_progress(cur: sqlite3.Cursor, yil: int, fakulte_id: int, bolum_id: int) -> dict[str, Any]` (satır 342): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_upsert_department_status(cur: sqlite3.Cursor, fakulte_id: int, bolum_id: int, yil: int, progress: dict[str, Any]) -> None` (satır 373): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_upsert_faculty_status(cur: sqlite3.Cursor, fakulte_id: int, yil: int, criteria_status: str, total_department_count: int, completed_department_count: int, algorithm_run_status: str, generated_year: int | None, year_active: int) -> None` (satır 406): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `is_department_criteria_complete(conn: sqlite3.Connection, yil: int, fakulte_id: int, bolum_id: int) -> bool` (satır 450): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `is_faculty_criteria_complete(conn: sqlite3.Connection, yil: int, fakulte_id: int, refresh: bool=True) -> bool` (satır 475): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `mark_criteria_status(conn: sqlite3.Connection, yil: int, fakulte_id: int, bolum_id: int | None=None) -> dict[str, Any]` (satır 550): Kaydedilen kriter sonrasi durum tablosunu gunceller.
    - `get_faculty_year_status(conn: sqlite3.Connection, fakulte_id: int, yil: int, refresh: bool=False) -> dict[str, Any]` (satır 765): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `is_algorithm_run_for_year(conn: sqlite3.Connection, fakulte_id: int, yil: int) -> bool` (satır 813): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `mark_algorithm_run(conn: sqlite3.Connection, fakulte_id: int, source_year: int, generated_year: int | None, success: bool) -> None` (satır 818): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `reset_year_workflow_for_import(conn: sqlite3.Connection, yil: int, scopes: list[tuple[int, int]]) -> dict[str, int]` (satır 892): Import sonrasi yalnizca ilgili yil/fakulte/bolum kapsaminda workflow durumunu sifirlar.
    - `list_active_years_for_faculty(conn: sqlite3.Connection, fakulte_id: int) -> list[int]` (satır 952): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_years_eligible_for_algorithm(conn: sqlite3.Connection, fakulte_id: int) -> list[int]` (satır 988): Algoritma / sonraki yil mufredat uretimi icin secilebilir yillar.
    - `record_cross_department_usage(conn: sqlite3.Connection, fakulte_id: int, bolum_id: int, source_year: int, generated_year: int, dis_bolum_ders_sayisi: int) -> None` (satır 1039): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

## app/ui

### `app/ui/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/ui/benchmark/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/ui/benchmark/api_client.py`
  - Sınıflar:
    - `ApiResult` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `BenchmarkApiClient` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, base_url: str=DEFAULT_BASE_URL, timeout: float=6.0) -> None` (satır 28): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_scenarios(self) -> ApiResult` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_algorithms(self) -> ApiResult` (satır 35): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `load_dataset(self, payload: dict[str, Any] | None=None) -> ApiResult` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `execute_run(self, payload: dict[str, Any]) -> ApiResult` (satır 42): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `compare_runs(self, payload: dict[str, Any]) -> ApiResult` (satır 46): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_recommendation(self, payload: dict[str, Any]) -> ApiResult` (satır 50): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_runs(self) -> ApiResult` (satır 62): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_run_detail(self, run_id: str) -> ApiResult` (satır 65): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_ml_readiness(self) -> ApiResult` (satır 69): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_ml_model_runs(self) -> ApiResult` (satır 72): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_ml_predictions(self) -> ApiResult` (satır 75): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_algorithm_governance(self) -> ApiResult` (satır 78): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_algorithm_tasks(self) -> ApiResult` (satır 81): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `get_governed_runs(self) -> ApiResult` (satır 84): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_normalize_run_payload(self, payload: dict[str, Any]) -> dict[str, Any]` (satır 87): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_request(self, method: str, path: str, payload: dict[str, Any] | None=None) -> Any` (satır 96): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_with_mock(self, call, fallback) -> ApiResult` (satır 108): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/benchmark/benchmark_panel.py`
  - Sınıflar:
    - `BenchmarkPanel(ttk.Frame)` (satır 21): Main Benchmark Platform tab with left navigation and stacked pages.
      - `__init__(self, parent, app=None)` (satır 24): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build(self) -> None` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_add_nav_button(self, key: str, label: str) -> None` (satır 87): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `show_page(self, key: str) -> None` (satır 106): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `refresh(self) -> None` (satır 117): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/benchmark/mock_data.py`
  - Fonksiyonlar:
    - `get_mock_scenarios()` (satır 366): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_mock_algorithms()` (satır 370): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_mock_ml_readiness()` (satır 374): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_mock_ml_model_runs()` (satır 378): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_mock_ml_predictions()` (satır 382): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_mock_algorithm_governance()` (satır 386): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_mock_algorithm_tasks()` (satır 390): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_mock_governed_runs()` (satır 394): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_mock_dataset_load_result()` (satır 398): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_mock_execute_run(payload=None)` (satır 408): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_mock_recommendation(problem_type='prediction')` (satır 432): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_mock_runs()` (satır 449): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `get_mock_run_detail(run_id)` (satır 453): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/benchmark/pages/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/ui/benchmark/pages/algorithm_explorer_page.py`
  - Sınıflar:
    - `AlgorithmExplorerPage(ttk.Frame)` (satır 10): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent, api_client)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build(self) -> None` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `load_algorithms(self) -> None` (satır 73): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `apply_filter(self) -> None` (satır 88): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `on_select(self, event=None) -> None` (satır 101): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `generate_output(self) -> None` (satır 120): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/benchmark/pages/algorithm_governance_page.py`
  - Fonksiyonlar:
    - `_extract_data(payload: Any) -> list[dict[str, Any]]` (satır 198): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_role_label(role: str | None) -> str` (satır 211): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `AlgorithmGovernancePage(ttk.Frame)` (satır 10): Algoritma yönetişimi ve istatistiksel değerlendirme paneli.
      - `__init__(self, parent, api_client)` (satır 13): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build(self) -> None` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_role_matrix(self) -> None` (satır 60): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_task_mapping(self) -> None` (satır 81): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_guard_panel(self) -> None` (satır 97): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_result_panel(self) -> None` (satır 103): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `load_data(self) -> None` (satır 121): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_fill_roles(self, rows: list[dict[str, Any]]) -> None` (satır 130): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_fill_tasks(self, rows: list[dict[str, Any]]) -> None` (satır 149): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_fill_runs(self, rows: list[dict[str, Any]]) -> None` (satır 164): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_fill_guard_text(self, rows: list[dict[str, Any]]) -> None` (satır 181): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/benchmark/pages/allocation_fairness_page.py`
  - Sınıflar:
    - `AllocationFairnessPage(ttk.Frame)` (satır 10): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent, api_client)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build(self) -> None` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run_allocation(self) -> None` (satır 65): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/benchmark/pages/comparison_page.py`
  - Sınıflar:
    - `ComparisonPage(ttk.Frame)` (satır 10): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent, api_client)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build(self) -> None` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `load_data(self) -> None` (satır 65): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `apply_filters(self) -> None` (satır 76): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/benchmark/pages/dashboard_page.py`
  - Sınıflar:
    - `DashboardPage(ttk.Frame)` (satır 10): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent, api_client)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build(self) -> None` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `load_initial_data(self) -> None` (satır 87): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_render_algorithm_checks(self, algorithms) -> None` (satır 103): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_sync_algo_count(self) -> None` (satır 115): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `selected_algorithms(self) -> list[str]` (satır 119): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `clear_selection(self) -> None` (satır 122): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `refresh_results(self) -> None` (satır 128): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run_benchmark(self) -> None` (satır 131): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_update_from_run(self, run: dict) -> None` (satır 164): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/benchmark/pages/dataset_lab_page.py`
  - Sınıflar:
    - `DatasetLabPage(ttk.Frame)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent, api_client)` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build(self) -> None` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `pick_file(self) -> None` (satır 83): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `load_dataset(self) -> None` (satır 91): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `preview_data(self) -> None` (satır 107): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `generate_synthetic(self) -> None` (satır 110): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/benchmark/pages/decision_engine_page.py`
  - Sınıflar:
    - `DecisionEnginePage(ttk.Frame)` (satır 9): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent, api_client)` (satır 10): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build(self) -> None` (satır 16): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `request_recommendation(self) -> None` (satır 81): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/benchmark/pages/ml_readiness_page.py`
  - Sınıflar:
    - `MLReadinessPage(ttk.Frame)` (satır 9): Benchmark Platformu içinde ML güvenilirlik ve hazırlık paneli.
      - `__init__(self, parent, api_client)` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build(self) -> None` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `load_data(self) -> None` (satır 69): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_readiness(self, rows: list[dict]) -> None` (satır 91): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_runs(self, rows: list[dict]) -> None` (satır 115): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/benchmark/pages/run_history_page.py`
  - Sınıflar:
    - `RunHistoryPage(ttk.Frame)` (satır 10): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent, api_client)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build(self) -> None` (satır 18): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `load_runs(self) -> None` (satır 64): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_normalize_runs(self, runs)` (satır 78): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `apply_filters(self) -> None` (satır 106): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `show_detail(self) -> None` (satır 116): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `compare_selected(self) -> None` (satır 130): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/benchmark/widgets.py`
  - Fonksiyonlar:
    - `run_async(root: tk.Misc, worker: Callable[[], Any], on_success: Callable[[Any], None], on_error: Callable[[Exception], None] | None=None) -> None` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `algorithm_group_color(group: str) -> str` (satır 221): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `SectionHeader(ttk.Frame)` (satır 46): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent, title: str, description: str | None=None)` (satır 47): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `MetricCard(tk.Frame)` (satır 54): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent, title: str, value: Any, subtitle: str | None=None, accent: str=COLORS['blue'])` (satır 55): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `set_value(self, value: Any, subtitle: str | None=None) -> None` (satır 64): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `StatusCard(MetricCard)` (satır 70): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent, title: str, value: Any, status_type: str='info')` (satır 78): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `ErrorBanner(tk.Frame)` (satır 82): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent)` (satır 83): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `show(self, message: str, level: str='error') -> None` (satır 88): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `clear(self) -> None` (satır 98): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `EmptyState(ttk.Frame)` (satır 102): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent, text: str)` (satır 103): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `DataTable(ttk.Frame)` (satır 108): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent, columns: list[str], height: int=8)` (satır 109): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `set_rows(self, rows: list[dict[str, Any]] | list[list[Any]], best_key: str | None=None) -> None` (satır 127): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `selected_values(self) -> list[Any]` (satır 141): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `sort_by(self, col: str, descending: bool) -> None` (satır 147): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_format(self, value: Any) -> str` (satır 163): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `JsonPreviewWidget(ttk.Frame)` (satır 169): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent, height: int=12)` (satır 170): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `set_json(self, value: Any) -> None` (satır 182): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `BarChart(tk.Canvas)` (satır 189): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent, height: int=180)` (satır 190): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `plot(self, rows: list[dict[str, Any]], label_key: str, value_key: str, color: str=COLORS['blue']) -> None` (satır 193): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/style.py`
  - Fonksiyonlar:
    - `apply_style(root: tk.Tk)` (satır 28): Uygulama genel teması (tek yerden yönet).

### `app/ui/tabs/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/ui/tabs/ahp_weight_page.py`
  - Sınıflar:
    - `AHPWeightPage(ttk.Frame)` (satır 27): Karar Merkezi dışında kullanılabilen AHP profil ve ikili karşılaştırma ekranı.
      - `__init__(self, parent, app=None)` (satır 30): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_conn(self)` (satır 37): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_ui(self)` (satır 43): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_profiles_tab(self)` (satır 56): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_wizard_tab(self)` (satır 95): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_impact_tab(self)` (satır 137): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `refresh(self)` (satır 144): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `load_selected_profile(self)` (satır 178): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `create_default_profile(self)` (satır 187): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `apply_pairwise_value(self)` (satır 203): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `calculate_current_matrix(self)` (satır 221): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `save_matrix_to_selected(self)` (satır 231): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `validate_selected(self)` (satır 249): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `submit_selected(self)` (satır 252): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `approve_selected(self)` (satır 255): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `reject_selected(self)` (satır 258): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `activate_selected(self)` (satır 264): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `clone_selected(self)` (satır 267): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `archive_selected(self)` (satır 270): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `load_impact(self)` (satır 273): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_profile_action(self, action, message: str)` (satır 286): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_selected_profile(self)` (satır 300): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_current_matrix(self, keys)` (satır 307): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_saaty_value(self) -> float` (satır 313): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_scope_text(self, profile)` (satır 320): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/tabs/analysis_tab.py`
  - Sınıflar:
    - `AnalysisTab(ttk.Frame)` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent, app)` (satır 20): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `refresh(self)` (satır 38): Sekmeyi (yeniden) çiz.
      - `_has_table(self, table_name: str) -> bool` (satır 106): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_create_card(self, parent, title, value, color_code)` (satır 113): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_fetch_dashboard_stats(self)` (satır 120): Ozet istatistikleri (toplam ogrenci, ders, basari orani, anket) veritabanindan ceker.
      - `_plot_top_success(self, ax)` (satır 164): En yuksek basari oranina sahip 5 dersi yatay bar grafik olarak cizer.
      - `_plot_top_popularity(self, ax)` (satır 207): En populer 7 dersi pasta grafik olarak cizer.

### `app/ui/tabs/calc_tab.py`
  - Sınıflar:
    - `CalcTab(ttk.Frame)` (satır 42): 🧮 Hesaplama & Test sekmesi:
      - `__init__(self, parent, app)` (satır 50): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_on_sub_tab_changed(self, event=None)` (satır 89): Alt sekme degistiginde sadece ilk acilista yukle; sonrasinda
      - `refresh(self, force_reload=False)` (satır 108): DB path guncelle. force_reload=True olmadikca mevcut filtre
      - `_refresh_algo_faculty_options(self)` (satır 155): Algoritma paneli için fakülte listesini yükler.
      - `_on_algo_faculty_change(self, event=None)` (satır 173): Fakülte değişince yıl listesini o fakülteye göre güncelle.
      - `_refresh_algo_year_options(self)` (satır 177): Algoritma paneli yil listesi: secili fakultede tum bolumlerin kriter girisi
      - `_algo_scope(self) -> tuple[int, str, int]` (satır 208): Algoritma paneli: (fakulte_id, fakulte_ad, akademik_yil).
      - `setup_algo_panel(self, parent)` (satır 224): Algoritma kontrol panelini olusturur:
      - `_run_full_algorithm_batch_for_next_year(self)` (satır 416): Eski 'Tumunu Calistir' davranisini korur.
      - `run_single_step(self, algo_id: str)` (satır 445): Tek bir algoritma adimini calistirir. Sonucu results_cache'e kaydeder ve UI status etiketini gunceller.
      - `show_result(self, algo_id: str)` (satır 957): Secilen algoritmanin cache'deki sonucunu log panelinde gosterir.
      - `_toggle_fullscreen(self)` (satır 970): Ders analiz panelini tam ekran yapar veya eski haline dondurur.

### `app/ui/tabs/course_analysis_tab.py`
  - Sınıflar:
    - `_Tooltip` (satır 50): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, widget, text: str)` (satır 51): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_show(self, w, text)` (satır 56): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_hide(self)` (satır 66): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_SearchableCombo(tk.Frame)` (satır 75): Aranabilir ders secim widget'i.
      - `__init__(self, parent, width=38, **kw)` (satır 88): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `set_values(self, values: list)` (satır 123): Tum secenek listesini ayarla.
      - `get(self)` (satır 127): Secili degeri dondur.
      - `set(self, value: str)` (satır 131): Secili degeri programatik olarak ayarla.
      - `bind_select(self, callback)` (satır 137): Secim yapildiginda cagrilacak fonksiyon.
      - `_toggle_popup(self)` (satır 143): Ok butonuyla listeyi ac/kapat.
      - `_on_entry_focus(self, _event)` (satır 150): Entry'ye tiklandiginda arama moduna gec.
      - `_on_key(self, event)` (satır 156): Her tus basildiginda listeyi filtrele.
      - `_open_popup(self, show_all=False)` (satır 165): Popup'i entry'nin hemen altinda ac.
      - `_refresh_list(self)` (satır 220): Listeyi mevcut arama metnine gore guncelle.
      - `_on_lb_click(self)` (satır 266): Listeden secim yapildiginda.
      - `_select_current(self)` (satır 289): Enter ile secili ogeni onayla.
      - `_cancel_search(self)` (satır 305): Escape ile aramayi iptal edip onceki secime don.
      - `_move_selection(self, delta)` (satır 311): Ok tuslari ile listede gezin.
      - `_on_popup_focus_out(self, event)` (satır 334): Popup disina tiklaninca kapat.
      - `_deferred_close(self)` (satır 352): Geckmeli kapatma - focus hala icerideyse kapatma.
      - `_close_popup(self)` (satır 362): Popup'i kapat ve temizle.
    - `CourseAnalysisTab(ttk.Frame)` (satır 375): Ders Analiz Laboratuvari sekmesi (Tkinter).
      - `__init__(self, parent, app)` (satır 378): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `refresh(self)` (satır 391): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_ui(self)` (satır 425): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_top_bar(self)` (satır 449): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_left_panel(self, parent)` (satır 492): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_mid_panel(self, parent)` (satır 520): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_right_panel(self, parent)` (satır 569): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_initial_data(self)` (satır 613): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_sync_year_for_faculty(self, fakulte_id: int)` (satır 616): Secili fakulte icin yalnizca o fakultenin mufredat yillarini listeler
      - `_refresh_courses_for_scope(self, fakulte_id: int, yil_raw: str | None)` (satır 651): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_faculties(self)` (satır 709): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_on_faculty_change(self, _event)` (satır 727): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_on_year_change(self, _event=None)` (satır 751): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_on_ders_selected(self, event=None)` (satır 778): Ders seçildiğinde (Analizi Başlat için hazır).
      - `_update_ders_combo(self, query: str)` (satır 782): Ders listesini SearchableCombo'ya yukle.
      - `_start_analysis(self)` (satır 801): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_on_result(self, result: dict)` (satır 847): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_fill_criteria(self, criteria: dict, criteria_status: dict=None)` (satır 873): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_fill_steps(self, steps: dict)` (satır 927): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_set_step_state(self, key: str, state: str, content: str)` (satır 1053): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_set_text(widget: tk.Text, content: str)` (satır 1069): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_fill_decision(self, decision: dict, course: dict, steps: dict=None)` (satır 1078): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_set_running(self, val: bool)` (satır 1129): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_mark_all_steps_error(self, msg: str)` (satır 1140): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_clear_all(self, keep_selection: bool=False)` (satır 1144): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/tabs/criteria_page.py`
  - Sınıflar:
    - `CriteriaPage` (satır 32): Kriter Girdi Sayfasi.
      - `__init__(self, parent, db, app=None)` (satır 47): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_ensure_table(self)` (satır 61): Kriter ve raporlama semalarini migration-safe sekilde hazirlar.
      - `_refresh_related_views(self, restore_course_id=None)` (satır 70): Kriter kaydı sonrası ilgili ekranları yeniler.
      - `setup_ui(self)` (satır 102): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `create_filter_ui(self, parent)` (satır 153): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `create_form_ui(self, parent)` (satır 202): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `create_completion_panel(self)` (satır 272): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `create_section_header(self, row, text)` (satır 325): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `create_input_row(self, row, label_text, default_val)` (satır 329): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_selected_faculty_id(self) -> int | None` (satır 338): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_selected_department_name(self) -> str | None` (satır 350): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_selected_department_id(self) -> int | None` (satır 353): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_selected_completion_scope(self) -> tuple[str, int | None, int | None, int | None, str | None]` (satır 369): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_matrix_display_value(self, row: dict[str, Any]) -> str` (satır 378): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `refresh_completion_panel(self)` (satır 389): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_generate_completion_tasks(self)` (satır 476): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_request_completion_override(self)` (satır 489): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_export_completion_matrix(self)` (satır 524): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_now_utc(self) -> str` (satır 561): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `import_kriterler_excel(self)` (satır 566): Secili kapsam icin kriter dosyasini uygular.
      - `load_faculties(self, preserve_selection=False)` (satır 604): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `on_faculty_change(self, event, _preserve_bolum=None)` (satır 623): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_on_department_change(self, event=None)` (satır 647): Bölüm değiştiğinde yıl listesini günceller.
      - `_refresh_years_for_selection(self)` (satır 651): Seçili fakülte/bölüm için müfredatı olan yılları yükler.
      - `load_courses(self, restore_course_id=None, show_warnings=True)` (satır 728): Fakültedeki seçmeli dersleri listeler; Güz/Bahar ve kriter filtresine göre.
      - `_has_col(self, table, col)` (satır 853): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_ders_tip_kolonu(self)` (satır 861): Ders tablosundaki seçmeli/zorunlu sütun adını döner (DersTipi, tip veya tur).
      - `_check_in_mufredat(self, yil: int, donem: str) -> bool` (satır 868): Ders bu yıl/dönem/bölüm müfredatında mı?
      - `_update_form_readonly(self)` (satır 894): 1 ve 2. kriterler filtreye göre açık/kilitli olur.
      - `_set_entry_value(self, entry, value, state='normal')` (satır 903): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_survey_record_locked(self, record: dict[str, Any] | None) -> bool` (satır 921): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_apply_survey_lock_state(self, locked: bool, source_text: str | None=None)` (satır 928): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_update_criteria_source_info(self, record: dict[str, Any] | None=None)` (satır 947): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_fetch_saved_criteria_record(self, ders_id, yil, donem)` (satır 982): ders_kriterleri kaydini acik kolon adlariyla dondurur.
      - `_fetch_saved_criteria(self, ders_id, yil, donem)` (satır 1054): ders_kriterleri kaydini sabit kolon sirasiyla dondurur.
      - `on_course_select(self, event)` (satır 1071): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `clear_form_inputs(self)` (satır 1192): Formu güvenli şekilde temizler
      - `update_calculations(self, event=None)` (satır 1209): Kullanıcı sayı girdikçe oranları anlık gösterir.
      - `save_data(self)` (satır 1244): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/tabs/data_management_page.py`
  - Sınıflar:
    - `DataManagementPage(ttk.Frame)` (satır 30): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent: tk.Misc, app: Any | None=None)` (satır 31): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_db_path(self) -> str | None` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_connect(self) -> sqlite3.Connection` (satır 42): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_ui(self) -> None` (satır 48): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_history(self) -> None` (satır 80): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_text_tabs(self) -> None` (satır 121): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_make_text(self, parent: tk.Misc) -> ScrolledText` (satır 145): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_set_text(self, widget: ScrolledText, value: Any) -> None` (satır 151): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `refresh_imports(self) -> None` (satır 159): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_on_history_select(self, _event: Any=None) -> None` (satır 193): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `load_selected_import(self) -> None` (satır 203): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `recalculate_diff(self) -> None` (satır 225): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `recalculate_impact(self) -> None` (satır 237): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `load_rollback_plan(self) -> None` (satır 249): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `approve_selected(self) -> None` (satır 260): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `activate_selected(self) -> None` (satır 263): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `reject_selected(self) -> None` (satır 266): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `rollback_selected(self) -> None` (satır 272): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_status_action(self, func: Any, success_message: str) -> None` (satır 283): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/tabs/data_quality_page.py`
  - Sınıflar:
    - `DataQualityPage(ttk.Frame)` (satır 19): Veri kalitesi ve kapsama raporu
      - `__init__(self, parent, app=None, db_path=None)` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_setup_ui(self)` (satır 29): UI bileşenlerini kur
      - `_build_summary_tab(self)` (satır 58): Veri Özeti sekmesi
      - `_build_coverage_tab(self)` (satır 93): Kapsama Raporu sekmesi
      - `_build_readiness_tab(self)` (satır 120): Veri Olgunluğu sekmesi
      - `_build_missing_data_tab(self)` (satır 142): Eksik Veri sekmesi
      - `_build_validation_issues_tab(self)` (satır 166): Validation İssues sekmesi
      - `_populate_years(self)` (satır 191): Akademik yılları doldur
      - `_populate_faculties(self)` (satır 209): Fakülteleri doldur
      - `_get_selected_faculty_id(self)` (satır 226): Seçili fakülteTidini al
      - `_generate_report(self)` (satır 236): Rapor oluştur
      - `_update_summary(self, readiness: dict, coverage: dict)` (satır 271): Summary sekmesini güncelle
      - `_update_coverage(self, coverage: dict)` (satır 309): Coverage sekmesini güncelle
      - `_update_readiness(self, readiness: dict)` (satır 357): Readiness sekmesini güncelle
      - `_refresh(self)` (satır 434): Sayfayı yenile

### `app/ui/tabs/decision_center_page.py`
  - Fonksiyonlar:
    - `_status_text(status: int | None) -> str` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_lifecycle_text(label: str | None) -> str` (satır 37): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
  - Sınıflar:
    - `DecisionCenterPage(ttk.Frame)` (satır 51): Karar Merkezi: AHP, policy, runs, course decisions and reports.
      - `__init__(self, parent, app, service_factory=None)` (satır 54): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_conn(self)` (satır 85): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_filters(self)` (satır 91): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_ahp_tab(self)` (satır 120): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_readiness_tab(self)` (satır 132): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_policy_tab(self)` (satır 144): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_runs_tab(self)` (satır 154): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_course_tab(self)` (satır 166): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_pool_lifecycle_tab(self)` (satır 181): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_semester_planning_tab(self)` (satır 218): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_sensitivity_tab(self)` (satır 222): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_approvals_tab(self)` (satır 230): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_fairness_tab(self)` (satır 238): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_tree(self, parent, columns)` (satır 244): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `refresh(self, force_reload: bool=False)` (satır 261): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_filters(self)` (satır 277): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_departments(self)` (satır 297): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_ahp(self)` (satır 316): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_policies(self)` (satır 339): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_runs(self)` (satır 355): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_run_related(self)` (satır 379): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_readiness(self)` (satır 387): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_request_readiness_override(self)` (satır 443): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_course_decisions(self, run_id)` (satır 479): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_pool_lifecycle(self)` (satır 503): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_show_pool_lifecycle_detail(self)` (satır 595): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_approve_pool_state(self)` (satır 633): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_reject_pool_state(self)` (satır 646): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_sensitivity(self, run_id)` (satır 659): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_approvals(self, run_id)` (satır 678): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_fairness(self, run_id)` (satır 697): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_show_course_detail(self)` (satır 725): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_selected_run_id(self)` (satır 788): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_select_run_from_tree(self)` (satır 795): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_create_profile(self)` (satır 806): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_activate_profile(self)` (satır 816): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_create_policy(self)` (satır 827): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_activate_policy(self)` (satır 837): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_execute_run(self)` (satır 848): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_clear(self, tree)` (satır 880): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/tabs/pool_tab.py`
  - Sınıflar:
    - `PoolTab(ttk.Frame)` (satır 66): Havuz Yonetimi sekmesi:
      - `__init__(self, parent, app)` (satır 75): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `refresh(self, select_latest_year=False)` (satır 93): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_ui(self)` (satır 135): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_legend(self)` (satır 238): Durum kodlari ve sayac mantigini gosteren aciklama kutusu.
      - `_build_pool_tree(self, parent)` (satır 275): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_curr_tree(self, parent)` (satır 332): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_on_pool_tree_motion(self, event)` (satır 346): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_show_tooltip(self, event, metin: str)` (satır 351): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_hide_tooltip(self)` (satır 365): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_ensure_year_scores(self, fakulte_id: int, yil: int, donem: str='G') -> None` (satır 376): Legacy helper (deprecated).
      - `load_faculties_to_combo(self, force_latest_year=False)` (satır 383): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_refresh_years_for_faculty(self, fakulte_id: int, force_latest_year: bool=False)` (satır 396): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `on_faculty_change(self, _event, force_latest_year: bool=False)` (satır 429): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `toggle_resting_courses(self)` (satır 452): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `load_pool_data(self)` (satır 460): Secili fakulte/bolum/yil icin havuz ve mufredat verilerini ceker, tablolara basar.
      - `_selected_pool_items(self)` (satır 652): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `set_selected_pool_status(self, new_status: int)` (satır 656): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `run_pool_health_check(self)` (satır 689): Secili fakulte+yil icin havuz statu dagilimi ve mufredat-havuz senkronizasyon raporunu cikartir.
      - `run_decision_engine(self)` (satır 793): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `open_student_simulation(self)` (satır 802): Mufredattaki derslerden ogrenci secim simulasyonu penceresi acar.

### `app/ui/tabs/relations_tab.py`
  - Sınıflar:
    - `RelationsTab(ttk.Frame)` (satır 18): 🔗 Ders İlişkileri & Kurallar sekmesi:
      - `__init__(self, parent, app)` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `refresh(self)` (satır 36): Sekmeye gelince/yenile basılınca çağır.
      - `_build_ui(self)` (satır 49): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `load_courses_for_relations(self)` (satır 112): Secili fakulteye ait dersleri listbox'a yukler.
      - `on_rel_course_select(self, _event)` (satır 137): Ders secildiginde NLP benzerlik analizi calistirir ve sonuclari tablo + graf olarak gosterir.

### `app/ui/tabs/security_readiness_page.py`
  - Sınıflar:
    - `SecurityReadinessPage(ttk.Frame)` (satır 11): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent)` (satır 12): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_setup_ui(self)` (satır 19): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `refresh_data(self)` (satır 63): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_update_ui(self, data)` (satır 82): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/tabs/semester_planning_page.py`
  - Sınıflar:
    - `SemesterPlanningPage(ttk.Frame)` (satır 18): Policy tabanli Güz/Bahar dönem planlama ekranı.
      - `__init__(self, parent, app=None)` (satır 21): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_conn(self)` (satır 27): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_ui(self)` (satır 33): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_plan_tab(self)` (satır 64): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_violations_tab(self)` (satır 72): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_scenarios_tab(self)` (satır 87): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_runs_tab(self)` (satır 103): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_make_tree(self, parent, title, columns)` (satır 122): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_int_or_none(self, value)` (satır 140): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `refresh(self)` (satır 144): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `generate_plan(self)` (satır 159): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_result(self, result)` (satır 177): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_fill_course_tree(self, tree, rows)` (satır 183): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_fill_violations(self, rows)` (satır 199): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_fill_scenarios(self, rows)` (satır 204): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_runs(self)` (satır 220): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `load_selected_run(self)` (satır 235): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/tabs/system_health_page.py`
  - Sınıflar:
    - `SystemHealthPage(ttk.Frame)` (satır 14): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent, app=None, system_service=None, user_context=None, config=None)` (satır 15): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_service(self)` (satır 23): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_ui(self)` (satır 29): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `refresh(self)` (satır 39): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/tabs/tools_tab.py`
  - Sınıflar:
    - `ToolsTab(ttk.Frame)` (satır 38): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `__init__(self, parent, app)` (satır 39): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_db_ready(self) -> bool` (satır 77): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `log(self, msg: str)` (satır 80): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_format_operation_error(self, exc: Exception) -> str` (satır 86): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_release_ui_db_connection(self) -> bool` (satır 95): Close the long-lived UI connection before service-level write operations.
      - `_restore_ui_db_connection(self)` (satır 113): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_run_external_db_operation(self, operation)` (satır 119): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_set_import_state_label(self, text: str)` (satır 130): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_selected_faculty_scope(self) -> tuple[int | None, str | None, int | None]` (satır 134): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_selected_department_name(self) -> str | None` (satır 150): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_selected_department_id(self) -> int | None` (satır 153): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_ui(self)` (satır 172): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `refresh(self)` (satır 329): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_clear_views(self)` (satır 341): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_parse_year_text(self, raw: str | None) -> int | None` (satır 347): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_merge_year_values(self, years: list[str], extra_year: int | None=None) -> list[str]` (satır 357): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_commit_year_input(self, _event=None)` (satır 363): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_fill_years(self)` (satır 374): Yil listesi: secili fakultenin gercek mufredat yillari (global sabit aralik yok).
      - `_fill_faculties(self)` (satır 419): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_on_faculty_change(self, _event)` (satır 432): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_on_year_change(self, _event)` (satır 459): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_on_department_change(self, _event)` (satır 463): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_update_import_state(self)` (satır 467): Yükleme durumunu günceller - artık yıl kısıtlaması yok, seçili yıl için yükleme yapılır.
      - `load_report(self)` (satır 501): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_render_snapshot(self, snapshot: dict[str, Any])` (satır 550): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `download_criteria_template(self)` (satır 601): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `import_criteria_excel(self)` (satır 644): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `download_survey_template(self)` (satır 737): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `import_curriculum_excel(self)` (satır 773): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `import_survey_excel(self)` (satır 833): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `sync_status_year(self)` (satır 921): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `backup_db(self)` (satır 958): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `export_current(self, which: str, fmt: str)` (satır 988): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/ui/tabs/view_tab.py`
  - Sınıflar:
    - `ViewTab(ttk.Frame)` (satır 24): Admin Panel: Tum tablolari incele.
      - `__init__(self, parent, app, table_service=None, config=None, user_context=None)` (satır 32): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_ui(self)` (satır 51): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `refresh(self)` (satır 153): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_service(self)` (satır 156): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_is_sql_console_allowed(self) -> bool` (satır 164): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `fill_tables(self)` (satır 167): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_on_table_select(self, _evt=None)` (satır 185): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_load_table(self, table: str)` (satır 193): Secilen tabloyu veritabanindan okuyup filtreleme/siralama icin hafizaya alir.
      - `_setup_tree_columns(self)` (satır 217): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_build_column_filters(self)` (satır 226): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_apply_filters(self)` (satır 248): Global arama ve kolon bazli filtreleri uygulayarak sonuclari gunceller.
      - `_clear_filters(self)` (satır 279): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_sort_by(self, col: str)` (satır 287): Belirtilen kolona gore siralama yapar. Ayni kolona tekrar tiklanirsa yonu tersine cevirir.
      - `_change_page(self, delta: int)` (satır 315): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `_render_page(self)` (satır 322): Filtrelenmis ve siralanmis verinin gecerli sayfasini Treeview'a basar.
      - `_open_sql_runner(self)` (satır 353): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

## app/utils

### `app/utils/etl.py`
  - Fonksiyonlar:
    - `import_students_from_excel(file_path)` (satır 10): Excel dosyasindan ogrenci kayitlarini okuyup sozluk listesi olarak doner.

### `app/utils/import_excel.py`
  - Fonksiyonlar:
    - `_normalize_text(s: str) -> str` (satır 54): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_resolve_fakulte(raw: str) -> str` (satır 60): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `_resolve_bolum(raw: str) -> str` (satır 68): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `safe_int(value, default=0)` (satır 76): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `safe_float(value, default=0.0)` (satır 85): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `safe_str(value, default='')` (satır 94): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
    - `clean_dataframe(df: pd.DataFrame, required_cols=None)` (satır 101): NaN/Null temizliği, boş satırları at.
    - `import_data(file_path, clear_existing=False)` (satır 122): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.

### `app/utils/logger.py`
  - Fonksiyonlar:
    - `log_operation(operation: str, detail: str='', success: bool=True)` (satır 30): İşlem loglaması - dosya ve konsola yazar.

## app/viewmodels

### `app/viewmodels/__init__.py`
  - Bu modülde üst seviye fonksiyon veya sınıf yok.

### `app/viewmodels/system_health.py`
  - Sınıflar:
    - `SystemHealthViewModel` (satır 10): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
      - `lines(self) -> list[str]` (satır 22): Docstring yok; işlev imza ve çağrıldığı katmandan çıkarılmalı.
