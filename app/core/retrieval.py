"""
Retrieval Engine for RAG.

Handles semantic search and context retrieval from vector store.
"""
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.embeddings_factory import create_embedding_service
from app.core.embeddings_base import BaseEmbeddingService
from app.core.vector_store import get_vector_store, QdrantVectorStore, SearchResult
from app.config import settings


logger = logging.getLogger(__name__)


class RetrievedChunk(BaseModel):
    """Represents a retrieved text chunk with metadata."""

    text: str = Field(..., description="Text content of the chunk")
    score: float = Field(..., description="Similarity score (0-1)")
    document_id: str = Field(..., description="Source document ID")
    filename: str = Field(..., description="Source filename")
    chunk_index: int = Field(..., description="Chunk index in document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        frozen = True


class RetrievalResult(BaseModel):
    """Result of retrieval operation."""

    query: str = Field(..., description="Original query")
    chunks: List[RetrievedChunk] = Field(..., description="Retrieved chunks")
    total_found: int = Field(..., description="Total number of results")
    context: str = Field(..., description="Assembled context from chunks")

    @property
    def has_results(self) -> bool:
        """Check if any results were found."""
        return len(self.chunks) > 0

    @property
    def source_documents(self) -> List[str]:
        """Get unique list of source document IDs."""
        return list(set(chunk.document_id for chunk in self.chunks))


class RetrievalEngine:
    """
    Engine for retrieving relevant content from vector store.

    Handles query embedding, semantic search, and context assembly.
    """

    def __init__(
        self,
        vector_store: Optional[QdrantVectorStore] = None,
    ):
        """
        Initialize retrieval engine.

        Args:
            vector_store: Vector store for search

        Note:
            Embedding service is created per-query based on KB's embedding model.
        """
        self.vector_store = vector_store or get_vector_store()

        logger.info("Initialized RetrievalEngine")

    async def retrieve(
        self,
        query: str,
        collection_name: str,
        embedding_model: str,
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> RetrievalResult:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: User query text
            collection_name: Qdrant collection to search
            embedding_model: Embedding model to use for query embedding
            top_k: Number of top results to return (default: 5)
            score_threshold: Minimum similarity score (optional)
            filters: Optional metadata filters

        Returns:
            RetrievalResult with chunks and assembled context

        Raises:
            ValueError: If query is empty
            Exception: If retrieval fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        logger.info(
            f"Retrieving for query: '{query[:50]}...' "
            f"(collection={collection_name}, model={embedding_model}, top_k={top_k})"
        )

        try:
            # 1. Create embedding service for this KB's model
            logger.debug(f"Creating embedding service for model: {embedding_model}")
            embeddings_service = create_embedding_service(model=embedding_model)

            # 2. Generate query embedding
            logger.debug("Generating query embedding")
            query_embedding = await embeddings_service.generate_embedding(query)

            # 3. Search vector store
            logger.debug(f"Searching vector store (top_k={top_k})")
            search_results = await self.vector_store.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=score_threshold,
                filter_conditions=filters,
            )

            # 4. Convert to RetrievedChunk objects
            chunks = self._convert_search_results(search_results)

            # 5. Assemble context
            context = self._assemble_context(chunks)

            logger.info(
                f"Retrieved {len(chunks)} chunks "
                f"(scores: {[f'{c.score:.3f}' for c in chunks[:3]]}...)"
            )

            return RetrievalResult(
                query=query,
                chunks=chunks,
                total_found=len(chunks),
                context=context,
            )

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            raise

    async def retrieve_by_document(
        self,
        query: str,
        collection_name: str,
        embedding_model: str,
        document_id: UUID,
        top_k: int = 5,
    ) -> RetrievalResult:
        """
        Retrieve relevant chunks from a specific document.

        Args:
            query: User query
            collection_name: Collection name
            embedding_model: Embedding model to use for query embedding
            document_id: Specific document to search
            top_k: Number of results

        Returns:
            RetrievalResult filtered to specific document
        """
        filters = {"document_id": str(document_id)}

        return await self.retrieve(
            query=query,
            collection_name=collection_name,
            embedding_model=embedding_model,
            top_k=top_k,
            filters=filters,
        )

    def _convert_search_results(
        self,
        search_results: List[SearchResult],
    ) -> List[RetrievedChunk]:
        """
        Convert SearchResult objects to RetrievedChunk objects.

        Args:
            search_results: Raw search results from vector store

        Returns:
            List of RetrievedChunk objects
        """
        chunks = []

        for result in search_results:
            payload = result.payload

            chunk = RetrievedChunk(
                text=payload.get("text", ""),
                score=result.score,
                document_id=payload.get("document_id", ""),
                filename=payload.get("filename", "unknown"),
                chunk_index=payload.get("chunk_index", 0),
                metadata={
                    "knowledge_base_id": payload.get("knowledge_base_id"),
                    "file_type": payload.get("file_type"),
                    "char_count": payload.get("char_count"),
                    "word_count": payload.get("word_count"),
                    "indexed_at": payload.get("indexed_at"),
                },
            )

            chunks.append(chunk)

        return chunks

    def _assemble_context(
        self,
        chunks: List[RetrievedChunk],
        max_length: Optional[int] = None,
    ) -> str:
        """
        Assemble context string from retrieved chunks.

        Combines chunks with metadata for LLM context.

        Args:
            chunks: Retrieved chunks
            max_length: Maximum context length in characters

        Returns:
            Assembled context string
        """
        if not chunks:
            return ""

        context_parts = []
        current_length = 0

        max_length = max_length or settings.MAX_CONTEXT_CHARS

        for i, chunk in enumerate(chunks):
            # Format chunk with metadata
            chunk_text = (
                f"[Source {i+1}: {chunk.filename}, chunk {chunk.chunk_index}]\n"
                f"{chunk.text}\n"
            )

            chunk_length = len(chunk_text)

            # Check if adding this chunk would exceed max length
            if current_length + chunk_length > max_length:
                logger.warning(
                    f"Context length limit reached ({max_length}), "
                    f"including {i} of {len(chunks)} chunks"
                )
                break

            context_parts.append(chunk_text)
            current_length += chunk_length

        context = "\n".join(context_parts)

        logger.debug(
            f"Assembled context: {len(context)} chars from {len(context_parts)} chunks"
        )

        return context

    async def rerank_results(
        self,
        query: str,
        chunks: List[RetrievedChunk],
    ) -> List[RetrievedChunk]:
        """
        Re-rank retrieved chunks (placeholder for future implementation).

        Could use cross-encoder or other re-ranking models.

        Args:
            query: Original query
            chunks: Initial retrieved chunks

        Returns:
            Re-ranked chunks
        """
        # For MVP, just return chunks as-is
        # Future: implement cross-encoder re-ranking
        logger.debug("Re-ranking not implemented, returning original order")
        return chunks


# Singleton instance
_retrieval_engine: Optional[RetrievalEngine] = None


def get_retrieval_engine() -> RetrievalEngine:
    """
    Get or create singleton instance of RetrievalEngine.

    Returns:
        RetrievalEngine instance
    """
    global _retrieval_engine

    if _retrieval_engine is None:
        _retrieval_engine = RetrievalEngine()

    return _retrieval_engine
