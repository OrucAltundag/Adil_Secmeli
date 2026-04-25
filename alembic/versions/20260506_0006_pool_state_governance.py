"""pool state governance

Revision ID: 20260506_0006
Revises: 20260505_0005
Create Date: 2026-05-06 00:06:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260506_0006"
down_revision = "20260505_0005"
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _add_column_if_missing(bind, table_name: str, column: sa.Column) -> None:
    if not _table_exists(bind, table_name):
        return
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns(table_name)}
    if column.name not in columns:
        op.add_column(table_name, column)


def upgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, "pool_state_policies"):
        op.create_table(
            "pool_state_policies",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("scope_type", sa.String(), nullable=False, server_default="global"),
            sa.Column("faculty_id", sa.Integer(), nullable=True),
            sa.Column("department_id", sa.Integer(), nullable=True),
            sa.Column("year", sa.Integer(), nullable=True),
            sa.Column("semester", sa.String(), nullable=True),
            sa.Column("low_score_threshold", sa.Float(), nullable=False, server_default="50"),
            sa.Column("medium_score_threshold", sa.Float(), nullable=False, server_default="70"),
            sa.Column("high_score_threshold", sa.Float(), nullable=False, server_default="80"),
            sa.Column("pool_entry_threshold", sa.Float(), nullable=False, server_default="60"),
            sa.Column("rest_threshold", sa.Float(), nullable=False, server_default="45"),
            sa.Column("cancel_candidate_threshold", sa.Float(), nullable=False, server_default="35"),
            sa.Column("reactivation_threshold", sa.Float(), nullable=False, server_default="75"),
            sa.Column("rest_after_years_in_pool", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("cancel_after_years_in_rest", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("max_years_in_pool", sa.Integer(), nullable=True),
            sa.Column("new_course_grace_period_years", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("revised_course_grace_period_years", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("require_approval_for_cancel", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("require_approval_for_reactivation", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("protect_accreditation_courses", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("protect_strategic_courses", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("protect_required_courses", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("low_confidence_blocks_cancel", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("low_confidence_blocks_rest", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("minimum_data_confidence_for_cancel", sa.Float(), nullable=False, server_default="0.75"),
            sa.Column("minimum_data_confidence_for_rest", sa.Float(), nullable=False, server_default="0.60"),
            sa.Column("allow_reactivation_from_rest", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("allow_reactivation_from_cancelled", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("reactivation_requires_manual_approval", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.String(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.String(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("notes", sa.Text(), nullable=True),
        )
    if not _table_exists(bind, "course_state_transitions"):
        op.create_table(
            "course_state_transitions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("decision_run_id", sa.Integer(), nullable=True),
            sa.Column("course_id", sa.Integer(), nullable=False),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("semester", sa.String(), nullable=True),
            sa.Column("old_status", sa.Integer(), nullable=True),
            sa.Column("recommended_status", sa.Integer(), nullable=True),
            sa.Column("final_status", sa.Integer(), nullable=True),
            sa.Column("lifecycle_label", sa.String(), nullable=True),
            sa.Column("trigger", sa.String(), nullable=False, server_default="algorithm"),
            sa.Column("rule_applied", sa.String(), nullable=True),
            sa.Column("topsis_score", sa.Float(), nullable=True),
            sa.Column("trend_score", sa.Float(), nullable=True),
            sa.Column("trend_label", sa.String(), nullable=True),
            sa.Column("data_confidence_score", sa.Float(), nullable=True),
            sa.Column("policy_id", sa.Integer(), nullable=True),
            sa.Column("governance_flags_snapshot_json", sa.Text(), nullable=True),
            sa.Column("counter_before", sa.Integer(), nullable=True),
            sa.Column("counter_after", sa.Integer(), nullable=True),
            sa.Column("approval_required", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("approval_status", sa.String(), nullable=True),
            sa.Column("override_applied", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("override_id", sa.Integer(), nullable=True),
            sa.Column("explanation", sa.Text(), nullable=True),
            sa.Column("warnings_json", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(), nullable=True),
            sa.Column("created_at", sa.String(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
    if not _table_exists(bind, "course_state_approvals"):
        op.create_table(
            "course_state_approvals",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("course_id", sa.Integer(), nullable=False),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("semester", sa.String(), nullable=True),
            sa.Column("transition_id", sa.Integer(), nullable=True),
            sa.Column("requested_status", sa.Integer(), nullable=False),
            sa.Column("current_status", sa.Integer(), nullable=True),
            sa.Column("approval_type", sa.String(), nullable=False),
            sa.Column("approval_status", sa.String(), nullable=False, server_default="pending"),
            sa.Column("requested_by", sa.String(), nullable=True),
            sa.Column("requested_at", sa.String(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("approval_reason", sa.Text(), nullable=True),
            sa.Column("reviewed_by", sa.String(), nullable=True),
            sa.Column("reviewed_at", sa.String(), nullable=True),
            sa.Column("review_note", sa.Text(), nullable=True),
            sa.Column("expires_at", sa.String(), nullable=True),
            sa.Column("created_at", sa.String(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.String(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
    if not _table_exists(bind, "course_state_overrides"):
        op.create_table(
            "course_state_overrides",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("course_id", sa.Integer(), nullable=False),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("semester", sa.String(), nullable=True),
            sa.Column("transition_id", sa.Integer(), nullable=True),
            sa.Column("recommended_status", sa.Integer(), nullable=True),
            sa.Column("overridden_final_status", sa.Integer(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("requested_by", sa.String(), nullable=True),
            sa.Column("approved_by", sa.String(), nullable=True),
            sa.Column("approved_at", sa.String(), nullable=True),
            sa.Column("created_at", sa.String(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("expires_at", sa.String(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        )
    for table_name, cols in {
        "course_governance_flags": [
            sa.Column("protected_flag", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("required_course_flag", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("service_course_flag", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("new_course_flag", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("revised_course_flag", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("revision_year", sa.Integer(), nullable=True),
            sa.Column("first_offered_year", sa.Integer(), nullable=True),
            sa.Column("protection_reason", sa.Text(), nullable=True),
            sa.Column("updated_by", sa.String(), nullable=True),
        ],
        "havuz": [
            sa.Column("recommended_status", sa.Integer(), nullable=True),
            sa.Column("final_status", sa.Integer(), nullable=True),
            sa.Column("lifecycle_label", sa.String(), nullable=True),
            sa.Column("approval_required", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("approval_status", sa.String(), nullable=True),
            sa.Column("transition_id", sa.Integer(), nullable=True),
            sa.Column("explanation", sa.Text(), nullable=True),
            sa.Column("policy_id", sa.Integer(), nullable=True),
        ],
    }.items():
        for col in cols:
            _add_column_if_missing(bind, table_name, col)
    op.create_index("ix_pool_state_policies_scope", "pool_state_policies", ["scope_type", "faculty_id", "department_id", "year", "semester", "is_active"], if_not_exists=True)
    op.create_index("ix_course_state_transitions_scope", "course_state_transitions", ["year", "course_id", "semester", "approval_status"], if_not_exists=True)
    op.create_index("ix_course_state_approvals_scope", "course_state_approvals", ["year", "course_id", "semester", "approval_status"], if_not_exists=True)
    op.create_index("ix_course_state_overrides_scope", "course_state_overrides", ["year", "course_id", "semester", "is_active"], if_not_exists=True)


def downgrade() -> None:
    for table_name in (
        "course_state_overrides",
        "course_state_approvals",
        "course_state_transitions",
        "pool_state_policies",
    ):
        op.drop_table(table_name)
