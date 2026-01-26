"""
Factory for creating embedding services.

Provides unified interface for creating embedding services from different providers.
"""
import logging
from typing import Optional

from app.config import settings
from app.core.embeddings_base import (
    BaseEmbeddingService,
    EmbeddingProvider,
    EMBEDDING_MODELS,
)
from app.core.embeddings import OpenAIEmbeddingService
from app.core.embeddings_voyage import VoyageEmbeddingService
from app.core.embeddings_ollama import OllamaEmbeddingService


logger = logging.getLogger(__name__)


def create_embedding_service(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> BaseEmbeddingService:
    """
    Create embedding service based on model name.

    Args:
        model: Embedding model name (auto-detects provider from model name)
        api_key: API key for the provider (optional, uses settings if not provided)

    Returns:
        Appropriate embedding service instance

    Raises:
        ValueError: If model is unknown or API key is missing
    """
    # Use default model from settings if not provided
    model = model or settings.OPENAI_EMBEDDING_MODEL

    # Get model configuration
    if model not in EMBEDDING_MODELS:
        raise ValueError(
            f"Unknown embedding model: {model}. "
            f"Available models: {', '.join(EMBEDDING_MODELS.keys())}"
        )

    model_config = EMBEDDING_MODELS[model]
    provider = model_config.provider

    logger.info(f"Creating {provider.value} embedding service for model: {model}")

    # Create appropriate service based on provider
    if provider == EmbeddingProvider.OPENAI:
        return OpenAIEmbeddingService(
            api_key=api_key or settings.OPENAI_API_KEY,
            model=model,
        )
    elif provider == EmbeddingProvider.VOYAGE:
        voyage_api_key = api_key or getattr(settings, "VOYAGE_API_KEY", None)
        if not voyage_api_key:
            raise ValueError(
                "VOYAGE_API_KEY not found in settings. "
                "Please set VOYAGE_API_KEY environment variable."
            )
        return VoyageEmbeddingService(
            api_key=voyage_api_key,
            model=model,
        )
    elif provider == EmbeddingProvider.OLLAMA:
        ollama_url = getattr(settings, "OLLAMA_BASE_URL", None)
        if not ollama_url:
            raise ValueError(
                "OLLAMA_BASE_URL not found in settings. "
                "Please set OLLAMA_BASE_URL environment variable."
            )
        return OllamaEmbeddingService(
            base_url=ollama_url,
            model=model,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def get_model_info(model: str) -> dict:
    """
    Get information about an embedding model.

    Args:
        model: Model name

    Returns:
        Dictionary with model information
    """
    if model not in EMBEDDING_MODELS:
        raise ValueError(f"Unknown model: {model}")

    config = EMBEDDING_MODELS[model]
    return {
        "model": model,
        "provider": config.provider.value,
        "dimension": config.dimension,
        "description": config.description,
        "cost_per_million_tokens": config.cost_per_million_tokens,
    }


def list_available_models() -> list:
    """
    List all available embedding models.

    Returns:
        List of dictionaries with model information
    """
    return [get_model_info(model) for model in EMBEDDING_MODELS.keys()]


def get_models_by_provider(provider: EmbeddingProvider) -> list:
    """
    Get all models for a specific provider.

    Args:
        provider: Embedding provider

    Returns:
        List of model names for the provider
    """
    return [
        model
        for model, config in EMBEDDING_MODELS.items()
        if config.provider == provider
    ]
