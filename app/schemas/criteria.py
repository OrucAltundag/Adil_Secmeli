# -*- coding: utf-8 -*-
"""Criteria API schemaları."""

from pydantic import BaseModel


class CriteriaScopeQuery(BaseModel):
    year: int
    faculty_id: int | None = None
    department_id: int | None = None
    semester: str | None = None
