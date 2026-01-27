"""LLM models endpoints."""
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException

from app.core.llm_base import LLM_MODELS, LLMProvider
from app.api.v1.ollama import fetch_ollama_models, is_embedding_model


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/models")
async def list_llm_models():
    """
    List all available LLM models from all providers.

    Returns models from OpenAI, Anthropic, and Ollama.
    """
    try:
        # Get static models (OpenAI, Anthropic)
        static_models = []
        for model_name, model_config in LLM_MODELS.items():
            static_models.append({
                "model": model_name,
                "provider": model_config.provider.value,
                "context_window": model_config.context_window,
                "cost_input": model_config.cost_per_million_input_tokens,
                "cost_output": model_config.cost_per_million_output_tokens,
                "description": model_config.description,
            })

        # Get Ollama models (dynamic)
        ollama_models = []
        try:
            all_ollama = await fetch_ollama_models()
            for model in all_ollama:
                if not is_embedding_model(model):
                    ollama_models.append({
                        "model": model.get("name"),
                        "provider": "ollama",
                        "context_window": None,  # Not available from API
                        "cost_input": 0.0,
                        "cost_output": 0.0,
                        "description": f"Local Ollama model - {model.get('details', {}).get('family', 'Unknown')} family",
                        "size": model.get("size"),
                        "family": model.get("details", {}).get("family"),
                        "parameter_size": model.get("details", {}).get("parameter_size"),
                    })
        except Exception as e:
            logger.warning(f"Failed to fetch Ollama models: {e}")

        return {
            "models": static_models + ollama_models,
            "providers": {
                "openai": len([m for m in static_models if m["provider"] == "openai"]),
                "anthropic": len([m for m in static_models if m["provider"] == "anthropic"]),
                "ollama": len(ollama_models),
            },
            "total": len(static_models) + len(ollama_models),
        }

    except Exception as e:
        logger.error(f"Failed to list LLM models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def list_llm_providers():
    """List all available LLM providers."""
    return {
        "providers": [
            {
                "name": "openai",
                "display_name": "OpenAI",
                "models_count": len([m for m in LLM_MODELS.values() if m.provider == LLMProvider.OPENAI]),
            },
            {
                "name": "anthropic",
                "display_name": "Anthropic",
                "models_count": len([m for m in LLM_MODELS.values() if m.provider == LLMProvider.ANTHROPIC]),
            },
            {
                "name": "ollama",
                "display_name": "Ollama (Local)",
                "models_count": None,  # Dynamic
            },
        ]
    }
