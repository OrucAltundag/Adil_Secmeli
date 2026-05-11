# -*- coding: utf-8 -*-
import os
import shutil
import hashlib
from datetime import datetime, timezone
import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.db.models import DataSnapshot
from app.core.config import AppConfig

class BackupRestoreService:
    def __init__(self, db: Session, config: AppConfig):
        self.db = db
        self.config = config

    def create_sqlite_backup(self, snapshot_type: str, scope_type: str = "global", 
                           faculty_id: int = None, department_id: int = None, year: int = None, 
                           related_import_job_id: str = None, related_decision_run_id: int = None, 
                           created_by: str = "system") -> DataSnapshot:
        
        db_path = self.config.sqlite_db_path
        if not os.path.exists(db_path):
            raise Exception(f"Database file not found at {db_path}")

        snapshot_id = f"snap_{uuid.uuid4().hex}"
        
        # Ensure backups directory exists
        base_dir = os.path.dirname(db_path)
        backup_dir = os.path.join(base_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)

        backup_path = os.path.join(backup_dir, f"{snapshot_id}.db")

        # Copy file
        shutil.copy2(db_path, backup_path)

        # Hash
        hash_sha256 = hashlib.sha256()
        with open(backup_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        snapshot_hash = hash_sha256.hexdigest()

        snapshot = DataSnapshot(
            id=snapshot_id,
            snapshot_type=snapshot_type,
            scope_type=scope_type,
            faculty_id=faculty_id,
            department_id=department_id,
            year=year,
            related_import_job_id=related_import_job_id,
            related_decision_run_id=related_decision_run_id,
            snapshot_path=backup_path,
            snapshot_hash=snapshot_hash,
            created_by=created_by,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot

    def create_pre_import_backup(self, import_job_id: str, created_by: str) -> DataSnapshot:
        if not self.config.backup_before_import:
            return None
        return self.create_sqlite_backup("import_pre_apply", related_import_job_id=import_job_id, created_by=created_by)

    def restore_from_snapshot(self, snapshot_id: str) -> bool:
        snapshot = self.db.query(DataSnapshot).filter(DataSnapshot.id == snapshot_id).first()
        if not snapshot:
            raise HTTPException(status_code=404, detail="Snapshot not found")

        backup_path = snapshot.snapshot_path
        if not os.path.exists(backup_path):
            raise HTTPException(status_code=404, detail="Backup file is missing on disk")

        # Verify hash
        hash_sha256 = hashlib.sha256()
        with open(backup_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        if hash_sha256.hexdigest() != snapshot.snapshot_hash:
            raise HTTPException(status_code=400, detail="Snapshot hash mismatch. File may be corrupted.")

        # In a real system, you cannot replace the DB file while the connection is open
        # This is a conceptual implementation for SQLite. In reality you'd need to close the DB connection,
        # copy the file, and restart or reconnect.
        
        db_path = self.config.sqlite_db_path
        shutil.copy2(backup_path, db_path)

        return True
