"""Embeddings configuration endpoints."""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status

from app.api.v1.ollama import fetch_ollama_model_dimension, fetch_ollama_models, is_embedding_model
from app.core.embeddings_base import EmbeddingProvider
from app.core.embeddings_factory import (
    get_model_info,
    get_models_by_provider,
    list_available_models,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/models", response_model=List[Dict[str, Any]])
async def list_embedding_models():
    """
    List all available embedding models.

    Returns information about all supported embedding models including:
    - Model name
    - Provider (OpenAI, Voyage AI, Ollama)
    - Dimension size
    - Cost per million tokens
    - Description

    Also includes embedding models pulled locally into Ollama that aren't in
    the static catalog yet - their dimension is resolved live via Ollama's
    /api/show. A model whose dimension can't be resolved is omitted rather
    than shown broken.
    """
    static_models = list_available_models()
    catalogued_names = {m["model"] for m in static_models}

    dynamic_models: List[Dict[str, Any]] = []
    try:
        for model in await fetch_ollama_models():
            name = model.get("name")
            if not name or name in catalogued_names or not is_embedding_model(model):
                continue
            dimension = await fetch_ollama_model_dimension(name)
            if dimension is None:
                logger.warning(
                    f"Skipping Ollama embedding model '{name}': could not resolve dimension"
                )
                continue
            family = model.get("details", {}).get("family", "Unknown")
            dynamic_models.append(
                {
                    "model": name,
                    "provider": "ollama",
                    "dimension": dimension,
                    "description": f"Local Ollama model - {family} family",
                    "cost_per_million_tokens": 0.0,
                }
            )
    except Exception as e:
        logger.warning(f"Failed to fetch Ollama embedding models: {e}")

    return static_models + dynamic_models


@router.get("/models/{model_name}", response_model=Dict[str, Any])
async def get_embedding_model(model_name: str):
    """
    Get information about a specific embedding model.

    Args:
        model_name: Name of the embedding model

    Returns:
        Model information

    Raises:
        404: If model is not found
    """
    try:
        return get_model_info(model_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/providers/{provider}/models", response_model=List[str])
async def list_provider_models(provider: str):
    """
    List all models for a specific provider.

    Args:
        provider: Provider name (openai, voyage)

    Returns:
        List of model names for the provider

    Raises:
        400: If provider is invalid
    """
    try:
        provider_enum = EmbeddingProvider(provider.lower())
        models = get_models_by_provider(provider_enum)
        return models
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid provider: {provider}. Valid providers: openai, voyage",
        )


@router.get("/providers", response_model=List[str])
async def list_providers():
    """
    List all available embedding providers.

    Returns:
        List of provider names
    """
    return [provider.value for provider in EmbeddingProvider]
