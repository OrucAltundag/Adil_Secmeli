# -*- coding: utf-8 -*-
"""Pydantic modelleri: dönem planlama API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SemesterPlanningPolicyRequest(BaseModel):
    name: str = "Dönem Planlama Politikası"
    scope_type: str = "global"
    faculty_id: int | None = None
    department_id: int | None = None
    year: int | None = None
    curriculum_year: int | None = None
    total_elective_target: int = 8
    fall_min: int = 4
    fall_max: int = 4
    spring_min: int = 4
    spring_max: int = 4
    max_semester_imbalance: int = 0
    allow_unbalanced_distribution: bool = False
    same_course_repeat_policy: str = "disallow"
    same_course_repeat_requires_approval: bool = True
    high_demand_repeat_threshold: float | None = None
    consider_course_availability: bool = True
    consider_instructor_availability: bool = False
    consider_resource_constraints: bool = False
    consider_prerequisites: bool = True
    consider_required_course_load: bool = False
    consider_expected_demand: bool = True
    consider_capacity_balance: bool = True
    consider_time_conflicts: bool = False
    hard_constraint_policy: str = "strict"
    soft_constraint_weights: dict[str, float] | None = None
    activate: bool = True
    notes: str | None = None


class CourseAvailabilityRequest(BaseModel):
    course_id: int
    year: int | None = None
    faculty_id: int | None = None
    department_id: int | None = None
    allowed_fall: bool = True
    allowed_spring: bool = True
    preferred_semester: str = "either"
    availability_type: str = "always"
    unavailable_reason: str | None = None
    effective_from_year: int | None = None
    effective_to_year: int | None = None
    notes: str | None = None


class InstructorRequest(BaseModel):
    name: str
    email: str | None = None
    faculty_id: int | None = None
    department_id: int | None = None
    is_active: bool = True


class InstructorAvailabilityRequest(BaseModel):
    instructor_id: int
    year: int
    semester: str
    available: bool = True
    max_elective_courses: int = 2
    current_assigned_elective_count: int | None = None
    unavailable_reason: str | None = None
    notes: str | None = None


class TeachingResourceRequest(BaseModel):
    resource_name: str
    resource_type: str
    faculty_id: int | None = None
    department_id: int | None = None
    capacity: int | None = None
    available_fall: bool = True
    available_spring: bool = True
    notes: str | None = None


class ResourceRequirementRequest(BaseModel):
    course_id: int
    resource_type: str
    required_capacity: int | None = None
    required_hours: float | None = None
    hard_requirement: bool = True
    notes: str | None = None


class PrerequisiteRequest(BaseModel):
    course_id: int
    prerequisite_course_id: int
    prerequisite_type: str = "hard"
    relation_note: str | None = None


class SemesterPlanGenerateRequest(BaseModel):
    year: int
    faculty_id: int | None = None
    department_id: int | None = None
    curriculum_year: int | None = None
    candidate_courses: list[dict[str, Any]] | list[int] | None = None
    run_name: str | None = None
    created_by: str | None = None
    persist: bool = True
    generate_alternatives: bool = True
    scenario_type: str = Field(default="score_priority")
