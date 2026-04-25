# -*- coding: utf-8 -*-
"""Curriculum API schemaları."""

from pydantic import BaseModel


class CurriculumScope(BaseModel):
    year: int | None = None
    department_id: int | None = None
    semester: str | None = None
