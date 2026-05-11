# -*- coding: utf-8 -*-
import pytest
from app.core.config import AppConfig
from app.services.file_upload_security_service import FileUploadSecurityService
from fastapi import HTTPException

def test_file_upload_extension_validation():
    config = AppConfig()
    service = FileUploadSecurityService(config)
    
    # Should not raise exception
    service.validate_extension("data.xlsx")
    service.validate_extension("data.XLSX")
    
    # Should raise exception
    with pytest.raises(HTTPException) as exc:
        service.validate_extension("malicious.exe")
    assert exc.value.status_code == 400

def test_file_upload_mime_type_validation():
    config = AppConfig()
    service = FileUploadSecurityService(config)
    
    # Should not raise exception
    service.validate_mime_type("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    # Should raise exception
    with pytest.raises(HTTPException) as exc:
        service.validate_mime_type("application/x-msdownload")
    assert exc.value.status_code == 400

def test_sanitize_filename():
    config = AppConfig()
    service = FileUploadSecurityService(config)
    
    assert service.sanitize_filename("test.xlsx") == "test.xlsx"
    assert service.sanitize_filename("../../../etc/passwd.xlsx") == "passwd.xlsx"
