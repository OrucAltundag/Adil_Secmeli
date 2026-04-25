# -*- coding: utf-8 -*-
"""Pool lifecycle API schemaları."""

from pydantic import BaseModel


class PoolTransitionRequest(BaseModel):
    course_id: int
    year: int
    semester: str | None = None
    current_status: int = 0
    topsis_score: float | None = None
    trend_label: str | None = None
    data_confidence_score: float | None = None
