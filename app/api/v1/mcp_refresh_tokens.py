"""MCP refresh token management endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_admin_id
from app.models.database import AdminUser
from app.services.mcp_tokens import list_mcp_refresh_tokens, revoke_mcp_refresh_token

router = APIRouter(prefix="/mcp-refresh-tokens", tags=["mcp"])


class MCPRefreshTokenResponse(BaseModel):
    jti: str
    admin_user_id: int
    admin_username: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


@router.get("/", response_model=list[MCPRefreshTokenResponse])
async def list_refresh_tokens(
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(get_current_admin_id),
):
    tokens = await list_mcp_refresh_tokens(db)
    if not tokens:
        return []

    admin_ids = {t.admin_user_id for t in tokens}
    result = await db.execute(
        select(AdminUser.id, AdminUser.username).where(AdminUser.id.in_(admin_ids))
    )
    admin_map = {row[0]: row[1] for row in result.all()}

    return [
        MCPRefreshTokenResponse(
            jti=t.jti,
            admin_user_id=t.admin_user_id,
            admin_username=admin_map.get(t.admin_user_id, "unknown"),
            created_at=t.created_at,
            expires_at=t.expires_at,
            revoked_at=t.revoked_at,
        )
        for t in tokens
    ]


@router.delete("/{jti}", response_model=dict)
async def revoke_refresh_token(
    jti: str,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(get_current_admin_id),
):
    ok = await revoke_mcp_refresh_token(db, jti)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refresh token not found")
    return {"status": "revoked", "jti": jti}
