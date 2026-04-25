"""AHP profile governance tables and columns.

Revision ID: 20260509_0009
Revises: 20260508_0008
Create Date: 2026-05-09
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260509_0009"
down_revision = "20260508_0008"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table_name: str) -> set[str]:
    if table_name not in _tables():
        return set()
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table_name)}


def _create_table_if_missing(table_name: str, *columns) -> None:
    if table_name not in _tables():
        op.create_table(table_name, *columns)


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if table_name in _tables() and column.name not in _columns(table_name):
        op.add_column(table_name, column)


def upgrade() -> None:
    _create_table_if_missing(
        "decision_criteria_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("criterion_key", sa.String(), nullable=False, unique=True),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("criterion_type", sa.String(), nullable=False, server_default="score"),
        sa.Column("is_benefit", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("default_enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("min_value", sa.Float()),
        sa.Column("max_value", sa.Float()),
        sa.Column("normalization_method", sa.String()),
        sa.Column("source_type", sa.String()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "ahp_profile_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("scope_type", sa.String(), nullable=False, server_default="global"),
        sa.Column("faculty_id", sa.Integer()),
        sa.Column("department_id", sa.Integer()),
        sa.Column("year", sa.Integer()),
        sa.Column("semester", sa.String()),
        sa.Column("max_consistency_ratio", sa.Float(), nullable=False, server_default="0.10"),
        sa.Column("require_approval_for_activation", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("allow_inconsistent_profile_for_draft_runs", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("allow_default_profile_if_missing", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("mark_decisions_stale_on_profile_change", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("require_notes_for_manual_profile", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "ahp_profile_approval_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("old_status", sa.String()),
        sa.Column("new_status", sa.String()),
        sa.Column("actor", sa.String()),
        sa.Column("message", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "decision_staleness_flags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("decision_run_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("old_reference_id", sa.Integer()),
        sa.Column("new_reference_id", sa.Integer()),
        sa.Column("message", sa.Text()),
        sa.Column("requires_recalculation", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("resolved_at", sa.DateTime()),
        sa.Column("resolved_by", sa.String()),
    )
    _create_table_if_missing(
        "ahp_sensitivity_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("decision_run_id", sa.Integer(), nullable=False),
        sa.Column("ahp_profile_id", sa.Integer()),
        sa.Column("variation_percent", sa.Float(), nullable=False, server_default="0.05"),
        sa.Column("tested_variations_json", sa.Text()),
        sa.Column("affected_courses_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sensitive_courses_json", sa.Text()),
        sa.Column("stability_summary_json", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "ahp_course_sensitivity_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sensitivity_result_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("base_score", sa.Float()),
        sa.Column("min_score", sa.Float()),
        sa.Column("max_score", sa.Float()),
        sa.Column("score_range", sa.Float()),
        sa.Column("base_decision", sa.String()),
        sa.Column("changed_decision", sa.String()),
        sa.Column("stability_level", sa.String(), nullable=False, server_default="medium"),
        sa.Column("explanation", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )

    for column in [
        sa.Column("profile_name", sa.String()),
        sa.Column("profile_code", sa.String()),
        sa.Column("semester", sa.String()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("consistency_warning", sa.Text()),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("approved_by", sa.String()),
        sa.Column("approved_at", sa.DateTime()),
        sa.Column("rejected_by", sa.String()),
        sa.Column("rejected_at", sa.DateTime()),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("parent_profile_id", sa.Integer()),
        sa.Column("superseded_by_profile_id", sa.Integer()),
    ]:
        _add_column_if_missing("ahp_weight_profiles", column)

    for column in [
        sa.Column("ahp_profile_version", sa.Integer()),
        sa.Column("ahp_weights_snapshot_json", sa.Text()),
        sa.Column("ahp_consistency_ratio", sa.Float()),
        sa.Column("ahp_profile_status_at_run", sa.String()),
        sa.Column("ahp_profile_source", sa.String()),
        sa.Column("stale_flag", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("recalculate_required", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    ]:
        _add_column_if_missing("decision_runs", column)

    for column in [
        sa.Column("ahp_profile_id", sa.Integer()),
        sa.Column("weighted_contribution_json", sa.Text()),
    ]:
        _add_column_if_missing("course_score_breakdowns", column)

    for column in [
        sa.Column("ahp_profile_id", sa.Integer()),
        sa.Column("weights_snapshot_json", sa.Text()),
    ]:
        _add_column_if_missing("skor", column)


def downgrade() -> None:
    for table in [
        "ahp_course_sensitivity_items",
        "ahp_sensitivity_results",
        "decision_staleness_flags",
        "ahp_profile_approval_logs",
        "ahp_profile_policies",
        "decision_criteria_definitions",
    ]:
        if table in _tables():
            op.drop_table(table)

