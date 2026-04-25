# -*- coding: utf-8 -*-
"""Merkezi uygulama konfigürasyonu."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle) or {}
    except Exception:
        return {}


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
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    @property
    def db_path(self) -> str:
        return self.sqlite_db_path

    def as_legacy_dict(self) -> dict[str, Any]:
        return {
            "db_path": self.sqlite_db_path,
            "db_url": self.database_url,
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
        }


def load_app_config(config_path: str = "config.json") -> AppConfig:
    """config.json + environment değerlerini tek yerde birleştirir."""
    if load_dotenv is not None:
        load_dotenv(override=False)
    cfg = _load_json(config_path)
    base_dir = Path(__file__).resolve().parents[2]
    default_db = Path(cfg.get("db_path") or base_dir / "data" / "adil_secmeli.db")
    db_path = Path(os.getenv("SQLITE_DB_PATH") or os.getenv("DB_PATH") or default_db)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
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
    database_url = str(os.getenv("DATABASE_URL") or cfg.get("db_url") or f"sqlite:///{db_path}")
    return AppConfig(
        project_name=str(cfg.get("project_name") or os.getenv("PROJECT_NAME") or "Adil Seçmeli"),
        version=str(cfg.get("version") or os.getenv("APP_VERSION") or "1.0.0"),
        app_mode=str(os.getenv("APP_MODE") or cfg.get("app_mode") or "auto"),
        environment=environment,
        sqlite_db_path=str(db_path),
        database_url=database_url,
        debug=debug,
        enable_sql_console=enable_sql_console,
        enable_developer_tools=developer_tools,
        enable_schema_compat=enable_schema_compat,
        allow_runtime_schema_mutation=allow_runtime_schema_mutation,
        allow_runtime_schema_mutation_in_production=allow_runtime_schema_mutation_in_production,
        api_auth_enabled=_bool(os.getenv("API_AUTH_ENABLED"), _bool(cfg.get("api_auth_enabled"), False)),
        enable_ml_decision_influence=_bool(os.getenv("ENABLE_ML_DECISION_INFLUENCE"), _bool(cfg.get("enable_ml_decision_influence"), False)),
        require_high_confidence_for_ml_influence=_bool(os.getenv("REQUIRE_HIGH_CONFIDENCE_FOR_ML_INFLUENCE"), _bool(cfg.get("require_high_confidence_for_ml_influence"), True)),
        allow_experimental_ml_in_decision=_bool(os.getenv("ALLOW_EXPERIMENTAL_ML_IN_DECISION"), _bool(cfg.get("allow_experimental_ml_in_decision"), False)),
        api_host=str(os.getenv("API_HOST") or cfg.get("api_host") or "0.0.0.0"),
        api_port=_int(os.getenv("API_PORT") or cfg.get("api_port"), 8000),
        log_level=str(os.getenv("LOG_LEVEL") or cfg.get("log_level") or "INFO").upper(),
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
