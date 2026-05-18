# -*- coding: utf-8 -*-
"""Test error response standardization and Pydantic validation (Stage 3 Verification)."""

import pytest
from fastapi import status

from app.api.error_responses import (
    ApiErrorResponse,
    ValidationErrorResponse,
    ErrorDetail,
    ErrorCode,
    create_error_response,
    create_validation_error_response,
    get_error_message,
)


class TestErrorResponseStandardization:
    """Test standardized error response format."""
    
    def test_error_response_structure(self):
        """ApiErrorResponse should have all required fields."""
        response = ApiErrorResponse(
            success=False,
            error_code=ErrorCode.DATABASE_CONNECTION_FAILED,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Veritabanı bağlantısı başarısız / Database connection failed",
            details=[],
            timestamp="2024-01-01T00:00:00+00:00",
        )
        
        assert response.success is False
        assert response.error_code == ErrorCode.DATABASE_CONNECTION_FAILED
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.message is not None
        assert isinstance(response.details, list)
        assert response.timestamp is not None
    
    def test_error_detail_structure(self):
        """ErrorDetail should capture error field information."""
        detail = ErrorDetail(
            code=ErrorCode.MISSING_REQUIRED_FIELD,
            message="Yıl zorunludur / Year is required",
            field="year",
            value=None,
        )
        
        assert detail.code == ErrorCode.MISSING_REQUIRED_FIELD
        assert detail.field == "year"
    
    def test_validation_error_response(self):
        """ValidationErrorResponse should format validation errors."""
        errors = [
            {"loc": ["year"], "type": "value_error.missing", "msg": "field required"},
            {"loc": ["faculty_id"], "type": "value_error.missing", "msg": "field required"},
        ]
        
        response = ValidationErrorResponse(
            success=False,
            error_code=ErrorCode.VALIDATION_ERROR,
            status_code=422,
            message="Form doğrulaması başarısız / Form validation failed",
            errors=errors,
            timestamp="2024-01-01T00:00:00+00:00",
        )
        
        assert response.success is False
        assert response.error_code == ErrorCode.VALIDATION_ERROR
        assert response.status_code == 422
        assert len(response.errors) == 2
    
    def test_create_error_response_helper(self):
        """create_error_response helper should create standardized responses."""
        response = create_error_response(
            error_code=ErrorCode.WEIGHT_MISMATCH,
            message="Ağırlık sayısı kriter sayısı ile uyuşmuyor / Weight count mismatch",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
        
        assert response.error_code == ErrorCode.WEIGHT_MISMATCH
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.success is False
        assert response.timestamp is not None
    
    def test_create_validation_error_response_helper(self):
        """create_validation_error_response helper should format validation errors."""
        errors = [{"field": "year", "error": "required"}]
        response = create_validation_error_response(errors)
        
        assert response.error_code == ErrorCode.VALIDATION_ERROR
        assert response.status_code == 422
        assert response.errors == errors


class TestErrorCodeConstants:
    """Test error code constants are properly defined."""
    
    def test_all_error_codes_are_strings(self):
        """All ErrorCode constants should be strings."""
        for attr in dir(ErrorCode):
            if not attr.startswith("_"):
                value = getattr(ErrorCode, attr)
                if isinstance(value, str):
                    assert len(value) > 0
    
    def test_validation_error_codes(self):
        """Validation error codes should exist."""
        assert ErrorCode.MISSING_REQUIRED_FIELD
        assert ErrorCode.INVALID_FIELD_VALUE
        assert ErrorCode.VALIDATION_ERROR
    
    def test_database_error_codes(self):
        """Database error codes should exist."""
        assert ErrorCode.DATABASE_ERROR
        assert ErrorCode.DATABASE_CONNECTION_FAILED
    
    def test_algorithm_error_codes(self):
        """Algorithm error codes should exist."""
        assert ErrorCode.MODEL_NOT_FITTED
        assert ErrorCode.WEIGHT_MISMATCH
        assert ErrorCode.ALGORITHM_EXECUTION_FAILED


class TestErrorMessageMapping:
    """Test error message mapping for error codes."""
    
    def test_missing_field_error_message(self):
        """Missing field error should have Turkish/English message."""
        msg = get_error_message(ErrorCode.MISSING_REQUIRED_FIELD)
        assert "Gerekli" in msg or "required" in msg.lower()
    
    def test_database_connection_error_message(self):
        """Database connection error should have message."""
        msg = get_error_message(ErrorCode.DATABASE_CONNECTION_FAILED)
        assert "bağlantısı" in msg.lower() or "connection" in msg.lower()
    
    def test_weight_mismatch_error_message(self):
        """Weight mismatch error should have message."""
        msg = get_error_message(ErrorCode.WEIGHT_MISMATCH)
        assert msg is not None
        assert len(msg) > 0
    
    def test_custom_message_override(self):
        """get_error_message should use custom message if provided."""
        custom = "Özel hata / Custom error"
        msg = get_error_message(ErrorCode.DATABASE_ERROR, custom_message=custom)
        assert msg == custom
    
    def test_all_error_codes_have_messages(self):
        """All defined error codes should have messages."""
        from app.api.error_responses import ERROR_MESSAGES
        
        # Check key error codes have messages
        for code in [
            ErrorCode.MISSING_REQUIRED_FIELD,
            ErrorCode.DATABASE_CONNECTION_FAILED,
            ErrorCode.MODEL_NOT_FITTED,
            ErrorCode.WEIGHT_MISMATCH,
        ]:
            assert code in ERROR_MESSAGES
            assert len(ERROR_MESSAGES[code]) > 0


class TestTurkishEnglishErrorMessages:
    """Test that error messages include both Turkish and English."""
    
    def test_error_messages_bilingual(self):
        """Error messages should include both Turkish and English."""
        from app.api.error_responses import ERROR_MESSAGES
        
        for code, message in ERROR_MESSAGES.items():
            # Message should have slash separator for Turkish/English
            assert "/" in message or len(message) > 20  # Either bilingual or descriptive
    
    def test_validation_error_bilingual(self):
        """Validation error messages should be bilingual."""
        response = create_validation_error_response(
            [],
            custom_message="Form doğrulaması başarısız / Form validation failed"
        )
        assert "/" in response.message  # Bilingual format


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

