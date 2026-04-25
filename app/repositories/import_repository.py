# -*- coding: utf-8 -*-
"""Import governance kayıtları için repository."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.base import fetch_all_dicts


class ImportRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_batches(self, limit: int = 200) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM import_batches ORDER BY id DESC LIMIT ?", (int(limit),))
        return fetch_all_dicts(cur)
