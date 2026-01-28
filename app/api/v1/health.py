"""Health check endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.schemas import HealthCheck, ReadinessCheck
from app.models.database import AppSettings as AppSettingsModel
from app.config import settings
from app.core.vector_store import get_vector_store
from app.core.lexical_store import get_lexical_store

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
        "qdrant": False,
        "opensearch": False,
        "openai": False,  # TODO: Implement in Phase 2
    }

    # Check database
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            checks["database"] = True
    except Exception as e:
        print(f"Database check failed: {e}")

    # Check Qdrant
    try:
        vector_store = get_vector_store()
        checks["qdrant"] = await vector_store.health_check()
    except Exception:
        checks["qdrant"] = False

    # Check OpenSearch
    try:
        lexical_store = get_lexical_store()
        checks["opensearch"] = await lexical_store.client.ping()
    except Exception:
        checks["opensearch"] = False

    # TODO: Check OpenAI
    # try:
    #     openai_client = get_openai_client()
    #     # Simple API call to verify
    #     checks["openai"] = True
    # except Exception:
    #     pass

    requires_opensearch = False
    try:
        result = await db.execute(select(AppSettingsModel).order_by(AppSettingsModel.id).limit(1))
        row = result.scalar_one_or_none()
        if row and row.retrieval_mode == "hybrid":
            requires_opensearch = True
    except Exception:
        requires_opensearch = False

    all_ready = checks["database"] and checks["qdrant"] and (checks["opensearch"] or not requires_opensearch)
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
    try:
        lexical_store = get_lexical_store()
        opensearch_available = await lexical_store.client.ping()
    except Exception:
        opensearch_available = False

    return {
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "features": {
            "async_processing": settings.ENABLE_ASYNC_PROCESSING,
            "cache": settings.ENABLE_CACHE,
            "metrics": settings.ENABLE_METRICS,
        },
        "integrations": {
            "opensearch_available": opensearch_available,
        },
        "limits": {
            "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
            "max_chunk_size": settings.MAX_CHUNK_SIZE,
            "chunk_overlap": settings.CHUNK_OVERLAP,
        },
        "supported_formats": settings.allowed_file_types_list,
    }
