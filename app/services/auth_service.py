# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import AppConfig, load_app_config
from app.core.security import (
    generate_api_key,
    generate_client_id,
    hash_api_key,
    verify_api_key,
)
from app.db.database import get_session
from app.db.models import ApiClient
from app.schemas.auth import ApiClientCreate, ApiClientCreatedResponse, UserContext

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self, db: Session, config: AppConfig):
        self.db = db
        self.config = config

    def create_api_client(self, data: ApiClientCreate) -> ApiClientCreatedResponse:
        client_id = generate_client_id()
        raw_key = generate_api_key()
        hashed_key = hash_api_key(raw_key)

        new_client = ApiClient(
            id=client_id,
            client_name=data.client_name,
            api_key_hash=hashed_key,
            role=data.role,
            faculty_id=data.faculty_id,
            department_id=data.department_id,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            notes=data.notes
        )
        self.db.add(new_client)
        self.db.commit()
        self.db.refresh(new_client)

        return ApiClientCreatedResponse(
            id=new_client.id,
            client_name=new_client.client_name,
            role=new_client.role,
            faculty_id=new_client.faculty_id,
            department_id=new_client.department_id,
            is_active=new_client.is_active,
            created_at=new_client.created_at,
            last_used_at=new_client.last_used_at,
            api_key=raw_key
        )

    def verify_request(self, request: Request) -> Optional[ApiClient]:
        auth_header = request.headers.get("Authorization")
        api_key_header = request.headers.get("X-API-Key")

        raw_key = None
        if api_key_header:
            raw_key = api_key_header
        elif auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() in ["apikey", "bearer"]:
                raw_key = parts[1]

        if not raw_key:
            return None

        # To avoid timing attacks or full table scans, we must find the client by some criteria.
        # But we only have the raw key.
        # For simplicity, we can fetch all active clients and check.
        # In a very large scale system, we'd prefix the key with client ID.
        clients = self.db.query(ApiClient).filter(ApiClient.is_active == True).all()
        for client in clients:
            if verify_api_key(raw_key, client.api_key_hash):
                # Update last used
                client.last_used_at = datetime.now(timezone.utc)
                self.db.commit()
                return client
        return None

    def get_current_user_context(self, request: Request) -> UserContext:
        is_prod = self.config.environment == "production"

        if not self.config.api_auth_enabled:
            # If disabled in production, log a strong warning, but still allow if the config says so
            if is_prod:
                logger.warning("SECURITY WARNING: API_AUTH_ENABLED is false in production environment!")

            return UserContext(
                user_id="demo_user",
                username="Demo Admin",
                role="admin",
                is_authenticated=True,
                environment=self.config.environment
            )

        client = self.verify_request(request)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "ApiKey"},
            )

        return UserContext(
            client_id=client.id,
            username=client.client_name,
            role=client.role,
            faculty_id=client.faculty_id,
            department_id=client.department_id,
            is_authenticated=True,
            environment=self.config.environment
        )

def get_auth_service(db: Session = Depends(get_session)) -> AuthService:
    config = load_app_config()
    return AuthService(db, config)

def get_current_user(request: Request, auth_service: AuthService = Depends(get_auth_service)) -> UserContext:
    return auth_service.get_current_user_context(request)
