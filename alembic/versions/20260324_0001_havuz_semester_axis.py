"""add havuz donem axis and unique constraints

Revision ID: 20260324_0001
Revises:
Create Date: 2026-03-24 17:05:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260324_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("havuz"):
        return
    cols = {col["name"] for col in inspector.get_columns("havuz")}

    if "donem" not in cols:
        op.execute("ALTER TABLE havuz ADD COLUMN donem TEXT NOT NULL DEFAULT 'Guz'")

    op.execute(
        """
        UPDATE havuz
        SET donem = CASE
            WHEN LOWER(SUBSTR(TRIM(COALESCE(donem, '')), 1, 1)) = 'b' THEN 'Bahar'
            ELSE 'Guz'
        END
        """
    )

    op.execute(
        """
        DELETE FROM havuz
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM havuz
            GROUP BY ders_id, fakulte_id, yil, donem
        )
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_havuz_ders_fac_yil_donem
        ON havuz (ders_id, fakulte_id, yil, donem)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_havuz_fakulte_yil_donem
        ON havuz (fakulte_id, yil, donem)
        """
    )


def downgrade() -> None:
    # SQLite'da kolon dusurme veri tasima gerektirir; veri kaybi riski olmamasi icin
    # downgrade adiminda sadece indexleri geri aliyoruz.
    op.execute("DROP INDEX IF EXISTS ix_havuz_fakulte_yil_donem")
    op.execute("DROP INDEX IF EXISTS uq_havuz_ders_fac_yil_donem")
