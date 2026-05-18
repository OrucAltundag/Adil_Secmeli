# -*- coding: utf-8 -*-
"""Copy the current SQLite data set into a PostgreSQL database.

This script creates the current SQLAlchemy model schema on PostgreSQL, copies
common columns from the SQLite source, and reports source/target row counts.
It intentionally refuses to append into non-empty target tables unless the user
passes an explicit flag.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

import sqlalchemy as sa

from app.core.config import load_app_config
from app.db.backend import is_postgresql_url
from app.db.models import Base
from app.db.session import stamp_database_head

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
BATCH_SIZE = 500


def _quote_ident(name: str) -> str:
    if not IDENTIFIER_RE.match(name):
        raise ValueError(f"Gecersiz tablo/kolon adi: {name}")
    return '"' + name.replace('"', '""') + '"'


def _sqlite_table_names(conn: sqlite3.Connection) -> set[str]:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return {str(row[0]) for row in cur.fetchall()}


def _sqlite_column_names(conn: sqlite3.Connection, table_name: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({_quote_ident(table_name)})")
    return {str(row[1]) for row in cur.fetchall()}


def _sqlite_column_info(conn: sqlite3.Connection, table_name: str) -> list[sqlite3.Row]:
    return list(conn.execute(f"PRAGMA table_info({_quote_ident(table_name)})").fetchall())


def _sqlite_type_to_sa(type_name: str) -> sa.types.TypeEngine:
    normalized = str(type_name or "").strip().upper()
    if "INT" in normalized:
        return sa.Integer()
    if any(token in normalized for token in ("REAL", "FLOA", "DOUB")):
        return sa.Float()
    if "BLOB" in normalized:
        return sa.LargeBinary()
    if any(token in normalized for token in ("NUM", "DEC")):
        return sa.Float()
    return sa.Text()


def _legacy_table_from_sqlite(conn: sqlite3.Connection, table_name: str, metadata: sa.MetaData) -> sa.Table:
    columns: list[sa.Column] = []
    for row in _sqlite_column_info(conn, table_name):
        name = str(row["name"])
        is_pk = bool(row["pk"])
        columns.append(
            sa.Column(
                name,
                _sqlite_type_to_sa(str(row["type"])),
                primary_key=is_pk,
                nullable=False if is_pk else not bool(row["notnull"]),
            )
        )
    if not columns:
        raise ValueError(f"Tabloda kolon bulunamadi: {table_name}")
    return sa.Table(table_name, metadata, *columns)


def _target_count(conn: sa.Connection, table_name: str) -> int:
    row = conn.exec_driver_sql(f"SELECT COUNT(*) FROM {_quote_ident(table_name)}").fetchone()
    return int(row[0] or 0) if row else 0


def _source_count(conn: sqlite3.Connection, table_name: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) FROM {_quote_ident(table_name)}").fetchone()
    return int(row[0] or 0) if row else 0


def _iter_sqlite_rows(
    conn: sqlite3.Connection,
    table_name: str,
    columns: list[str],
    *,
    batch_size: int = BATCH_SIZE,
):
    quoted_cols = ", ".join(_quote_ident(col) for col in columns)
    cur = conn.execute(f"SELECT {quoted_cols} FROM {_quote_ident(table_name)}")
    while True:
        rows = cur.fetchmany(batch_size)
        if not rows:
            break
        yield [dict(row) for row in rows]


def _coerce_value(column: sa.Column, value: Any) -> Any:
    if value is None:
        return None
    column_type = column.type
    if isinstance(column_type, sa.Boolean):
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "t", "yes", "y", "evet", "on"}
        return bool(value)
    if isinstance(column_type, sa.DateTime) and isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            try:
                return datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None
    if isinstance(column_type, sa.Date) and not isinstance(column_type, sa.DateTime) and isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None
    return value


def _coerce_batch(table: sa.Table, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    columns = table.c
    return [
        {name: _coerce_value(columns[name], value) for name, value in row.items()}
        for row in rows
    ]


def _reset_postgres_sequence(conn: sa.Connection, table: sa.Table) -> None:
    integer_pk = [
        col.name
        for col in table.primary_key.columns
        if isinstance(col.type, sa.Integer)
    ]
    if len(integer_pk) != 1:
        return
    table_name = table.name
    column_name = integer_pk[0]
    quoted_table = _quote_ident(table_name)
    quoted_col = _quote_ident(column_name)
    sequence_row = conn.exec_driver_sql(
        "SELECT pg_get_serial_sequence(%s, %s)",
        (table_name, column_name),
    ).fetchone()
    if not sequence_row or not sequence_row[0]:
        return
    conn.exec_driver_sql(
        f"""
        SELECT setval(
            %s::regclass,
            COALESCE((SELECT MAX({quoted_col}) FROM {quoted_table}), 1),
            (SELECT MAX({quoted_col}) IS NOT NULL FROM {quoted_table})
        )
        """,
        (str(sequence_row[0]),),
    )


def migrate(
    sqlite_path: str | Path,
    postgres_url: str,
    *,
    truncate_target: bool = False,
    append: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    sqlite_path = Path(sqlite_path).resolve()
    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite kaynak bulunamadi: {sqlite_path}")
    if not is_postgresql_url(postgres_url):
        raise ValueError("Hedef DATABASE_URL postgresql+psycopg://... biciminde olmali.")
    if truncate_target and append:
        raise ValueError("--truncate-target ve --append birlikte kullanilamaz.")

    engine = sa.create_engine(postgres_url, future=True)
    source = sqlite3.connect(sqlite_path)
    source.row_factory = sqlite3.Row
    result: dict[str, Any] = {
        "source": str(sqlite_path),
        "target_backend": "postgresql",
        "dry_run": dry_run,
        "truncate_target": truncate_target,
        "append": append,
        "tables": {},
        "skipped_tables": [],
    }
    try:
        source_tables = _sqlite_table_names(source)
        if not dry_run:
            Base.metadata.create_all(bind=engine)
            stamp_database_head(engine)
        legacy_metadata = sa.MetaData()
        model_table_names = set(Base.metadata.tables.keys())
        model_tables = [table for table in Base.metadata.sorted_tables if table.name in source_tables]
        legacy_tables = [
            _legacy_table_from_sqlite(source, table_name, legacy_metadata)
            for table_name in sorted(source_tables - model_table_names - {"alembic_version"})
        ]
        if not dry_run:
            legacy_metadata.create_all(bind=engine)
        tables_to_copy = [*model_tables, *legacy_tables]

        with engine.begin() as target:
            if truncate_target and not dry_run:
                for table in reversed(tables_to_copy):
                    target.exec_driver_sql(f"TRUNCATE TABLE {_quote_ident(table.name)} RESTART IDENTITY CASCADE")

            for table in tables_to_copy:
                source_columns = _sqlite_column_names(source, table.name)
                common_columns = [col.name for col in table.columns if col.name in source_columns]
                if not common_columns:
                    result["skipped_tables"].append({"table": table.name, "reason": "common_column_not_found"})
                    continue

                source_count = _source_count(source, table.name)
                target_before = 0 if dry_run else _target_count(target, table.name)
                if target_before and source_count and not append and not truncate_target:
                    raise RuntimeError(
                        f"Hedef tablo bos degil: {table.name}. Devam icin --append "
                        "veya hedefi temizlemek icin --truncate-target kullanin."
                    )

                inserted = 0
                if not dry_run and source_count:
                    for batch in _iter_sqlite_rows(source, table.name, common_columns):
                        coerced = _coerce_batch(table, batch)
                        if coerced:
                            target.execute(sa.insert(table), coerced)
                            inserted += len(coerced)
                    _reset_postgres_sequence(target, table)

                target_after = target_before if dry_run else _target_count(target, table.name)
                result["tables"][table.name] = {
                    "source_rows": source_count,
                    "target_rows_before": target_before,
                    "inserted_rows": inserted,
                    "target_rows_after": target_after,
                    "columns_copied": common_columns,
                }
    finally:
        source.close()
        engine.dispose()
    return result


def _parse_args() -> argparse.Namespace:
    cfg = load_app_config()
    parser = argparse.ArgumentParser(description="SQLite verisini PostgreSQL'e tasir.")
    parser.add_argument("--sqlite-path", default=cfg.sqlite_db_path, help="Kaynak SQLite .db dosyasi.")
    parser.add_argument("--postgres-url", default=os.getenv("DATABASE_URL") or cfg.database_url, help="Hedef PostgreSQL SQLAlchemy URL.")
    parser.add_argument("--truncate-target", action="store_true", help="Hedef tablolari kopyalamadan once temizle.")
    parser.add_argument("--append", action="store_true", help="Bos olmayan hedef tablolara eklemeye izin ver.")
    parser.add_argument("--dry-run", action="store_true", help="Veri yazmadan tablo/satir planini raporla.")
    parser.add_argument("--json", action="store_true", help="Sonucu JSON olarak yazdir.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = migrate(
        sqlite_path=args.sqlite_path,
        postgres_url=args.postgres_url,
        truncate_target=args.truncate_target,
        append=args.append,
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Kaynak: {report['source']}")
        print(f"Hedef: {report['target_backend']}")
        for table_name, item in report["tables"].items():
            print(
                f"- {table_name}: source={item['source_rows']} "
                f"inserted={item['inserted_rows']} target={item['target_rows_after']}"
            )
        if report["skipped_tables"]:
            print(f"Atlanan tablolar: {len(report['skipped_tables'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
