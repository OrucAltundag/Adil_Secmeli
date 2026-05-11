# -*- coding: utf-8 -*-
import re
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, List

from app.db.models import SqlConsoleAuditLog
from app.core.config import AppConfig
from app.schemas.auth import UserContext
from app.services.security_audit_service import SecurityAuditService

DANGEROUS_KEYWORDS = [
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
    r"\bALTER\b", r"\bCREATE\b", r"\bREPLACE\b", r"\bTRUNCATE\b",
    r"\bPRAGMA\s+writable_schema\b", r"\bATTACH\s+DATABASE\b", r"\bDETACH\s+DATABASE\b"
]

class SqlConsoleService:
    def __init__(self, db: Session, config: AppConfig, audit_service: SecurityAuditService):
        self.db = db
        self.config = config
        self.audit_service = audit_service

    def is_sql_console_enabled(self, user: UserContext) -> bool:
        if not self.config.enable_sql_console:
            return False
        
        is_prod = self.config.environment == "production"
        if is_prod:
            # Absolute hard block in production
            return False
            
        # Roles allowed to use SQL Console
        return user.role in ["admin", "developer"]

    def is_dangerous_sql(self, sql_text: str) -> bool:
        upper_sql = sql_text.upper()
        for pattern in DANGEROUS_KEYWORDS:
            if re.search(pattern, upper_sql):
                return True
        return False

    def is_read_only_sql(self, sql_text: str) -> bool:
        return not self.is_dangerous_sql(sql_text) and bool(re.search(r"^\s*SELECT\b", sql_text.upper()))

    def execute_sql(self, sql_text: str, user: UserContext, skip_dangerous_check: bool = False) -> Dict[str, Any]:
        if not self.is_sql_console_enabled(user):
            self._log_audit(user, sql_text, success=False, allowed=False, error_msg="SQL console is disabled or user not authorized.")
            return {"success": False, "error": "SQL console is disabled or user not authorized."}

        dangerous = self.is_dangerous_sql(sql_text)
        read_only = self.is_read_only_sql(sql_text)
        
        # Determine if allowed
        allowed = True
        error_msg = None
        
        if dangerous:
            if not self.config.allow_dangerous_sql and not skip_dangerous_check:
                allowed = False
                error_msg = "Dangerous SQL detected and blocked by policy."
            
        if self.config.sql_console_read_only_in_production and self.config.environment == "production" and not read_only:
            allowed = False
            error_msg = "SQL console is read-only in production."

        if not allowed:
            self._log_audit(user, sql_text, dangerous=dangerous, read_only=read_only, success=False, allowed=False, error_msg=error_msg)
            return {"success": False, "error": error_msg}

        try:
            result = self.db.execute(text(sql_text))
            
            if read_only or result.returns_rows:
                rows = result.fetchall()
                data = [dict(row._mapping) for row in rows]
                row_count = len(data)
                self._log_audit(user, sql_text, dangerous=dangerous, read_only=read_only, success=True, allowed=True, row_count=row_count)
                
                # Commit any side effects (like PRAGMA that might return rows)
                self.db.commit() 
                return {"success": True, "data": data, "row_count": row_count}
            else:
                row_count = result.rowcount
                self.db.commit()
                self._log_audit(user, sql_text, dangerous=dangerous, read_only=read_only, success=True, allowed=True, row_count=row_count)
                return {"success": True, "data": [], "row_count": row_count, "message": "Query executed successfully."}
                
        except Exception as e:
            self.db.rollback()
            self._log_audit(user, sql_text, dangerous=dangerous, read_only=read_only, success=False, allowed=True, error_msg=str(e))
            return {"success": False, "error": str(e)}

    def _log_audit(self, user: UserContext, sql_text: str, dangerous: bool = False, read_only: bool = True, success: bool = False, allowed: bool = False, error_msg: str = None, row_count: int = None):
        log_entry = SqlConsoleAuditLog(
            user_id=user.user_id,
            client_id=user.client_id,
            role=user.role,
            sql_text=sql_text,
            statement_type="DANGEROUS" if dangerous else ("SELECT" if read_only else "OTHER"),
            read_only=read_only,
            dangerous=dangerous,
            allowed=allowed,
            success=success,
            error_message=error_msg,
            row_count=row_count,
            executed_at=datetime.now(timezone.utc),
            environment=user.environment
        )
        self.db.add(log_entry)
        self.db.commit()

        # Also log to main security audit
        self.audit_service.log_event(
            event_type="sql_console_executed" if allowed else "sql_console_blocked",
            actor_type="user",
            actor_id=user.username,
            role=user.role,
            action="execute_sql",
            message=f"SQL executed: success={success}, allowed={allowed}",
            success=success,
            severity="warning" if dangerous else "info",
            metadata={"sql": sql_text, "error": error_msg}
        )
