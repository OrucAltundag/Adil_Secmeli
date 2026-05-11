# -*- coding: utf-8 -*-
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status, Depends

from app.schemas.auth import UserContext
from app.core.config import load_app_config, AppConfig

# Role definitions
ROLE_ADMIN = "admin"
ROLE_DEVELOPER = "developer"
ROLE_FACULTY_COORDINATOR = "faculty_coordinator"
ROLE_DEPARTMENT_COORDINATOR = "department_coordinator"
ROLE_VIEWER = "viewer"
ROLE_API_CLIENT = "api_client"

# Action definitions
ACTION_VIEW_DATA = "view_data"
ACTION_VIEW_REPORTS = "view_reports"
ACTION_EDIT_CRITERIA = "edit_criteria"
ACTION_IMPORT_DATA = "import_data"
ACTION_PREVIEW_IMPORT = "preview_import"
ACTION_APPROVE_IMPORT = "approve_import"
ACTION_ROLLBACK_IMPORT = "rollback_import"
ACTION_RUN_ALGORITHM = "run_algorithm"
ACTION_RUN_BENCHMARK = "run_benchmark"
ACTION_MANAGE_AHP_PROFILE = "manage_ahp_profile"
ACTION_MANAGE_DECISION_POLICY = "manage_decision_policy"
ACTION_APPROVE_CANCEL = "approve_cancel"
ACTION_OVERRIDE_DECISION = "override_decision"
ACTION_USE_SQL_CONSOLE = "use_sql_console"
ACTION_EXECUTE_WRITE_SQL = "execute_write_sql"
ACTION_MANAGE_SCHEMA = "manage_schema"
ACTION_MANAGE_USERS = "manage_users"
ACTION_MANAGE_SETTINGS = "manage_settings"
ACTION_VIEW_AUDIT_LOGS = "view_audit_logs"
ACTION_EXPORT_DATA = "export_data"

# Permission Matrix Base
ROLE_PERMISSIONS = {
    ROLE_ADMIN: ["*"], # * means all permissions
    ROLE_DEVELOPER: [
        ACTION_USE_SQL_CONSOLE, ACTION_MANAGE_SCHEMA, ACTION_VIEW_AUDIT_LOGS,
        ACTION_RUN_BENCHMARK, ACTION_VIEW_DATA, ACTION_VIEW_REPORTS
    ],
    ROLE_FACULTY_COORDINATOR: [
        ACTION_VIEW_DATA, ACTION_EDIT_CRITERIA, ACTION_IMPORT_DATA, ACTION_PREVIEW_IMPORT,
        ACTION_APPROVE_IMPORT, ACTION_RUN_ALGORITHM, ACTION_VIEW_REPORTS, ACTION_EXPORT_DATA,
        ACTION_MANAGE_AHP_PROFILE, ACTION_MANAGE_DECISION_POLICY, ACTION_APPROVE_CANCEL, ACTION_OVERRIDE_DECISION
    ],
    ROLE_DEPARTMENT_COORDINATOR: [
        ACTION_VIEW_DATA, ACTION_EDIT_CRITERIA, ACTION_PREVIEW_IMPORT, ACTION_VIEW_REPORTS, ACTION_EXPORT_DATA
    ],
    ROLE_VIEWER: [
        ACTION_VIEW_DATA, ACTION_VIEW_REPORTS, ACTION_EXPORT_DATA
    ],
    ROLE_API_CLIENT: [
        ACTION_VIEW_DATA, ACTION_VIEW_REPORTS # default minimal API client perms, can be overridden by specific client scopes
    ]
}

class PermissionService:
    def __init__(self, config: AppConfig):
        self.config = config

    def has_permission(self, user: UserContext, action: str) -> bool:
        if not self.config.require_rbac:
            return True
        
        user_role = user.role
        if not user_role:
            return False

        allowed_actions = ROLE_PERMISSIONS.get(user_role, [])
        if "*" in allowed_actions:
            return True
        
        return action in allowed_actions

    def can_access_faculty(self, user: UserContext, faculty_id: int) -> bool:
        if not self.config.require_rbac or user.role in [ROLE_ADMIN, ROLE_DEVELOPER]:
            return True
        return user.faculty_id is None or user.faculty_id == faculty_id

    def can_access_department(self, user: UserContext, department_id: int) -> bool:
        if not self.config.require_rbac or user.role in [ROLE_ADMIN, ROLE_DEVELOPER]:
            return True
        # A faculty coordinator can access any department within their faculty
        # This simple check assumes the calling code verified the department belongs to the faculty.
        if user.role == ROLE_FACULTY_COORDINATOR:
             return True # Scope should be verified higher up
        return user.department_id is None or user.department_id == department_id

    def require_permission(self, user: UserContext, action: str):
        if not self.has_permission(user, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: Requires '{action}' capability."
            )

def get_permission_service() -> PermissionService:
    config = load_app_config()
    return PermissionService(config)

# Helper dependency generator
def require_action(action: str):
    def dependency(user: UserContext = Depends(get_current_user), permission_service: PermissionService = Depends(get_permission_service)):
        permission_service.require_permission(user, action)
        return user
    return dependency

# Since require_action uses get_current_user, we need to import it. We'll do it inside the function or at the module level.
from app.services.auth_service import get_current_user
