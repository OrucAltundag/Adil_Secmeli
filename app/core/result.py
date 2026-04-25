# -*- coding: utf-8 -*-
"""Servis katmanı için ortak sonuç modeli."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ServiceWarning:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceResult:
    success: bool
    data: Any = None
    message: str | None = None
    warnings: list[Any] = field(default_factory=list)
    errors: list[Any] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(
        cls,
        data: Any = None,
        message: str | None = None,
        warnings: list[Any] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> "ServiceResult":
        return cls(True, data=data, message=message, warnings=warnings or [], meta=meta or {})

    @classmethod
    def fail(
        cls,
        message: str,
        errors: list[Any] | None = None,
        data: Any = None,
        meta: dict[str, Any] | None = None,
    ) -> "ServiceResult":
        return cls(False, data=data, message=message, errors=errors or [], meta=meta or {})

    def to_api(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "warnings": self.warnings,
            "meta": self.meta,
        }
        if not self.success:
            payload["errors"] = self.errors
        return payload

    def unwrap(self) -> Any:
        if not self.success:
            raise RuntimeError(self.message or "Servis hatası")
        return self.data
