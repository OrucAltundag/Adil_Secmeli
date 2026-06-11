# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import load_app_config
from app.db.database import get_session
from app.schemas.auth import (
    ApiClientCreate,
    ApiClientCreatedResponse,
    UserContext,
)
from app.services.auth_service import AuthService, get_auth_service
from app.services.backup_restore_service import BackupRestoreService
from app.services.file_upload_security_service import FileUploadSecurityService
from app.services.permission_service import (
    require_action,
)
from app.services.secure_import_service import SecureImportService
from app.services.security_audit_service import SecurityAuditService
from app.services.security_health_service import SecurityHealthService
from app.services.sql_console_service import SqlConsoleService

router = APIRouter(prefix="/security", tags=["security"])

@router.get("/health")
def security_health():
    config = load_app_config()
    health_service = SecurityHealthService(config)
    return health_service.check_security_configuration()

@router.get("/readiness")
def security_readiness():
    config = load_app_config()
    health_service = SecurityHealthService(config)
    return health_service.check_security_configuration()

@router.post("/api-clients", response_model=ApiClientCreatedResponse)
def create_api_client(
    data: ApiClientCreate,
    user: UserContext = Depends(require_action("manage_users")),
    auth_service: AuthService = Depends(get_auth_service)
):
    return auth_service.create_api_client(data)

@router.post("/sql-console/execute")
def execute_sql(
    sql_text: str,
    user: UserContext = Depends(require_action("use_sql_console")),
    db: Session = Depends(get_session)
):
    config = load_app_config()
    audit_service = SecurityAuditService(db, config)
    sql_service = SqlConsoleService(db, config, audit_service)

    result = sql_service.execute_sql(sql_text, user)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.post("/imports/upload")
async def upload_secure_import(
    import_type: str,
    faculty_id: int | None = None,
    year: int | None = None,
    file: UploadFile = File(...),
    user: UserContext = Depends(require_action("import_data")),
    db: Session = Depends(get_session)
):
    config = load_app_config()
    upload_security = FileUploadSecurityService(config)
    audit_service = SecurityAuditService(db, config)
    secure_import_service = SecureImportService(db, config, upload_security, audit_service)

    job = await secure_import_service.create_import_job(import_type, file, user, faculty_id, year)
    return {"job_id": job.id, "status": job.status, "message": "File uploaded securely"}

@router.post("/imports/{job_id}/approve")
def approve_secure_import(
    job_id: str,
    user: UserContext = Depends(require_action("approve_import")),
    db: Session = Depends(get_session)
):
    config = load_app_config()
    upload_security = FileUploadSecurityService(config)
    audit_service = SecurityAuditService(db, config)
    secure_import_service = SecureImportService(db, config, upload_security, audit_service)

    job = secure_import_service.approve_import_job(job_id, user)
    return {"job_id": job.id, "status": job.status}

@router.get("/audit-logs/verify-chain")
def verify_audit_chain(
    user: UserContext = Depends(require_action("view_audit_logs")),
    db: Session = Depends(get_session)
):
    config = load_app_config()
    audit_service = SecurityAuditService(db, config)
    return audit_service.verify_audit_chain()

@router.post("/backups/create")
def create_backup(
    snapshot_type: str = "manual",
    user: UserContext = Depends(require_action("manage_schema")),
    db: Session = Depends(get_session)
):
    config = load_app_config()
    backup_service = BackupRestoreService(db, config)
    snapshot = backup_service.create_sqlite_backup(snapshot_type=snapshot_type, created_by=user.username)
    return {"snapshot_id": snapshot.id, "path": snapshot.snapshot_path}
