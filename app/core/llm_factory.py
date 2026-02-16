"""
Factory for creating LLM services.

Provides unified interface for creating LLM services from different providers.
"""

import logging
from typing import Optional

from app.config import settings
from app.core.llm_base import (
    LLM_MODELS,
    BaseLLMService,
    LLMProvider,
)

logger = logging.getLogger(__name__)


def create_llm_service(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    provider: Optional[str] = None,
) -> BaseLLMService:
    """
    Create LLM service based on model name or provider.

    Args:
        model: LLM model name (auto-detects provider from model name)
        api_key: API key for the provider (optional, uses settings if not provided)
        provider: Provider name (optional, overrides model-based detection)

    Returns:
        Appropriate LLM service instance

    Raises:
        ValueError: If model is unknown or API key is missing
    """
    # Determine provider
    if provider:
        provider_enum = LLMProvider(provider.lower())
    elif model:
        # Check if model is in known models
        if model in LLM_MODELS:
            provider_enum = LLM_MODELS[model].provider
        else:
            # Unknown model - assume it's a dynamic Ollama model
            logger.info(f"Unknown model '{model}', assuming Ollama dynamic model")
            provider_enum = LLMProvider.OLLAMA
    else:
        # Use default from settings
        provider_enum = LLMProvider(settings.LLM_PROVIDER.lower())
        model = _get_default_model_for_provider(provider_enum)

    logger.info(f"Creating {provider_enum.value} LLM service for model: {model}")

    # Create appropriate service based on provider
    if provider_enum == LLMProvider.OPENAI:
        from app.core.llm_openai import OpenAILLMService

        return OpenAILLMService(
            api_key=api_key or settings.OPENAI_API_KEY,
            model=model or settings.OPENAI_CHAT_MODEL,
        )
    elif provider_enum == LLMProvider.ANTHROPIC:
        from app.core.llm_anthropic import AnthropicLLMService

        anthropic_key = api_key or settings.ANTHROPIC_API_KEY
        if not anthropic_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in settings. "
                "Please set ANTHROPIC_API_KEY environment variable."
            )
        return AnthropicLLMService(
            api_key=anthropic_key,
            model=model or settings.ANTHROPIC_CHAT_MODEL,
        )
    elif provider_enum == LLMProvider.DEEPSEEK:
        from app.core.llm_deepseek import DeepSeekLLMService

        deepseek_key = api_key or settings.DEEPSEEK_API_KEY
        if not deepseek_key:
            raise ValueError(
                "DEEPSEEK_API_KEY not found in settings. "
                "Please set DEEPSEEK_API_KEY environment variable."
            )
        return DeepSeekLLMService(
            api_key=deepseek_key,
            model=model or settings.DEEPSEEK_CHAT_MODEL,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
    elif provider_enum == LLMProvider.OLLAMA:
        from app.core.llm_ollama import OllamaLLMService

        ollama_url = settings.OLLAMA_BASE_URL
        if not ollama_url:
            raise ValueError(
                "OLLAMA_BASE_URL not found in settings. "
                "Please set OLLAMA_BASE_URL environment variable."
            )
        return OllamaLLMService(
            base_url=ollama_url,
            model=model or settings.OLLAMA_CHAT_MODEL,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider_enum}")


def _get_default_model_for_provider(provider: LLMProvider) -> str:
    """Get default model for a provider."""
    if provider == LLMProvider.OPENAI:
        return settings.OPENAI_CHAT_MODEL
    elif provider == LLMProvider.ANTHROPIC:
        return settings.ANTHROPIC_CHAT_MODEL
    elif provider == LLMProvider.DEEPSEEK:
        return settings.DEEPSEEK_CHAT_MODEL
    elif provider == LLMProvider.OLLAMA:
        return settings.OLLAMA_CHAT_MODEL
    else:
        raise ValueError(f"Unknown provider: {provider}")


def get_model_info(model: str) -> dict:
    """
    Get information about an LLM model.

    Args:
        model: Model name

    Returns:
        Dictionary with model information
    """
    if model not in LLM_MODELS:
        raise ValueError(f"Unknown model: {model}")

    config = LLM_MODELS[model]
    return {
        "model": model,
        "provider": config.provider.value,
        "context_window": config.context_window,
        "description": config.description,
        "cost_per_million_input_tokens": config.cost_per_million_input_tokens,
        "cost_per_million_output_tokens": config.cost_per_million_output_tokens,
    }


def list_available_models() -> list:
    """
    List all available LLM models.

    Returns:
        List of dictionaries with model information
    """
    return [get_model_info(model) for model in LLM_MODELS.keys()]


def get_models_by_provider(provider: LLMProvider) -> list:
    """
    Get all models for a specific provider.

    Args:
        provider: LLM provider

    Returns:
        List of model names for the provider
    """
    return [model for model, config in LLM_MODELS.items() if config.provider == provider]
