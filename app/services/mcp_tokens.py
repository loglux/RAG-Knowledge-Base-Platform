"""MCP token management service."""

import hashlib
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Optional, List
from uuid import UUID, uuid4

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import MCPToken, MCPRefreshToken

MCP_TOKEN_TYPE = "mcp"
MCP_ACCESS_TOKEN_TYPE = "mcp_access"
MCP_REFRESH_TOKEN_TYPE = "mcp_refresh"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _token_prefix(token: str, length: int = 8) -> str:
    return token[:length]


async def create_mcp_token(
    db: AsyncSession,
    admin_user_id: int,
    name: Optional[str] = None,
    expires_in_days: Optional[int] = None,
) -> tuple[MCPToken, str]:
    """Create a new MCP token and return (record, plaintext token)."""
    now = datetime.utcnow()
    expires_at = None
    if expires_in_days and expires_in_days > 0:
        expires_at = now + timedelta(days=expires_in_days)

    payload = {
        "sub": str(admin_user_id),
        "type": MCP_TOKEN_TYPE,
        "jti": str(uuid4()),
        "iat": now,
    }
    if expires_at:
        payload["exp"] = expires_at

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    token_hash = _hash_token(token)
    prefix = _token_prefix(token)

    record = MCPToken(
        admin_user_id=admin_user_id,
        name=name,
        token_hash=token_hash,
        token_prefix=prefix,
        created_at=datetime.utcnow(),
        expires_at=expires_at,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record, token


def _utcnow() -> datetime:
    return datetime.utcnow()


def create_mcp_access_token(admin_id: int, expires_in_minutes: Optional[int] = None) -> tuple[str, int]:
    if expires_in_minutes is None:
        raise ValueError("MCP access token TTL is not configured")
    ttl_minutes = expires_in_minutes
    expires = _utcnow() + timedelta(minutes=ttl_minutes)
    payload = {
        "sub": str(admin_id),
        "type": MCP_ACCESS_TOKEN_TYPE,
        "exp": expires,
        "iat": _utcnow(),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, ttl_minutes * 60


def create_mcp_refresh_token(admin_id: int, expires_in_days: Optional[int] = None) -> tuple[str, str, datetime]:
    jti = str(uuid4())
    if expires_in_days is None:
        raise ValueError("MCP refresh token TTL is not configured")
    ttl_days = expires_in_days
    expires = _utcnow() + timedelta(days=ttl_days)
    payload = {
        "sub": str(admin_id),
        "type": MCP_REFRESH_TOKEN_TYPE,
        "jti": jti,
        "exp": expires,
        "iat": _utcnow(),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti, expires


async def list_mcp_tokens(db: AsyncSession) -> List[MCPToken]:
    result = await db.execute(select(MCPToken).order_by(MCPToken.created_at.desc()))
    return list(result.scalars().all())


async def list_mcp_refresh_tokens(db: AsyncSession) -> List[MCPRefreshToken]:
    result = await db.execute(select(MCPRefreshToken).order_by(MCPRefreshToken.created_at.desc()))
    return list(result.scalars().all())


async def revoke_mcp_token(db: AsyncSession, token_id: UUID) -> bool:
    result = await db.execute(select(MCPToken).where(MCPToken.id == token_id))
    token = result.scalar_one_or_none()
    if not token:
        return False
    if token.revoked_at is None:
        token.revoked_at = datetime.utcnow()
        await db.commit()
    return True


async def delete_mcp_token(db: AsyncSession, token_id: UUID) -> bool:
    result = await db.execute(select(MCPToken).where(MCPToken.id == token_id))
    token = result.scalar_one_or_none()
    if not token:
        return False
    await db.delete(token)
    await db.commit()
    return True


async def verify_mcp_token(db: AsyncSession, token: str) -> Optional[MCPToken]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_type = payload.get("type")
        if token_type != MCP_TOKEN_TYPE:
            return None
    except JWTError:
        return None

    token_hash = _hash_token(token)
    result = await db.execute(select(MCPToken).where(MCPToken.token_hash == token_hash))
    record = result.scalar_one_or_none()
    if not record:
        return None
    if record.revoked_at is not None:
        return None
    if record.expires_at and record.expires_at <= datetime.utcnow():
        return None
    record.last_used_at = datetime.utcnow()
    await db.commit()
    return record


async def verify_mcp_access_token(token: str) -> Optional[SimpleNamespace]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != MCP_ACCESS_TOKEN_TYPE:
            return None
        admin_id = payload.get("sub")
        if not admin_id:
            return None
        return SimpleNamespace(admin_user_id=int(admin_id))
    except JWTError:
        return None


async def store_mcp_refresh_token(
    db: AsyncSession,
    admin_user_id: int,
    jti: str,
    expires_at: datetime,
) -> MCPRefreshToken:
    record = MCPRefreshToken(
        admin_user_id=admin_user_id,
        jti=jti,
        expires_at=expires_at,
        created_at=_utcnow(),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def revoke_mcp_refresh_token(db: AsyncSession, jti: str) -> bool:
    result = await db.execute(select(MCPRefreshToken).where(MCPRefreshToken.jti == jti))
    token = result.scalar_one_or_none()
    if not token:
        return False
    if token.revoked_at is None:
        token.revoked_at = _utcnow()
        await db.commit()
    return True


async def validate_mcp_refresh_token(db: AsyncSession, token: str) -> Optional[tuple[int, str]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
    if payload.get("type") != MCP_REFRESH_TOKEN_TYPE:
        return None
    admin_id = payload.get("sub")
    jti = payload.get("jti")
    if not admin_id or not jti:
        return None
    result = await db.execute(select(MCPRefreshToken).where(MCPRefreshToken.jti == jti))
    record = result.scalar_one_or_none()
    if not record or record.revoked_at is not None:
        return None
    if record.expires_at <= _utcnow():
        return None
    return int(admin_id), jti
