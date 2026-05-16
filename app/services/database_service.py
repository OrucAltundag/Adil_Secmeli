# -*- coding: utf-8 -*-
"""UI dışındaki katmanlar için SQLite database adapter servisi."""

from __future__ import annotations

from app.core.config import AppConfig, load_app_config
from app.repositories.sqlite_repository import SQLiteRepository


class DatabaseService:
    def __init__(self, db_path: str | None = None, config: AppConfig | None = None):
        self.config = config or load_app_config()
        self.db_path = db_path or self.config.sqlite_db_path
        self.repository = SQLiteRepository(self.db_path)

    def table_names(self) -> list[str]:
        return self.repository.table_names()

    def table_count(self) -> int:
        return self.repository.table_count()

    def database_profile(self) -> list[dict[str, object]]:
        return self.repository.profile_tables()
