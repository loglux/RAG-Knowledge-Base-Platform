"""
Single-use admin invite links.

An existing admin creates an invite; the raw token is shown to them exactly
once (same pattern as app/services/mcp_tokens.py - only its SHA256 hash is
persisted), to be shared out-of-band (WhatsApp, Telegram, ...). The invitee
opens a link containing the token and picks their own username/password -
the token itself is never a secret the admin has to transmit or the invitee
has to be handed in plaintext by someone else.
"""

import hashlib
import secrets
from datetime import timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AdminInvite
from app.utils.time import utcnow

DEFAULT_EXPIRES_IN_HOURS = 72


class AdminInviteError(Exception):
    """Invite is missing, expired, revoked, or already used."""


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def create_invite(
    db: AsyncSession,
    created_by: int,
    label: Optional[str] = None,
    expires_in_hours: int = DEFAULT_EXPIRES_IN_HOURS,
) -> tuple[AdminInvite, str]:
    """Create a new invite. Returns (record, plaintext token) - the token is
    never retrievable again after this call returns."""
    token = secrets.token_urlsafe(32)
    invite = AdminInvite(
        token_hash=_hash_token(token),
        label=label,
        created_by=created_by,
        expires_at=utcnow() + timedelta(hours=expires_in_hours),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    return invite, token


async def get_valid_invite(db: AsyncSession, token: str) -> AdminInvite:
    """
    Look up an invite by its raw token and verify it's still usable.

    Raises:
        AdminInviteError: token doesn't exist, or is expired/revoked/used.
    """
    result = await db.execute(
        select(AdminInvite).where(AdminInvite.token_hash == _hash_token(token))
    )
    invite = result.scalar_one_or_none()
    if invite is None:
        raise AdminInviteError("Invite not found.")
    if invite.revoked_at is not None:
        raise AdminInviteError("This invite has been revoked.")
    if invite.used_at is not None:
        raise AdminInviteError("This invite has already been used.")
    if invite.expires_at < utcnow():
        raise AdminInviteError("This invite has expired.")
    return invite


async def list_invites(db: AsyncSession) -> List[AdminInvite]:
    """List every invite, most recent first - any admin can see who else
    has been invited (matches the "any admin can invite" trust model)."""
    result = await db.execute(select(AdminInvite).order_by(AdminInvite.created_at.desc()))
    return list(result.scalars().all())


async def revoke_invite(db: AsyncSession, invite_id: UUID) -> AdminInvite:
    """Revoke a pending invite. Raises AdminInviteError if already used."""
    invite = await db.get(AdminInvite, invite_id)
    if invite is None:
        raise AdminInviteError("Invite not found.")
    if invite.used_at is not None:
        raise AdminInviteError("Cannot revoke an invite that's already been used.")
    invite.revoked_at = utcnow()
    await db.commit()
    await db.refresh(invite)
    return invite
