"""Prompt version management endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.models.database import AppSettings as AppSettingsModel
from app.models.database import PromptVersion as PromptVersionModel
from app.models.database import SelfCheckPromptVersion as SelfCheckPromptVersionModel
from app.models.schemas import (
    PromptVersionCreate,
    PromptVersionDetail,
    PromptVersionSummary,
    SelfCheckPromptVersionCreate,
    SelfCheckPromptVersionDetail,
    SelfCheckPromptVersionSummary,
)
from app.services.prompts import validate_system_prompt

router = APIRouter()


async def _get_or_create_settings(db: AsyncSession) -> AppSettingsModel:
    result = await db.execute(select(AppSettingsModel).order_by(AppSettingsModel.id).limit(1))
    row = result.scalar_one_or_none()
    if row is None:
        row = AppSettingsModel()
        db.add(row)
        await db.flush()
    return row


@router.get("/", response_model=list[PromptVersionSummary])
async def list_prompt_versions(
    db: AsyncSession = Depends(get_db),
):
    """List prompt versions (most recent first)."""
    result = await db.execute(
        select(PromptVersionModel).order_by(desc(PromptVersionModel.created_at))
    )
    prompts = result.scalars().all()
    return [
        PromptVersionSummary(
            id=prompt.id,
            name=prompt.name,
            created_at=prompt.created_at,
        )
        for prompt in prompts
    ]


@router.get("/active", response_model=Optional[PromptVersionDetail])
async def get_active_prompt(
    db: AsyncSession = Depends(get_db),
):
    """Get active prompt version detail."""
    settings = await _get_or_create_settings(db)
    if not settings.active_prompt_version_id:
        return None
    result = await db.execute(
        select(PromptVersionModel).where(PromptVersionModel.id == settings.active_prompt_version_id)
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        return None
    return PromptVersionDetail(
        id=prompt.id,
        name=prompt.name,
        system_content=prompt.system_content,
        created_at=prompt.created_at,
    )


@router.post("/", response_model=PromptVersionDetail)
async def create_prompt_version(
    payload: PromptVersionCreate,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """Create a new prompt version (optionally activate it)."""
    errors = validate_system_prompt(payload.system_content)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(errors),
        )

    default_name = f"KB Chat Prompt — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    prompt_name = payload.name.strip() if payload.name else default_name
    prompt = PromptVersionModel(
        name=prompt_name,
        system_content=payload.system_content,
        created_by=user_id,
    )
    db.add(prompt)
    await db.flush()

    if payload.activate:
        settings = await _get_or_create_settings(db)
        settings.active_prompt_version_id = prompt.id
        await db.flush()

    return PromptVersionDetail(
        id=prompt.id,
        name=prompt.name,
        system_content=prompt.system_content,
        created_at=prompt.created_at,
    )


@router.get("/self-check", response_model=list[SelfCheckPromptVersionSummary])
async def list_self_check_prompt_versions(
    db: AsyncSession = Depends(get_db),
):
    """List self-check prompt versions (most recent first)."""
    result = await db.execute(
        select(SelfCheckPromptVersionModel).order_by(desc(SelfCheckPromptVersionModel.created_at))
    )
    prompts = result.scalars().all()
    return [
        SelfCheckPromptVersionSummary(
            id=prompt.id,
            name=prompt.name,
            created_at=prompt.created_at,
        )
        for prompt in prompts
    ]


@router.get("/self-check/active", response_model=Optional[SelfCheckPromptVersionDetail])
async def get_active_self_check_prompt(
    db: AsyncSession = Depends(get_db),
):
    """Get active self-check prompt version detail."""
    settings = await _get_or_create_settings(db)
    if not settings.active_self_check_prompt_version_id:
        return None
    result = await db.execute(
        select(SelfCheckPromptVersionModel).where(
            SelfCheckPromptVersionModel.id == settings.active_self_check_prompt_version_id
        )
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        return None
    return SelfCheckPromptVersionDetail(
        id=prompt.id,
        name=prompt.name,
        system_content=prompt.system_content,
        created_at=prompt.created_at,
    )


@router.get("/self-check/{prompt_id}", response_model=SelfCheckPromptVersionDetail)
async def get_self_check_prompt_version(
    prompt_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get self-check prompt version detail."""
    result = await db.execute(
        select(SelfCheckPromptVersionModel).where(SelfCheckPromptVersionModel.id == prompt_id)
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Self-check prompt version not found"
        )
    return SelfCheckPromptVersionDetail(
        id=prompt.id,
        name=prompt.name,
        system_content=prompt.system_content,
        created_at=prompt.created_at,
    )


@router.post("/self-check", response_model=SelfCheckPromptVersionDetail)
async def create_self_check_prompt_version(
    payload: SelfCheckPromptVersionCreate,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """Create a new self-check prompt version (optionally activate it)."""
    errors = validate_system_prompt(payload.system_content)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(errors),
        )

    default_name = f"Self-Check Prompt — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    prompt_name = payload.name.strip() if payload.name else default_name
    prompt = SelfCheckPromptVersionModel(
        name=prompt_name,
        system_content=payload.system_content,
        created_by=user_id,
    )
    db.add(prompt)
    await db.flush()

    if payload.activate:
        settings = await _get_or_create_settings(db)
        settings.active_self_check_prompt_version_id = prompt.id
        await db.flush()

    return SelfCheckPromptVersionDetail(
        id=prompt.id,
        name=prompt.name,
        system_content=prompt.system_content,
        created_at=prompt.created_at,
    )


@router.post("/self-check/{prompt_id}/activate", response_model=SelfCheckPromptVersionDetail)
async def activate_self_check_prompt_version(
    prompt_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Activate an existing self-check prompt version."""
    result = await db.execute(
        select(SelfCheckPromptVersionModel).where(SelfCheckPromptVersionModel.id == prompt_id)
    )
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Self-check prompt version not found"
        )

    errors = validate_system_prompt(prompt.system_content)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(errors),
        )

    settings = await _get_or_create_settings(db)
    settings.active_self_check_prompt_version_id = prompt.id
    await db.flush()

    return SelfCheckPromptVersionDetail(
        id=prompt.id,
        name=prompt.name,
        system_content=prompt.system_content,
        created_at=prompt.created_at,
    )


@router.get("/{prompt_id}", response_model=PromptVersionDetail)
async def get_prompt_version(
    prompt_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get prompt version detail."""
    result = await db.execute(select(PromptVersionModel).where(PromptVersionModel.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Prompt version not found"
        )
    return PromptVersionDetail(
        id=prompt.id,
        name=prompt.name,
        system_content=prompt.system_content,
        created_at=prompt.created_at,
    )


@router.post("/{prompt_id}/activate", response_model=PromptVersionDetail)
async def activate_prompt_version(
    prompt_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Activate an existing prompt version."""
    result = await db.execute(select(PromptVersionModel).where(PromptVersionModel.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Prompt version not found"
        )

    errors = validate_system_prompt(prompt.system_content)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(errors),
        )

    settings = await _get_or_create_settings(db)
    settings.active_prompt_version_id = prompt.id
    await db.flush()

    return PromptVersionDetail(
        id=prompt.id,
        name=prompt.name,
        system_content=prompt.system_content,
        created_at=prompt.created_at,
    )
