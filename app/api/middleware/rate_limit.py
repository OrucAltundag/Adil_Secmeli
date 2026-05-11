# -*- coding: utf-8 -*-
import time
from fastapi import Request, status
from fastapi.responses import JSONResponse
from collections import defaultdict
from typing import Dict

from app.core.config import load_app_config
from app.services.security_audit_service import SecurityAuditService
from app.db.database import SessionLocal

# Simple in-memory rate limiter for demonstration.
# In a real production scenario, use Redis.
class RateLimiter:
    def __init__(self):
        self._requests: Dict[str, list] = defaultdict(list)

    def _cleanup(self, key: str, window: int):
        now = time.time()
        self._requests[key] = [t for t in self._requests[key] if now - t < window]

    def is_allowed(self, key: str, limit: int, window: int = 60) -> bool:
        self._cleanup(key, window)
        if len(self._requests[key]) >= limit:
            return False
        self._requests[key].append(time.time())
        return True

limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    config = load_app_config()
    
    if not config.rate_limit_enabled:
        return await call_next(request)

    # Determine key
    # Ideally client_id if authenticated, else IP
    # We will just use IP for this middleware as auth is handled later in the pipeline
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path

    # Determine limit based on path
    limit = config.rate_limit_per_minute
    if "/import" in path:
        limit = config.rate_limit_import_per_minute
    elif "/algorithm" in path:
        limit = config.rate_limit_algorithm_run_per_minute

    if not limiter.is_allowed(client_ip, limit):
        # Log to audit
        db = SessionLocal()
        try:
            audit = SecurityAuditService(db, config)
            audit.log_event(
                event_type="rate_limit_exceeded",
                actor_type="ip",
                actor_id=client_ip,
                action="request",
                message=f"Rate limit exceeded on {path}",
                success=False,
                severity="warning"
            )
        finally:
            db.close()
            
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Çok fazla istek gönderildi. Lütfen daha sonra tekrar deneyin."},
        )

    response = await call_next(request)
    return response
