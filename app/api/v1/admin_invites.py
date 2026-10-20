"""
Admin invite endpoints.

Registered under the public api_router (like setup.py/uploads.py), not
protected_router - the create/list/revoke endpoints enforce auth themselves
via get_current_user_id, while the token-check/accept endpoints are
intentionally public (an invitee has no account yet to authenticate with).
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.models.schemas import (
    AdminInviteAcceptRequest,
    AdminInviteCreateRequest,
    AdminInviteCreateResponse,
    AdminInviteStatusResponse,
    AdminInviteSummary,
)
from app.services.admin_invites import (
    AdminInviteError,
    create_invite,
    get_valid_invite,
    list_invites,
    revoke_invite,
)
from app.services.setup_manager import SetupError, SetupManager
from app.utils.time import utcnow

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin-invites", tags=["admin-invites"])


def _invite_status(invite) -> str:
    if invite.used_at is not None:
        return "used"
    if invite.revoked_at is not None:
        return "revoked"
    if invite.expires_at < utcnow():
        return "expired"
    return "pending"


@router.post("/", response_model=AdminInviteCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_invite(
    request: AdminInviteCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin_id: Optional[int] = Depends(get_current_user_id),
):
    """
    Create a one-time invite link for a new admin account.

    Any existing admin can invite - there's no separate "owner" tier.
    The returned token is shown exactly once; share the link out-of-band
    (WhatsApp, Telegram, ...). The invitee opens it and picks their own
    username/password - nobody but them ever sees their password.
    """
    assert admin_id is not None  # get_current_user_id raises 401 before returning None
    invite, token = await create_invite(
        db=db,
        created_by=admin_id,
        label=request.label,
        expires_in_hours=request.expires_in_hours,
    )
    return AdminInviteCreateResponse(
        id=invite.id,
        invite_token=token,
        label=invite.label,
        expires_at=invite.expires_at,
    )


@router.get("/", response_model=List[AdminInviteSummary])
async def list_admin_invites(
    db: AsyncSession = Depends(get_db),
    admin_id: Optional[int] = Depends(get_current_user_id),
):
    """List every invite (pending/used/revoked/expired), most recent first."""
    invites = await list_invites(db)
    return [
        AdminInviteSummary(
            id=invite.id,
            label=invite.label,
            created_by=invite.created_by,
            created_at=invite.created_at,
            expires_at=invite.expires_at,
            revoked_at=invite.revoked_at,
            used_at=invite.used_at,
            status=_invite_status(invite),
        )
        for invite in invites
    ]


@router.delete("/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_admin_invite(
    invite_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_id: Optional[int] = Depends(get_current_user_id),
):
    """Revoke a pending invite before it's used."""
    try:
        await revoke_invite(db, invite_id)
    except AdminInviteError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return None


@router.get("/{token}/check", response_model=AdminInviteStatusResponse)
async def check_admin_invite(token: str, db: AsyncSession = Depends(get_db)):
    """
    Public: check whether an invite token is still valid, without consuming it.

    The invite-accept page calls this first to decide what to show the
    visitor (a signup form, or "this link is no longer valid").
    """
    try:
        invite = await get_valid_invite(db, token)
    except AdminInviteError as exc:
        return AdminInviteStatusResponse(valid=False, detail=str(exc))
    return AdminInviteStatusResponse(valid=True, label=invite.label, detail=None)


@router.post("/{token}/accept", status_code=status.HTTP_201_CREATED)
async def accept_admin_invite(
    token: str,
    request: AdminInviteAcceptRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Public: consume an invite and create the new admin account.

    The invitee logs in separately afterwards with their new credentials -
    this endpoint only creates the account.
    """
    try:
        invite = await get_valid_invite(db, token)
    except AdminInviteError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    try:
        admin = await SetupManager.create_admin_user(
            db=db,
            username=request.username,
            password=request.password,
            email=request.email,
        )
    except SetupError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    invite.used_at = utcnow()
    invite.used_by_admin_id = admin.id
    await db.commit()

    logger.info(f"Admin invite {invite.id} accepted - created admin '{admin.username}'")

    return {
        "success": True,
        "username": admin.username,
        "message": "Account created. You can now log in.",
    }
