# -*- coding: utf-8 -*-
"""Course API schemaları."""

from pydantic import BaseModel


class CourseOut(BaseModel):
    ders_id: int
    kod: str | None = None
    ad: str | None = None
    kredi: float | None = None
    akts: float | None = None
    fakulte_id: int | None = None
    bolum_id: int | None = None
    course_type: str | None = None
