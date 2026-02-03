"""
Ollama Embeddings Service.

Handles generation of text embeddings using Ollama API (local models).
"""
import asyncio
import logging
from typing import List, Optional
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import settings
from app.core.embeddings_base import (
    BaseEmbeddingService,
    EmbeddingResult,
    EmbeddingProvider,
)


logger = logging.getLogger(__name__)


class OllamaEmbeddingService(BaseEmbeddingService):
    """
    Service for generating text embeddings using Ollama (local models).

    Features:
    - Async operations
    - Local model execution
    - Free (no API costs)
    - Supports multiple embedding models
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
    ):
        """
        Initialize Ollama embeddings service.

        Args:
            base_url: Ollama API base URL (uses settings.OLLAMA_BASE_URL if not provided)
            model: Embedding model name (uses settings.OLLAMA_EMBEDDING_MODEL if not provided)
            max_retries: Maximum number of retries for failed requests

        Raises:
            ValueError: If base URL is missing
        """
        # Ollama doesn't use API key (dummy value for base class)
        api_key = "local"
        model = model or settings.OLLAMA_EMBEDDING_MODEL

        # Initialize base class
        super().__init__(api_key=api_key, model=model, max_retries=max_retries)

        # Validate provider
        if self.provider != EmbeddingProvider.OLLAMA:
            raise ValueError(f"Model {model} is not an Ollama model")

        self.base_url = base_url or settings.OLLAMA_BASE_URL
        if not self.base_url:
            raise ValueError("OLLAMA_BASE_URL is required for Ollama embedding service")

        # Create client with connection limits to avoid overwhelming Ollama server
        limits = httpx.Limits(
            max_connections=1,  # Process one at a time
            max_keepalive_connections=1  # Keep only one connection alive
        )
        self.client = httpx.AsyncClient(
            timeout=60.0,  # Increased timeout for slow models
            limits=limits
        )

        logger.info(f"Initialized OllamaEmbeddingService with model: {self.model} at {self.base_url}")

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True,
    )
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Retries up to 5 times with exponential backoff if Ollama server fails.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            ValueError: If text is empty
            httpx.HTTPError: If Ollama API call fails after retries
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            logger.debug(f"Generating embedding for text of length {len(text)}")

            response = await self.client.post(
                f"{self.base_url}/api/embed",
                json={
                    "model": self.model,
                    "input": text,
                }
            )
            if response.status_code >= 400:
                logger.error(
                    "Ollama /api/embed error %s: %s",
                    response.status_code,
                    response.text,
                )
            response.raise_for_status()

            data = response.json()
            embedding = data.get("embedding")
            if not embedding:
                embeddings = data.get("embeddings") or []
                if embeddings:
                    embedding = embeddings[0]

            if not embedding:
                raise ValueError("No embedding returned from Ollama (/api/embed)")

            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding

        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {e}")
            raise

    async def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 10,  # Ollama processes one at a time
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts.

        Note: Ollama processes embeddings one at a time, so we process sequentially.

        Args:
            texts: List of texts to embed
            batch_size: Not used for Ollama (kept for interface compatibility)

        Returns:
            List of EmbeddingResult objects with embeddings and original indices

        Raises:
            ValueError: If texts list is empty
            httpx.HTTPError: If any request fails
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        logger.info(f"Generating embeddings for {len(texts)} texts using Ollama")

        results: List[EmbeddingResult] = []

        # Process one at a time (Ollama doesn't support batch)
        for i, text in enumerate(texts):
            try:
                embedding = await self.generate_embedding(text)
                results.append(
                    EmbeddingResult(
                        text=text,
                        embedding=embedding,
                        index=i,
                    )
                )

                # Add small delay to avoid overloading Ollama server
                if i < len(texts) - 1:  # Don't delay after last item
                    await asyncio.sleep(0.2)  # 200ms delay between requests

            except Exception as e:
                logger.error(f"Failed to process text {i}: {e}")
                raise

        logger.info(f"Successfully generated {len(results)} embeddings")
        return results

    async def get_embedding_dimension(self) -> int:
        """
        Get the dimension size of embeddings for the current model.

        Returns:
            Integer representing embedding dimension size
        """
        # Return from model config (more efficient than test embedding)
        return self.dimension

    async def close(self):
        """Close the HTTP client and cleanup resources."""
        await self.client.aclose()
        logger.info("OllamaEmbeddingService closed")


# Singleton helpers removed; use app.core.embeddings_factory.get_embedding_service()
