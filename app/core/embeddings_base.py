"""
Base classes for embedding providers.

Provides abstract interface for different embedding services (OpenAI, Voyage AI, etc).
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class EmbeddingProvider(str, Enum):
    """Supported embedding providers."""
    OPENAI = "openai"
    VOYAGE = "voyage"
    OLLAMA = "ollama"


class EmbeddingModel(BaseModel):
    """Embedding model configuration."""
    provider: EmbeddingProvider
    model_name: str
    dimension: int
    description: str
    cost_per_million_tokens: float


# Available embedding models
EMBEDDING_MODELS = {
    # OpenAI models
    "text-embedding-3-small": EmbeddingModel(
        provider=EmbeddingProvider.OPENAI,
        model_name="text-embedding-3-small",
        dimension=1536,
        description="OpenAI small embedding model - fast and cost-effective",
        cost_per_million_tokens=0.02,
    ),
    "text-embedding-3-large": EmbeddingModel(
        provider=EmbeddingProvider.OPENAI,
        model_name="text-embedding-3-large",
        dimension=3072,
        description="OpenAI large embedding model - highest quality",
        cost_per_million_tokens=0.13,
    ),
    # Voyage AI models
    "voyage-4-lite": EmbeddingModel(
        provider=EmbeddingProvider.VOYAGE,
        model_name="voyage-4-lite",
        dimension=1024,
        description="Voyage lite model - optimized for latency and cost",
        cost_per_million_tokens=0.02,
    ),
    "voyage-4": EmbeddingModel(
        provider=EmbeddingProvider.VOYAGE,
        model_name="voyage-4",
        dimension=1024,
        description="Voyage standard model - balanced performance",
        cost_per_million_tokens=0.06,
    ),
    "voyage-4-large": EmbeddingModel(
        provider=EmbeddingProvider.VOYAGE,
        model_name="voyage-4-large",
        dimension=1024,
        description="Voyage large model - best general-purpose quality",
        cost_per_million_tokens=0.12,
    ),
    "voyage-code-3": EmbeddingModel(
        provider=EmbeddingProvider.VOYAGE,
        model_name="voyage-code-3",
        dimension=1024,
        description="Voyage model optimized for code retrieval",
        cost_per_million_tokens=0.18,
    ),
    "voyage-finance-2": EmbeddingModel(
        provider=EmbeddingProvider.VOYAGE,
        model_name="voyage-finance-2",
        dimension=1024,
        description="Voyage model optimized for finance domain",
        cost_per_million_tokens=0.12,
    ),
    "voyage-law-2": EmbeddingModel(
        provider=EmbeddingProvider.VOYAGE,
        model_name="voyage-law-2",
        dimension=1024,
        description="Voyage model optimized for legal domain",
        cost_per_million_tokens=0.12,
    ),
    # Ollama models (local, free)
    "nomic-embed-text": EmbeddingModel(
        provider=EmbeddingProvider.OLLAMA,
        model_name="nomic-embed-text",
        dimension=768,
        description="Ollama Nomic Embed Text - high quality local embeddings",
        cost_per_million_tokens=0.0,  # Free (local)
    ),
    "mxbai-embed-large": EmbeddingModel(
        provider=EmbeddingProvider.OLLAMA,
        model_name="mxbai-embed-large",
        dimension=1024,
        description="Ollama MixBread AI Embed Large - multilingual embeddings",
        cost_per_million_tokens=0.0,  # Free (local)
    ),
    "all-minilm": EmbeddingModel(
        provider=EmbeddingProvider.OLLAMA,
        model_name="all-minilm",
        dimension=384,
        description="Ollama All-MiniLM - fast and lightweight embeddings",
        cost_per_million_tokens=0.0,  # Free (local)
    ),
    "embeddinggemma": EmbeddingModel(
        provider=EmbeddingProvider.OLLAMA,
        model_name="embeddinggemma",
        dimension=768,
        description="Ollama Embedding Gemma - Google's embedding model",
        cost_per_million_tokens=0.0,  # Free (local)
    ),
    "qwen3-embedding": EmbeddingModel(
        provider=EmbeddingProvider.OLLAMA,
        model_name="qwen3-embedding",
        dimension=4096,
        description="Ollama Qwen3 Embedding - high-dimensional embeddings",
        cost_per_million_tokens=0.0,  # Free (local)
    ),
}


class EmbeddingResult(BaseModel):
    """Result of embedding generation."""
    text: str
    embedding: List[float]
    index: int


class BaseEmbeddingService(ABC):
    """
    Abstract base class for embedding services.

    All embedding providers must implement this interface.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        max_retries: int = 3,
    ):
        """
        Initialize embedding service.

        Args:
            api_key: API key for the provider
            model: Model name to use
            max_retries: Maximum number of retries for failed requests
        """
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries

        # Get model configuration
        if model not in EMBEDDING_MODELS:
            raise ValueError(f"Unknown embedding model: {model}")

        self.model_config = EMBEDDING_MODELS[model]

    @property
    def provider(self) -> EmbeddingProvider:
        """Get the provider type."""
        return self.model_config.provider

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        return self.model_config.dimension

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            ValueError: If text is empty
            Exception: If API call fails after retries
        """
        pass

    @abstractmethod
    async def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 100,
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts with batch processing.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in each batch

        Returns:
            List of EmbeddingResult objects with embeddings and original indices

        Raises:
            ValueError: If texts list is empty
            Exception: If any batch fails after retries
        """
        pass

    @abstractmethod
    async def get_embedding_dimension(self) -> int:
        """
        Get the dimension size of embeddings for the current model.

        Returns:
            Integer representing embedding dimension size
        """
        pass

    @abstractmethod
    async def close(self):
        """Close the client and cleanup resources."""
        pass
