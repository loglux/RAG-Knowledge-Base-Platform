"""
Retrieval Engine for RAG.

Handles semantic search and context retrieval from vector store.
"""
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.embeddings_factory import get_embedding_service
from app.core.embeddings_base import BaseEmbeddingService
from app.core.vector_store import get_vector_store, QdrantVectorStore, SearchResult
from app.core.lexical_store import get_lexical_store, OpenSearchStore
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
        lexical_store: Optional[OpenSearchStore] = None,
    ):
        """
        Initialize retrieval engine.

        Args:
            vector_store: Vector store for search

        Note:
            Embedding service is created per-query based on KB's embedding model.
        """
        self.vector_store = vector_store or get_vector_store()
        self.lexical_store = lexical_store or get_lexical_store()

        logger.info("Initialized RetrievalEngine")

    async def retrieve_hybrid(
        self,
        query: str,
        collection_name: str,
        embedding_model: str,
        knowledge_base_id: str,
        top_k: int = 5,
        dense_top_k: Optional[int] = None,
        lexical_top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        dense_weight: float = 0.6,
        lexical_weight: float = 0.4,
        bm25_match_mode: Optional[str] = None,
        bm25_min_should_match: Optional[int] = None,
        bm25_use_phrase: Optional[bool] = None,
        bm25_analyzer: Optional[str] = None,
        use_mmr: bool = False,
        mmr_diversity: float = 0.5,
    ) -> RetrievalResult:
        """
        Hybrid retrieval combining dense vectors (Qdrant) and BM25 (OpenSearch).
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        dense_limit = dense_top_k or max(top_k, 10)
        lexical_limit = lexical_top_k or max(top_k, 10)

        # Dense search
        dense_results = await self.vector_store.search(
            collection_name=collection_name,
            query_vector=await get_embedding_service(model=embedding_model).generate_embedding(query),
            limit=dense_limit,
            score_threshold=score_threshold,
            filter_conditions=filters,
            use_mmr=use_mmr,
            mmr_diversity=mmr_diversity,
        )
        dense_chunks = self._convert_search_results(dense_results)

        # Lexical search
        lexical_chunks: List[RetrievedChunk] = []
        try:
            lexical_hits = await self.lexical_store.search(
                query=query,
                knowledge_base_id=knowledge_base_id,
                limit=lexical_limit,
                filters=filters,
                match_mode=bm25_match_mode,
                min_should_match=bm25_min_should_match,
                use_phrase=bm25_use_phrase,
                analyzer=bm25_analyzer,
            )
            lexical_chunks = self._convert_lexical_results(lexical_hits)
        except Exception as e:
            logger.warning(f"Lexical search failed, using dense only: {e}")

        # Normalize and merge
        merged = self._merge_hybrid_results(
            dense_chunks=dense_chunks,
            lexical_chunks=lexical_chunks,
            dense_weight=dense_weight,
            lexical_weight=lexical_weight,
        )

        # Apply score threshold if provided (normalized 0..1 scale)
        if score_threshold is not None:
            merged = [c for c in merged if c.score >= score_threshold]

        merged = merged[:top_k]
        context = self._assemble_context(merged)

        return RetrievalResult(
            query=query,
            chunks=merged,
            total_found=len(merged),
            context=context,
        )

    async def retrieve(
        self,
        query: str,
        collection_name: str,
        embedding_model: str,
        top_k: int = 5,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        use_mmr: bool = False,
        mmr_diversity: float = 0.5,
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
            use_mmr: Enable MMR for diversity-aware search (default: False)
            mmr_diversity: MMR diversity parameter 0.0-1.0 (default: 0.5 balanced)

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
            embeddings_service = get_embedding_service(model=embedding_model)

            # 2. Generate query embedding
            logger.debug("Generating query embedding")
            query_embedding = await embeddings_service.generate_embedding(query)

            # 3. Search vector store
            logger.debug(f"Searching vector store (top_k={top_k}, mmr={use_mmr})")
            search_results = await self.vector_store.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=score_threshold,
                filter_conditions=filters,
                use_mmr=use_mmr,
                mmr_diversity=mmr_diversity,
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

    async def expand_windowed(
        self,
        *,
        collection_name: str,
        chunks: List[RetrievedChunk],
        window_size: int,
    ) -> List[RetrievedChunk]:
        """
        Expand retrieved chunks by including neighboring chunks within a window.

        Args:
            collection_name: Qdrant collection to scroll
            chunks: Base retrieved chunks
            window_size: Number of chunks to include on each side

        Returns:
            Expanded chunks ordered around original matches
        """
        if not chunks or window_size <= 0:
            return chunks

        indices_by_doc: Dict[str, set[int]] = {}
        for chunk in chunks:
            start = max(0, chunk.chunk_index - window_size)
            end = chunk.chunk_index + window_size
            for idx in range(start, end + 1):
                indices_by_doc.setdefault(chunk.document_id, set()).add(idx)

        expanded_map: Dict[str, RetrievedChunk] = {
            f"{chunk.document_id}:{chunk.chunk_index}": chunk for chunk in chunks
        }

        for document_id, indices in indices_by_doc.items():
            if not indices:
                continue
            results = await self.vector_store.scroll(
                collection_name=collection_name,
                filter_conditions={
                    "document_id": document_id,
                    "chunk_index": sorted(indices),
                },
                limit=len(indices),
            )
            extra_chunks = self._convert_search_results(results)
            for extra in extra_chunks:
                key = f"{extra.document_id}:{extra.chunk_index}"
                if key in expanded_map:
                    continue
                metadata = dict(extra.metadata or {})
                metadata.update(
                    {
                        "source_type": "window",
                        "window_radius": window_size,
                    }
                )
                expanded_map[key] = extra.model_copy(update={"score": 0.0, "metadata": metadata})

        ordered: List[RetrievedChunk] = []
        seen: set[str] = set()
        for chunk in chunks:
            start = max(0, chunk.chunk_index - window_size)
            end = chunk.chunk_index + window_size
            for idx in range(start, end + 1):
                key = f"{chunk.document_id}:{idx}"
                candidate = expanded_map.get(key)
                if not candidate or key in seen:
                    continue
                ordered.append(candidate)
                seen.add(key)

        return ordered

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
                    "source_type": "dense",
                    "dense_score_raw": float(result.score),
                },
            )

            chunks.append(chunk)

        return chunks

    def _convert_lexical_results(
        self,
        search_results: List[Dict[str, Any]],
    ) -> List[RetrievedChunk]:
        chunks: List[RetrievedChunk] = []
        for result in search_results:
            payload = result.get("source", {})
            chunks.append(
                RetrievedChunk(
                    text=payload.get("content", ""),
                    score=float(result.get("score", 0.0)),
                    document_id=payload.get("document_id", ""),
                    filename=payload.get("filename", "unknown"),
                    chunk_index=payload.get("chunk_index", 0),
                    metadata={
                        "knowledge_base_id": payload.get("knowledge_base_id"),
                        "file_type": payload.get("file_type"),
                        "char_count": payload.get("char_count"),
                        "word_count": payload.get("word_count"),
                        "source_type": "lexical",
                        "lexical_score_raw": float(result.get("score", 0.0)),
                    },
                )
            )
        return chunks

    @staticmethod
    def _normalize_scores(chunks: List[RetrievedChunk]) -> Dict[str, float]:
        if not chunks:
            return {}
        max_score = max(c.score for c in chunks) or 1.0
        norm = {}
        for c in chunks:
            key = f"{c.document_id}:{c.chunk_index}"
            norm[key] = c.score / max_score
        return norm

    def _merge_hybrid_results(
        self,
        *,
        dense_chunks: List[RetrievedChunk],
        lexical_chunks: List[RetrievedChunk],
        dense_weight: float,
        lexical_weight: float,
    ) -> List[RetrievedChunk]:
        total_weight = dense_weight + lexical_weight
        if total_weight > 0:
            dense_weight = dense_weight / total_weight
            lexical_weight = lexical_weight / total_weight

        dense_norm = self._normalize_scores(dense_chunks)
        lexical_norm = self._normalize_scores(lexical_chunks)

        dense_by_key = {f"{c.document_id}:{c.chunk_index}": c for c in dense_chunks}
        lexical_by_key = {f"{c.document_id}:{c.chunk_index}": c for c in lexical_chunks}

        combined: Dict[str, RetrievedChunk] = {}
        for key in set(dense_by_key.keys()).union(lexical_by_key.keys()):
            base = dense_by_key.get(key) or lexical_by_key.get(key)
            if base:
                combined[key] = base

        for key, chunk in combined.items():
            score = (dense_norm.get(key, 0.0) * dense_weight) + (
                lexical_norm.get(key, 0.0) * lexical_weight
            )
            dense_chunk = dense_by_key.get(key)
            lexical_chunk = lexical_by_key.get(key)
            metadata = dict(chunk.metadata or {})
            metadata.update(
                {
                    "source_type": "hybrid" if (dense_chunk and lexical_chunk) else metadata.get("source_type"),
                    "dense_score_raw": getattr(dense_chunk, "score", None),
                    "lexical_score_raw": getattr(lexical_chunk, "score", None),
                    "dense_score_norm": dense_norm.get(key, 0.0),
                    "lexical_score_norm": lexical_norm.get(key, 0.0),
                    "combined_score": score,
                    "dense_weight": dense_weight,
                    "lexical_weight": lexical_weight,
                }
            )
            combined[key] = chunk.model_copy(update={"score": score, "metadata": metadata})

        return sorted(combined.values(), key=lambda c: c.score, reverse=True)

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

        max_length = max_length if max_length is not None else settings.MAX_CONTEXT_CHARS
        if max_length is not None and max_length <= 0:
            max_length = None

        for i, chunk in enumerate(chunks):
            # Format chunk with metadata
            chunk_text = (
                f"[Source {i+1}: {chunk.filename}, chunk {chunk.chunk_index}]\n"
                f"{chunk.text}\n"
            )

            chunk_length = len(chunk_text)

            # Check if adding this chunk would exceed max length
            if max_length is not None and current_length + chunk_length > max_length:
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
