# -*- coding: utf-8 -*-
"""Import API schemaları."""

from pydantic import BaseModel


class ImportPreviewRequest(BaseModel):
    import_type: str
    year: int | None = None
    faculty_id: int | None = None
    department_id: int | None = None
    semester: str | None = None
