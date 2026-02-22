"""OAuth-style token endpoint for MCP clients."""

import base64
import hashlib
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

import bcrypt
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.system_settings import SystemSettingsManager
from app.db.session import get_db
from app.models.database import AdminUser, MCPAuthCode
from app.services.mcp_oauth_events import record_mcp_oauth_event
from app.services.mcp_tokens import (
    create_mcp_access_token,
    create_mcp_refresh_token,
    revoke_mcp_refresh_token,
    store_mcp_refresh_token,
    validate_mcp_refresh_token,
)

router = APIRouter(prefix="/oauth", tags=["oauth"])
public_router = APIRouter(tags=["oauth"])

AUTH_CODE_TTL_MINUTES = 10


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _s256_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def _parse_list_setting(raw: Optional[str]) -> list[str]:
    if raw is None:
        return []
    raw = raw.strip()
    if not raw:
        return []
    if raw.startswith("["):
        try:
            return [str(item).strip() for item in json.loads(raw) if str(item).strip()]
        except Exception:
            return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _validate_redirect_uri_format(redirect_uri: str) -> None:
    parsed = urlparse(redirect_uri)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid redirect_uri")
    if parsed.fragment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="redirect_uri must not contain fragment"
        )
    if parsed.scheme == "http":
        host = (parsed.hostname or "").lower()
        if host not in {"localhost", "127.0.0.1", "::1"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="HTTP redirect_uri is allowed only for localhost",
            )


async def _validate_oauth_client(db: AsyncSession, client_id: str, redirect_uri: str) -> None:
    if not client_id or len(client_id) < 3 or len(client_id) > 128:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")

    _validate_redirect_uri_format(redirect_uri)

    allowed_clients = _parse_list_setting(
        await SystemSettingsManager.get_setting(db, "mcp_oauth_allowed_client_ids")
    )
    if allowed_clients and client_id not in allowed_clients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth client is not allowed"
        )

    allowed_redirect_uris = _parse_list_setting(
        await SystemSettingsManager.get_setting(db, "mcp_oauth_allowed_redirect_uris")
    )
    if not allowed_redirect_uris:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth redirect allowlist is not configured",
        )
    if redirect_uri not in allowed_redirect_uris:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="redirect_uri is not allowed"
        )


def _normalize_base_url(base_url: Optional[str], mcp_path: str) -> Optional[str]:
    if not base_url:
        return None
    value = base_url.strip().rstrip("/")
    if not value:
        return None
    path = mcp_path if mcp_path.startswith("/") else f"/{mcp_path}"
    if value.endswith(path):
        value = value[: -len(path)].rstrip("/")
    return value


async def _get_public_base_url(db: AsyncSession, request: Request) -> str:
    raw = await SystemSettingsManager.get_setting(db, "mcp_public_base_url")
    mcp_path = (await SystemSettingsManager.get_setting(db, "mcp_path")) or "/mcp"
    normalized = _normalize_base_url(raw, mcp_path)
    if normalized:
        return normalized
    base = str(request.base_url).rstrip("/")
    return base


def _parse_positive_int(value: str | None, field_name: str) -> int:
    if not value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing {field_name} setting"
        )
    try:
        parsed = int(value)
        if parsed > 0:
            return parsed
    except (TypeError, ValueError):
        pass
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field_name} setting"
    )


class OAuthTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None


class OAuthAuthorizeParams(BaseModel):
    response_type: str
    client_id: str
    redirect_uri: str
    code_challenge: str
    code_challenge_method: str
    state: Optional[str] = None


@public_router.get("/authorize", response_class=HTMLResponse)
async def oauth_authorize_form(
    request: Request,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    code_challenge_method: str = "S256",
    state: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    mode = (await SystemSettingsManager.get_setting(db, "mcp_auth_mode") or "bearer").lower()
    if mode != "oauth2":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OAuth2 is disabled")
    if response_type != "code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported response_type"
        )
    if code_challenge_method not in {"S256"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported code_challenge_method"
        )
    await _validate_oauth_client(db, client_id, redirect_uri)

    hidden = {
        "response_type": response_type,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "state": state or "",
    }
    inputs = "\n".join(f'<input type="hidden" name="{k}" value="{v}">' for k, v in hidden.items())
    return HTMLResponse(f"""
        <html>
          <head>
            <title>MCP Authorization</title>
          </head>
          <body style="font-family: sans-serif; max-width: 520px; margin: 40px auto;">
            <h2>MCP Authorization</h2>
            <p>Sign in with an admin account to authorize the client.</p>
            <form method="post" action="/authorize">
              {inputs}
              <label>Username</label><br/>
              <input type="text" name="username" style="width: 100%; padding: 8px; margin: 6px 0;" /><br/>
              <label>Password</label><br/>
              <input type="password" name="password" style="width: 100%; padding: 8px; margin: 6px 0;" /><br/>
              <button type="submit" style="padding: 10px 16px;">Authorize</button>
            </form>
          </body>
        </html>
        """)


