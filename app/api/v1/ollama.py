"""Ollama models endpoints."""

import logging
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class OllamaConnectionTest(BaseModel):
    """Request to test Ollama connection."""

    base_url: str


async def fetch_ollama_models() -> List[Dict[str, Any]]:
    """
    Fetch models from Ollama server.

    Returns:
        List of models with their details
    """
    if not settings.OLLAMA_BASE_URL:
        raise ValueError("OLLAMA_BASE_URL not configured")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
    except Exception as e:
        logger.error(f"Failed to fetch Ollama models: {e}")
        raise


def is_embedding_model(model: Dict[str, Any]) -> bool:
    """
    Determine if model is for embeddings.

    Args:
        model: Model info from Ollama API

    Returns:
        True if embedding model
    """
    name = model.get("name", "").lower()
    family = model.get("details", {}).get("family", "").lower()

    # Check by name
    if "embed" in name or "minilm" in name:
        return True

    # Check by family (BERT models are typically for embeddings)
    if "bert" in family:
        return True

    return False


@router.get("/models")
async def list_ollama_models():
    """
    List all Ollama models with type classification.

    Returns models grouped by type (embedding/llm).
    """
    try:
        models = await fetch_ollama_models()

        embedding_models = []
        llm_models = []

        for model in models:
            model_info = {
                "name": model.get("name"),
                "size": model.get("size"),
                "family": model.get("details", {}).get("family"),
                "modified_at": model.get("modified_at"),
            }

            if is_embedding_model(model):
                embedding_models.append(model_info)
            else:
                llm_models.append(model_info)

        return {
            "embedding_models": embedding_models,
            "llm_models": llm_models,
            "total": len(models),
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Ollama not configured: {e}"
        )
    except Exception as e:
        logger.error(f"Failed to list Ollama models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Ollama models: {e}",
        )


@router.get("/models/embeddings")
async def list_ollama_embedding_models():
    """List only embedding models from Ollama."""
    try:
        models = await fetch_ollama_models()
        embedding_models = [
            {
                "name": m.get("name"),
                "size": m.get("size"),
                "family": m.get("details", {}).get("family"),
            }
            for m in models
            if is_embedding_model(m)
        ]

        return {
            "models": embedding_models,
            "count": len(embedding_models),
        }

    except Exception as e:
        logger.error(f"Failed to list embedding models: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/models/llm")
async def list_ollama_llm_models():
    """List only LLM models from Ollama."""
    try:
        models = await fetch_ollama_models()
        llm_models = [
            {
                "name": m.get("name"),
                "size": m.get("size"),
                "family": m.get("details", {}).get("family"),
                "parameter_size": m.get("details", {}).get("parameter_size"),
            }
            for m in models
            if not is_embedding_model(m)
        ]

        return {
            "models": llm_models,
            "count": len(llm_models),
        }

    except Exception as e:
        logger.error(f"Failed to list LLM models: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/status")
async def ollama_status():
    """Check Ollama server status."""
    if not settings.OLLAMA_BASE_URL:
        return {"available": False, "error": "OLLAMA_BASE_URL not configured"}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()

            return {
                "available": True,
                "url": settings.OLLAMA_BASE_URL,
                "models_count": len(response.json().get("models", [])),
            }
    except Exception as e:
        return {"available": False, "url": settings.OLLAMA_BASE_URL, "error": str(e)}


@router.post("/test-connection")
async def test_ollama_connection(payload: OllamaConnectionTest):
    """
    Test connection to Ollama server.

    Used by Setup Wizard to validate Ollama URL before saving.

    Args:
        payload: Ollama connection test request with base_url

    Returns:
        Connection status with available models count
    """
    base_url = payload.base_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Try to fetch tags endpoint
            response = await client.get(f"{base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            models = data.get("models", [])

            return {
                "success": True,
                "available": True,
                "url": base_url,
                "models_count": len(models),
                "message": f"✅ Connected successfully! Found {len(models)} model(s)",
            }

    except httpx.TimeoutException:
        return {
            "success": False,
            "available": False,
            "url": base_url,
            "error": "Connection timeout (5s). Check if Ollama is running and accessible.",
            "message": "❌ Connection timeout",
        }
    except httpx.ConnectError:
        return {
            "success": False,
            "available": False,
            "url": base_url,
            "error": f"Cannot connect to {base_url}. Check URL and network.",
            "message": "❌ Connection failed",
        }
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "available": False,
            "url": base_url,
            "error": f"HTTP {e.response.status_code}: {e.response.text}",
            "message": f"❌ HTTP {e.response.status_code}",
        }
    except Exception as e:
        logger.error(f"Ollama connection test failed for {base_url}: {e}")
        return {
            "success": False,
            "available": False,
            "url": base_url,
            "error": str(e),
            "message": "❌ Connection failed",
        }
