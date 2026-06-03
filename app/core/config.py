# -*- coding: utf-8 -*-
"""Merkezi uygulama konfigürasyonu."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.engine.url import make_url

from app.db.backend import database_backend, is_sqlite_url

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - opsiyonel bagimlilik
    load_dotenv = None


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "evet"}


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _load_json(path: str = "config.json") -> dict[str, Any]:
    config_path = resolve_config_path(path)
    if not config_path.exists():
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            return json.load(handle) or {}
    except Exception:
        return {}


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_project_path(path: str | os.PathLike[str] | None, *, base_dir: Path | None = None) -> Path:
    if path is None:
        return (base_dir or PROJECT_ROOT).resolve()
    resolved = Path(path)
    if resolved.is_absolute():
        return resolved
    return ((base_dir or PROJECT_ROOT) / resolved).resolve()


def resolve_config_path(config_path: str | os.PathLike[str] = "config.json") -> Path:
    return resolve_project_path(config_path, base_dir=PROJECT_ROOT)


def resolve_sqlite_db_path(
    db_path: str | os.PathLike[str] | None = None,
    *,
    base_dir: Path | None = None,
) -> Path:
    candidate = db_path or Path("data") / "adil_secmeli.db"
    return resolve_project_path(candidate, base_dir=base_dir or PROJECT_ROOT)


def _configured_sqlite_db_path(
    db_path: str | os.PathLike[str] | None = None,
    *,
    base_dir: Path | None = None,
) -> Path:
    resolved = resolve_sqlite_db_path(db_path, base_dir=base_dir)
    default_path = resolve_sqlite_db_path(None, base_dir=PROJECT_ROOT)
    if db_path and not resolved.exists() and default_path.exists():
        return default_path
    return resolved


def _sqlite_path_from_url(database_url: str, *, base_dir: Path | None = None) -> Path | None:
    try:
        parsed = make_url(database_url)
        db_path = parsed.database
        if not db_path or str(db_path).strip() == ":memory:":
            return None
        resolved = Path(db_path)
        if not resolved.is_absolute():
            resolved = resolve_sqlite_db_path(resolved, base_dir=base_dir)
        return resolved.resolve()
    except Exception:
        return None


def normalize_sqlite_database_url(database_url: str, *, base_dir: Path | None = None) -> str:
    try:
        parsed = make_url(database_url)
        db_path = parsed.database
        if not db_path:
            return database_url
        resolved_path = Path(db_path)
        if not resolved_path.is_absolute():
            resolved_path = resolve_sqlite_db_path(resolved_path, base_dir=base_dir)
        return f"sqlite:///{resolved_path.as_posix()}"
    except Exception:
        return database_url


@dataclass(frozen=True)
class AppConfig:
    project_name: str = "Adil Seçmeli"
    version: str = "1.0.0"
    app_mode: str = "auto"
    environment: str = "development"
    sqlite_db_path: str = "./data/adil_secmeli.db"
    database_url: str = "sqlite:///./data/adil_secmeli.db"
    debug: bool = False
    enable_sql_console: bool = False
    enable_developer_tools: bool = False
    enable_schema_compat: bool = True
    allow_runtime_schema_mutation: bool = True
    allow_runtime_schema_mutation_in_production: bool = False
    api_auth_enabled: bool = False
    enable_ml_decision_influence: bool = False
    require_high_confidence_for_ml_influence: bool = True
    allow_experimental_ml_in_decision: bool = False
    enable_yearly_criteria_workflow: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    # Security Configuration
    api_auth_token_secret: str = ""
    api_token_expire_minutes: int = 1440
    api_key_hashes: str = ""
    require_rbac: bool = False
    allow_dangerous_sql: bool = False
    sql_console_read_only_in_production: bool = True
    max_upload_size_mb: int = 10
    max_import_rows: int = 10000
    allowed_upload_extensions: str = ".xlsx,.csv"
    allowed_upload_mime_types: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 60
    rate_limit_import_per_minute: int = 5
    rate_limit_algorithm_run_per_minute: int = 2
    cors_allowed_origins: str = ""
    cors_allow_credentials: bool = True
    backup_before_import: bool = False
    import_requires_approval: bool = False
    security_audit_enabled: bool = True

    @property
    def db_path(self) -> str:
        return self.sqlite_db_path

    @property
    def db_backend(self) -> str:
        return database_backend(self.database_url)

    def as_legacy_dict(self) -> dict[str, Any]:
        return {
            "db_path": self.sqlite_db_path,
            "db_url": self.database_url,
            "db_backend": self.db_backend,
            "api_host": self.api_host,
            "api_port": self.api_port,
            "log_level": self.log_level,
            "debug": self.debug,
            "enable_sql_console": self.enable_sql_console,
            "enable_developer_tools": self.enable_developer_tools,
            "enable_schema_compat": self.enable_schema_compat,
            "allow_runtime_schema_mutation": self.allow_runtime_schema_mutation,
            "allow_runtime_schema_mutation_in_production": self.allow_runtime_schema_mutation_in_production,
            "enable_ml_decision_influence": self.enable_ml_decision_influence,
            "require_high_confidence_for_ml_influence": self.require_high_confidence_for_ml_influence,
            "allow_experimental_ml_in_decision": self.allow_experimental_ml_in_decision,
            "enable_yearly_criteria_workflow": self.enable_yearly_criteria_workflow,
        }


def load_app_config(config_path: str = "config.json") -> AppConfig:
    """config.json + environment değerlerini tek yerde birleştirir."""
    if load_dotenv is not None:
        load_dotenv(override=False)
    config_file = resolve_config_path(config_path)
    cfg = _load_json(str(config_file))
    base_dir = config_file.parent
    db_path_env = os.getenv("SQLITE_DB_PATH") or os.getenv("DB_PATH")
    if db_path_env:
        sqlite_db_path = resolve_sqlite_db_path(db_path_env, base_dir=base_dir)
    else:
        sqlite_db_path = _configured_sqlite_db_path(cfg.get("db_path"), base_dir=base_dir)
    environment = str(os.getenv("ENVIRONMENT") or cfg.get("environment") or "development").lower()
    debug = _bool(os.getenv("DEBUG"), _bool(cfg.get("debug"), environment == "development"))
    developer_tools = _bool(
        os.getenv("ENABLE_DEVELOPER_TOOLS"),
        _bool(cfg.get("enable_developer_tools"), debug and environment != "production"),
    )
    sql_console_default = developer_tools and environment != "production"
    enable_sql_console = _bool(os.getenv("ENABLE_SQL_CONSOLE"), _bool(cfg.get("enable_sql_console"), sql_console_default))
    if environment == "production" and "ENABLE_SQL_CONSOLE" not in os.environ:
        enable_sql_console = False
    enable_schema_compat = _bool(os.getenv("ENABLE_SCHEMA_COMPAT"), _bool(cfg.get("enable_schema_compat"), True))
    runtime_mutation_default = bool(enable_schema_compat and environment != "production")
    allow_runtime_schema_mutation = _bool(
        os.getenv("ALLOW_RUNTIME_SCHEMA_MUTATION"),
        _bool(cfg.get("allow_runtime_schema_mutation"), runtime_mutation_default),
    )
    allow_runtime_schema_mutation_in_production = _bool(
        os.getenv("ALLOW_RUNTIME_SCHEMA_MUTATION_IN_PRODUCTION"),
        _bool(cfg.get("allow_runtime_schema_mutation_in_production"), False),
    )
    if environment == "production" and "ALLOW_RUNTIME_SCHEMA_MUTATION" not in os.environ:
        allow_runtime_schema_mutation = False
    raw_database_url = str(os.getenv("DATABASE_URL") or cfg.get("db_url") or "").strip()
    if raw_database_url:
        if is_sqlite_url(raw_database_url):
            normalized_url = normalize_sqlite_database_url(raw_database_url, base_dir=base_dir)
            normalized_path = _sqlite_path_from_url(normalized_url, base_dir=base_dir)
            if normalized_path and not normalized_path.exists() and sqlite_db_path.exists():
                database_url = f"sqlite:///{sqlite_db_path.as_posix()}"
            else:
                database_url = normalized_url
        else:
            database_url = raw_database_url
    else:
        database_url = f"sqlite:///{sqlite_db_path}"
    if not is_sqlite_url(database_url) and not raw_database_url:
        database_url = "postgresql+psycopg2://postgres:postgres@localhost:5432/adil_secmeli"

    # Default production behavior logic
    is_prod = (environment == "production")
    api_auth_enabled = _bool(os.getenv("API_AUTH_ENABLED"), _bool(cfg.get("api_auth_enabled"), is_prod))
    require_rbac = _bool(os.getenv("REQUIRE_RBAC"), _bool(cfg.get("require_rbac"), is_prod))
    allow_dangerous_sql = _bool(os.getenv("ALLOW_DANGEROUS_SQL"), _bool(cfg.get("allow_dangerous_sql"), False))
    sql_console_read_only_in_production = _bool(os.getenv("SQL_CONSOLE_READ_ONLY_IN_PRODUCTION"), _bool(cfg.get("sql_console_read_only_in_production"), True))
    rate_limit_enabled = _bool(os.getenv("RATE_LIMIT_ENABLED"), _bool(cfg.get("rate_limit_enabled"), is_prod))
    backup_before_import = _bool(os.getenv("BACKUP_BEFORE_IMPORT"), _bool(cfg.get("backup_before_import"), is_prod))
    import_requires_approval = _bool(os.getenv("IMPORT_REQUIRES_APPROVAL"), _bool(cfg.get("import_requires_approval"), is_prod))
    security_audit_enabled = _bool(os.getenv("SECURITY_AUDIT_ENABLED"), _bool(cfg.get("security_audit_enabled"), True))

    return AppConfig(
        project_name=str(cfg.get("project_name") or os.getenv("PROJECT_NAME") or "Adil Seçmeli"),
        version=str(cfg.get("version") or os.getenv("APP_VERSION") or "1.0.0"),
        app_mode=str(os.getenv("APP_MODE") or cfg.get("app_mode") or "auto"),
        environment=environment,
        sqlite_db_path=str(sqlite_db_path),
        database_url=database_url,
        debug=debug,
        enable_sql_console=enable_sql_console,
        enable_developer_tools=developer_tools,
        enable_schema_compat=enable_schema_compat,
        allow_runtime_schema_mutation=allow_runtime_schema_mutation,
        allow_runtime_schema_mutation_in_production=allow_runtime_schema_mutation_in_production,
        api_auth_enabled=api_auth_enabled,
        enable_ml_decision_influence=_bool(os.getenv("ENABLE_ML_DECISION_INFLUENCE"), _bool(cfg.get("enable_ml_decision_influence"), False)),
        require_high_confidence_for_ml_influence=_bool(os.getenv("REQUIRE_HIGH_CONFIDENCE_FOR_ML_INFLUENCE"), _bool(cfg.get("require_high_confidence_for_ml_influence"), True)),
        allow_experimental_ml_in_decision=_bool(os.getenv("ALLOW_EXPERIMENTAL_ML_IN_DECISION"), _bool(cfg.get("allow_experimental_ml_in_decision"), False)),
        enable_yearly_criteria_workflow=_bool(
            os.getenv("ENABLE_YEARLY_CRITERIA_WORKFLOW"),
            _bool(cfg.get("enable_yearly_criteria_workflow"), True),
        ),
        api_host=str(os.getenv("API_HOST") or cfg.get("api_host") or "0.0.0.0"),
        api_port=_int(os.getenv("API_PORT") or cfg.get("api_port"), 8000),
        log_level=str(os.getenv("LOG_LEVEL") or cfg.get("log_level") or "INFO").upper(),
        api_auth_token_secret=str(os.getenv("API_AUTH_TOKEN_SECRET") or cfg.get("api_auth_token_secret") or ""),
        api_token_expire_minutes=_int(os.getenv("API_TOKEN_EXPIRE_MINUTES") or cfg.get("api_token_expire_minutes"), 1440),
        api_key_hashes=str(os.getenv("API_KEY_HASHES") or cfg.get("api_key_hashes") or ""),
        require_rbac=require_rbac,
        allow_dangerous_sql=allow_dangerous_sql,
        sql_console_read_only_in_production=sql_console_read_only_in_production,
        max_upload_size_mb=_int(os.getenv("MAX_UPLOAD_SIZE_MB") or cfg.get("max_upload_size_mb"), 10),
        max_import_rows=_int(os.getenv("MAX_IMPORT_ROWS") or cfg.get("max_import_rows"), 10000),
        allowed_upload_extensions=str(os.getenv("ALLOWED_UPLOAD_EXTENSIONS") or cfg.get("allowed_upload_extensions") or ".xlsx,.csv"),
        allowed_upload_mime_types=str(os.getenv("ALLOWED_UPLOAD_MIME_TYPES") or cfg.get("allowed_upload_mime_types") or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv"),
        rate_limit_enabled=rate_limit_enabled,
        rate_limit_per_minute=_int(os.getenv("RATE_LIMIT_PER_MINUTE") or cfg.get("rate_limit_per_minute"), 60),
        rate_limit_import_per_minute=_int(os.getenv("RATE_LIMIT_IMPORT_PER_MINUTE") or cfg.get("rate_limit_import_per_minute"), 5),
        rate_limit_algorithm_run_per_minute=_int(os.getenv("RATE_LIMIT_ALGORITHM_RUN_PER_MINUTE") or cfg.get("rate_limit_algorithm_run_per_minute"), 2),
        cors_allowed_origins=str(os.getenv("CORS_ALLOWED_ORIGINS") or cfg.get("cors_allowed_origins") or ""),
        cors_allow_credentials=_bool(os.getenv("CORS_ALLOW_CREDENTIALS"), _bool(cfg.get("cors_allow_credentials"), True)),
        backup_before_import=backup_before_import,
        import_requires_approval=import_requires_approval,
        security_audit_enabled=security_audit_enabled,
    )


class Settings:
    """Eski importları kırmamak için korunan uyumluluk sınıfı."""

    PROJECT_NAME: str = "Adil Secmeli Ders Asistani"
    VERSION: str = "1.0.0"
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DB_NAME = "adil_secmeli.db"
    DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'data', DB_NAME)}"
    WEIGHTS = {"performance": 0.5, "popularity": 0.3, "survey": 0.2}


settings = Settings()