@public_router.post("/authorize")
async def oauth_authorize(
    request: Request,
    response_type: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form("S256"),
    state: Optional[str] = Form(None),
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if response_type != "code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported response_type"
        )
    if code_challenge_method not in {"S256"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported code_challenge_method"
        )
    await _validate_oauth_client(db, client_id, redirect_uri)

    mode = (await SystemSettingsManager.get_setting(db, "mcp_auth_mode") or "bearer").lower()
    if mode != "oauth2":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OAuth2 is disabled")

    result = await db.execute(select(AdminUser).where(AdminUser.username == username))
    admin = result.scalar_one_or_none()
    if not admin or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not bcrypt.checkpw(password.encode("utf-8"), admin.password_hash.encode("utf-8")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    code = secrets.token_urlsafe(32)
    record = MCPAuthCode(
        admin_user_id=admin.id,
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_hash=_hash_code(code),
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        expires_at=datetime.utcnow() + timedelta(minutes=AUTH_CODE_TTL_MINUTES),
    )
    db.add(record)
    await db.commit()

    await record_mcp_oauth_event(
        db,
        event_type="authorize",
        admin_user_id=admin.id,
        client_id=client_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    redirect = f"{redirect_uri}?code={code}"
    if state:
        redirect += f"&state={state}"
    return RedirectResponse(url=redirect, status_code=status.HTTP_302_FOUND)


@public_router.post("/token", response_model=OAuthTokenResponse)
async def oauth_token_root(
    request: Request,
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    return await _handle_oauth_token(
        request=request,
        grant_type=grant_type,
        code=code,
        code_verifier=code_verifier,
        redirect_uri=redirect_uri,
        client_id=client_id,
        username=username,
        password=password,
        refresh_token=refresh_token,
        db=db,
    )


@router.post("/token", response_model=OAuthTokenResponse)
async def oauth_token(
    request: Request,
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    return await _handle_oauth_token(
        request=request,
        grant_type=grant_type,
        code=code,
        code_verifier=code_verifier,
        redirect_uri=redirect_uri,
        client_id=client_id,
        username=username,
        password=password,
        refresh_token=refresh_token,
        db=db,
    )


async def _handle_oauth_token(
    request: Request,
    grant_type: str,
    code: Optional[str],
    code_verifier: Optional[str],
    redirect_uri: Optional[str],
    client_id: Optional[str],
    username: Optional[str],
    password: Optional[str],
    refresh_token: Optional[str],
    db: AsyncSession,
):
    mode = (await SystemSettingsManager.get_setting(db, "mcp_auth_mode") or "bearer").lower()

    if grant_type == "password":
        if mode != "refresh":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Password grant disabled"
            )
        if not username or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Missing credentials"
            )
        result = await db.execute(select(AdminUser).where(AdminUser.username == username))
        admin = result.scalar_one_or_none()
        if not admin or not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        if not bcrypt.checkpw(password.encode("utf-8"), admin.password_hash.encode("utf-8")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

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

        await record_mcp_oauth_event(
            db,
            event_type="token",
            admin_user_id=admin.id,
            client_id=client_id or "password",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        return OAuthTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            refresh_token=refresh_token_value,
        )

    if grant_type == "authorization_code":
        if mode != "oauth2":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Authorization code grant disabled"
            )
        if not code or not code_verifier or not redirect_uri or not client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing authorization_code parameters",
            )
        await _validate_oauth_client(db, client_id, redirect_uri)

        code_hash = _hash_code(code)
        result = await db.execute(select(MCPAuthCode).where(MCPAuthCode.code_hash == code_hash))
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code")
        if record.used_at is not None or record.expires_at < datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Expired code")
        if record.client_id != client_id or record.redirect_uri != redirect_uri:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code parameters"
            )

        if record.code_challenge_method != "S256":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported code challenge method"
            )
        if _s256_challenge(code_verifier) != record.code_challenge:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid code verifier"
            )

        record.used_at = datetime.utcnow()
        await db.commit()

        access_ttl = _parse_positive_int(
            await SystemSettingsManager.get_setting(db, "mcp_access_token_ttl_minutes"),
            "mcp_access_token_ttl_minutes",
        )
        refresh_ttl = _parse_positive_int(
            await SystemSettingsManager.get_setting(db, "mcp_refresh_token_ttl_days"),
            "mcp_refresh_token_ttl_days",
        )
        access_token, expires_in = create_mcp_access_token(record.admin_user_id, access_ttl)
        refresh_token_value, jti, expires_at = create_mcp_refresh_token(
            record.admin_user_id, refresh_ttl
        )
        await store_mcp_refresh_token(db, record.admin_user_id, jti, expires_at)

        await record_mcp_oauth_event(
            db,
            event_type="token",
            admin_user_id=record.admin_user_id,
            client_id=client_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        return OAuthTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            refresh_token=refresh_token_value,
        )

    if grant_type == "refresh_token":
        if mode not in {"refresh", "oauth2"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token grant disabled"
            )
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Missing refresh token"
            )
        validated = await validate_mcp_refresh_token(db, refresh_token)
        if not validated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )

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

        await record_mcp_oauth_event(
            db,
            event_type="refresh",
            admin_user_id=admin_id,
            client_id=client_id or "refresh_token",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        return OAuthTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            refresh_token=refresh_token_value,
        )

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported grant_type")


@public_router.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_metadata(request: Request, db: AsyncSession = Depends(get_db)):
    base_url = await _get_public_base_url(db, request)
    return JSONResponse(
        {
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/authorize",
            "token_endpoint": f"{base_url}/token",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
        }
    )


@public_router.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_metadata(request: Request, db: AsyncSession = Depends(get_db)):
    base_url = await _get_public_base_url(db, request)
    mcp_path = (await SystemSettingsManager.get_setting(db, "mcp_path")) or "/mcp"
    mcp_path = mcp_path if mcp_path.startswith("/") else f"/{mcp_path}"
    return JSONResponse(
        {
            "resource": f"{base_url}{mcp_path}",
            "authorization_servers": [base_url],
        }
    )


@public_router.get("/.well-known/oauth-protected-resource/{resource:path}")
async def oauth_protected_resource_metadata_path(
    request: Request,
    resource: str,
    db: AsyncSession = Depends(get_db),
):
    return await oauth_protected_resource_metadata(request, db)
