"""
Qdrant Vector Store Service.

Handles all interactions with Qdrant vector database including collection management,
vector operations, and similarity search.
"""
import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchAny,
    MatchValue,
    SearchRequest,
    NearestQuery,
    Mmr,
)
from qdrant_client.http import models as rest

from app.config import settings


logger = logging.getLogger(__name__)


class VectorStoreException(Exception):
    """Base exception for vector store operations."""
    pass


class CollectionNotFoundError(VectorStoreException):
    """Raised when collection doesn't exist."""
    pass


class SearchResult:
    """Represents a search result from vector store."""

    def __init__(
        self,
        id: str,
        score: float,
        payload: Dict[str, Any],
        vector: Optional[List[float]] = None,
    ):
        """
        Initialize search result.

        Args:
            id: Point ID
            score: Similarity score
            payload: Point payload/metadata
            vector: Optional vector data
        """
        self.id = id
        self.score = score
        self.payload = payload
        self.vector = vector

    def __repr__(self) -> str:
        return f"SearchResult(id={self.id}, score={self.score:.4f})"


class QdrantVectorStore:
    """
    Service for managing vector storage in Qdrant.

    Handles collection management, vector indexing, and similarity search.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        vector_size: Optional[int] = None,
    ):
        """
        Initialize Qdrant vector store.

        Args:
            url: Qdrant server URL (uses settings.QDRANT_URL if not provided)
            api_key: Optional API key for authentication
            vector_size: Vector dimension size (uses settings.QDRANT_VECTOR_SIZE if not provided)
        """
        self.url = url or settings.QDRANT_URL
        self.api_key = api_key or settings.QDRANT_API_KEY
        self.vector_size = vector_size or settings.QDRANT_VECTOR_SIZE

        self.client = AsyncQdrantClient(
            url=self.url,
            api_key=self.api_key,
        )

        logger.info(f"Initialized QdrantVectorStore at {self.url}")

    async def health_check(self) -> bool:
        """
        Check if Qdrant is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to list collections as a health check
            await self.client.get_collections()
            logger.info("Qdrant health check passed")
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    async def create_collection(
        self,
        collection_name: str,
        vector_size: Optional[int] = None,
        distance: Distance = Distance.COSINE,
    ) -> bool:
        """
        Create a new collection in Qdrant.

        Args:
            collection_name: Name of the collection
            vector_size: Vector dimension (uses default if not provided)
            distance: Distance metric (default: COSINE for RAG)

        Returns:
            True if created successfully

        Raises:
            VectorStoreException: If creation fails
        """
        try:
            size = vector_size or self.vector_size

            # Check if collection already exists
            collections = await self.client.get_collections()
            existing = [c.name for c in collections.collections]

            if collection_name in existing:
                logger.info(f"Collection '{collection_name}' already exists")
                return True

            # Create collection
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=size,
                    distance=distance,
                ),
            )

            logger.info(
                f"Created collection '{collection_name}' "
                f"(size={size}, distance={distance})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to create collection '{collection_name}': {e}")
            raise VectorStoreException(f"Failed to create collection: {e}") from e

    async def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection from Qdrant.

        Args:
            collection_name: Name of collection to delete

        Returns:
            True if deleted successfully
        """
        try:
            await self.client.delete_collection(collection_name=collection_name)
            logger.info(f"Deleted collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to delete collection '{collection_name}': {e}")
            return False

    async def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists (including aliases).

        Args:
            collection_name: Name of collection or alias to check

        Returns:
            True if collection or alias exists
        """
        try:
            # Check actual collections
            collections = await self.client.get_collections()
            existing = [c.name for c in collections.collections]
            if collection_name in existing:
                return True

            # Check aliases
            try:
                aliases_response = await self.client.get_collection_aliases(collection_name)
                # If we get here without exception, the alias exists
                return True
            except Exception:
                # Alias doesn't exist, which is fine
                return False

        except Exception as e:
            logger.error(f"Failed to check collection existence: {e}")
            return False

    async def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
        batch_size: Optional[int] = None,
    ) -> List[str]:
        """
        Insert vectors with metadata into a collection.

        Args:
            collection_name: Name of the collection
            vectors: List of vector embeddings
            payloads: List of metadata dictionaries (one per vector)
            ids: Optional list of IDs (generated if not provided)

        Returns:
            List of inserted point IDs

        Raises:
            CollectionNotFoundError: If collection doesn't exist
            VectorStoreException: If insert fails
        """
        if len(vectors) != len(payloads):
            raise ValueError("Number of vectors must match number of payloads")

        try:
            # Check collection exists
            if not await self.collection_exists(collection_name):
                raise CollectionNotFoundError(
                    f"Collection '{collection_name}' does not exist"
                )

            # Generate IDs if not provided
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in range(len(vectors))]
            elif len(ids) != len(vectors):
                raise ValueError("Number of IDs must match number of vectors")

            # Create points
            points = [
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
                for point_id, vector, payload in zip(ids, vectors, payloads)
            ]

            # Log vector size diagnostics
            try:
                sample_dim = len(vectors[0]) if vectors else 0
                collection_info = await self.client.get_collection(collection_name)
                collection_dim = None
                try:
                    collection_dim = collection_info.config.params.vectors.size
                except Exception:
                    collection_dim = None
                logger.info(
                    "Upserting %s vectors into '%s' (sample_dim=%s, collection_dim=%s)",
                    len(points),
                    collection_name,
                    sample_dim,
                    collection_dim,
                )
            except Exception as e:
                logger.warning("Failed to read collection vector size: %s", e)

            # Upsert points (batched)
            effective_batch_size = batch_size or len(points)
            if effective_batch_size <= 0:
                effective_batch_size = len(points)

            for start in range(0, len(points), effective_batch_size):
                batch = points[start:start + effective_batch_size]
                await self.client.upsert(
                    collection_name=collection_name,
                    points=batch,
                )

            logger.info(
                f"Inserted {len(points)} vectors into collection '{collection_name}'"
            )
            return ids

        except CollectionNotFoundError:
            raise
        except Exception as e:
            logger.error(
                "Failed to insert vectors: %s (type=%s, args=%s)",
                e,
                type(e).__name__,
                getattr(e, "args", None),
            )
            logger.exception("Vector insert exception")
            raise VectorStoreException(f"Failed to insert vectors: {e}") from e

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
        use_mmr: bool = False,
        mmr_diversity: float = 0.5,
        mmr_candidates_limit: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        Search for similar vectors in a collection.

        Args:
            collection_name: Name of the collection to search
            query_vector: Query vector
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score (optional)
            filter_conditions: Optional metadata filters
            use_mmr: Enable MMR (Maximal Marginal Relevance) for diversity-aware search
            mmr_diversity: MMR diversity parameter (0.0=pure relevance, 1.0=pure diversity)
            mmr_candidates_limit: Number of candidates to pre-select for MMR (defaults to limit * 10)

        Returns:
            List of SearchResult objects

        Raises:
            CollectionNotFoundError: If collection doesn't exist
            VectorStoreException: If search fails
        """
        try:
            # Check collection exists
            if not await self.collection_exists(collection_name):
                raise CollectionNotFoundError(
                    f"Collection '{collection_name}' does not exist"
                )

            # Build filter if provided
            query_filter = None
            if filter_conditions:
                query_filter = self._build_filter(filter_conditions)

            # Build query (with MMR if enabled)
            if use_mmr:
                # MMR-enabled query for diversity-aware search
                candidates = mmr_candidates_limit or (limit * 10)
                query = NearestQuery(
                    nearest=query_vector,
                    mmr=Mmr(
                        diversity=mmr_diversity,
                        candidates_limit=candidates,
                    ),
                )
                logger.debug(
                    f"Using MMR search (diversity={mmr_diversity}, "
                    f"candidates={candidates})"
                )
            else:
                # Standard vector search
                query = query_vector

            # Perform search
            query_response = await self.client.query_points(
                collection_name=collection_name,
                query=query,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter,
            )
            search_result = query_response.points

            # Convert to SearchResult objects
            results = [
                SearchResult(
                    id=str(hit.id),
                    score=hit.score,
                    payload=hit.payload or {},
                    vector=hit.vector,
                )
                for hit in search_result
            ]

            logger.info(
                f"Search in '{collection_name}' returned {len(results)} results "
                f"(limit={limit})"
            )
            return results

        except CollectionNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise VectorStoreException(f"Search failed: {e}") from e

    async def delete_by_document_id(
        self,
        collection_name: str,
        document_id: str,
    ) -> int:
        """
        Delete all vectors associated with a document.

        Args:
            collection_name: Name of the collection
            document_id: Document ID to delete vectors for

        Returns:
            Number of vectors deleted

        Raises:
            VectorStoreException: If deletion fails
        """
        try:
            # Build filter for document_id
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            )

            # Count points to be deleted (Qdrant delete doesn't return count)
            count_result = await self.client.count(
                collection_name=collection_name,
                count_filter=filter_condition,
                exact=True,
            )

            # Delete points matching filter
            await self.client.delete(
                collection_name=collection_name,
                points_selector=rest.FilterSelector(filter=filter_condition),
            )

            # Extract count from result
            # Note: Qdrant returns operation_id on success
            logger.info(
                f"Deleted vectors for document '{document_id}' "
                f"from collection '{collection_name}'"
            )

            return count_result.count

        except Exception as e:
            logger.error(f"Failed to delete vectors for document '{document_id}': {e}")
            raise VectorStoreException(f"Failed to delete vectors: {e}") from e

    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get information about a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary with collection information

        Raises:
            CollectionNotFoundError: If collection doesn't exist
        """
        try:
            # Use count() which is more reliable than get_collection()
            # due to version compatibility issues
            exists = await self.collection_exists(collection_name)
            if not exists:
                raise CollectionNotFoundError(
                    f"Collection '{collection_name}' not found"
                )

            # Get basic info
            count = await self.client.count(
                collection_name=collection_name,
                exact=True,
            )

            return {
                "name": collection_name,
                "points_count": count.count,
                "exists": True,
            }

        except CollectionNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise CollectionNotFoundError(
                f"Collection '{collection_name}' not found"
            ) from e

    def _build_filter(self, conditions: Dict[str, Any]) -> Filter:
        """
        Build a Qdrant filter from conditions dictionary.

        Supports:
        - Simple match: {"field": "value"}
        - Range conditions: {"field": {"gte": 5, "lte": 10}}

        Args:
            conditions: Dictionary of field->value conditions

        Returns:
            Qdrant Filter object
        """
        from qdrant_client.models import Range

        must_conditions = []

        for key, value in conditions.items():
            # Check if value is a range condition (dict with gte/lte/gt/lt)
            if isinstance(value, dict) and any(k in value for k in ["gte", "lte", "gt", "lt"]):
                # Range condition
                must_conditions.append(
                    FieldCondition(
                        key=key,
                        range=Range(
                            gte=value.get("gte"),
                            lte=value.get("lte"),
                            gt=value.get("gt"),
                            lt=value.get("lt"),
                        ),
                    )
                )
            else:
                if isinstance(value, list):
                    must_conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchAny(any=value),
                        )
                    )
                    continue
                # Simple match condition
                must_conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value),
                    )
                )

        return Filter(must=must_conditions)

    async def close(self):
        """Close the Qdrant client."""
        await self.client.close()
        logger.info("QdrantVectorStore closed")


# Singleton instance
_vector_store: Optional[QdrantVectorStore] = None


def get_vector_store() -> QdrantVectorStore:
    """
    Get or create singleton instance of QdrantVectorStore.

    Returns:
        QdrantVectorStore instance
    """
    global _vector_store

    if _vector_store is None:
        _vector_store = QdrantVectorStore()

    return _vector_store


async def close_vector_store():
    """Close the singleton vector store."""
    global _vector_store

    if _vector_store is not None:
        await _vector_store.close()
        _vector_store = None
