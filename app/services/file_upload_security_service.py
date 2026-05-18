# -*- coding: utf-8 -*-
import hashlib
import os
import re
import unicodedata

from fastapi import HTTPException, UploadFile

from app.core.config import AppConfig


class FileUploadSecurityService:
    def __init__(self, config: AppConfig):
        self.config = config

    def sanitize_filename(self, filename: str) -> str:
        """Secure the filename and remove path traversal artifacts."""
        filename = os.path.basename(filename)
        filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode('utf-8')
        safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '', filename)
        if not safe_name:
            raise HTTPException(status_code=400, detail="Invalid filename.")
        return safe_name

    def validate_extension(self, filename: str) -> None:
        """Validate file extension against allowlist."""
        ext = os.path.splitext(filename)[1].lower()
        allowed = [e.strip() for e in self.config.allowed_upload_extensions.split(',')]
        if ext not in allowed:
            raise HTTPException(status_code=400, detail=f"File extension {ext} not allowed.")

    def validate_mime_type(self, content_type: str) -> None:
        """Validate MIME type."""
        allowed = [m.strip() for m in self.config.allowed_upload_mime_types.split(',')]
        if content_type not in allowed:
            raise HTTPException(status_code=400, detail=f"MIME type {content_type} not allowed.")

    async def validate_size_and_hash(self, file: UploadFile) -> tuple[str, int]:
        """Validate file size and compute hash in chunks."""
        max_bytes = self.config.max_upload_size_mb * 1024 * 1024
        file_hash = hashlib.sha256()
        total_size = 0

        # Read in chunks
        chunk_size = 65536
        while chunk := await file.read(chunk_size):
            total_size += len(chunk)
            if total_size > max_bytes:
                raise HTTPException(status_code=413, detail=f"File exceeds maximum allowed size of {self.config.max_upload_size_mb} MB.")
            file_hash.update(chunk)

        # Seek back to 0 for normal reading later
        await file.seek(0)

        return file_hash.hexdigest(), total_size

    async def validate_upload(self, file: UploadFile) -> tuple[str, int]:
        """Perform all file security validations and return hash + byte size."""
        self.validate_extension(file.filename)
        self.validate_mime_type(file.content_type)
        return await self.validate_size_and_hash(file)
