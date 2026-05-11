# -*- coding: utf-8 -*-
"""Uygulama genelinde standart hata modeli."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ErrorPayload:
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    suggestion: str | None = None
    severity: str = "error"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "suggestion": self.suggestion,
            "severity": self.severity,
        }


class AppError(Exception):
    status_code = 500
    default_code = "APP_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        suggestion: str | None = None,
        severity: str = "error",
    ) -> None:
        super().__init__(message)
        self.payload = ErrorPayload(
            code=code or self.default_code,
            message=message,
            details=details or {},
            suggestion=suggestion,
            severity=severity,
        )

    @property
    def code(self) -> str:
        return self.payload.code

    def to_dict(self) -> dict[str, Any]:
        return self.payload.to_dict()

    def to_api_response(self) -> dict[str, Any]:
        return {"success": False, "error": self.to_dict()}

    def to_user_message(self) -> str:
        if self.payload.suggestion:
            return f"{self.payload.message}\n\nÖneri: {self.payload.suggestion}"
        return self.payload.message


class ValidationAppError(AppError):
    status_code = 400
    default_code = "VALIDATION_ERROR"


class NotFoundAppError(AppError):
    status_code = 404
    default_code = "NOT_FOUND"


class BusinessRuleAppError(AppError):
    status_code = 422
    default_code = "BUSINESS_RULE_VIOLATION"


class PermissionAppError(AppError):
    status_code = 403
    default_code = "PERMISSION_DENIED"


class DatabaseAppError(AppError):
    status_code = 500
    default_code = "DATABASE_ERROR"


class SchemaAppError(AppError):
    status_code = 500
    default_code = "SCHEMA_ERROR"


class ConflictAppError(AppError):
    status_code = 409
    default_code = "CONFLICT"


def app_error_from_exception(exc: Exception) -> AppError:
    from app.core.config import load_app_config
    import uuid
    
    config = load_app_config()
    is_prod = config.environment == "production"
    
    if isinstance(exc, AppError):
        # We don't want to expose raw details even in AppError if it's production
        # unless it's a validation error
        if is_prod and not isinstance(exc, ValidationAppError):
             exc.payload.details = {}
        return exc
    
    request_id = uuid.uuid4().hex
    # Log the raw exception with request_id here in a real app
    
    details = {}
    if not is_prod:
        details = {"type": type(exc).__name__, "raw": str(exc)}
    
    # We always include request_id so user can report it
    details["request_id"] = request_id
    
    return AppError("Beklenmeyen bir hata oluştu.", details=details)
