# -*- coding: utf-8 -*-
import secrets
import hashlib
import hmac

def generate_api_key(prefix: str = "ak") -> str:
    """Generate a secure API key."""
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}_{random_part}"

def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256 for storage."""
    # We use a simple SHA-256 hash here as API keys have high entropy.
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()

def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Constant-time comparison for API keys."""
    computed_hash = hash_api_key(plain_key)
    return hmac.compare_digest(computed_hash, hashed_key)

def generate_client_id() -> str:
    """Generate a unique client ID."""
    return f"client_{secrets.token_hex(8)}"
