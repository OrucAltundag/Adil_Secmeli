# -*- coding: utf-8 -*-
"""Ortak API response schemaları."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ServiceWarning(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    suggestion: str | None = None
    severity: str = "error"


class PaginationMeta(BaseModel):
    page: int = 1
    page_size: int = 100
    total: int | None = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    message: str | None = None
    warnings: list[Any] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class ApiErrorResponse(BaseModel):
    success: bool = False
    error: ErrorResponse
