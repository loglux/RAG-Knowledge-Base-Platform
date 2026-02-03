"""
OpenAI Embeddings Service.

Handles generation of text embeddings using OpenAI API with proper error handling,
retries, and batch processing support.
"""
import asyncio
import logging
from typing import List, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from openai import AsyncOpenAI, OpenAIError, RateLimitError, APITimeoutError

from app.config import settings
from app.core.embeddings_base import (
    BaseEmbeddingService,
    EmbeddingResult,
    EmbeddingProvider,
)


logger = logging.getLogger(__name__)


class OpenAIEmbeddingService(BaseEmbeddingService):
    """
    Service for generating text embeddings using OpenAI API.

    Features:
    - Async operations
    - Automatic retries with exponential backoff
    - Batch processing
    - Error handling
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
    ):
        """
        Initialize OpenAI embeddings service.

        Args:
            api_key: OpenAI API key (uses settings.OPENAI_API_KEY if not provided)
            model: Embedding model name (uses settings.OPENAI_EMBEDDING_MODEL if not provided)
            max_retries: Maximum number of retries for failed requests
        """
        api_key = api_key or settings.OPENAI_API_KEY
        model = model or settings.OPENAI_EMBEDDING_MODEL

        if not api_key:
            raise ValueError("OpenAI API key is required")

        # Initialize base class
        super().__init__(api_key=api_key, model=model, max_retries=max_retries)

        # Validate provider
        if self.provider != EmbeddingProvider.OPENAI:
            raise ValueError(f"Model {model} is not an OpenAI model")

        self.client = AsyncOpenAI(api_key=self.api_key)

        logger.info(f"Initialized OpenAIEmbeddingService with model: {self.model}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
        reraise=True,
    )
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            OpenAIError: If OpenAI API call fails after retries
            ValueError: If text is empty
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            logger.debug(f"Generating embedding for text of length {len(text)}")

            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
            )

            embedding = response.data[0].embedding

            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding

        except RateLimitError as e:
            logger.warning(f"Rate limit hit, will retry: {e}")
            raise
        except APITimeoutError as e:
            logger.warning(f"API timeout, will retry: {e}")
            raise
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {e}")
            raise

    async def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 100,
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts with batch processing.

        OpenAI API supports up to 2048 texts per request, but we use smaller batches
        for better error handling and progress tracking.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process in each batch (default: 100)

        Returns:
            List of EmbeddingResult objects with embeddings and original indices

        Raises:
            OpenAIError: If any batch fails after retries
            ValueError: If texts list is empty
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
                batch_results = await self._generate_batch(batch, start_index=i)
                results.extend(batch_results)

            except Exception as e:
                logger.error(f"Failed to process batch {batch_num}: {e}")
                raise

        logger.info(f"Successfully generated {len(results)} embeddings")
        return results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
        reraise=True,
    )
    async def _generate_batch(
        self,
        texts: List[str],
        start_index: int = 0,
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: Batch of texts to embed
            start_index: Starting index for results (for tracking original positions)

        Returns:
            List of EmbeddingResult objects
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
            )

            results = [
                EmbeddingResult(
                    text=texts[i],
                    embedding=response.data[i].embedding,
                    index=start_index + i,
                )
                for i in range(len(texts))
            ]

            return results

        except RateLimitError as e:
            logger.warning(f"Rate limit hit on batch, will retry: {e}")
            raise
        except APITimeoutError as e:
            logger.warning(f"API timeout on batch, will retry: {e}")
            raise
        except OpenAIError as e:
            logger.error(f"OpenAI API error on batch: {e}")
            raise

    async def get_embedding_dimension(self) -> int:
        """
        Get the dimension size of embeddings for the current model.

        Returns:
            Integer representing embedding dimension size

        Raises:
            OpenAIError: If unable to determine dimension
        """
        try:
            # Generate a test embedding to determine dimension
            test_embedding = await self.generate_embedding("test")
            dimension = len(test_embedding)

            logger.info(f"Model {self.model} produces {dimension}-dimensional embeddings")
            return dimension

        except Exception as e:
            logger.error(f"Failed to determine embedding dimension: {e}")
            raise

    async def close(self):
        """Close the OpenAI client and cleanup resources."""
        await self.client.close()
        logger.info("EmbeddingsService closed")


 # Singleton helpers removed; use app.core.embeddings_factory.get_embedding_service()
