"""Setup wizard API endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.services.setup_manager import SetupManager, SetupError
from app.core.system_settings import SystemSettingsManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/setup", tags=["setup"])


# Pydantic schemas
class AdminCreateRequest(BaseModel):
    """Request to create admin user."""
    username: str = Field(..., min_length=3, max_length=50, description="Admin username")
    password: str = Field(..., min_length=8, description="Admin password (min 8 characters)")
    email: Optional[str] = Field(None, description="Admin email (optional)")


class APIKeysRequest(BaseModel):
    """Request to save API keys."""
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    voyage_api_key: Optional[str] = Field(None, description="VoyageAI API key")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")


class DatabaseSettingsRequest(BaseModel):
    """Request to save database settings."""
    qdrant_url: Optional[str] = Field(None, description="Qdrant HTTP URL")
    qdrant_api_key: Optional[str] = Field(None, description="Qdrant API key")
    opensearch_url: Optional[str] = Field(None, description="OpenSearch HTTP URL")
    opensearch_username: Optional[str] = Field(None, description="OpenSearch username")
    opensearch_password: Optional[str] = Field(None, description="OpenSearch password")


class SystemSettingsRequest(BaseModel):
    """Request to save system settings."""
    system_name: Optional[str] = Field(None, description="System name")
    max_file_size_mb: Optional[int] = Field(None, ge=1, le=1000, description="Max file size in MB")
    max_chunk_size: Optional[int] = Field(None, ge=100, le=10000, description="Max chunk size")
    chunk_overlap: Optional[int] = Field(None, ge=0, le=2000, description="Chunk overlap")


class SetupCompleteRequest(BaseModel):
    """Request to mark setup as complete."""
    admin_id: Optional[int] = Field(None, description="Admin user ID who completed setup")


# API Endpoints

@router.get("/status")
async def get_setup_status(db: AsyncSession = Depends(get_db)):
    """
    Get current setup status.

    Returns information about whether setup is complete and what has been configured.
    """
    try:
        status_info = await SetupManager.get_setup_status(db)
        return {
            "success": True,
            "data": status_info
        }

    except Exception as e:
        logger.error(f"Failed to get setup status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get setup status: {str(e)}"
        )


@router.post("/admin")
async def create_admin_user(
    request: AdminCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create initial admin user.

    This should be the first step in the setup wizard.
    """
    try:
        # Check if setup is already complete
        is_complete = await SystemSettingsManager.is_setup_complete(db)
        if is_complete:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Setup is already complete. Admin user already exists."
            )

        # Create admin
        admin = await SetupManager.create_admin_user(
            db=db,
            username=request.username,
            password=request.password,
            email=request.email,
        )

        return {
            "success": True,
            "data": {
                "id": admin.id,
                "username": admin.username,
                "email": admin.email,
                "created_at": admin.created_at.isoformat(),
            },
            "message": "Admin user created successfully"
        }

    except SetupError as e:
        logger.error(f"Setup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create admin user: {str(e)}"
        )


@router.post("/api-keys")
async def save_api_keys(
    request: APIKeysRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Save API keys for external services.

    At least one API key should be provided (OpenAI is recommended).
    """
    try:
        # Validate at least one key is provided
        if not any([request.openai_api_key, request.voyage_api_key, request.anthropic_api_key]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one API key must be provided"
            )

        # Save keys
        await SetupManager.save_api_keys(
            db=db,
            openai_api_key=request.openai_api_key,
            voyage_api_key=request.voyage_api_key,
            anthropic_api_key=request.anthropic_api_key,
        )

        return {
            "success": True,
            "message": "API keys saved successfully"
        }

    except SetupError as e:
        logger.error(f"Setup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save API keys: {str(e)}"
        )


@router.post("/database")
async def save_database_settings(
    request: DatabaseSettingsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Save database connection settings.

    This step is optional - defaults will be used if not configured.
    """
    try:
        await SetupManager.save_database_settings(
            db=db,
            qdrant_url=request.qdrant_url,
            qdrant_api_key=request.qdrant_api_key,
            opensearch_url=request.opensearch_url,
            opensearch_username=request.opensearch_username,
            opensearch_password=request.opensearch_password,
        )

        return {
            "success": True,
            "message": "Database settings saved successfully"
        }

    except SetupError as e:
        logger.error(f"Setup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to save database settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save database settings: {str(e)}"
        )


@router.post("/system")
async def save_system_settings(
    request: SystemSettingsRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Save general system settings.

    This step is optional - defaults will be used if not configured.
    """
    try:
        await SetupManager.save_system_settings(
            db=db,
            system_name=request.system_name,
            max_file_size_mb=request.max_file_size_mb,
            max_chunk_size=request.max_chunk_size,
            chunk_overlap=request.chunk_overlap,
        )

        return {
            "success": True,
            "message": "System settings saved successfully"
        }

    except SetupError as e:
        logger.error(f"Setup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to save system settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save system settings: {str(e)}"
        )


@router.post("/complete")
async def complete_setup(
    request: SetupCompleteRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Mark setup as complete.

    This should be called after all setup steps are done.
    After this, the setup wizard will no longer be shown.
    """
    try:
        # Verify at least one API key is configured
        api_keys_configured = False
        for key in ["openai_api_key", "voyage_api_key", "anthropic_api_key"]:
            value = await SystemSettingsManager.get_setting(db, key)
            if value:
                api_keys_configured = True
                break

        if not api_keys_configured:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one API key must be configured before completing setup"
            )

        # Mark setup as complete
        await SetupManager.mark_setup_complete(
            db=db,
            updated_by=request.admin_id,
        )

        return {
            "success": True,
            "message": "Setup completed successfully. System is ready to use."
        }

    except SetupError as e:
        logger.error(f"Setup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete setup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete setup: {str(e)}"
        )
