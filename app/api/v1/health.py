"""Health check endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.schemas import HealthCheck, ReadinessCheck
from app.config import settings

router = APIRouter()


@router.get("/health", response_model=HealthCheck, status_code=status.HTTP_200_OK)
async def health_check():
    """
    Basic health check endpoint.

    Returns OK if the service is running.
    """
    return HealthCheck(
        status="ok",
        timestamp=datetime.utcnow()
    )


@router.get("/ready", response_model=ReadinessCheck)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check - verifies all dependencies are available.

    Checks:
    - Database connectivity
    - Qdrant connectivity (TODO)
    - OpenAI API (TODO)
    """
    checks = {
        "database": False,
        "qdrant": False,  # TODO: Implement in Phase 3
        "openai": False,  # TODO: Implement in Phase 2
    }

    # Check database
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            checks["database"] = True
    except Exception as e:
        print(f"Database check failed: {e}")

    # TODO: Check Qdrant
    # try:
    #     qdrant_client = get_qdrant_client()
    #     await qdrant_client.health()
    #     checks["qdrant"] = True
    # except Exception:
    #     pass

    # TODO: Check OpenAI
    # try:
    #     openai_client = get_openai_client()
    #     # Simple API call to verify
    #     checks["openai"] = True
    # except Exception:
    #     pass

    all_ready = checks["database"]  # For now, only database is checked
    status_code = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessCheck(
        ready=all_ready,
        checks=checks,
        timestamp=datetime.utcnow()
    )


@router.get("/info")
async def info():
    """
    API information endpoint.

    Returns configuration details (non-sensitive).
    """
    return {
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "features": {
            "async_processing": settings.ENABLE_ASYNC_PROCESSING,
            "cache": settings.ENABLE_CACHE,
            "metrics": settings.ENABLE_METRICS,
        },
        "limits": {
            "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
            "max_chunk_size": settings.MAX_CHUNK_SIZE,
            "chunk_overlap": settings.CHUNK_OVERLAP,
        },
        "supported_formats": settings.allowed_file_types_list,
    }
