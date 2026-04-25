"""Algorithm governance benchmark tables.

Revision ID: 20260508_0008
Revises: 20260507_0007
Create Date: 2026-05-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260508_0008"
down_revision = "20260507_0007"
branch_labels = None
depends_on = None


def _create_table_if_missing(table_name: str, *columns) -> None:
    if table_name not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(table_name, *columns)


def upgrade() -> None:
    _create_table_if_missing(
        "algorithm_governance_registry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("algorithm_key", sa.String(), nullable=False, unique=True),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("algorithm_family", sa.String(), nullable=False),
        sa.Column("task_type", sa.String(), nullable=False),
        sa.Column("usage_role", sa.String(), nullable=False),
        sa.Column("can_affect_final_decision", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("default_enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("minimum_sample_count", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("minimum_samples_per_class", sa.Integer()),
        sa.Column("requires_feature_scaling", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("requires_target", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("supports_probability", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("supports_feature_importance", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("supports_explainability", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("supports_cross_validation", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("recommended_validation_strategy", sa.String()),
        sa.Column("recommended_metrics_json", sa.Text()),
        sa.Column("risk_notes", sa.Text()),
        sa.Column("user_facing_warning", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "algorithm_task_mapping",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_key", sa.String(), nullable=False),
        sa.Column("algorithm_key", sa.String(), nullable=False),
        sa.Column("allowed_usage_role", sa.String(), nullable=False),
        sa.Column("is_recommended", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    _create_table_if_missing(
        "algorithm_benchmark_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_name", sa.String()),
        sa.Column("task_type", sa.String(), nullable=False),
        sa.Column("dataset_name", sa.String()),
        sa.Column("dataset_scope_json", sa.Text()),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("feature_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("target_column", sa.String()),
        sa.Column("algorithms_json", sa.Text()),
        sa.Column("validation_strategy", sa.String()),
        sa.Column("primary_metric_name", sa.String()),
        sa.Column("status", sa.String(), nullable=False, server_default="created"),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("created_by", sa.String()),
        sa.Column("summary_json", sa.Text()),
        sa.Column("warnings_json", sa.Text()),
        sa.Column("error_message", sa.Text()),
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS benchmark_metric_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            benchmark_run_id INTEGER,
            algorithm_key TEXT NOT NULL,
            task_type TEXT NOT NULL,
            metrics_json TEXT,
            primary_metric_name TEXT,
            primary_metric_value REAL,
            warnings_json TEXT,
            created_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS benchmark_validation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            benchmark_run_id INTEGER,
            algorithm_key TEXT NOT NULL,
            validation_strategy TEXT NOT NULL,
            fold_count INTEGER,
            split_summary_json TEXT,
            fold_metrics_json TEXT,
            mean_metrics_json TEXT,
            std_metrics_json TEXT,
            warnings_json TEXT,
            created_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS benchmark_statistical_comparisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            benchmark_run_id INTEGER,
            task_type TEXT NOT NULL,
            primary_metric_name TEXT,
            compared_algorithms_json TEXT,
            confidence_intervals_json TEXT,
            pairwise_tests_json TEXT,
            global_test_json TEXT,
            effect_sizes_json TEXT,
            significance_groups_json TEXT,
            summary_text TEXT,
            created_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS benchmark_data_leakage_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            benchmark_run_id INTEGER,
            algorithm_key TEXT,
            leakage_detected INTEGER NOT NULL DEFAULT 0,
            leakage_level TEXT NOT NULL DEFAULT 'none',
            warnings_json TEXT,
            blocked INTEGER NOT NULL DEFAULT 0,
            summary_text TEXT,
            created_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS benchmark_model_diagnostics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            benchmark_run_id INTEGER,
            algorithm_key TEXT NOT NULL,
            overfitting_warning INTEGER NOT NULL DEFAULT 0,
            overfitting_score REAL,
            train_validation_gap_json TEXT,
            class_imbalance_warning INTEGER NOT NULL DEFAULT 0,
            class_distribution_json TEXT,
            high_variance_warning INTEGER NOT NULL DEFAULT 0,
            diagnostics_json TEXT,
            summary_text TEXT,
            created_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS clustering_evaluation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            benchmark_run_id INTEGER,
            algorithm_key TEXT NOT NULL,
            cluster_count INTEGER NOT NULL DEFAULT 0,
            noise_ratio REAL,
            silhouette_score REAL,
            davies_bouldin_score REAL,
            calinski_harabasz_score REAL,
            cluster_size_distribution_json TEXT,
            stability_score REAL,
            dbscan_params_json TEXT,
            warnings_json TEXT,
            summary_text TEXT,
            created_at TEXT
        )
        """
    )


def downgrade() -> None:
    for table in (
        "clustering_evaluation_results",
        "benchmark_model_diagnostics",
        "benchmark_data_leakage_reports",
        "benchmark_statistical_comparisons",
        "benchmark_validation_results",
        "benchmark_metric_results",
        "algorithm_benchmark_runs",
        "algorithm_task_mapping",
        "algorithm_governance_registry",
    ):
        op.drop_table(table)
