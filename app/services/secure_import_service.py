# -*- coding: utf-8 -*-
import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import AppConfig
from app.db.models import SecureImportJob
from app.schemas.auth import UserContext
from app.services.file_upload_security_service import FileUploadSecurityService
from app.services.security_audit_service import SecurityAuditService


class SecureImportService:
    def __init__(self, db: Session, config: AppConfig, upload_security: FileUploadSecurityService, audit_service: SecurityAuditService):
        self.db = db
        self.config = config
        self.upload_security = upload_security
        self.audit_service = audit_service

    async def create_import_job(self, import_type: str, file: UploadFile, user: UserContext, faculty_id: int = None, year: int = None) -> SecureImportJob:
        file_hash, size_bytes = await self.upload_security.validate_upload(file)

        job_id = f"import_{uuid.uuid4().hex}"

        job = SecureImportJob(
            id=job_id,
            import_type=import_type,
            original_filename=self.upload_security.sanitize_filename(file.filename),
            file_hash=file_hash,
            file_size_bytes=size_bytes,
            mime_type=file.content_type,
            uploaded_by=user.username,
            faculty_id=faculty_id,
            year=year,
            status="uploaded",
            approval_required=self.config.import_requires_approval,
            uploaded_at=datetime.now(timezone.utc)
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        self.audit_service.log_event(
            event_type="import_uploaded",
            actor_type="user",
            actor_id=user.username,
            role=user.role,
            faculty_id=faculty_id,
            action="upload_import",
            message=f"Uploaded import job {job_id} ({file.filename})",
            resource_type="import_job",
            resource_id=job_id
        )

        return job

    def validate_import_job(self, job_id: str, summary_data: dict, rows: list) -> SecureImportJob:
        # Expected to be called by specific import services after parsing
        job = self.db.query(SecureImportJob).filter(SecureImportJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        job.row_count = len(rows)
        job.warning_count = sum(1 for r in rows if r.get('status') == 'warning')
        job.error_count = sum(1 for r in rows if r.get('status') == 'error')
        job.critical_count = sum(1 for r in rows if r.get('status') == 'critical')

        job.preview_summary_json = json.dumps(summary_data)

        if job.critical_count > 0:
            job.status = "validation_failed"
        else:
            job.status = "pending_approval" if job.approval_required else "validated"

        self.db.commit()
        self.db.refresh(job)
        return job

    def approve_import_job(self, job_id: str, user: UserContext) -> SecureImportJob:
        job = self.db.query(SecureImportJob).filter(SecureImportJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status != "pending_approval":
            raise HTTPException(status_code=400, detail=f"Cannot approve job in {job.status} state")

        job.status = "approved"
        job.approved_by = user.username
        job.approved_at = datetime.now(timezone.utc)
        self.db.commit()

        self.audit_service.log_event(
            event_type="import_approved",
            actor_type="user",
            actor_id=user.username,
            role=user.role,
            action="approve_import",
            message=f"Approved import job {job_id}",
            resource_type="import_job",
            resource_id=job_id
        )

        return job

    def mark_applied(self, job_id: str, user: UserContext) -> SecureImportJob:
        job = self.db.query(SecureImportJob).filter(SecureImportJob.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        job.status = "applied"
        job.applied_by = user.username
        job.applied_at = datetime.now(timezone.utc)
        self.db.commit()

        self.audit_service.log_event(
            event_type="import_applied",
            actor_type="user",
            actor_id=user.username,
            role=user.role,
            action="apply_import",
            message=f"Applied import job {job_id}",
            resource_type="import_job",
            resource_id=job_id
        )

        return job
