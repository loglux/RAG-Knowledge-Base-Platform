"""
Text Chunking Service.

Handles splitting text documents into chunks for embedding and indexing.
Supports multiple chunking strategies.
"""
import logging
import re
from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field

from app.config import settings


logger = logging.getLogger(__name__)


class Chunk(BaseModel):
    """Represents a chunk of text with metadata."""

    content: str = Field(..., description="The text content of the chunk")
    index: int = Field(..., description="Index of this chunk in the document")
    start_char: int = Field(..., description="Starting character position in original document")
    end_char: int = Field(..., description="Ending character position in original document")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    def __len__(self) -> int:
        """Return length of chunk content."""
        return len(self.content)

    @property
    def char_count(self) -> int:
        """Get character count."""
        return len(self.content)

    @property
    def word_count(self) -> int:
        """Get approximate word count."""
        return len(self.content.split())


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""

    @abstractmethod
    def split(self, text: str, metadata: Optional[dict] = None) -> List[Chunk]:
        """
        Split text into chunks.

        Args:
            text: Text to split
            metadata: Optional metadata to attach to all chunks

        Returns:
            List of Chunk objects
        """
        pass


class FixedSizeChunking(ChunkingStrategy):
    """
    Fixed-size chunking strategy with overlap.

    Splits text into chunks of approximately equal size with configurable overlap
    between consecutive chunks. Tries to split on sentence boundaries when possible.
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        respect_sentence_boundary: bool = True,
    ):
        """
        Initialize fixed-size chunking strategy.

        Args:
            chunk_size: Maximum chunk size in characters (default: from settings)
            chunk_overlap: Number of overlapping characters between chunks (default: from settings)
            respect_sentence_boundary: Try to split on sentence boundaries (default: True)
        """
        self.chunk_size = chunk_size or settings.MAX_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.respect_sentence_boundary = respect_sentence_boundary

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be smaller than chunk size")

        logger.info(
            f"Initialized FixedSizeChunking: size={self.chunk_size}, "
            f"overlap={self.chunk_overlap}, respect_boundaries={self.respect_sentence_boundary}"
        )

    def split(self, text: str, metadata: Optional[dict] = None) -> List[Chunk]:
        """
        Split text into fixed-size chunks with overlap.

        Args:
            text: Text to split
            metadata: Optional metadata to attach to all chunks

        Returns:
            List of Chunk objects
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for chunking")
            return []

        # Normalize whitespace
        text = self._normalize_text(text)

        if len(text) <= self.chunk_size:
            # Text fits in single chunk
            logger.debug(f"Text fits in single chunk: {len(text)} chars")
            return [
                Chunk(
                    content=text,
                    index=0,
                    start_char=0,
                    end_char=len(text),
                    metadata=metadata or {},
                )
            ]

        chunks: List[Chunk] = []
        start = 0
        chunk_index = 0

        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size

            # If this is not the last chunk and we should respect boundaries
            if end < len(text) and self.respect_sentence_boundary:
                # Try to find a good breaking point
                end = self._find_break_point(text, start, end)

            # Extract chunk content
            chunk_content = text[start:end].strip()

            if chunk_content:  # Only add non-empty chunks
                chunks.append(
                    Chunk(
                        content=chunk_content,
                        index=chunk_index,
                        start_char=start,
                        end_char=end,
                        metadata=metadata or {},
                    )
                )
                chunk_index += 1

            # Move to next chunk with overlap
            start = end - self.chunk_overlap

            # Ensure we make progress even if overlap is large
            if start <= chunks[-1].start_char if chunks else 0:
                start = end

        logger.info(
            f"Split text of {len(text)} chars into {len(chunks)} chunks "
            f"(avg size: {len(text) // len(chunks) if chunks else 0})"
        )

        return chunks

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text whitespace while preserving line breaks.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        # Replace multiple spaces/tabs with single space, but preserve newlines
        text = re.sub(r'[ \t]+', ' ', text)
        # Replace 3+ newlines with 2 newlines (preserve paragraph breaks)
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text

    def _find_break_point(self, text: str, start: int, end: int) -> int:
        """
        Find a good breaking point near the target end position.

        Tries to break on sentence boundaries, then paragraph boundaries,
        then word boundaries.

        Args:
            text: Full text
            start: Start position of chunk
            end: Target end position

        Returns:
            Adjusted end position
        """
        # Define search window (look back up to 20% of chunk size)
        search_start = max(start, end - int(self.chunk_size * 0.2))
        search_text = text[search_start:end]

        # Try to find sentence boundary (. ! ? followed by space or newline)
        sentence_pattern = r'[.!?][\s\n]'
        matches = list(re.finditer(sentence_pattern, search_text))
        if matches:
            # Take the last match
            last_match = matches[-1]
            return search_start + last_match.end()

        # Try to find paragraph boundary (double newline)
        if '\n\n' in search_text:
            last_para = search_text.rfind('\n\n')
            if last_para > 0:
                return search_start + last_para + 2

        # Try to find word boundary (space)
        if ' ' in search_text:
            last_space = search_text.rfind(' ')
            if last_space > 0:
                return search_start + last_space + 1

        # Fallback: use target end
        return end


