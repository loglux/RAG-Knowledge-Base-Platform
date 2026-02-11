"""OAuth-style token endpoint for MCP clients."""
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, Form, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.system_settings import SystemSettingsManager
from app.models.database import AdminUser
from app.services.mcp_tokens import (
    create_mcp_access_token,
    create_mcp_refresh_token,
    store_mcp_refresh_token,
    revoke_mcp_refresh_token,
    validate_mcp_refresh_token,
)

router = APIRouter(prefix="/oauth", tags=["oauth"])


def _parse_positive_int(value: str | None, field_name: str) -> int:
    if not value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing {field_name} setting")
    try:
        parsed = int(value)
        if parsed > 0:
            return parsed
    except (TypeError, ValueError):
        pass
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field_name} setting")


class OAuthTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None


@router.post("/token", response_model=OAuthTokenResponse)
async def oauth_token(
    grant_type: str = Form(...),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    if grant_type == "password":
        if not username or not password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing credentials")
        result = await db.execute(select(AdminUser).where(AdminUser.username == username))
        admin = result.scalar_one_or_none()
        if not admin or not admin.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not bcrypt.checkpw(password.encode("utf-8"), admin.password_hash.encode("utf-8")):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        access_ttl = _parse_positive_int(
            await SystemSettingsManager.get_setting(db, "mcp_access_token_ttl_minutes"),
            "mcp_access_token_ttl_minutes",
        )
        refresh_ttl = _parse_positive_int(
            await SystemSettingsManager.get_setting(db, "mcp_refresh_token_ttl_days"),
            "mcp_refresh_token_ttl_days",
        )
        access_token, expires_in = create_mcp_access_token(admin.id, access_ttl)
        refresh_token_value, jti, expires_at = create_mcp_refresh_token(admin.id, refresh_ttl)
        await store_mcp_refresh_token(db, admin.id, jti, expires_at)

        return OAuthTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            refresh_token=refresh_token_value,
        )

    if grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing refresh token")
        validated = await validate_mcp_refresh_token(db, refresh_token)
        if not validated:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        admin_id, jti = validated

        # Rotate refresh token
        await revoke_mcp_refresh_token(db, jti)
        access_ttl = _parse_positive_int(
            await SystemSettingsManager.get_setting(db, "mcp_access_token_ttl_minutes"),
            "mcp_access_token_ttl_minutes",
        )
        refresh_ttl = _parse_positive_int(
            await SystemSettingsManager.get_setting(db, "mcp_refresh_token_ttl_days"),
            "mcp_refresh_token_ttl_days",
        )
        access_token, expires_in = create_mcp_access_token(admin_id, access_ttl)
        refresh_token_value, new_jti, expires_at = create_mcp_refresh_token(admin_id, refresh_ttl)
        await store_mcp_refresh_token(db, admin_id, new_jti, expires_at)

        return OAuthTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            refresh_token=refresh_token_value,
        )

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported grant_type")
