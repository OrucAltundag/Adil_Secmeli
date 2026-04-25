# -*- coding: utf-8 -*-
"""Veritabanı erişimi ve runtime schema davranışı için mimari politika."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import AppConfig, load_app_config


OFFICIAL_DB_ACCESS = "repository"
ALLOW_SQLITE_IN_REPOSITORIES = True
ALLOW_SQLITE_IN_UI = False
ALLOW_SQLITE_IN_API = False
ALLOW_SCHEMA_COMPAT_MUTATION_IN_PRODUCTION = False
ALLOW_SQL_CONSOLE_IN_PRODUCTION = False

SQLITE_ALLOWED_AREAS = {
    "app/db/schema_compat.py": "Legacy SQLite şema uyumluluğu",
    "app/db/sqlite_connection.py": "Merkezi SQLite bağlantı adapterı",
    "app/db/session.py": "Kısa ömürlü session/transaction adapterı",
    "app/repositories": "Kontrollü repository sorguları",
    "app/ui/tabs/view_tab.py": "Admin tablo görüntüleyici ve SQL Console",
}

RAW_SQL_ALLOWED_AREAS = {
    "app/repositories": "Parametreli veri erişim sorguları",
    "app/db/schema_compat.py": "Idempotent legacy şema uyumluluğu",
    "alembic/versions": "Resmi migration dosyaları",
}


@dataclass(frozen=True)
class DatabasePolicySummary:
    official_db_access: str
    sqlite_allowed_in_repositories: bool
    sqlite_allowed_in_ui: bool
    sqlite_allowed_in_api: bool
    schema_compat_enabled: bool
    runtime_schema_mutation_allowed: bool
    sql_console_allowed_in_production: bool
    notes: list[str]


def runtime_schema_mutation_allowed(config: AppConfig | None = None) -> bool:
    cfg = config or load_app_config()
    if not cfg.enable_schema_compat:
        return False
    if cfg.environment == "production":
        return bool(cfg.allow_runtime_schema_mutation and cfg.allow_runtime_schema_mutation_in_production)
    return bool(cfg.allow_runtime_schema_mutation)


def sql_console_allowed_by_policy(config: AppConfig | None = None) -> bool:
    cfg = config or load_app_config()
    if cfg.environment == "production" and not ALLOW_SQL_CONSOLE_IN_PRODUCTION:
        return False
    return bool(cfg.enable_sql_console and cfg.enable_developer_tools)


def database_policy_summary(config: AppConfig | None = None) -> dict[str, Any]:
    cfg = config or load_app_config()
    summary = DatabasePolicySummary(
        official_db_access=OFFICIAL_DB_ACCESS,
        sqlite_allowed_in_repositories=ALLOW_SQLITE_IN_REPOSITORIES,
        sqlite_allowed_in_ui=ALLOW_SQLITE_IN_UI,
        sqlite_allowed_in_api=ALLOW_SQLITE_IN_API,
        schema_compat_enabled=cfg.enable_schema_compat,
        runtime_schema_mutation_allowed=runtime_schema_mutation_allowed(cfg),
        sql_console_allowed_in_production=ALLOW_SQL_CONSOLE_IN_PRODUCTION,
        notes=[
            "Yeni iş kodunda resmi veri erişim yolu Service -> Repository -> SQLAlchemy/DB Session katmanıdır.",
            "schema_compat yalnızca eski/demo SQLite dosyaları için kontrollü uyumluluk katmanıdır.",
            "UI ve API katmanlarında doğrudan DB erişimi yeni kod için yasaktır.",
        ],
    )
    return summary.__dict__
