# -*- coding: utf-8 -*-
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class UserContext(BaseModel):
    user_id: Optional[str] = None
    client_id: Optional[str] = None
    username: str
    role: str
    faculty_id: Optional[int] = None
    department_id: Optional[int] = None
    is_authenticated: bool = False
    environment: str = "production"
    permissions: Optional[List[str]] = None

class ApiClientCreate(BaseModel):
    client_name: str
    role: str = "api_client"
    faculty_id: Optional[int] = None
    department_id: Optional[int] = None
    notes: Optional[str] = None

class ApiClientResponse(BaseModel):
    id: str
    client_name: str
    role: str
    faculty_id: Optional[int] = None
    department_id: Optional[int] = None
    is_active: bool
    created_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

class ApiClientCreatedResponse(ApiClientResponse):
    api_key: str  # Only returned once on creation
