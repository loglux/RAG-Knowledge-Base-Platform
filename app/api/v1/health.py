"""Health check endpoints."""

import logging
from datetime import datetime
from typing import Optional

import httpx
from anthropic import AsyncAnthropic
from fastapi import APIRouter, Depends, status
from openai import AsyncOpenAI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.embeddings_base import EMBEDDING_MODELS
from app.core.lexical_store import get_lexical_store
from app.core.vector_store import get_vector_store
from app.db.session import get_db
from app.models.database import AppSettings as AppSettingsModel
from app.models.schemas import HealthCheck, ReadinessCheck

logger = logging.getLogger(__name__)

router = APIRouter()


# Health check helper functions


async def check_openai_health(api_key: Optional[str] = None) -> bool:
    """Check OpenAI API availability."""
    try:
        key = api_key or settings.OPENAI_API_KEY
        if not key:
            return False

        client = AsyncOpenAI(api_key=key)
        # List models - free, fast, validates API key
        await client.models.list()
        await client.close()
        return True
    except Exception as e:
        logger.error(f"OpenAI health check failed: {e}")
        return False


async def check_anthropic_health(api_key: Optional[str] = None) -> bool:
    """Check Anthropic API availability."""
    try:
        key = api_key or settings.ANTHROPIC_API_KEY
        if not key:
            return False

        client = AsyncAnthropic(api_key=key)
        # Minimal message to validate key (1 token on cheapest model)
        await client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1,
            messages=[{"role": "user", "content": "test"}],
        )
        await client.close()
        return True
    except Exception as e:
        logger.error(f"Anthropic health check failed: {e}")
        return False


async def check_voyage_health(api_key: Optional[str] = None) -> bool:
    """Check Voyage AI API availability."""
    try:
        key = api_key or settings.VOYAGE_API_KEY
        if not key:
            return False

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                "https://api.voyageai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {key}"},
                json={"input": ["test"], "model": "voyage-4-lite"},
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Voyage health check failed: {e}")
        return False


async def check_ollama_health(base_url: Optional[str] = None) -> bool:
    """Check Ollama server availability."""
    try:
        url = base_url or settings.OLLAMA_BASE_URL
        if not url:
            return False

        async with httpx.AsyncClient(timeout=5.0) as client:
            # /api/tags is a free endpoint that lists available models
            response = await client.get(f"{url}/api/tags")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Ollama health check failed: {e}")
        return False


def get_provider_for_model(model_name: str) -> Optional[str]:
    """Determine the provider for a given model name."""
    # Check embedding models
    if model_name in EMBEDDING_MODELS:
        return EMBEDDING_MODELS[model_name].provider.value

    # Check LLM models by naming convention
    if model_name.startswith("gpt-") or model_name.startswith("text-embedding-"):
        return "openai"
    elif model_name.startswith("claude-"):
        return "anthropic"
    elif model_name.startswith("voyage-"):
        return "voyage"
    else:
        # Assume Ollama for other models
        return "ollama"


@router.get("/health", response_model=HealthCheck, status_code=status.HTTP_200_OK)
async def health_check():
    """
    Basic health check endpoint.

    Returns OK if the service is running.
    """
    return HealthCheck(status="ok", timestamp=datetime.utcnow())


@router.get("/ready", response_model=ReadinessCheck)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check - verifies all dependencies are available.

    Dynamically checks only the LLM providers that are actually configured and in use
    based on the default models in app settings.

    Always checks:
    - Database connectivity
    - Qdrant vector store

    Conditionally checks:
    - OpenSearch (if retrieval_mode is "hybrid")
    - LLM providers (based on configured default models)
    """
    checks = {
        "database": False,
        "qdrant": False,
    }

    # Check database
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            checks["database"] = True
    except Exception as e:
        logger.error(f"Database check failed: {e}")

    # Check Qdrant
    try:
        vector_store = get_vector_store()
        checks["qdrant"] = await vector_store.health_check()
    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        checks["qdrant"] = False

    # Get app settings to determine which providers to check
    requires_opensearch = False
    default_llm_model = settings.OPENAI_CHAT_MODEL
    default_embedding_model = "text-embedding-3-small"  # Default fallback

    try:
        result = await db.execute(select(AppSettingsModel).order_by(AppSettingsModel.id).limit(1))
        row = result.scalar_one_or_none()
        if row:
            requires_opensearch = row.retrieval_mode == "hybrid"
            if row.default_llm_model:
                default_llm_model = row.default_llm_model
            # Use first KB's embedding model as proxy for default embedding
            # (in real system, this would be in app settings)
    except Exception as e:
        logger.error(f"Failed to fetch app settings: {e}")

    # Check OpenSearch if needed
    if requires_opensearch:
        try:
            lexical_store = get_lexical_store()
            checks["opensearch"] = await lexical_store.client.ping()
        except Exception as e:
            logger.error(f"OpenSearch health check failed: {e}")
            checks["opensearch"] = False

    # Determine which LLM providers are in use
    providers_to_check = set()

    # Add provider for chat model
    chat_provider = get_provider_for_model(default_llm_model)
    if chat_provider:
        providers_to_check.add(chat_provider)

    # Add provider for embedding model
    embedding_provider = get_provider_for_model(default_embedding_model)
    if embedding_provider:
        providers_to_check.add(embedding_provider)

    # Check each required provider
    for provider in providers_to_check:
        if provider == "openai":
            checks["openai"] = await check_openai_health()
        elif provider == "anthropic":
            checks["anthropic"] = await check_anthropic_health()
        elif provider == "voyage":
            checks["voyage"] = await check_voyage_health()
        elif provider == "ollama":
            checks["ollama"] = await check_ollama_health()

    # System is ready if all checked services are healthy
    all_ready = all(checks.values())
    return ReadinessCheck(ready=all_ready, checks=checks, timestamp=datetime.utcnow())


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
