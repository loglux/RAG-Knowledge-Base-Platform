"""MCP mount manager for dynamic reloads."""
import logging
from typing import List, Optional

from fastapi import FastAPI
from starlette.routing import BaseRoute, Mount

from app.config import settings
from app.mcp.middleware import MCPAcceptMiddleware, MCPAuthMiddleware
from app.mcp.server import get_mcp_app

logger = logging.getLogger(__name__)


def _normalize_mount_path() -> str:
    path = settings.MCP_PATH if settings.MCP_PATH.startswith("/") else f"/{settings.MCP_PATH}"
    path = path.rstrip("/") or "/mcp"
    return path


def _remove_routes(routes: List[BaseRoute], remove: List[BaseRoute]) -> List[BaseRoute]:
    if not remove:
        return list(routes)
    remove_set = {id(route) for route in remove}
    return [route for route in routes if id(route) not in remove_set]


async def reload_mcp_routes(app: FastAPI) -> None:
    """Rebuild and remount MCP routes based on latest settings."""
    try:
        mcp_app, well_known_routes, oauth_enabled = get_mcp_app()
    except Exception as exc:
        logger.warning("Failed to rebuild MCP app: %s", exc)
        return

    if mcp_app is None:
        logger.warning("MCP app is not available; skipping reload.")
        return

    try:
        mcp_app.add_middleware(MCPAcceptMiddleware)
        if not oauth_enabled:
            mcp_app.add_middleware(MCPAuthMiddleware)
        if hasattr(mcp_app, "router"):
            mcp_app.router.redirect_slashes = False
    except Exception as exc:
        logger.warning("Failed to configure MCP middleware: %s", exc)

    mount_path = _normalize_mount_path()

    # Remove previous MCP routes if present
    previous_well_known: List[BaseRoute] = getattr(app.state, "mcp_well_known_routes", [])
    previous_mount: Optional[BaseRoute] = getattr(app.state, "mcp_mount_route", None)
    to_remove = list(previous_well_known)
    if previous_mount is not None:
        to_remove.append(previous_mount)

    routes = _remove_routes(list(app.router.routes), to_remove)

    # Add new well-known routes (if any) at the front
    if well_known_routes:
        routes = list(well_known_routes) + routes

    # Mount MCP endpoint at the end
    mount_route = Mount(mount_path, app=mcp_app)
    routes.append(mount_route)

    app.router.routes = routes
    app.state.mcp_well_known_routes = list(well_known_routes)
    app.state.mcp_mount_route = mount_route

    logger.info("Reloaded MCP routes at %s (oauth=%s)", mount_path, oauth_enabled)
