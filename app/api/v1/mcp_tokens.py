"""MCP token management endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_admin_id
from app.services.mcp_tokens import (
    create_mcp_token,
    delete_mcp_token,
    list_mcp_tokens,
    revoke_mcp_token,
)

router = APIRouter(prefix="/mcp-tokens", tags=["mcp"])


class MCPTokenCreateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Label for the token")
    expires_in_days: Optional[int] = Field(None, ge=1, le=3650, description="Optional TTL in days")


class MCPTokenResponse(BaseModel):
    id: UUID
    name: Optional[str]
    token_prefix: str
    created_at: datetime
    expires_at: Optional[datetime]
    revoked_at: Optional[datetime]
    last_used_at: Optional[datetime]


class MCPTokenCreateResponse(BaseModel):
    token: str
    record: MCPTokenResponse


@router.get("/", response_model=list[MCPTokenResponse])
async def list_tokens(
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(get_current_admin_id),
):
    tokens = await list_mcp_tokens(db)
    return [
        MCPTokenResponse(
            id=t.id,
            name=t.name,
            token_prefix=t.token_prefix,
            created_at=t.created_at,
            expires_at=t.expires_at,
            revoked_at=t.revoked_at,
            last_used_at=t.last_used_at,
        )
        for t in tokens
    ]


@router.post("/", response_model=MCPTokenCreateResponse)
async def create_token(
    payload: MCPTokenCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(get_current_admin_id),
):
    record, token = await create_mcp_token(
        db=db,
        admin_user_id=admin_id,
        name=payload.name,
        expires_in_days=payload.expires_in_days,
    )
    return MCPTokenCreateResponse(
        token=token,
        record=MCPTokenResponse(
            id=record.id,
            name=record.name,
            token_prefix=record.token_prefix,
            created_at=record.created_at,
            expires_at=record.expires_at,
            revoked_at=record.revoked_at,
            last_used_at=record.last_used_at,
        ),
    )


@router.delete("/{token_id}", response_model=dict)
async def revoke_token(
    token_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(get_current_admin_id),
):
    ok = await revoke_mcp_token(db, token_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    return {"status": "revoked", "token_id": str(token_id)}


@router.delete("/{token_id}/purge", response_model=dict)
async def delete_token(
    token_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(get_current_admin_id),
):
    ok = await delete_mcp_token(db, token_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    return {"status": "deleted", "token_id": str(token_id)}
