# -*- coding: utf-8 -*-
"""Standardized API error responses and exception handlers."""

from typing import Any
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detailed error information."""
    code: str = Field(..., description="Error code (e.g., 'MISSING_FIELD', 'INVALID_VALUE')")
    message: str = Field(..., description="Human-readable error message in Turkish and English")
    field: str | None = Field(None, description="Field name if error is field-specific")
    value: Any = Field(None, description="The invalid value that was provided")


class ApiErrorResponse(BaseModel):
    """Standard API error response format."""
    success: bool = Field(False, description="Always False for error responses")
    error_code: str = Field(..., description="HTTP-agnostic error code")
    status_code: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Main error message (Turkish/English)")
    details: list[ErrorDetail] = Field(default_factory=list, description="Detailed error information")
    timestamp: str = Field(..., description="ISO8601 timestamp when error occurred")
    request_path: str | None = Field(default=None, description="API endpoint path that caused error")


class ValidationErrorResponse(BaseModel):
    """Specific response for validation errors (422 status)."""
    success: bool = Field(False)
    error_code: str = Field("VALIDATION_ERROR")
    status_code: int = Field(422)
    message: str = Field("Form validation failed")
    errors: list[dict[str, Any]] = Field(default_factory=list, description="List of validation errors per field")
    timestamp: str = Field(...)


class ApiException(HTTPException):
    """Custom API exception with standardized format."""
    
    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: list[ErrorDetail] | None = None,
        field: str | None = None,
        value: Any = None,
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or []
        
        # Add primary error to details if field-specific
        if field or value is not None:
            self.details.insert(0, ErrorDetail(
                code=error_code,
                message=message,
                field=field,
                value=value,
            ))
        
        super().__init__(
            status_code=status_code,
            detail=message,
        )


# Standardized error codes
class ErrorCode:
    """Standard error code constants."""
    # Validation errors
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FIELD_VALUE = "INVALID_FIELD_VALUE"
    INVALID_FIELD_TYPE = "INVALID_FIELD_TYPE"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    
    # Resource errors
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    
    # Database errors
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_CONNECTION_FAILED = "DATABASE_CONNECTION_FAILED"
    
    # Algorithm errors
    ALGORITHM_EXECUTION_FAILED = "ALGORITHM_EXECUTION_FAILED"
    MODEL_NOT_FITTED = "MODEL_NOT_FITTED"
    WEIGHT_MISMATCH = "WEIGHT_MISMATCH"
    
    # Business logic errors
    CRITERIA_NOT_COMPLETE = "CRITERIA_NOT_COMPLETE"
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"
    
    # Server errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


# Common error messages (Turkish/English)
ERROR_MESSAGES = {
    ErrorCode.MISSING_REQUIRED_FIELD: "Gerekli alan eksik / Missing required field",
    ErrorCode.INVALID_FIELD_VALUE: "Geçersiz alan değeri / Invalid field value",
    ErrorCode.INVALID_FIELD_TYPE: "Geçersiz veri tipi / Invalid data type",
    ErrorCode.VALIDATION_ERROR: "Form doğrulaması başarısız / Form validation failed",
    ErrorCode.RESOURCE_NOT_FOUND: "Kaynak bulunamadı / Resource not found",
    ErrorCode.RESOURCE_ALREADY_EXISTS: "Kaynak zaten var / Resource already exists",
    ErrorCode.INVALID_STATE_TRANSITION: "Geçersiz durum geçişi / Invalid state transition",
    ErrorCode.DATABASE_ERROR: "Veritabanı hatası / Database error",
    ErrorCode.DATABASE_CONNECTION_FAILED: "Veritabanı bağlantısı başarısız / Database connection failed",
    ErrorCode.ALGORITHM_EXECUTION_FAILED: "Algoritma çalıştırılamadı / Algorithm execution failed",
    ErrorCode.MODEL_NOT_FITTED: "Model eğitilmedi / Model not fitted",
    ErrorCode.WEIGHT_MISMATCH: "Ağırlık uyuşmazlığı / Weight mismatch",
    ErrorCode.CRITERIA_NOT_COMPLETE: "Kriter girişleri tamamlanmadı / Criteria not complete",
    ErrorCode.BUSINESS_RULE_VIOLATION: "İş kuralı ihlali / Business rule violation",
    ErrorCode.OPERATION_NOT_ALLOWED: "İşleme izin verilmedi / Operation not allowed",
    ErrorCode.INTERNAL_SERVER_ERROR: "İç sunucu hatası / Internal server error",
    ErrorCode.NOT_IMPLEMENTED: "Uygulanmadı / Not implemented",
}


def get_error_message(error_code: str, custom_message: str | None = None) -> str:
    """Get standard error message for error code."""
    if custom_message:
        return custom_message
    return ERROR_MESSAGES.get(error_code, "Bilinmeyen hata / Unknown error")


def create_error_response(
    error_code: str,
    message: str | None = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: list[ErrorDetail] | None = None,
) -> ApiErrorResponse:
    """Create a standardized error response."""
    from datetime import datetime, timezone
    
    return ApiErrorResponse(
        success=False,
        error_code=error_code,
        status_code=status_code,
        message=message or get_error_message(error_code),
        details=details or [],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def create_validation_error_response(
    errors: list[dict[str, Any]],
    custom_message: str | None = None,
) -> ValidationErrorResponse:
    """Create a validation error response."""
    from datetime import datetime, timezone
    
    return ValidationErrorResponse(
        success=False,
        error_code=ErrorCode.VALIDATION_ERROR,
        status_code=422,
        message=custom_message or "Form doğrulaması başarısız / Form validation failed",
        errors=errors,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
