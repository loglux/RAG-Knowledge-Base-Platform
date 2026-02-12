"""MCP OAuth event listing endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_admin_id
from app.models.database import AdminUser
from app.services.mcp_oauth_events import list_mcp_oauth_events

router = APIRouter(prefix="/mcp-oauth-events", tags=["mcp"])


class MCPOAuthEventResponse(BaseModel):
    id: str
    event_type: str
    client_id: str | None
    admin_user_id: int | None
    admin_username: str | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime


@router.get("/", response_model=list[MCPOAuthEventResponse])
async def list_oauth_events(
    limit: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin_id: int = Depends(get_current_admin_id),
):
    events = await list_mcp_oauth_events(db, limit=limit)
    if not events:
        return []

    admin_ids = {e.admin_user_id for e in events if e.admin_user_id is not None}
    admin_map = {}
    if admin_ids:
        result = await db.execute(select(AdminUser.id, AdminUser.username).where(AdminUser.id.in_(admin_ids)))
        admin_map = {row[0]: row[1] for row in result.all()}

    return [
        MCPOAuthEventResponse(
            id=str(e.id),
            event_type=e.event_type,
            client_id=e.client_id,
            admin_user_id=e.admin_user_id,
            admin_username=admin_map.get(e.admin_user_id),
            ip_address=e.ip_address,
            user_agent=e.user_agent,
            created_at=e.created_at,
        )
        for e in events
    ]
