"""MCP OAuth event logging."""
from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import MCPAuthEvent


async def record_mcp_oauth_event(
    db: AsyncSession,
    *,
    event_type: str,
    admin_user_id: Optional[int],
    client_id: Optional[str],
    ip_address: Optional[str],
    user_agent: Optional[str],
) -> MCPAuthEvent:
    event = MCPAuthEvent(
        event_type=event_type,
        admin_user_id=admin_user_id,
        client_id=client_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def list_mcp_oauth_events(db: AsyncSession, limit: int = 20) -> Sequence[MCPAuthEvent]:
    stmt = select(MCPAuthEvent).order_by(MCPAuthEvent.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()
