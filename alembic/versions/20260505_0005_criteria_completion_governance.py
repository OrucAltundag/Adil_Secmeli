"""add criteria completion governance tables

Revision ID: 20260505_0005
Revises: 20260504_0004
Create Date: 2026-05-05 10:00:00
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text


revision = "20260505_0005"
down_revision = "20260504_0004"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    row = op.get_bind().execute(
        text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name LIMIT 1"),
        {"name": table_name},
    ).fetchone()
    return bool(row)


def _column_names(table_name: str) -> set[str]:
    if not _table_exists(table_name):
        return set()
    rows = op.get_bind().execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return {str(row[1]) for row in rows}


def _add_column_if_missing(table_name: str, column_name: str, ddl: str) -> None:
    if not _table_exists(table_name):
        return
    if column_name not in _column_names(table_name):
        op.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}")


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS criteria_completion_matrix (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope_type TEXT NOT NULL,
            faculty_id INTEGER,
            department_id INTEGER,
            course_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            semester TEXT,
            criterion_key TEXT NOT NULL,
            is_required INTEGER NOT NULL DEFAULT 1,
            is_present INTEGER NOT NULL DEFAULT 0,
            is_valid INTEGER NOT NULL DEFAULT 0,
            value_text TEXT,
            value_numeric REAL,
            missing_reason TEXT,
            invalid_reason TEXT,
            source_type TEXT,
            source_id INTEGER,
            checked_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS criteria_validation_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope_type TEXT NOT NULL,
            faculty_id INTEGER,
            department_id INTEGER,
            course_id INTEGER,
            year INTEGER NOT NULL,
            semester TEXT,
            criterion_key TEXT,
            severity TEXT NOT NULL DEFAULT 'warning',
            issue_type TEXT NOT NULL DEFAULT 'unknown_error',
            raw_value TEXT,
            message TEXT NOT NULL,
            suggestion TEXT,
            created_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS criteria_completion_policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            scope_type TEXT NOT NULL DEFAULT 'global',
            faculty_id INTEGER,
            department_id INTEGER,
            year INTEGER,
            semester TEXT,
            required_completion_ratio REAL NOT NULL DEFAULT 1.0,
            required_fields_json TEXT NOT NULL,
            optional_fields_json TEXT,
            allow_new_course_missing_history INTEGER NOT NULL DEFAULT 1,
            new_course_grace_period_years INTEGER NOT NULL DEFAULT 2,
            min_survey_response_count INTEGER,
            block_on_invalid_numeric INTEGER NOT NULL DEFAULT 1,
            block_on_critical_issues INTEGER NOT NULL DEFAULT 1,
            allow_override INTEGER NOT NULL DEFAULT 1,
            override_requires_reason INTEGER NOT NULL DEFAULT 1,
            override_requires_approval INTEGER NOT NULL DEFAULT 1,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT,
            updated_at TEXT,
            notes TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS criteria_missing_data_risks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope_type TEXT NOT NULL,
            faculty_id INTEGER,
            department_id INTEGER,
            course_id INTEGER,
            year INTEGER NOT NULL,
            semester TEXT,
            risk_score REAL NOT NULL DEFAULT 0.0,
            risk_level TEXT NOT NULL DEFAULT 'low',
            missing_required_fields_json TEXT,
            missing_optional_fields_json TEXT,
            affected_weight_sum REAL,
            explanation TEXT,
            created_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS criteria_completion_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope_type TEXT NOT NULL,
            faculty_id INTEGER,
            department_id INTEGER,
            course_id INTEGER,
            year INTEGER NOT NULL,
            semester TEXT,
            assigned_to TEXT,
            assigned_role TEXT,
            due_date TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            missing_fields_json TEXT,
            validation_issues_json TEXT,
            priority TEXT NOT NULL DEFAULT 'medium',
            created_by TEXT,
            created_at TEXT,
            updated_at TEXT,
            completed_at TEXT,
            approved_by TEXT,
            approved_at TEXT,
            notes TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS criteria_completion_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope_type TEXT NOT NULL,
            faculty_id INTEGER,
            department_id INTEGER,
            course_id INTEGER,
            year INTEGER NOT NULL,
            semester TEXT,
            missing_fields_json TEXT,
            validation_issues_json TEXT,
            reason TEXT NOT NULL,
            requested_by TEXT,
            requested_at TEXT,
            approval_status TEXT NOT NULL DEFAULT 'pending',
            approved_by TEXT,
            approved_at TEXT,
            rejected_by TEXT,
            rejected_at TEXT,
            rejection_reason TEXT,
            expires_at TEXT,
            allowed_for_run_id INTEGER,
            used_at TEXT,
            created_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS criteria_completion_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope_type TEXT NOT NULL,
            faculty_id INTEGER,
            department_id INTEGER,
            year INTEGER NOT NULL,
            semester TEXT,
            old_status TEXT,
            new_status TEXT NOT NULL,
            old_completion_ratio REAL,
            new_completion_ratio REAL NOT NULL DEFAULT 0.0,
            old_completion_level TEXT,
            new_completion_level TEXT,
            changed_by TEXT,
            change_reason TEXT,
            created_at TEXT,
            summary_json TEXT
        )
        """
    )

    for table_name in ("criteria_department_status", "criteria_faculty_status"):
        for column_name, ddl in (
            ("semester", "TEXT"),
            ("completion_ratio", "REAL NOT NULL DEFAULT 0.0"),
            ("completion_level", "TEXT NOT NULL DEFAULT 'not_started'"),
            ("required_completion_ratio", "REAL NOT NULL DEFAULT 1.0"),
            ("total_courses", "INTEGER NOT NULL DEFAULT 0"),
            ("completed_courses", "INTEGER NOT NULL DEFAULT 0"),
            ("partial_courses", "INTEGER NOT NULL DEFAULT 0"),
            ("missing_courses", "INTEGER NOT NULL DEFAULT 0"),
            ("invalid_courses", "INTEGER NOT NULL DEFAULT 0"),
            ("total_required_fields", "INTEGER NOT NULL DEFAULT 0"),
            ("completed_required_fields", "INTEGER NOT NULL DEFAULT 0"),
            ("missing_required_fields", "INTEGER NOT NULL DEFAULT 0"),
            ("invalid_required_fields", "INTEGER NOT NULL DEFAULT 0"),
            ("last_checked_at", "TEXT"),
            ("blocking_reason", "TEXT"),
            ("can_run_algorithm", "INTEGER NOT NULL DEFAULT 0"),
            ("override_active", "INTEGER NOT NULL DEFAULT 0"),
        ):
            _add_column_if_missing(table_name, column_name, ddl)

    for ddl in (
        "CREATE INDEX IF NOT EXISTS ix_criteria_completion_matrix_scope ON criteria_completion_matrix (scope_type, faculty_id, department_id, year, semester, course_id)",
        "CREATE INDEX IF NOT EXISTS ix_criteria_completion_matrix_field ON criteria_completion_matrix (criterion_key, is_required, is_present, is_valid)",
        "CREATE INDEX IF NOT EXISTS ix_criteria_validation_issues_scope ON criteria_validation_issues (scope_type, faculty_id, department_id, year, semester, severity)",
        "CREATE INDEX IF NOT EXISTS ix_criteria_completion_policies_scope ON criteria_completion_policies (scope_type, faculty_id, department_id, year, semester, is_active)",
        "CREATE INDEX IF NOT EXISTS ix_criteria_missing_data_risks_scope ON criteria_missing_data_risks (scope_type, faculty_id, department_id, year, semester, risk_level)",
        "CREATE INDEX IF NOT EXISTS ix_criteria_completion_tasks_scope ON criteria_completion_tasks (scope_type, faculty_id, department_id, year, semester, status)",
        "CREATE INDEX IF NOT EXISTS ix_criteria_completion_overrides_scope ON criteria_completion_overrides (scope_type, faculty_id, department_id, course_id, year, semester, approval_status)",
        "CREATE INDEX IF NOT EXISTS ix_criteria_completion_history_scope ON criteria_completion_history (scope_type, faculty_id, department_id, year, semester, created_at)",
    ):
        op.execute(ddl)


def downgrade() -> None:
    for table_name in (
        "criteria_completion_history",
        "criteria_completion_overrides",
        "criteria_completion_tasks",
        "criteria_missing_data_risks",
        "criteria_completion_policies",
        "criteria_validation_issues",
        "criteria_completion_matrix",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table_name}")
