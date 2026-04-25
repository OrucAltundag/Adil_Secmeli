# -*- coding: utf-8 -*-
"""Reporting API schemaları."""

from pydantic import BaseModel


class ReportExportRequest(BaseModel):
    format: str = "csv"
