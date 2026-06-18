"""Add per-course ELECTRE and Decision Tree validation evidence.

Revision ID: 20260618_0013
Revises: 20260512_0012
Create Date: 2026-06-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260618_0013"
down_revision = "20260512_0012"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table_name not in set(inspector.get_table_names()):
        return set()
    return {str(column["name"]) for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    columns = _columns("course_decisions")
    additions = [
        sa.Column("dt_prediction_status", sa.Integer()),
        sa.Column("dt_confidence", sa.Float()),
        sa.Column("dt_comparison", sa.String()),
        sa.Column("dt_rule_path", sa.Text()),
        sa.Column("dt_details_json", sa.Text()),
    ]
    for column in additions:
        if column.name not in columns:
            op.add_column("course_decisions", column)


def downgrade() -> None:
    columns = _columns("course_decisions")
    with op.batch_alter_table("course_decisions") as batch:
        for name in [
            "dt_details_json",
            "dt_rule_path",
            "dt_comparison",
            "dt_confidence",
            "dt_prediction_status",
        ]:
            if name in columns:
                batch.drop_column(name)

