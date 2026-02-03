"""JWT auth utilities."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from jose import jwt, JWTError

from app.config import settings


ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


def _utcnow() -> datetime:
    return datetime.utcnow()


def create_access_token(admin_id: int, username: str, role: str) -> str:
    expires = _utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(admin_id),
        "username": username,
        "role": role,
        "type": ACCESS_TOKEN_TYPE,
        "exp": expires,
        "iat": _utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(admin_id: int) -> tuple[str, str, datetime]:
    jti = str(uuid4())
    expires = _utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(admin_id),
        "type": REFRESH_TOKEN_TYPE,
        "jti": jti,
        "exp": expires,
        "iat": _utcnow(),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti, expires


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def is_token_type(payload: dict, token_type: str) -> bool:
    return payload.get("type") == token_type


def get_admin_id(payload: dict) -> Optional[int]:
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        return int(sub)
    except Exception:
        return None
