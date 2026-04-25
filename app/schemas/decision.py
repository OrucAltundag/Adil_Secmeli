# -*- coding: utf-8 -*-
"""Decision API schemaları."""

from pydantic import BaseModel


class DecisionRunRequest(BaseModel):
    year: int
    faculty_id: int | None = None
    semester: str | None = None
