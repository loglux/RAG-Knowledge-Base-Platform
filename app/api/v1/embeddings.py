"""Embeddings configuration endpoints."""
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status

from app.core.embeddings_base import EMBEDDING_MODELS, EmbeddingProvider
from app.core.embeddings_factory import (
    get_model_info,
    list_available_models,
    get_models_by_provider,
)


router = APIRouter()


@router.get("/models", response_model=List[Dict[str, Any]])
async def list_embedding_models():
    """
    List all available embedding models.

    Returns information about all supported embedding models including:
    - Model name
    - Provider (OpenAI, Voyage AI)
    - Dimension size
    - Cost per million tokens
    - Description
    """
    return list_available_models()


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


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
            detail=f"Invalid provider: {provider}. Valid providers: openai, voyage"
        )


@router.get("/providers", response_model=List[str])
async def list_providers():
    """
    List all available embedding providers.

    Returns:
        List of provider names
    """
    return [provider.value for provider in EmbeddingProvider]
