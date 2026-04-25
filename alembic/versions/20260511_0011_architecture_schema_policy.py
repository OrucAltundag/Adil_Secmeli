"""Architecture schema policy audit tables.

Revision ID: 20260511_0011
Revises: 20260510_0010
Create Date: 2026-05-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260511_0011"
down_revision = "20260510_0010"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _create_table_if_missing(table_name: str, *columns) -> None:
    if table_name not in _tables():
        op.create_table(table_name, *columns)


def upgrade() -> None:
    _create_table_if_missing(
        "schema_compat_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("table_name", sa.String(), nullable=False),
        sa.Column("column_name", sa.String()),
        sa.Column("index_name", sa.String()),
        sa.Column("sql_text", sa.Text()),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("message", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "sql_console_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String()),
        sa.Column("sql_text", sa.Text(), nullable=False),
        sa.Column("statement_type", sa.String()),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text()),
        sa.Column("row_count", sa.Integer()),
        sa.Column("executed_at", sa.DateTime()),
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_schema_compat_logs_created ON schema_compat_logs (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sql_console_audit_executed ON sql_console_audit_logs (executed_at)")


def downgrade() -> None:
    for table in ["sql_console_audit_logs", "schema_compat_logs"]:
        if table in _tables():
            op.drop_table(table)
