"""add import governance audit tables

Revision ID: 20260504_0004
Revises: 20260503_0003
Create Date: 2026-05-04 10:00:00
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text


revision = "20260504_0004"
down_revision = "20260503_0003"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    row = bind.execute(
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
        CREATE TABLE IF NOT EXISTS import_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_type TEXT NOT NULL,
            source_table TEXT,
            source_import_id INTEGER,
            original_filename TEXT,
            stored_filename TEXT,
            file_hash_sha256 TEXT,
            file_size INTEGER,
            sheet_names_json TEXT,
            row_count INTEGER NOT NULL DEFAULT 0,
            column_count INTEGER NOT NULL DEFAULT 0,
            column_signature_hash TEXT,
            scope_type TEXT,
            school_id INTEGER,
            faculty_id INTEGER,
            department_id INTEGER,
            year INTEGER,
            semester TEXT,
            uploaded_by TEXT,
            uploaded_at TEXT,
            status TEXT NOT NULL DEFAULT 'uploaded',
            previous_import_batch_id INTEGER,
            superseded_by_import_batch_id INTEGER,
            duplicate_of_import_batch_id INTEGER,
            validation_summary_json TEXT,
            quality_score REAL,
            quality_level TEXT,
            error_message TEXT,
            notes TEXT,
            approved_by TEXT,
            approved_at TEXT,
            rejected_by TEXT,
            rejected_at TEXT,
            rejection_reason TEXT,
            rolled_back_by TEXT,
            rolled_back_at TEXT,
            rollback_reason TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS import_quality_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_batch_id INTEGER NOT NULL,
            quality_score REAL NOT NULL DEFAULT 0.0,
            quality_level TEXT NOT NULL DEFAULT 'low',
            required_columns_ok INTEGER NOT NULL DEFAULT 1,
            successful_row_ratio REAL NOT NULL DEFAULT 0.0,
            matched_course_ratio REAL NOT NULL DEFAULT 0.0,
            valid_numeric_ratio REAL NOT NULL DEFAULT 0.0,
            duplicate_row_count INTEGER NOT NULL DEFAULT 0,
            unmatched_row_count INTEGER NOT NULL DEFAULT 0,
            invalid_numeric_count INTEGER NOT NULL DEFAULT 0,
            missing_required_count INTEGER NOT NULL DEFAULT 0,
            out_of_range_count INTEGER NOT NULL DEFAULT 0,
            warning_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            summary_json TEXT,
            created_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS import_row_issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_batch_id INTEGER NOT NULL,
            source_row_id INTEGER,
            row_number INTEGER NOT NULL DEFAULT 0,
            severity TEXT NOT NULL DEFAULT 'warning',
            issue_type TEXT NOT NULL DEFAULT 'unknown_error',
            field_name TEXT,
            raw_value TEXT,
            normalized_value TEXT,
            message TEXT NOT NULL,
            suggestion TEXT,
            created_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS import_diffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_batch_id INTEGER NOT NULL,
            compared_to_import_batch_id INTEGER,
            added_count INTEGER NOT NULL DEFAULT 0,
            removed_count INTEGER NOT NULL DEFAULT 0,
            changed_count INTEGER NOT NULL DEFAULT 0,
            unchanged_count INTEGER NOT NULL DEFAULT 0,
            summary_json TEXT,
            created_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS import_diff_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_diff_id INTEGER NOT NULL,
            change_type TEXT NOT NULL,
            entity_key TEXT,
            course_id INTEGER,
            field_name TEXT,
            before_value TEXT,
            after_value TEXT,
            before_row_json TEXT,
            after_row_json TEXT,
            message TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS import_rollback_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_batch_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            affected_table TEXT NOT NULL,
            affected_record_id INTEGER,
            before_json TEXT,
            after_json TEXT,
            message TEXT,
            created_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_run_import_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_run_id INTEGER,
            import_batch_id INTEGER NOT NULL,
            import_type TEXT NOT NULL,
            created_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS import_impact_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            import_batch_id INTEGER NOT NULL,
            previous_decision_run_id INTEGER,
            new_decision_run_id INTEGER,
            changed_decision_count INTEGER NOT NULL DEFAULT 0,
            curriculum_to_pool_count INTEGER NOT NULL DEFAULT 0,
            pool_to_curriculum_count INTEGER NOT NULL DEFAULT 0,
            rest_candidate_count INTEGER NOT NULL DEFAULT 0,
            cancel_candidate_count INTEGER NOT NULL DEFAULT 0,
            significant_score_change_count INTEGER NOT NULL DEFAULT 0,
            data_confidence_improved_count INTEGER,
            data_confidence_decreased_count INTEGER,
            summary_json TEXT,
            summary_text TEXT,
            created_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS criteria_value_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            faculty_id INTEGER,
            department_id INTEGER,
            field_name TEXT NOT NULL,
            value_text TEXT,
            value_numeric REAL,
            source_type TEXT NOT NULL,
            source_import_batch_id INTEGER,
            source_row_id INTEGER,
            is_locked INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            overridden_by_source_id INTEGER,
            override_reason TEXT,
            created_by TEXT,
            created_at TEXT
        )
        """
    )

    for table_name in ("criteria_import", "survey_import"):
        for column_name, ddl in (
            ("import_batch_id", "INTEGER"),
            ("file_hash_sha256", "TEXT"),
            ("file_size", "INTEGER"),
            ("quality_score", "REAL"),
            ("quality_level", "TEXT"),
            ("previous_import_id", "INTEGER"),
            ("superseded_by_import_id", "INTEGER"),
            ("duplicate_of_import_id", "INTEGER"),
            ("rolled_back_at", "TEXT"),
            ("rollback_reason", "TEXT"),
        ):
            _add_column_if_missing(table_name, column_name, ddl)

    for table_name in ("criteria_import_rows", "survey_import_rows"):
        for column_name, ddl in (
            ("import_batch_id", "INTEGER"),
            ("issue_count", "INTEGER NOT NULL DEFAULT 0"),
            ("normalized_row_json", "TEXT"),
            ("row_hash", "TEXT"),
        ):
            _add_column_if_missing(table_name, column_name, ddl)

    for column_name, ddl in (
        ("source_import_batch_id", "INTEGER"),
        ("is_active", "INTEGER NOT NULL DEFAULT 1"),
        ("superseded_by_import_batch_id", "INTEGER"),
    ):
        _add_column_if_missing("ders_kriterleri", column_name, ddl)

    for ddl in (
        "CREATE INDEX IF NOT EXISTS ix_import_batches_type_scope ON import_batches (import_type, faculty_id, department_id, year, semester, status)",
        "CREATE INDEX IF NOT EXISTS ix_import_batches_hash ON import_batches (file_hash_sha256, import_type)",
        "CREATE INDEX IF NOT EXISTS ix_import_batches_source ON import_batches (source_table, source_import_id)",
        "CREATE INDEX IF NOT EXISTS ix_import_quality_checks_batch ON import_quality_checks (import_batch_id, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_import_row_issues_batch ON import_row_issues (import_batch_id, severity, issue_type)",
        "CREATE INDEX IF NOT EXISTS ix_import_diffs_batch ON import_diffs (import_batch_id, compared_to_import_batch_id)",
        "CREATE INDEX IF NOT EXISTS ix_import_diff_items_diff ON import_diff_items (import_diff_id, change_type)",
        "CREATE INDEX IF NOT EXISTS ix_import_rollback_logs_batch ON import_rollback_logs (import_batch_id, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_decision_run_import_sources_batch ON decision_run_import_sources (import_batch_id, decision_run_id)",
        "CREATE INDEX IF NOT EXISTS ix_import_impact_reports_batch ON import_impact_reports (import_batch_id, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_criteria_value_sources_lookup ON criteria_value_sources (course_id, year, field_name, is_active)",
    ):
        op.execute(ddl)


def downgrade() -> None:
    for table_name in (
        "criteria_value_sources",
        "import_impact_reports",
        "decision_run_import_sources",
        "import_rollback_logs",
        "import_diff_items",
        "import_diffs",
        "import_row_issues",
        "import_quality_checks",
        "import_batches",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table_name}")
