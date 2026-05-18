# -*- coding: utf-8 -*-
from typing import Any, Dict

from app.core.config import AppConfig


class SecurityHealthService:
    def __init__(self, config: AppConfig):
        self.config = config

    def check_security_configuration(self) -> Dict[str, Any]:
        score = 0
        max_score = 100
        checks = []

        is_prod = self.config.environment == "production"

        # 1. API Auth
        if self.config.api_auth_enabled:
            score += 20
            checks.append({"name": "API Authentication", "status": "pass", "message": "API Auth is enabled."})
        else:
            checks.append({"name": "API Authentication", "status": "fail" if is_prod else "warn", "message": "API Auth is disabled."})

        # 2. RBAC
        if self.config.require_rbac:
            score += 15
            checks.append({"name": "Role-Based Access Control", "status": "pass", "message": "RBAC is enabled."})
        else:
            checks.append({"name": "Role-Based Access Control", "status": "fail" if is_prod else "warn", "message": "RBAC is disabled."})

        # 3. SQL Console
        if not self.config.enable_sql_console:
            score += 15
            checks.append({"name": "SQL Console", "status": "pass", "message": "SQL Console is disabled."})
        else:
            checks.append({"name": "SQL Console", "status": "fail" if is_prod else "warn", "message": "SQL Console is enabled."})

        # 4. Dangerous SQL
        if not self.config.allow_dangerous_sql:
            score += 10
            checks.append({"name": "Dangerous SQL Prevention", "status": "pass", "message": "Dangerous SQL is blocked."})
        else:
            checks.append({"name": "Dangerous SQL Prevention", "status": "fail" if is_prod else "warn", "message": "Dangerous SQL is allowed."})

        # 5. Schema Mutation
        if not self.config.allow_runtime_schema_mutation_in_production:
            score += 10
            checks.append({"name": "Schema Mutation Lock", "status": "pass", "message": "Runtime schema mutation is locked in production."})
        else:
            checks.append({"name": "Schema Mutation Lock", "status": "fail" if is_prod else "warn", "message": "Runtime schema mutation is allowed in production."})

        # 6. Import Approval
        if self.config.import_requires_approval:
            score += 10
            checks.append({"name": "Import Approval Flow", "status": "pass", "message": "Imports require approval."})
        else:
            checks.append({"name": "Import Approval Flow", "status": "warn", "message": "Imports do not require approval."})

        # 7. Rate Limiting
        if self.config.rate_limit_enabled:
            score += 5
            checks.append({"name": "Rate Limiting", "status": "pass", "message": "Rate limiting is enabled."})
        else:
            checks.append({"name": "Rate Limiting", "status": "warn", "message": "Rate limiting is disabled."})

        # 8. Audit Logging
        if self.config.security_audit_enabled:
            score += 10
            checks.append({"name": "Security Audit Logging", "status": "pass", "message": "Audit logging is enabled."})
        else:
            checks.append({"name": "Security Audit Logging", "status": "fail" if is_prod else "warn", "message": "Audit logging is disabled."})

        # 9. CORS
        if self.config.cors_allowed_origins and self.config.cors_allowed_origins != "*":
            score += 5
            checks.append({"name": "CORS Policy", "status": "pass", "message": "Specific CORS origins configured."})
        else:
            checks.append({"name": "CORS Policy", "status": "warn", "message": "CORS origins are too permissive or not set."})

        # Level calculation
        level = "unsafe"
        if score >= 90:
            level = "production_ready"
        elif score >= 75:
            level = "production_candidate"
        elif score >= 50:
            level = "partially_ready"
        elif score >= 30:
            level = "demo_only"

        # Final adjustments
        if is_prod and level in ["unsafe", "demo_only", "partially_ready"]:
            level = "unsafe" # Forces it to look unsafe if prod is fundamentally flawed

        return {
            "score": score,
            "max_score": max_score,
            "level": level,
            "environment": self.config.environment,
            "checks": checks
        }
