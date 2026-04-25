"""add decision governance tables

Revision ID: 20260503_0003
Revises: 20260325_0002
Create Date: 2026-05-03 12:00:00
"""

from __future__ import annotations

from alembic import op


revision = "20260503_0003"
down_revision = "20260325_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ahp_weight_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            scope_type TEXT NOT NULL DEFAULT 'global',
            faculty_id INTEGER,
            department_id INTEGER,
            year INTEGER,
            criteria_keys_json TEXT NOT NULL,
            pairwise_matrix_json TEXT NOT NULL,
            weights_json TEXT NOT NULL,
            consistency_index REAL,
            consistency_ratio REAL,
            is_consistent INTEGER NOT NULL DEFAULT 1,
            source TEXT NOT NULL DEFAULT 'default',
            created_by TEXT,
            notes TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            scope_type TEXT NOT NULL DEFAULT 'global',
            faculty_id INTEGER,
            department_id INTEGER,
            year INTEGER,
            mode TEXT NOT NULL DEFAULT 'static_threshold',
            curriculum_keep_threshold REAL NOT NULL DEFAULT 70,
            pool_threshold REAL NOT NULL DEFAULT 50,
            rest_threshold REAL NOT NULL DEFAULT 40,
            cancel_candidate_threshold REAL DEFAULT 30,
            min_success_rate REAL,
            min_survey_count INTEGER,
            min_enrollment_rate REAL,
            new_course_grace_period_years INTEGER NOT NULL DEFAULT 2,
            low_data_confidence_threshold REAL NOT NULL DEFAULT 0.50,
            sensitivity_margin REAL NOT NULL DEFAULT 3.0,
            top_percent_curriculum REAL,
            middle_percent_pool REAL,
            bottom_percent_rest REAL,
            require_manual_approval_for_cancel INTEGER NOT NULL DEFAULT 1,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_name TEXT NOT NULL,
            year INTEGER NOT NULL,
            faculty_id INTEGER,
            department_id INTEGER,
            semester TEXT,
            algorithm_version TEXT NOT NULL,
            ahp_profile_id INTEGER,
            decision_policy_id INTEGER,
            input_data_hash TEXT,
            status TEXT NOT NULL DEFAULT 'started',
            started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            created_by TEXT,
            summary_json TEXT,
            error_message TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS course_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_run_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            faculty_id INTEGER,
            department_id INTEGER,
            semester TEXT,
            old_status INTEGER,
            recommended_status INTEGER,
            final_status INTEGER,
            topsis_score REAL,
            trend_score REAL,
            trend_label TEXT,
            data_confidence_score REAL,
            decision_stability TEXT,
            approval_required INTEGER NOT NULL DEFAULT 0,
            approval_status TEXT,
            approval_by TEXT,
            approval_at TEXT,
            approval_reason TEXT,
            override_applied INTEGER NOT NULL DEFAULT 0,
            override_reason TEXT,
            main_reason TEXT,
            rule_triggered TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS course_score_breakdowns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_run_id INTEGER,
            course_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            faculty_id INTEGER,
            department_id INTEGER,
            raw_values_json TEXT,
            normalized_values_json TEXT,
            weighted_values_json TEXT,
            weights_json TEXT,
            positive_distance REAL,
            negative_distance REAL,
            closeness_coefficient REAL,
            final_score REAL,
            contribution_json TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS course_trend_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_run_id INTEGER,
            course_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            values_by_year_json TEXT,
            trend_score REAL,
            trend_label TEXT,
            volatility_score REAL,
            data_points_count INTEGER NOT NULL DEFAULT 0,
            explanation TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS course_data_confidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_run_id INTEGER,
            course_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            score REAL NOT NULL DEFAULT 0,
            level TEXT NOT NULL DEFAULT 'low',
            has_success_data INTEGER NOT NULL DEFAULT 0,
            has_popularity_data INTEGER NOT NULL DEFAULT 0,
            has_survey_data INTEGER NOT NULL DEFAULT 0,
            has_trend_data INTEGER NOT NULL DEFAULT 0,
            has_recent_data INTEGER NOT NULL DEFAULT 0,
            survey_count INTEGER,
            data_points_count INTEGER NOT NULL DEFAULT 0,
            missing_fields_json TEXT,
            explanation TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS course_decision_explanations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_decision_id INTEGER NOT NULL,
            main_reason TEXT,
            secondary_reasons_json TEXT,
            positive_factors_json TEXT,
            negative_factors_json TEXT,
            rule_triggered TEXT,
            confidence_level TEXT,
            human_readable_text TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_sensitivity_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_run_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            base_score REAL,
            min_score REAL,
            max_score REAL,
            score_range REAL,
            decision_changed INTEGER NOT NULL DEFAULT 0,
            stability_level TEXT NOT NULL DEFAULT 'medium',
            tested_variations_json TEXT,
            explanation TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_fairness_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_run_id INTEGER NOT NULL,
            faculty_id INTEGER,
            department_id INTEGER,
            year INTEGER NOT NULL,
            report_json TEXT,
            summary_text TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS course_governance_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            strategic_flag INTEGER NOT NULL DEFAULT 0,
            accreditation_flag INTEGER NOT NULL DEFAULT 0,
            instructor_changed INTEGER NOT NULL DEFAULT 0,
            content_updated INTEGER NOT NULL DEFAULT 0,
            protected_until_year INTEGER,
            notes TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(course_id)
        )
        """
    )

    indexes = [
        "CREATE INDEX IF NOT EXISTS ix_ahp_profiles_scope ON ahp_weight_profiles (scope_type, faculty_id, department_id, year, is_active)",
        "CREATE INDEX IF NOT EXISTS ix_decision_policies_scope ON decision_policies (scope_type, faculty_id, department_id, year, is_active)",
        "CREATE INDEX IF NOT EXISTS ix_decision_runs_scope ON decision_runs (year, faculty_id, department_id, semester, status)",
        "CREATE INDEX IF NOT EXISTS ix_course_decisions_run ON course_decisions (decision_run_id, course_id)",
        "CREATE INDEX IF NOT EXISTS ix_course_score_breakdowns_run ON course_score_breakdowns (decision_run_id, course_id)",
        "CREATE INDEX IF NOT EXISTS ix_course_trend_run ON course_trend_analysis (decision_run_id, course_id)",
        "CREATE INDEX IF NOT EXISTS ix_course_confidence_run ON course_data_confidence (decision_run_id, course_id)",
        "CREATE INDEX IF NOT EXISTS ix_sensitivity_run ON decision_sensitivity_results (decision_run_id, course_id)",
        "CREATE INDEX IF NOT EXISTS ix_fairness_run ON decision_fairness_reports (decision_run_id)",
    ]
    for ddl in indexes:
        op.execute(ddl)


def downgrade() -> None:
    for index_name in [
        "ix_fairness_run",
        "ix_sensitivity_run",
        "ix_course_confidence_run",
        "ix_course_trend_run",
        "ix_course_score_breakdowns_run",
        "ix_course_decisions_run",
        "ix_decision_runs_scope",
        "ix_decision_policies_scope",
        "ix_ahp_profiles_scope",
    ]:
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
    for table_name in [
        "course_governance_flags",
        "decision_fairness_reports",
        "decision_sensitivity_results",
        "course_decision_explanations",
        "course_data_confidence",
        "course_trend_analysis",
        "course_score_breakdowns",
        "course_decisions",
        "decision_runs",
        "decision_policies",
        "ahp_weight_profiles",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table_name}")
