"""Prompt version helpers."""
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    AppSettings as AppSettingsModel,
    PromptVersion as PromptVersionModel,
    SelfCheckPromptVersion as SelfCheckPromptVersionModel,
)


async def get_active_chat_prompt(db: AsyncSession) -> Tuple[Optional[str], Optional[UUID]]:
    """Return (system_content, prompt_version_id) for the active chat prompt."""
    result = await db.execute(select(AppSettingsModel).order_by(AppSettingsModel.id).limit(1))
    settings = result.scalar_one_or_none()
    if not settings or not settings.active_prompt_version_id:
        return None, None

    prompt_result = await db.execute(
        select(PromptVersionModel).where(PromptVersionModel.id == settings.active_prompt_version_id)
    )
    prompt = prompt_result.scalar_one_or_none()
    if not prompt:
        return None, None

    return prompt.system_content, prompt.id


async def get_active_self_check_prompt(db: AsyncSession) -> Tuple[Optional[str], Optional[UUID]]:
    """Return (system_content, prompt_version_id) for the active self-check prompt."""
    result = await db.execute(select(AppSettingsModel).order_by(AppSettingsModel.id).limit(1))
    settings = result.scalar_one_or_none()
    if not settings or not settings.active_self_check_prompt_version_id:
        return None, None

    prompt_result = await db.execute(
        select(SelfCheckPromptVersionModel).where(
            SelfCheckPromptVersionModel.id == settings.active_self_check_prompt_version_id
        )
    )
    prompt = prompt_result.scalar_one_or_none()
    if not prompt:
        return None, None

    return prompt.system_content, prompt.id


def validate_system_prompt(system_content: str) -> list[str]:
    """Return list of validation errors for system prompt."""
    errors: list[str] = []
    if not system_content or not system_content.strip():
        errors.append("System prompt cannot be empty")
    return errors
