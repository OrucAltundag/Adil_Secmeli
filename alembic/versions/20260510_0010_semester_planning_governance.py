"""Semester planning governance tables.

Revision ID: 20260510_0010
Revises: 20260509_0009
Create Date: 2026-05-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260510_0010"
down_revision = "20260509_0009"
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
        "semester_planning_policies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("scope_type", sa.String(), nullable=False, server_default="global"),
        sa.Column("faculty_id", sa.Integer()),
        sa.Column("department_id", sa.Integer()),
        sa.Column("year", sa.Integer()),
        sa.Column("curriculum_year", sa.Integer()),
        sa.Column("total_elective_target", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("fall_min", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("fall_max", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("spring_min", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("spring_max", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("max_semester_imbalance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("allow_unbalanced_distribution", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("same_course_repeat_policy", sa.String(), nullable=False, server_default="disallow"),
        sa.Column("same_course_repeat_requires_approval", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("high_demand_repeat_threshold", sa.Float()),
        sa.Column("consider_course_availability", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("consider_instructor_availability", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("consider_resource_constraints", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("consider_prerequisites", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("consider_required_course_load", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("consider_expected_demand", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("consider_capacity_balance", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("consider_time_conflicts", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("minimum_plan_score", sa.Float()),
        sa.Column("hard_constraint_policy", sa.String(), nullable=False, server_default="strict"),
        sa.Column("soft_constraint_weight_json", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.Column("notes", sa.Text()),
    )
    _create_table_if_missing("course_semester_availability", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("course_id", sa.Integer(), nullable=False), sa.Column("year", sa.Integer()), sa.Column("faculty_id", sa.Integer()), sa.Column("department_id", sa.Integer()), sa.Column("allowed_fall", sa.Boolean(), nullable=False, server_default=sa.text("1")), sa.Column("allowed_spring", sa.Boolean(), nullable=False, server_default=sa.text("1")), sa.Column("preferred_semester", sa.String(), nullable=False, server_default="either"), sa.Column("availability_type", sa.String(), nullable=False, server_default="always"), sa.Column("unavailable_reason", sa.Text()), sa.Column("effective_from_year", sa.Integer()), sa.Column("effective_to_year", sa.Integer()), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()), sa.Column("notes", sa.Text()))
    _create_table_if_missing("instructors", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(), nullable=False), sa.Column("email", sa.String()), sa.Column("faculty_id", sa.Integer()), sa.Column("department_id", sa.Integer()), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()))
    _create_table_if_missing("course_instructor_assignments", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("course_id", sa.Integer(), nullable=False), sa.Column("instructor_id", sa.Integer(), nullable=False), sa.Column("priority", sa.Integer(), nullable=False, server_default="1"), sa.Column("can_teach", sa.Boolean(), nullable=False, server_default=sa.text("1")), sa.Column("preferred", sa.Boolean(), nullable=False, server_default=sa.text("0")), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()), sa.Column("notes", sa.Text()))
    _create_table_if_missing("instructor_semester_availability", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("instructor_id", sa.Integer(), nullable=False), sa.Column("year", sa.Integer(), nullable=False), sa.Column("semester", sa.String(), nullable=False), sa.Column("available", sa.Boolean(), nullable=False, server_default=sa.text("1")), sa.Column("max_elective_courses", sa.Integer(), nullable=False, server_default="2"), sa.Column("current_assigned_elective_count", sa.Integer()), sa.Column("unavailable_reason", sa.Text()), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()), sa.Column("notes", sa.Text()))
    _create_table_if_missing("teaching_resources", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("resource_name", sa.String(), nullable=False), sa.Column("resource_type", sa.String(), nullable=False), sa.Column("faculty_id", sa.Integer()), sa.Column("department_id", sa.Integer()), sa.Column("capacity", sa.Integer()), sa.Column("available_fall", sa.Boolean(), nullable=False, server_default=sa.text("1")), sa.Column("available_spring", sa.Boolean(), nullable=False, server_default=sa.text("1")), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()), sa.Column("notes", sa.Text()))
    _create_table_if_missing("course_resource_requirements", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("course_id", sa.Integer(), nullable=False), sa.Column("resource_type", sa.String(), nullable=False), sa.Column("required_capacity", sa.Integer()), sa.Column("required_hours", sa.Float()), sa.Column("hard_requirement", sa.Boolean(), nullable=False, server_default=sa.text("1")), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()), sa.Column("notes", sa.Text()))
    _create_table_if_missing("semester_resource_capacity", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("resource_id", sa.Integer(), nullable=False), sa.Column("year", sa.Integer(), nullable=False), sa.Column("semester", sa.String(), nullable=False), sa.Column("available_capacity", sa.Integer()), sa.Column("available_hours", sa.Float()), sa.Column("reserved_hours", sa.Float()), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()))
    _create_table_if_missing("course_prerequisites", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("course_id", sa.Integer(), nullable=False), sa.Column("prerequisite_course_id", sa.Integer(), nullable=False), sa.Column("prerequisite_type", sa.String(), nullable=False, server_default="hard"), sa.Column("relation_note", sa.Text()), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()))
    _create_table_if_missing("semester_required_course_loads", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("faculty_id", sa.Integer()), sa.Column("department_id", sa.Integer(), nullable=False), sa.Column("year", sa.Integer(), nullable=False), sa.Column("semester", sa.String(), nullable=False), sa.Column("required_course_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("total_credits", sa.Float()), sa.Column("total_ects", sa.Float()), sa.Column("workload_score", sa.Float()), sa.Column("notes", sa.Text()), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()))
    _create_table_if_missing("course_time_constraints", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("course_id", sa.Integer(), nullable=False), sa.Column("year", sa.Integer()), sa.Column("semester", sa.String()), sa.Column("unavailable_slots_json", sa.Text()), sa.Column("preferred_slots_json", sa.Text()), sa.Column("conflict_group", sa.String()), sa.Column("created_at", sa.DateTime()), sa.Column("updated_at", sa.DateTime()), sa.Column("notes", sa.Text()))
    _create_table_if_missing("semester_plan_runs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("run_name", sa.String()), sa.Column("year", sa.Integer(), nullable=False), sa.Column("faculty_id", sa.Integer()), sa.Column("department_id", sa.Integer()), sa.Column("policy_id", sa.Integer()), sa.Column("total_candidate_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("selected_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("fall_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("spring_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("plan_score", sa.Float()), sa.Column("status", sa.String(), nullable=False, server_default="created"), sa.Column("metrics_json", sa.Text()), sa.Column("policy_snapshot_json", sa.Text()), sa.Column("warnings_json", sa.Text()), sa.Column("created_at", sa.DateTime()), sa.Column("completed_at", sa.DateTime()), sa.Column("created_by", sa.String()), sa.Column("error_message", sa.Text()))
    _create_table_if_missing("semester_plan_course_assignments", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("plan_run_id", sa.Integer(), nullable=False), sa.Column("course_id", sa.Integer(), nullable=False), sa.Column("assigned_semester", sa.String(), nullable=False), sa.Column("assignment_type", sa.String(), nullable=False, server_default="selected"), sa.Column("course_score", sa.Float()), sa.Column("expected_demand", sa.Float()), sa.Column("expected_capacity", sa.Float()), sa.Column("constraint_status", sa.String(), nullable=False, server_default="ok"), sa.Column("explanation", sa.Text()), sa.Column("created_at", sa.DateTime()))
    _create_table_if_missing("semester_plan_constraint_violations", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("plan_run_id", sa.Integer(), nullable=False), sa.Column("course_id", sa.Integer()), sa.Column("constraint_type", sa.String(), nullable=False), sa.Column("severity", sa.String(), nullable=False, server_default="warning"), sa.Column("message", sa.Text(), nullable=False), sa.Column("suggestion", sa.Text()), sa.Column("created_at", sa.DateTime()))
    _create_table_if_missing("semester_plan_scenarios", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("plan_run_id", sa.Integer(), nullable=False), sa.Column("scenario_name", sa.String(), nullable=False), sa.Column("scenario_type", sa.String(), nullable=False), sa.Column("fall_courses_json", sa.Text()), sa.Column("spring_courses_json", sa.Text()), sa.Column("metrics_json", sa.Text()), sa.Column("constraint_violations_json", sa.Text()), sa.Column("explanations_json", sa.Text()), sa.Column("plan_score", sa.Float()), sa.Column("created_at", sa.DateTime()))
    _add_column_if_missing("mufredat", sa.Column("semester_plan_run_id", sa.Integer()))
    _add_column_if_missing("mufredat_ders", sa.Column("semester_plan_run_id", sa.Integer()))
    _add_column_if_missing("mufredat_ders", sa.Column("assignment_explanation", sa.Text()))
    _add_column_if_missing("mufredat_ders", sa.Column("constraint_status", sa.String()))


def downgrade() -> None:
    for table in [
        "semester_plan_scenarios",
        "semester_plan_constraint_violations",
        "semester_plan_course_assignments",
        "semester_plan_runs",
        "course_time_constraints",
        "semester_required_course_loads",
        "course_prerequisites",
        "semester_resource_capacity",
        "course_resource_requirements",
        "teaching_resources",
        "instructor_semester_availability",
        "course_instructor_assignments",
        "instructors",
        "course_semester_availability",
        "semester_planning_policies",
    ]:
        if table in _tables():
            op.drop_table(table)
