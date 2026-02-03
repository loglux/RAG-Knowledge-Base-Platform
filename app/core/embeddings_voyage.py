"""
Voyage AI Embeddings Service.

Handles generation of text embeddings using Voyage AI API with proper error handling,
retries, and batch processing support.
"""
import logging
from typing import List, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

try:
    import voyageai
    from voyageai.error import VoyageError
    VOYAGE_AVAILABLE = True
except ImportError:
    VOYAGE_AVAILABLE = False
    voyageai = None
    VoyageError = Exception

from app.config import settings
from app.core.embeddings_base import (
    BaseEmbeddingService,
    EmbeddingResult,
    EmbeddingProvider,
)


logger = logging.getLogger(__name__)


class VoyageEmbeddingService(BaseEmbeddingService):
    """
    Service for generating text embeddings using Voyage AI API.

    Features:
    - Async operations
    - Automatic retries with exponential backoff
    - Batch processing
    - Error handling
    - Support for input_type parameter for optimized retrieval
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
    ):
        """
        Initialize Voyage AI embeddings service.

        Args:
            api_key: Voyage AI API key (uses settings.VOYAGE_API_KEY if not provided)
            model: Embedding model name (uses settings.VOYAGE_EMBEDDING_MODEL if not provided)
            max_retries: Maximum number of retries for failed requests

        Raises:
            ImportError: If voyageai package is not installed
            ValueError: If API key is missing
        """
        if not VOYAGE_AVAILABLE:
            raise ImportError(
                "voyageai package is not installed. "
                "Install it with: pip install voyageai"
            )

        api_key = api_key or getattr(settings, "VOYAGE_API_KEY", None)
        model = model or getattr(settings, "VOYAGE_EMBEDDING_MODEL", "voyage-4")

        if not api_key:
            raise ValueError("Voyage AI API key is required")

        # Initialize base class
        super().__init__(api_key=api_key, model=model, max_retries=max_retries)

        # Validate provider
        if self.provider != EmbeddingProvider.VOYAGE:
            raise ValueError(f"Model {model} is not a Voyage AI model")

        self.client = voyageai.Client(api_key=self.api_key)

        logger.info(f"Initialized VoyageEmbeddingService with model: {self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(VoyageError),
        reraise=True,
    )
    async def generate_embedding(
        self,
        text: str,
        input_type: str = "document",
    ) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            input_type: Type of input - "query" or "document" (default: "document")

        Returns:
            List of floats representing the embedding vector

        Raises:
            ValueError: If text is empty
            VoyageError: If Voyage AI API call fails after retries
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            logger.debug(f"Generating embedding for text of length {len(text)}")

            # Voyage AI sync API (they don't have async yet)
            response = self.client.embed(
                texts=[text],
                model=self.model,
                input_type=input_type,
            )

            embedding = response.embeddings[0]

            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding

        except VoyageError as e:
            logger.error(f"Voyage AI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {e}")
            raise

    async def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 100,
        input_type: str = "document",
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts with batch processing.

        Voyage AI API supports batch processing, but we use smaller batches
        for better error handling and progress tracking.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in each batch (default: 100)
            input_type: Type of input - "query" or "document" (default: "document")

        Returns:
            List of EmbeddingResult objects with embeddings and original indices

        Raises:
            ValueError: If texts list is empty
            VoyageError: If any batch fails after retries
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        logger.info(f"Generating embeddings for {len(texts)} texts in batches of {batch_size}")

        results: List[EmbeddingResult] = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(texts) + batch_size - 1) // batch_size

            logger.debug(f"Processing batch {batch_num}/{total_batches}")

            try:
                batch_results = await self._generate_batch(
                    batch,
                    start_index=i,
                    input_type=input_type,
                )
                results.extend(batch_results)

            except Exception as e:
                logger.error(f"Failed to process batch {batch_num}: {e}")
                raise

        logger.info(f"Successfully generated {len(results)} embeddings")
        return results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(VoyageError),
        reraise=True,
    )
    async def _generate_batch(
        self,
        texts: List[str],
        start_index: int = 0,
        input_type: str = "document",
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: Batch of texts to embed
            start_index: Starting index for results (for tracking original positions)
            input_type: Type of input - "query" or "document"

        Returns:
            List of EmbeddingResult objects
        """
        try:
            # Voyage AI sync API
            response = self.client.embed(
                texts=texts,
                model=self.model,
                input_type=input_type,
            )

            results = [
                EmbeddingResult(
                    text=texts[i],
                    embedding=response.embeddings[i],
                    index=start_index + i,
                )
                for i in range(len(texts))
            ]

            return results

        except VoyageError as e:
            logger.error(f"Voyage AI API error on batch: {e}")
            raise

    async def get_embedding_dimension(self) -> int:
        """
        Get the dimension size of embeddings for the current model.

        Returns:
            Integer representing embedding dimension size
        """
        # Return from model config (more efficient than test embedding)
        return self.dimension

    async def close(self):
        """Close the Voyage AI client and cleanup resources."""
        # Voyage AI client doesn't need explicit closing
        logger.info("VoyageEmbeddingService closed")


# Singleton helpers removed; use app.core.embeddings_factory.get_embedding_service()
