"""MCP token management service."""

import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID, uuid4

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import MCPToken

MCP_TOKEN_TYPE = "mcp"


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


async def list_mcp_tokens(db: AsyncSession) -> List[MCPToken]:
    result = await db.execute(select(MCPToken).order_by(MCPToken.created_at.desc()))
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
    except JWTError:
        return None
    if payload.get("type") != MCP_TOKEN_TYPE:
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
