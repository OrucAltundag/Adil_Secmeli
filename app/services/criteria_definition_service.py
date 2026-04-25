# -*- coding: utf-8 -*-
"""AHP/TOPSIS karar kriteri tanım servisi."""

from __future__ import annotations

from datetime import datetime
import sqlite3
from typing import Any

from app.db.schema_compat import ensure_ahp_governance_schema


DEFAULT_DECISION_CRITERIA = [
    ("basari", "Başarı", "Başarı oranı ve not ortalaması etkisi.", "score", 1, 1, 0.0, 1.0, "minmax", "computed", 10),
    ("trend", "Trend", "Son yıllardaki yükseliş/düşüş eğilimi.", "score", 1, 1, 0.0, 1.0, "minmax", "computed", 20),
    ("populerlik", "Popülerlik / Doluluk", "Kontenjan doluluğu ve talep göstergesi.", "ratio", 1, 1, 0.0, 1.0, "minmax", "criteria_import", 30),
    ("anket", "Anket Talebi", "Öğrenci anket talebi.", "score", 1, 1, 0.0, 1.0, "minmax", "survey_import", 40),
]


def seed_default_decision_criteria(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    ensure_ahp_governance_schema(conn, commit=False)
    now = _now()
    for row in DEFAULT_DECISION_CRITERIA:
        conn.execute(
            """
            INSERT INTO decision_criteria_definitions (
                criterion_key, display_name, description, criterion_type, is_benefit,
                default_enabled, min_value, max_value, normalization_method, source_type,
                sort_order, is_active, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(criterion_key) DO UPDATE SET
                display_name=excluded.display_name,
                description=excluded.description,
                criterion_type=excluded.criterion_type,
                is_benefit=excluded.is_benefit,
                default_enabled=excluded.default_enabled,
                min_value=excluded.min_value,
                max_value=excluded.max_value,
                normalization_method=excluded.normalization_method,
                source_type=excluded.source_type,
                sort_order=excluded.sort_order,
                updated_at=excluded.updated_at
            """,
            (*row, now, now),
        )
    return list_active_criteria(conn)


def list_active_criteria(conn: sqlite3.Connection, include_inactive: bool = False) -> list[dict[str, Any]]:
    ensure_ahp_governance_schema(conn, commit=False)
    cur = conn.execute("SELECT COUNT(*) FROM decision_criteria_definitions")
    if int(cur.fetchone()[0] or 0) == 0:
        seed_default_decision_criteria(conn)
    sql = "SELECT * FROM decision_criteria_definitions"
    if not include_inactive:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY sort_order, criterion_key"
    cur = conn.execute(sql)
    return [_row_dict(row) for row in cur.fetchall()]


def get_criterion(conn: sqlite3.Connection, criterion_key: str) -> dict[str, Any] | None:
    list_active_criteria(conn, include_inactive=True)
    cur = conn.execute("SELECT * FROM decision_criteria_definitions WHERE criterion_key=?", (str(criterion_key),))
    row = cur.fetchone()
    return _row_dict(row) if row else None


def create_or_update_criterion(
    conn: sqlite3.Connection,
    *,
    criterion_key: str,
    display_name: str,
    description: str | None = None,
    criterion_type: str = "score",
    is_benefit: bool = True,
    default_enabled: bool = True,
    min_value: float | None = None,
    max_value: float | None = None,
    normalization_method: str | None = "minmax",
    source_type: str | None = "manual",
    sort_order: int = 100,
    is_active: bool = True,
) -> dict[str, Any]:
    ensure_ahp_governance_schema(conn, commit=False)
    now = _now()
    conn.execute(
        """
        INSERT INTO decision_criteria_definitions (
            criterion_key, display_name, description, criterion_type, is_benefit,
            default_enabled, min_value, max_value, normalization_method, source_type,
            sort_order, is_active, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(criterion_key) DO UPDATE SET
            display_name=excluded.display_name,
            description=excluded.description,
            criterion_type=excluded.criterion_type,
            is_benefit=excluded.is_benefit,
            default_enabled=excluded.default_enabled,
            min_value=excluded.min_value,
            max_value=excluded.max_value,
            normalization_method=excluded.normalization_method,
            source_type=excluded.source_type,
            sort_order=excluded.sort_order,
            is_active=excluded.is_active,
            updated_at=excluded.updated_at
        """,
        (
            criterion_key,
            display_name,
            description,
            criterion_type,
            int(is_benefit),
            int(default_enabled),
            min_value,
            max_value,
            normalization_method,
            source_type,
            int(sort_order),
            int(is_active),
            now,
            now,
        ),
    )
    row = get_criterion(conn, criterion_key)
    assert row is not None
    return row


def deactivate_criterion(conn: sqlite3.Connection, criterion_key: str) -> dict[str, Any]:
    ensure_ahp_governance_schema(conn, commit=False)
    conn.execute(
        "UPDATE decision_criteria_definitions SET is_active=0, updated_at=? WHERE criterion_key=?",
        (_now(), str(criterion_key)),
    )
    row = get_criterion(conn, criterion_key)
    return row or {"criterion_key": criterion_key, "is_active": False}


def criteria_direction_map(conn: sqlite3.Connection) -> dict[str, bool]:
    return {row["criterion_key"]: bool(row["is_benefit"]) for row in list_active_criteria(conn)}


def _row_dict(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    if isinstance(row, sqlite3.Row):
        data = {key: row[key] for key in row.keys()}
    else:
        # sqlite3 default tuple mode is not expected here, but keep safe fallback.
        keys = [
            "id",
            "criterion_key",
            "display_name",
            "description",
            "criterion_type",
            "is_benefit",
            "default_enabled",
            "min_value",
            "max_value",
            "normalization_method",
            "source_type",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        ]
        data = dict(zip(keys, row))
    for key in ("is_benefit", "default_enabled", "is_active"):
        if key in data:
            data[key] = bool(data[key])
    return data


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
