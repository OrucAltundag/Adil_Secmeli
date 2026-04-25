# -*- coding: utf-8 -*-
"""Karar kayıtları için repository."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.repositories.base import fetch_all_dicts


class DecisionRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM decision_runs ORDER BY id DESC LIMIT ?", (int(limit),))
        return fetch_all_dicts(cur)

    def list_course_decisions(self, decision_run_id: int) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM course_decisions WHERE decision_run_id = ? ORDER BY id", (int(decision_run_id),))
        return fetch_all_dicts(cur)
