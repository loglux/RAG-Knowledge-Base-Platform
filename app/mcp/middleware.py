"""MCP authentication middleware."""

from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.db.session import get_db_session
from app.core.system_settings import SystemSettingsManager
from app.services.mcp_tokens import verify_mcp_token, verify_mcp_access_token


async def _get_mcp_enabled() -> bool:
    async with get_db_session() as db:
        raw = await SystemSettingsManager.get_setting(db, "mcp_enabled")
    if raw is None:
        return bool(settings.MCP_ENABLED)
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


async def _get_mcp_auth_mode() -> str:
    async with get_db_session() as db:
        raw = await SystemSettingsManager.get_setting(db, "mcp_auth_mode")
    if raw is None or not str(raw).strip():
        return (settings.MCP_AUTH_MODE or "bearer").strip().lower()
    return str(raw).strip().lower()


class MCPAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not await _get_mcp_enabled():
            return JSONResponse({"detail": "MCP endpoint is disabled"}, status_code=404)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        mode = await _get_mcp_auth_mode()
        if mode == "bearer":
            async with get_db_session() as db:
                record = await verify_mcp_token(db, token)
        else:
            record = await verify_mcp_access_token(token)

        if record is None:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        request.state.mcp_admin_id = record.admin_user_id
        return await call_next(request)


class MCPAcceptMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        accept = request.headers.get("accept")
        if accept is None:
            normalized = ""
        else:
            normalized = accept.lower()

        want_json = "application/json" in normalized
        want_sse = "text/event-stream" in normalized

        if not want_json or not want_sse:
            headers = [(k, v) for (k, v) in request.scope.get("headers", []) if k.lower() != b"accept"]
            merged = []
            if accept:
                merged.append(accept)
            if not want_json:
                merged.append("application/json")
            if not want_sse:
                merged.append("text/event-stream")
            headers.append((b"accept", ", ".join(merged).encode("utf-8")))
            request.scope["headers"] = headers
        return await call_next(request)
