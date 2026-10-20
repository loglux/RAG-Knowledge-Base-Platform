"""LLM models endpoints."""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.api.v1.ollama import fetch_ollama_models, is_embedding_model
from app.core.llm_base import LLM_MODELS, LLMProvider
from app.core.model_discovery import fetch_anthropic_model_ids, fetch_openai_model_ids
from app.core.model_pricing import get_live_pricing

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
        static_models: List[Dict[str, Any]] = []
        for model_name, model_config in LLM_MODELS.items():
            static_models.append(
                {
                    "model": model_name,
                    "provider": model_config.provider.value,
                    "context_window": model_config.context_window,
                    "cost_input": model_config.cost_per_million_input_tokens,
                    "cost_output": model_config.cost_per_million_output_tokens,
                    "description": model_config.description,
                }
            )

        # Get Ollama models (dynamic)
        ollama_models: List[Dict[str, Any]] = []
        try:
            all_ollama = await fetch_ollama_models()
            for model in all_ollama:
                if not is_embedding_model(model):
                    ollama_models.append(
                        {
                            "model": model.get("name"),
                            "provider": "ollama",
                            "context_window": None,  # Not available from API
                            "cost_input": 0.0,
                            "cost_output": 0.0,
                            "description": f"Local Ollama model - {model.get('details', {}).get('family', 'Unknown')} family",
                            "size": model.get("size"),
                            "family": model.get("details", {}).get("family"),
                            "parameter_size": model.get("details", {}).get("parameter_size"),
                        }
                    )
        except Exception as e:
            logger.warning(f"Failed to fetch Ollama models: {e}")

        # Augment with live models the provider reports but we haven't
        # catalogued yet - surfaced with metadata missing rather than guessed.
        catalogued_ids = {m["model"] for m in static_models}
        live_models: List[Dict[str, Any]] = []
        for provider_name, fetch in (
            ("openai", fetch_openai_model_ids),
            ("anthropic", fetch_anthropic_model_ids),
        ):
            try:
                for model_id in await fetch():
                    if model_id in catalogued_ids:
                        continue
                    catalogued_ids.add(model_id)
                    live_models.append(
                        {
                            "model": model_id,
                            "provider": provider_name,
                            "context_window": None,
                            "cost_input": None,
                            "cost_output": None,
                            "description": "Reported by provider API - pricing/context not yet catalogued",
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to fetch live {provider_name} models: {e}")

        # Overlay live pricing/context-window from the LiteLLM community cost
        # map onto catalogued entries (corrects drift without hand-editing
        # LLM_MODELS) and onto newly-discovered entries (fills in what we
        # couldn't catalogue). Fields the map doesn't have are left as-is.
        for model_entry in static_models + live_models:
            live = await get_live_pricing(model_entry["model"])
            if not live:
                continue
            if live["cost_per_million_input_tokens"] is not None:
                model_entry["cost_input"] = live["cost_per_million_input_tokens"]
            if live["cost_per_million_output_tokens"] is not None:
                model_entry["cost_output"] = live["cost_per_million_output_tokens"]
            if live["context_window"] is not None:
                model_entry["context_window"] = live["context_window"]

        all_models = static_models + live_models + ollama_models

        return {
            "models": all_models,
            "providers": {
                "openai": len([m for m in all_models if m["provider"] == "openai"]),
                "anthropic": len([m for m in all_models if m["provider"] == "anthropic"]),
                "ollama": len(ollama_models),
            },
            "total": len(all_models),
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
                "models_count": len(
                    [m for m in LLM_MODELS.values() if m.provider == LLMProvider.OPENAI]
                ),
            },
            {
                "name": "anthropic",
                "display_name": "Anthropic",
                "models_count": len(
                    [m for m in LLM_MODELS.values() if m.provider == LLMProvider.ANTHROPIC]
                ),
            },
            {
                "name": "deepseek",
                "display_name": "DeepSeek",
                "models_count": len(
                    [m for m in LLM_MODELS.values() if m.provider == LLMProvider.DEEPSEEK]
                ),
            },
            {
                "name": "ollama",
                "display_name": "Ollama (Local)",
                "models_count": None,  # Dynamic
            },
        ]
    }
