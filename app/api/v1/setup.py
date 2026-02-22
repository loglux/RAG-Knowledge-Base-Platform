"""Setup wizard API endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.system_settings import SystemSettingsManager
from app.db.session import get_db
from app.dependencies import get_current_user
from app.services.setup_manager import SetupError, SetupManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/setup", tags=["setup"])
_bearer = HTTPBearer(auto_error=False)


async def require_setup_write_access(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> int | None:
    """
    Guard for setup mutation endpoints.

    - Before setup completion: allow unauthenticated setup flow.
    - After setup completion: require valid admin bearer token.
    """
    is_complete = await SystemSettingsManager.is_setup_complete(db)
    if not is_complete:
        return None

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    return await get_current_user(credentials)


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
    deepseek_api_key: Optional[str] = Field(None, description="DeepSeek API key")
    ollama_base_url: Optional[str] = Field(
        None, description="Ollama API base URL (e.g., http://localhost:11434)"
    )


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


class PostgresPasswordRequest(BaseModel):
    """Request to change PostgreSQL password."""

    username: str = Field(..., description="PostgreSQL username (usually kb_user)")
    new_password: Optional[str] = Field(None, description="New password (leave empty to generate)")
    generate_password: bool = Field(default=False, description="Generate secure random password")


class PostgresPasswordResponse(BaseModel):
    """Response with new PostgreSQL credentials."""

    username: str
    password: str
    message: str


# API Endpoints


@router.get("/status")
async def get_setup_status(db: AsyncSession = Depends(get_db)):
    """
    Get current setup status.

    Returns information about whether setup is complete and what has been configured.
    """
    try:
        status_info = await SetupManager.get_setup_status(db)
        return {"success": True, "data": status_info}

    except Exception as e:
        logger.error(f"Failed to get setup status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get setup status",
        )


@router.post("/admin")
async def create_admin_user(
    request: AdminCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: int | None = Depends(require_setup_write_access),
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
                detail="Setup is already complete. Admin user already exists.",
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
            "message": "Admin user created successfully",
        }

    except SetupError as e:
        logger.error(f"Setup error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create admin user",
        )


@router.get("/generate-password")
async def generate_password_preview():
    """
    Generate a secure random password (preview only, doesn't change anything).

    Use this to see what a generated password would look like before applying it.
    """
    try:
        password = SetupManager.generate_secure_password(length=24)
        return {
            "success": True,
            "data": {
                "password": password,
                "length": len(password),
            },
            "message": "Generated secure password. This is just a preview - not applied yet.",
        }
    except Exception as e:
        logger.error(f"Failed to generate password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate password",
        )


@router.post("/postgres-password", response_model=PostgresPasswordResponse)
async def change_postgres_password(
    request: PostgresPasswordRequest,
    db: AsyncSession = Depends(get_db),
    _: int | None = Depends(require_setup_write_access),
):
    """
    Change PostgreSQL password or generate a new secure password.

    This is an optional security step. You can:
    - Generate a random secure password (recommended)
    - Provide your own password

    **IMPORTANT**: Save the new password! You'll need it if you restart containers.
    """
    try:
        # Determine password to use
        if request.generate_password:
            new_password = SetupManager.generate_secure_password(length=24)
        elif request.new_password:
            new_password = request.new_password
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either provide new_password or set generate_password=true",
            )

        # Change password
        result = await SetupManager.change_postgres_password(
            db=db,
            username=request.username,
            new_password=new_password,
        )

        return PostgresPasswordResponse(
            username=result["username"],
            password=result["password"],
            message="PostgreSQL password changed successfully. IMPORTANT: Save these credentials!",
        )

    except SetupError as e:
        logger.error(f"Setup error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to change PostgreSQL password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change PostgreSQL password",
        )


@router.post("/api-keys")
async def save_api_keys(
    request: APIKeysRequest,
    db: AsyncSession = Depends(get_db),
    _: int | None = Depends(require_setup_write_access),
):
    """
    Save API keys for external services.

    At least one API key should be provided (OpenAI is recommended).
    """
    try:
        # Validate at least one provider is configured
        if not any(
            [
                request.openai_api_key,
                request.voyage_api_key,
                request.anthropic_api_key,
                request.deepseek_api_key,
                request.ollama_base_url,
            ]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one AI provider (API key or Ollama URL) must be configured",
            )

        # Save keys
        await SetupManager.save_api_keys(
            db=db,
            openai_api_key=request.openai_api_key,
            voyage_api_key=request.voyage_api_key,
            anthropic_api_key=request.anthropic_api_key,
            deepseek_api_key=request.deepseek_api_key,
            ollama_base_url=request.ollama_base_url,
        )

        return {"success": True, "message": "API keys saved successfully"}

    except SetupError as e:
        logger.error(f"Setup error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save API keys",
        )


@router.post("/database")
async def save_database_settings(
    request: DatabaseSettingsRequest,
    db: AsyncSession = Depends(get_db),
    _: int | None = Depends(require_setup_write_access),
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

        return {"success": True, "message": "Database settings saved successfully"}

    except SetupError as e:
        logger.error(f"Setup error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to save database settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save database settings",
        )


@router.post("/system")
async def save_system_settings(
    request: SystemSettingsRequest,
    db: AsyncSession = Depends(get_db),
    _: int | None = Depends(require_setup_write_access),
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

        return {"success": True, "message": "System settings saved successfully"}

    except SetupError as e:
        logger.error(f"Setup error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to save system settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save system settings",
        )


@router.post("/complete")
async def complete_setup(
    request: SetupCompleteRequest,
    db: AsyncSession = Depends(get_db),
    _: int | None = Depends(require_setup_write_access),
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
                detail="At least one API key must be configured before completing setup",
            )

        # Mark setup as complete
        await SetupManager.mark_setup_complete(
            db=db,
            updated_by=request.admin_id,
        )

        return {"success": True, "message": "Setup completed successfully. System is ready to use."}

    except SetupError as e:
        logger.error(f"Setup error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete setup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete setup",
        )
