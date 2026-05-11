"""Security and data quality schema completion.

Revision ID: 20260512_0012
Revises: 20260511_0011
Create Date: 2026-05-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260512_0012"
down_revision = "20260511_0011"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table_name: str) -> set[str]:
    if table_name not in _tables():
        return set()
    return {str(col["name"]) for col in sa.inspect(op.get_bind()).get_columns(table_name)}


def _create_table_if_missing(table_name: str, *columns) -> None:
    if table_name not in _tables():
        op.create_table(table_name, *columns)


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if table_name in _tables() and column.name not in _columns(table_name):
        op.add_column(table_name, column)


def _add_columns(table_name: str, columns: list[sa.Column]) -> None:
    for column in columns:
        _add_column_if_missing(table_name, column)


def upgrade() -> None:
    _add_columns(
        "sql_console_audit_logs",
        [
            sa.Column("client_id", sa.String()),
            sa.Column("role", sa.String()),
            sa.Column("read_only", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("dangerous", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("allowed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("environment", sa.String()),
            sa.Column("request_id", sa.String()),
        ],
    )

    _create_table_if_missing(
        "api_clients",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("client_name", sa.String(), nullable=False),
        sa.Column("api_key_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="api_client"),
        sa.Column("faculty_id", sa.Integer()),
        sa.Column("department_id", sa.Integer()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("last_used_at", sa.DateTime()),
        sa.Column("notes", sa.Text()),
    )
    _create_table_if_missing(
        "secure_import_jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("import_type", sa.String(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("stored_filename", sa.String()),
        sa.Column("file_hash", sa.String(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String()),
        sa.Column("uploaded_by", sa.String()),
        sa.Column("uploaded_at", sa.DateTime()),
        sa.Column("faculty_id", sa.Integer()),
        sa.Column("department_id", sa.Integer()),
        sa.Column("year", sa.Integer()),
        sa.Column("semester", sa.String()),
        sa.Column("status", sa.String(), nullable=False, server_default="uploaded"),
        sa.Column("validation_summary_json", sa.Text()),
        sa.Column("preview_summary_json", sa.Text()),
        sa.Column("row_count", sa.Integer()),
        sa.Column("warning_count", sa.Integer()),
        sa.Column("error_count", sa.Integer()),
        sa.Column("critical_count", sa.Integer()),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("approved_by", sa.String()),
        sa.Column("approved_at", sa.DateTime()),
        sa.Column("rejected_by", sa.String()),
        sa.Column("rejected_at", sa.DateTime()),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("applied_by", sa.String()),
        sa.Column("applied_at", sa.DateTime()),
        sa.Column("rollback_available", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("rollback_snapshot_id", sa.String()),
        sa.Column("notes", sa.Text()),
    )
    _create_table_if_missing(
        "secure_import_job_rows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("import_job_id", sa.String(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw_data_json", sa.Text(), nullable=False),
        sa.Column("normalized_data_json", sa.Text()),
        sa.Column("matched_course_id", sa.Integer()),
        sa.Column("row_status", sa.String(), nullable=False, server_default="valid"),
        sa.Column("issues_json", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "security_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("actor_type", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String()),
        sa.Column("role", sa.String()),
        sa.Column("faculty_id", sa.Integer()),
        sa.Column("department_id", sa.Integer()),
        sa.Column("resource_type", sa.String()),
        sa.Column("resource_id", sa.String()),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("severity", sa.String(), nullable=False, server_default="info"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("before_json", sa.Text()),
        sa.Column("after_json", sa.Text()),
        sa.Column("metadata_json", sa.Text()),
        sa.Column("request_id", sa.String()),
        sa.Column("ip_address", sa.String()),
        sa.Column("user_agent", sa.String()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("previous_hash", sa.String()),
        sa.Column("event_hash", sa.String()),
    )
    _create_table_if_missing(
        "data_snapshots",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("snapshot_type", sa.String(), nullable=False),
        sa.Column("scope_type", sa.String(), nullable=False),
        sa.Column("faculty_id", sa.Integer()),
        sa.Column("department_id", sa.Integer()),
        sa.Column("year", sa.Integer()),
        sa.Column("related_import_job_id", sa.String()),
        sa.Column("related_decision_run_id", sa.Integer()),
        sa.Column("snapshot_path", sa.String()),
        sa.Column("snapshot_hash", sa.String()),
        sa.Column("created_by", sa.String()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("notes", sa.Text()),
    )

    _create_table_if_missing(
        "data_coverage_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope_type", sa.String(), nullable=False, server_default="global"),
        sa.Column("faculty_id", sa.Integer()),
        sa.Column("department_id", sa.Integer()),
        sa.Column("year", sa.Integer()),
        sa.Column("semester", sa.String()),
        sa.Column("total_courses", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("courses_with_criteria", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("courses_with_performance", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("courses_with_popularity", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("courses_with_survey", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("courses_with_score", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("courses_with_trend_data", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("criteria_coverage_ratio", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("performance_coverage_ratio", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("popularity_coverage_ratio", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("survey_coverage_ratio", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("score_coverage_ratio", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("trend_coverage_ratio", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("overall_coverage_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("missing_data_summary_json", sa.Text()),
        sa.Column("recommendations_json", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    _add_columns(
        "data_coverage_reports",
        [
            sa.Column("scope_type", sa.String(), nullable=False, server_default="global"),
            sa.Column("faculty_id", sa.Integer()),
            sa.Column("department_id", sa.Integer()),
            sa.Column("year", sa.Integer()),
            sa.Column("semester", sa.String()),
            sa.Column("total_courses", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("courses_with_criteria", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("courses_with_performance", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("courses_with_popularity", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("courses_with_survey", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("courses_with_score", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("courses_with_trend_data", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("criteria_coverage_ratio", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("performance_coverage_ratio", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("popularity_coverage_ratio", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("survey_coverage_ratio", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("score_coverage_ratio", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("trend_coverage_ratio", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("overall_coverage_score", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("missing_data_summary_json", sa.Text()),
            sa.Column("recommendations_json", sa.Text()),
            sa.Column("created_at", sa.DateTime()),
        ],
    )

    _create_table_if_missing(
        "data_readiness_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope_type", sa.String(), nullable=False, server_default="global"),
        sa.Column("faculty_id", sa.Integer()),
        sa.Column("department_id", sa.Integer()),
        sa.Column("year", sa.Integer()),
        sa.Column("readiness_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("readiness_level", sa.String(), nullable=False, server_default="not_ready"),
        sa.Column("criteria_coverage_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("performance_coverage_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("popularity_coverage_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("survey_coverage_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("trend_readiness_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("validation_quality_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("data_confidence_average", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("blocking_issues_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("warning_issues_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("recommendation_summary", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "missing_data_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("semester", sa.String()),
        sa.Column("faculty_id", sa.Integer()),
        sa.Column("department_id", sa.Integer()),
        sa.Column("missing_field", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False, server_default="warning"),
        sa.Column("required_for_decision", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("message", sa.Text()),
        sa.Column("suggested_action", sa.Text()),
        sa.Column("detected_at", sa.DateTime()),
        sa.Column("resolved_at", sa.DateTime()),
        sa.Column("resolved_by", sa.String()),
    )
    _create_table_if_missing(
        "data_validation_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_type", sa.String(), nullable=False, server_default="manual_entry"),
        sa.Column("source_id", sa.Integer()),
        sa.Column("source_row_id", sa.Integer()),
        sa.Column("course_id", sa.Integer()),
        sa.Column("faculty_id", sa.Integer()),
        sa.Column("department_id", sa.Integer()),
        sa.Column("year", sa.Integer()),
        sa.Column("field_name", sa.String()),
        sa.Column("issue_type", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False, server_default="warning"),
        sa.Column("message", sa.Text()),
        sa.Column("suggested_action", sa.Text()),
        sa.Column("raw_value", sa.Text()),
        sa.Column("normalized_value", sa.Text()),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("resolved_by", sa.String()),
        sa.Column("resolved_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "low_confidence_decision_flags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("decision_run_id", sa.Integer(), nullable=False),
        sa.Column("course_decision_id", sa.Integer()),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("confidence_level", sa.String(), nullable=False, server_default="low"),
        sa.Column("reason", sa.Text()),
        sa.Column("recommended_action", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("resolved_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "data_collection_priorities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope_type", sa.String(), nullable=False, server_default="global"),
        sa.Column("faculty_id", sa.Integer()),
        sa.Column("department_id", sa.Integer()),
        sa.Column("year", sa.Integer()),
        sa.Column("priority_rank", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("target_entity_type", sa.String(), nullable=False),
        sa.Column("course_id", sa.Integer()),
        sa.Column("missing_field", sa.String()),
        sa.Column("priority_reason", sa.Text()),
        sa.Column("expected_impact", sa.String(), nullable=False, server_default="medium"),
        sa.Column("suggested_action", sa.Text()),
        sa.Column("status", sa.String(), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "post_decision_outcomes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("decision_run_id", sa.Integer()),
        sa.Column("course_decision_id", sa.Integer()),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("decision_year", sa.Integer(), nullable=False),
        sa.Column("outcome_year", sa.Integer(), nullable=False),
        sa.Column("final_status_applied", sa.Integer()),
        sa.Column("actual_enrollment", sa.Integer()),
        sa.Column("actual_capacity", sa.Integer()),
        sa.Column("actual_fill_rate", sa.Float()),
        sa.Column("actual_success_rate", sa.Float()),
        sa.Column("actual_average_grade", sa.Float()),
        sa.Column("actual_survey_demand", sa.Integer()),
        sa.Column("outcome_label", sa.String()),
        sa.Column("decision_was_effective", sa.Boolean()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "fairness_metric_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fairness_report_id", sa.Integer(), nullable=False),
        sa.Column("metric_key", sa.String(), nullable=False),
        sa.Column("metric_value", sa.Float()),
        sa.Column("metric_level", sa.String(), nullable=False, server_default="warning"),
        sa.Column("explanation", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "ml_dataset_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("snapshot_name", sa.String()),
        sa.Column("scope_json", sa.Text()),
        sa.Column("year", sa.Integer()),
        sa.Column("feature_schema_version", sa.String(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("feature_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("target_column", sa.String()),
        sa.Column("coverage_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("average_confidence_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("missing_data_summary_json", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_api_clients_active ON api_clients (is_active, role)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_secure_import_jobs_status ON secure_import_jobs (status, uploaded_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_security_audit_logs_created ON security_audit_logs (created_at, event_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_data_coverage_scope ON data_coverage_reports (scope_type, faculty_id, department_id, year, semester)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_data_readiness_scope ON data_readiness_assessments (scope_type, faculty_id, department_id, year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_missing_data_scope ON missing_data_items (year, faculty_id, department_id, severity)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_data_validation_scope ON data_validation_issues (year, severity, is_resolved)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_low_confidence_flags_scope ON low_confidence_decision_flags (year, confidence_level, course_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_data_collection_scope ON data_collection_priorities (year, status, priority_rank)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_post_decision_outcomes_scope ON post_decision_outcomes (decision_year, outcome_year, course_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_fairness_metric_items_report ON fairness_metric_items (fairness_report_id, metric_key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ml_dataset_snapshots_year ON ml_dataset_snapshots (year, feature_schema_version)")


def downgrade() -> None:
    for table in [
        "ml_dataset_snapshots",
        "fairness_metric_items",
        "post_decision_outcomes",
        "data_collection_priorities",
        "low_confidence_decision_flags",
        "data_validation_issues",
        "missing_data_items",
        "data_readiness_assessments",
        "data_coverage_reports",
        "data_snapshots",
        "security_audit_logs",
        "secure_import_job_rows",
        "secure_import_jobs",
        "api_clients",
    ]:
        if table in _tables():
            op.drop_table(table)
