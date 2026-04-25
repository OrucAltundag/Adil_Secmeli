"""ML governance tables.

Revision ID: 20260507_0007
Revises: 20260506_0006
Create Date: 2026-05-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260507_0007"
down_revision = "20260506_0006"
branch_labels = None
depends_on = None


def _create_table_if_missing(table_name: str, *columns, **kwargs) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        op.create_table(table_name, *columns, **kwargs)


def upgrade() -> None:
    _create_table_if_missing(
        "ml_algorithm_registry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("algorithm_key", sa.String(), nullable=False, unique=True),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("algorithm_type", sa.String(), nullable=False),
        sa.Column("usage_role", sa.String(), nullable=False, server_default="advisory_ml"),
        sa.Column("default_enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("min_training_samples", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("min_samples_per_class", sa.Integer()),
        sa.Column("requires_validation", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("supports_confidence", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("supports_explainability", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "ml_feature_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("feature_schema_version", sa.String(), nullable=False),
        sa.Column("scope_json", sa.Text()),
        sa.Column("year", sa.Integer()),
        sa.Column("faculty_id", sa.Integer()),
        sa.Column("department_id", sa.Integer()),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feature_names_json", sa.Text(), nullable=False),
        sa.Column("missing_features_summary_json", sa.Text()),
        sa.Column("imputation_strategy_json", sa.Text()),
        sa.Column("normalization_summary_json", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "ml_model_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("algorithm_key", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("model_type", sa.String(), nullable=False),
        sa.Column("usage_role", sa.String(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("feature_schema_version", sa.String(), nullable=False),
        sa.Column("training_scope_json", sa.Text()),
        sa.Column("training_sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("target_column", sa.String()),
        sa.Column("class_distribution_json", sa.Text()),
        sa.Column("parameters_json", sa.Text()),
        sa.Column("train_metrics_json", sa.Text()),
        sa.Column("validation_metrics_json", sa.Text()),
        sa.Column("cross_validation_json", sa.Text()),
        sa.Column("overfitting_report_json", sa.Text()),
        sa.Column("readiness_level", sa.String()),
        sa.Column("readiness_warnings_json", sa.Text()),
        sa.Column("status", sa.String(), nullable=False, server_default="created"),
        sa.Column("skip_reason", sa.Text()),
        sa.Column("artifact_path", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("created_by", sa.String()),
        sa.Column("notes", sa.Text()),
    )
    _create_table_if_missing(
        "ml_predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_run_id", sa.Integer()),
        sa.Column("algorithm_key", sa.String(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("faculty_id", sa.Integer()),
        sa.Column("department_id", sa.Integer()),
        sa.Column("prediction_type", sa.String(), nullable=False),
        sa.Column("predicted_value_text", sa.Text()),
        sa.Column("predicted_value_numeric", sa.Float()),
        sa.Column("confidence_score", sa.Float()),
        sa.Column("confidence_level", sa.String()),
        sa.Column("uncertainty_reasons_json", sa.Text()),
        sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("fallback_method", sa.String()),
        sa.Column("fallback_reason", sa.Text()),
        sa.Column("advisory_only", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("should_influence_decision", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("explanation", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "ml_prediction_explanations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("top_features_json", sa.Text()),
        sa.Column("feature_importance_json", sa.Text()),
        sa.Column("decision_path_json", sa.Text()),
        sa.Column("limitations_json", sa.Text()),
        sa.Column("human_readable_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "ml_readiness_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope_json", sa.Text()),
        sa.Column("year", sa.Integer()),
        sa.Column("faculty_id", sa.Integer()),
        sa.Column("department_id", sa.Integer()),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("algorithm_readiness_json", sa.Text()),
        sa.Column("feature_quality_json", sa.Text()),
        sa.Column("recommendations_json", sa.Text()),
        sa.Column("summary_text", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )

    op.create_index("ix_ml_algorithm_registry_key", "ml_algorithm_registry", ["algorithm_key", "usage_role"], if_not_exists=True)
    op.create_index("ix_ml_feature_snapshots_scope", "ml_feature_snapshots", ["year", "faculty_id", "department_id", "created_at"], if_not_exists=True)
    op.create_index("ix_ml_model_runs_algorithm", "ml_model_runs", ["algorithm_key", "status", "created_at"], if_not_exists=True)
    op.create_index("ix_ml_predictions_course", "ml_predictions", ["course_id", "year", "algorithm_key", "created_at"], if_not_exists=True)
    op.create_index("ix_ml_prediction_explanations_prediction", "ml_prediction_explanations", ["prediction_id"], if_not_exists=True)
    op.create_index("ix_ml_readiness_reports_scope", "ml_readiness_reports", ["year", "faculty_id", "department_id", "created_at"], if_not_exists=True)


def downgrade() -> None:
    for table in (
        "ml_readiness_reports",
        "ml_prediction_explanations",
        "ml_predictions",
        "ml_model_runs",
        "ml_feature_snapshots",
        "ml_algorithm_registry",
    ):
        op.drop_table(table)
