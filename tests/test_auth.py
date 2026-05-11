# -*- coding: utf-8 -*-
import pytest
from app.core.config import AppConfig
from app.schemas.auth import UserContext, ApiClientCreate
from app.services.permission_service import PermissionService, ROLE_ADMIN, ROLE_VIEWER, ACTION_USE_SQL_CONSOLE, ACTION_VIEW_DATA

def test_permission_service_rbac_disabled():
    config = AppConfig(require_rbac=False)
    service = PermissionService(config)
    
    user = UserContext(username="test", role=ROLE_VIEWER)
    # If RBAC is disabled, everything should be allowed
    assert service.has_permission(user, ACTION_USE_SQL_CONSOLE) is True

def test_permission_service_rbac_enabled():
    config = AppConfig(require_rbac=True)
    service = PermissionService(config)
    
    admin = UserContext(username="admin", role=ROLE_ADMIN)
    viewer = UserContext(username="viewer", role=ROLE_VIEWER)
    
    # Admin should have all permissions
    assert service.has_permission(admin, ACTION_USE_SQL_CONSOLE) is True
    assert service.has_permission(admin, ACTION_VIEW_DATA) is True
    
    # Viewer should have limited permissions
    assert service.has_permission(viewer, ACTION_VIEW_DATA) is True
    assert service.has_permission(viewer, ACTION_USE_SQL_CONSOLE) is False

def test_permission_service_faculty_scoping():
    config = AppConfig(require_rbac=True)
    service = PermissionService(config)
    
    fc = UserContext(username="fc", role="faculty_coordinator", faculty_id=1)
    
    # Can access own faculty
    assert service.can_access_faculty(fc, 1) is True
    # Cannot access another faculty
    assert service.can_access_faculty(fc, 2) is False
