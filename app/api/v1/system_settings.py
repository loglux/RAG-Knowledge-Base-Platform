"""System settings endpoints (API keys, database URLs, etc.)."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.system_settings import SystemSettingsManager
from app.services.setup_manager import SetupManager

logger = logging.getLogger(__name__)

router = APIRouter()


class SystemSettingsResponse(BaseModel):
    """Response with system settings (sensitive values masked)."""
    # API Keys (masked)
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key (masked)")
    voyage_api_key: Optional[str] = Field(None, description="VoyageAI API key (masked)")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key (masked)")
    ollama_base_url: Optional[str] = Field(None, description="Ollama API base URL")

    # Database URLs
    qdrant_url: Optional[str] = Field(None, description="Qdrant URL")
    qdrant_api_key: Optional[str] = Field(None, description="Qdrant API key (masked)")
    opensearch_url: Optional[str] = Field(None, description="OpenSearch URL")
    opensearch_username: Optional[str] = Field(None, description="OpenSearch username")
    opensearch_password: Optional[str] = Field(None, description="OpenSearch password (masked)")

    # System
    system_name: Optional[str] = Field(None, description="System name")
    max_file_size_mb: Optional[int] = Field(None, description="Max file size in MB")


class SystemSettingsUpdate(BaseModel):
    """Update system settings."""
    # API Keys
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    voyage_api_key: Optional[str] = Field(None, description="VoyageAI API key")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    ollama_base_url: Optional[str] = Field(None, description="Ollama API base URL")

    # Database URLs
    qdrant_url: Optional[str] = Field(None, description="Qdrant URL")
    qdrant_api_key: Optional[str] = Field(None, description="Qdrant API key")
    opensearch_url: Optional[str] = Field(None, description="OpenSearch URL")
    opensearch_username: Optional[str] = Field(None, description="OpenSearch username")
    opensearch_password: Optional[str] = Field(None, description="OpenSearch password")

    # System
    system_name: Optional[str] = Field(None, description="System name")
    max_file_size_mb: Optional[int] = Field(None, description="Max file size in MB")


class PostgresPasswordUpdate(BaseModel):
    """Update PostgreSQL password."""
    username: str = Field(..., description="PostgreSQL username")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")


def _mask_sensitive(value: Optional[str], show_chars: int = 4) -> Optional[str]:
    """Mask sensitive value, showing only last N characters."""
    if not value:
        return None
    if len(value) <= show_chars:
        return "*" * len(value)
    return "*" * (len(value) - show_chars) + value[-show_chars:]


@router.get("/", response_model=SystemSettingsResponse)
async def get_system_settings(db: AsyncSession = Depends(get_db)):
    """
    Get system settings (API keys, database URLs, etc.).

    Sensitive values are masked for security.
    """
    try:
        # Load all settings from database
        settings_dict = await SystemSettingsManager.load_from_db(db)

        # Mask sensitive values
        return SystemSettingsResponse(
            openai_api_key=_mask_sensitive(settings_dict.get("openai_api_key")),
            voyage_api_key=_mask_sensitive(settings_dict.get("voyage_api_key")),
            anthropic_api_key=_mask_sensitive(settings_dict.get("anthropic_api_key")),
            ollama_base_url=settings_dict.get("ollama_base_url"),  # Not sensitive
            qdrant_url=settings_dict.get("qdrant_url"),
            qdrant_api_key=_mask_sensitive(settings_dict.get("qdrant_api_key")),
            opensearch_url=settings_dict.get("opensearch_url"),
            opensearch_username=settings_dict.get("opensearch_username"),
            opensearch_password=_mask_sensitive(settings_dict.get("opensearch_password")),
            system_name=settings_dict.get("system_name"),
            max_file_size_mb=int(settings_dict.get("max_file_size_mb", 50)) if settings_dict.get("max_file_size_mb") else None,
        )

    except Exception as e:
        logger.error(f"Failed to get system settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system settings: {str(e)}"
        )


@router.put("/", response_model=dict)
async def update_system_settings(
    payload: SystemSettingsUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update system settings (API keys, database URLs, etc.).

    Only provided fields will be updated.
    """
    try:
        updated_count = 0

        # Update API keys
        if payload.openai_api_key is not None:
            await SystemSettingsManager.save_setting(
                db=db,
                key="openai_api_key",
                value=payload.openai_api_key,
                category="api",
                description="OpenAI API key",
                is_encrypted=False,
            )
            updated_count += 1

        if payload.voyage_api_key is not None:
            await SystemSettingsManager.save_setting(
                db=db,
                key="voyage_api_key",
                value=payload.voyage_api_key,
                category="api",
                description="VoyageAI API key",
                is_encrypted=False,
            )
            updated_count += 1

        if payload.anthropic_api_key is not None:
            await SystemSettingsManager.save_setting(
                db=db,
                key="anthropic_api_key",
                value=payload.anthropic_api_key,
                category="api",
                description="Anthropic API key",
                is_encrypted=False,
            )
            updated_count += 1

        if payload.ollama_base_url is not None:
            await SystemSettingsManager.save_setting(
                db=db,
                key="ollama_base_url",
                value=payload.ollama_base_url,
                category="api",
                description="Ollama API base URL",
                is_encrypted=False,
            )
            updated_count += 1

        # Update database URLs
        if payload.qdrant_url is not None:
            await SystemSettingsManager.save_setting(
                db=db,
                key="qdrant_url",
                value=payload.qdrant_url,
                category="database",
                description="Qdrant URL",
                is_encrypted=False,
            )
            updated_count += 1

        if payload.qdrant_api_key is not None:
            await SystemSettingsManager.save_setting(
                db=db,
                key="qdrant_api_key",
                value=payload.qdrant_api_key,
                category="database",
                description="Qdrant API key",
                is_encrypted=False,
            )
            updated_count += 1

        if payload.opensearch_url is not None:
            await SystemSettingsManager.save_setting(
                db=db,
                key="opensearch_url",
                value=payload.opensearch_url,
                category="database",
                description="OpenSearch URL",
                is_encrypted=False,
            )
            updated_count += 1

        if payload.opensearch_username is not None:
            await SystemSettingsManager.save_setting(
                db=db,
                key="opensearch_username",
                value=payload.opensearch_username,
                category="database",
                description="OpenSearch username",
                is_encrypted=False,
            )
            updated_count += 1

        if payload.opensearch_password is not None:
            await SystemSettingsManager.save_setting(
                db=db,
                key="opensearch_password",
                value=payload.opensearch_password,
                category="database",
                description="OpenSearch password",
                is_encrypted=False,
            )
            updated_count += 1

        # Update system settings
        if payload.system_name is not None:
            await SystemSettingsManager.save_setting(
                db=db,
                key="system_name",
                value=payload.system_name,
                category="system",
                description="System name",
                is_encrypted=False,
            )
            updated_count += 1

        if payload.max_file_size_mb is not None:
            await SystemSettingsManager.save_setting(
                db=db,
                key="max_file_size_mb",
                value=str(payload.max_file_size_mb),
                category="limits",
                description="Maximum file size in MB",
                is_encrypted=False,
            )
            updated_count += 1

        await db.commit()

        # Reload settings from database to apply changes
        from app.config import load_settings_from_db
        await load_settings_from_db()

        logger.info(f"Updated {updated_count} system settings")

        return {
            "success": True,
            "message": f"Updated {updated_count} settings successfully",
            "updated_count": updated_count
        }

    except Exception as e:
        logger.error(f"Failed to update system settings: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update system settings: {str(e)}"
        )


@router.post("/postgres-password", response_model=dict)
async def change_postgres_password(
    payload: PostgresPasswordUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Change PostgreSQL password.

    This will:
    1. Change password in PostgreSQL
    2. Recreate connection pool with new credentials
    """
    try:
        result = await SetupManager.change_postgres_password(
            db=db,
            username=payload.username,
            new_password=payload.new_password,
        )

        return {
            "success": True,
            "message": "PostgreSQL password changed successfully",
            "username": result["username"]
        }

    except Exception as e:
        logger.error(f"Failed to change PostgreSQL password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change PostgreSQL password: {str(e)}"
        )
