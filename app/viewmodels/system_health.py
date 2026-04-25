# -*- coding: utf-8 -*-
"""Sistem Sağlığı UI view modeli."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SystemHealthViewModel:
    app_mode: str
    environment: str
    db_path: str
    db_connection_ok: bool
    schema_ok: bool
    debug_tools_enabled: bool
    sql_console_enabled: bool
    sql_console_allowed: bool
    table_count: int
    runtime_schema_mutation_allowed: bool = False

    def lines(self) -> list[str]:
        return [
            f"Uygulama modu: {self.app_mode}",
            f"Ortam: {self.environment}",
            f"DB yolu: {self.db_path}",
            f"DB bağlantısı: {'OK' if self.db_connection_ok else 'Hata'}",
            f"Schema compatibility: {'OK' if self.schema_ok else 'Hata'}",
            f"Tablo sayısı: {self.table_count}",
            f"Developer tools: {'Açık' if self.debug_tools_enabled else 'Kapalı'}",
            f"SQL Console: {'Açık' if self.sql_console_enabled else 'Kapalı'}",
            f"SQL Console yetkisi: {'Var' if self.sql_console_allowed else 'Yok'}",
            f"Runtime schema mutation: {'Açık' if self.runtime_schema_mutation_allowed else 'Kapalı'}",
        ]
