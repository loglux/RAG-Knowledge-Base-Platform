"""Authentication endpoints (JWT + refresh tokens)."""

from datetime import datetime

import bcrypt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_admin_id,
    is_token_type,
)
from app.db.session import get_db
from app.dependencies import get_current_admin_id
from app.models.database import AdminRefreshToken, AdminUser
from app.models.schemas import LoginRequest, MeResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/api/v1/auth",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AdminUser).where(AdminUser.username == payload.username))
    admin = result.scalar_one_or_none()
    if not admin or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not bcrypt.checkpw(payload.password.encode("utf-8"), admin.password_hash.encode("utf-8")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(admin.id, admin.username, admin.role)
    refresh_token, jti, expires_at = create_refresh_token(admin.id)

    db.add(
        AdminRefreshToken(
            admin_user_id=admin.id,
            jti=jti,
            expires_at=expires_at,
            created_at=datetime.utcnow(),
        )
    )
    admin.last_login = datetime.utcnow()
    await db.commit()

    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        admin_id=admin.id,
        username=admin.username,
        role=admin.role,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token"
        )

    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    if not is_token_type(payload, REFRESH_TOKEN_TYPE):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    admin_id = get_admin_id(payload)
    jti = payload.get("jti")
    if not admin_id or not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    token_result = await db.execute(select(AdminRefreshToken).where(AdminRefreshToken.jti == jti))
    token_row = token_result.scalar_one_or_none()
    if not token_row or token_row.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked"
        )

    if token_row.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
        )

    # Rotate refresh token
    token_row.revoked_at = datetime.utcnow()
    access_token = None
    refresh_token_new, new_jti, expires_at = create_refresh_token(admin_id)

    db.add(
        AdminRefreshToken(
            admin_user_id=admin_id,
            jti=new_jti,
            expires_at=expires_at,
            created_at=datetime.utcnow(),
        )
    )

    admin_result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
    admin = admin_result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = create_access_token(admin.id, admin.username, admin.role)
    await db.commit()

    _set_refresh_cookie(response, refresh_token_new)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        admin_id=admin.id,
        username=admin.username,
        role=admin.role,
    )


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token:
        try:
            payload = decode_token(refresh_token)
            jti = payload.get("jti")
            if jti:
                await db.execute(
                    update(AdminRefreshToken)
                    .where(AdminRefreshToken.jti == jti)
                    .values(revoked_at=datetime.utcnow())
                )
                await db.commit()
        except Exception:
            pass

    _clear_refresh_cookie(response)
    return {"success": True}


@router.get("/me", response_model=MeResponse)
async def me(
    admin_id: int = Depends(get_current_admin_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AdminUser).where(AdminUser.id == admin_id))
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return MeResponse(
        admin_id=admin.id,
        username=admin.username,
        role=admin.role,
    )
