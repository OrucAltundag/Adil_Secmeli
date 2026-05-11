# -*- coding: utf-8 -*-
from datetime import datetime, timezone
import hashlib
import json
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List

from app.db.models import SecurityAuditLog
from app.core.config import AppConfig

class SecurityAuditService:
    def __init__(self, db: Session, config: AppConfig):
        self.db = db
        self.config = config

    def log_event(
        self,
        event_type: str,
        actor_type: str,
        action: str,
        message: str,
        actor_id: Optional[str] = None,
        role: Optional[str] = None,
        faculty_id: Optional[int] = None,
        department_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        success: bool = True,
        severity: str = "info",
        before_data: Optional[Dict[str, Any]] = None,
        after_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> SecurityAuditLog:
        if not self.config.security_audit_enabled:
            return None

        # Fetch previous hash for chaining
        last_log = self.db.query(SecurityAuditLog).order_by(SecurityAuditLog.id.desc()).first()
        previous_hash = last_log.event_hash if last_log else None

        log_entry = SecurityAuditLog(
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            role=role,
            faculty_id=faculty_id,
            department_id=department_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            success=success,
            severity=severity,
            message=message,
            before_json=json.dumps(before_data) if before_data else None,
            after_json=json.dumps(after_data) if after_data else None,
            metadata_json=json.dumps(metadata) if metadata else None,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.now(timezone.utc),
            previous_hash=previous_hash
        )

        # Calculate event hash
        payload = f"{event_type}|{actor_id}|{action}|{success}|{log_entry.created_at.isoformat()}|{previous_hash or ''}"
        log_entry.event_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()

        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)
        return log_entry

    def verify_audit_chain(self) -> Dict[str, Any]:
        logs = self.db.query(SecurityAuditLog).order_by(SecurityAuditLog.id.asc()).all()
        if not logs:
            return {"is_valid": True, "message": "No logs found"}

        expected_previous_hash = None
        invalid_entries = []

        for log in logs:
            if log.previous_hash != expected_previous_hash:
                invalid_entries.append(log.id)
            
            # verify self hash
            payload = f"{log.event_type}|{log.actor_id}|{log.action}|{log.success}|{log.created_at.isoformat()}|{log.previous_hash or ''}"
            computed_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
            if computed_hash != log.event_hash:
                invalid_entries.append(log.id)

            expected_previous_hash = log.event_hash

        if invalid_entries:
            return {"is_valid": False, "invalid_ids": invalid_entries, "message": "Audit chain validation failed"}
        return {"is_valid": True, "message": "Audit chain is valid"}

    def get_recent_logs(self, limit: int = 100) -> List[SecurityAuditLog]:
        return self.db.query(SecurityAuditLog).order_by(SecurityAuditLog.id.desc()).limit(limit).all()
