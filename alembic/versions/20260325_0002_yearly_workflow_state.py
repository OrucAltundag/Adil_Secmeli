"""add yearly criteria workflow state tables

Revision ID: 20260325_0002
Revises: 20260324_0001
Create Date: 2026-03-25 16:20:00
"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260325_0002"
down_revision = "20260324_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS criteria_department_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fakulte_id INTEGER NOT NULL,
            bolum_id INTEGER NOT NULL,
            yil INTEGER NOT NULL,
            criteria_status TEXT NOT NULL DEFAULT 'not_started',
            required_course_count INTEGER NOT NULL DEFAULT 0,
            completed_course_count INTEGER NOT NULL DEFAULT 0,
            missing_course_count INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT,
            UNIQUE(fakulte_id, bolum_id, yil)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS criteria_faculty_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fakulte_id INTEGER NOT NULL,
            yil INTEGER NOT NULL,
            criteria_status TEXT NOT NULL DEFAULT 'not_started',
            total_department_count INTEGER NOT NULL DEFAULT 0,
            completed_department_count INTEGER NOT NULL DEFAULT 0,
            algorithm_run_status TEXT NOT NULL DEFAULT 'not_run',
            algorithm_run_at TEXT,
            generated_year INTEGER,
            year_active INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT,
            UNIQUE(fakulte_id, yil)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS curriculum_generation_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fakulte_id INTEGER NOT NULL,
            bolum_id INTEGER NOT NULL,
            source_year INTEGER NOT NULL,
            generated_year INTEGER NOT NULL,
            dis_bolum_ders_sayisi INTEGER NOT NULL DEFAULT 0,
            run_at TEXT,
            UNIQUE(fakulte_id, bolum_id, source_year, generated_year)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_criteria_department_status_scope
        ON criteria_department_status (fakulte_id, bolum_id, yil)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_criteria_faculty_status_scope
        ON criteria_faculty_status (fakulte_id, yil)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_generation_audit_scope
        ON curriculum_generation_audit (fakulte_id, bolum_id, source_year, generated_year)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_generation_audit_scope")
    op.execute("DROP INDEX IF EXISTS ix_criteria_faculty_status_scope")
    op.execute("DROP INDEX IF EXISTS ix_criteria_department_status_scope")
    op.execute("DROP TABLE IF EXISTS curriculum_generation_audit")
    op.execute("DROP TABLE IF EXISTS criteria_faculty_status")
    op.execute("DROP TABLE IF EXISTS criteria_department_status")
