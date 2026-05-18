# -*- coding: utf-8 -*-
"""Rol ve izin kontrolü için ortak altyapı."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import AppConfig, load_app_config

ROLES = {
    "admin",
    "developer",
    "faculty_coordinator",
    "department_coordinator",
    "viewer",
    "api_client",
}

ACTION_PERMISSIONS: dict[str, set[str]] = {
    "view_data": {"admin", "developer", "faculty_coordinator", "department_coordinator", "viewer", "api_client"},
    "edit_criteria": {"admin", "developer", "faculty_coordinator", "department_coordinator"},
    "import_data": {"admin", "developer", "faculty_coordinator", "department_coordinator", "api_client"},
    "approve_import": {"admin", "developer", "faculty_coordinator"},
    "run_algorithm": {"admin", "developer", "faculty_coordinator"},
    "approve_cancel": {"admin", "developer", "faculty_coordinator"},
    "override_decision": {"admin", "developer", "faculty_coordinator"},
    "use_sql_console": {"admin", "developer"},
    "manage_schema": {"admin", "developer"},
    "manage_settings": {"admin", "developer"},
}


@dataclass(frozen=True)
class UserContext:
    user_id: str | None = None
    role: str = "admin"
    faculty_id: int | None = None
    department_id: int | None = None
    is_debug: bool = False
    is_admin: bool = False

    @classmethod
    def demo_admin(cls, config: AppConfig | None = None) -> "UserContext":
        cfg = config or load_app_config()
        return cls(user_id="demo", role="admin", is_admin=True, is_debug=cfg.debug)


def can(user_context: UserContext | None, action: str, resource: Any | None = None, config: AppConfig | None = None) -> bool:
    cfg = config or load_app_config()
    user = user_context or UserContext.demo_admin(cfg)
    role = user.role if user.role in ROLES else "viewer"
    if user.is_admin:
        role = "admin"
    if action == "use_sql_console":
        from app.core.database_policy import sql_console_allowed_by_policy

        return bool(sql_console_allowed_by_policy(cfg) and (role in ACTION_PERMISSIONS[action] or user.is_admin))
    allowed = ACTION_PERMISSIONS.get(action, set())
    return role in allowed or user.is_admin


def require_permission(
    user_context: UserContext | None,
    action: str,
    resource: Any | None = None,
    config: AppConfig | None = None,
) -> None:
    from app.core.errors import PermissionAppError

    if not can(user_context, action, resource=resource, config=config):
        raise PermissionAppError(
            "Bu işlem için yetkiniz yok.",
            code="PERMISSION_DENIED",
            details={"action": action},
            suggestion="Yetkili kullanıcı veya geliştirici modu ile tekrar deneyin.",
        )
