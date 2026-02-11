"""MCP authentication middleware."""

from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.db.session import get_db_session
from app.core.system_settings import SystemSettingsManager
from app.services.mcp_tokens import verify_mcp_token


async def _get_mcp_enabled() -> bool:
    async with get_db_session() as db:
        raw = await SystemSettingsManager.get_setting(db, "mcp_enabled")
    if raw is None:
        return bool(settings.MCP_ENABLED)
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


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

        async with get_db_session() as db:
            record = await verify_mcp_token(db, token)

        if record is None:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        request.state.mcp_admin_id = record.admin_user_id
        return await call_next(request)