class SemanticChunking(ChunkingStrategy):
    """
    Semantic chunking strategy (placeholder for future implementation).

    This will use embeddings to identify semantic boundaries in text.
    For MVP, we use FixedSizeChunking.
    """

    def __init__(self):
        """Initialize semantic chunking (not implemented yet)."""
        raise NotImplementedError(
            "Semantic chunking not yet implemented. Use FixedSizeChunking for MVP."
        )

    def split(self, text: str, metadata: Optional[dict] = None) -> List[Chunk]:
        """Split text into semantically coherent chunks."""
        raise NotImplementedError("Semantic chunking not yet implemented")


class ChunkingService:
    """
    Service for managing text chunking operations.

    Provides a unified interface for different chunking strategies.
    """

    def __init__(self, strategy: Optional[ChunkingStrategy] = None):
        """
        Initialize chunking service.

        Args:
            strategy: Chunking strategy to use (default: FixedSizeChunking)
        """
        self.strategy = strategy or FixedSizeChunking()
        logger.info(f"Initialized ChunkingService with strategy: {type(self.strategy).__name__}")

    def chunk_text(self, text: str, metadata: Optional[dict] = None) -> List[Chunk]:
        """
        Chunk text using the configured strategy.

        Args:
            text: Text to chunk
            metadata: Optional metadata to attach to chunks

        Returns:
            List of Chunk objects

        Raises:
            ValueError: If text is empty
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        logger.debug(f"Chunking text of {len(text)} characters")
        chunks = self.strategy.split(text, metadata)

        # Log statistics
        if chunks:
            avg_size = sum(len(c.content) for c in chunks) / len(chunks)
            logger.info(
                f"Created {len(chunks)} chunks. "
                f"Avg size: {avg_size:.0f} chars, "
                f"Min: {min(len(c.content) for c in chunks)}, "
                f"Max: {max(len(c.content) for c in chunks)}"
            )

        return chunks

    def set_strategy(self, strategy: ChunkingStrategy):
        """
        Change the chunking strategy.

        Args:
            strategy: New chunking strategy to use
        """
        self.strategy = strategy
        logger.info(f"Changed chunking strategy to: {type(strategy).__name__}")


# Default service instance
def get_chunking_service(
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> ChunkingService:
    """
    Get a chunking service instance with fixed-size strategy.

    Args:
        chunk_size: Optional chunk size override
        chunk_overlap: Optional chunk overlap override

    Returns:
        ChunkingService instance
    """
    strategy = FixedSizeChunking(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return ChunkingService(strategy=strategy)
