"""
OpenSearch Lexical Store Service.

Provides BM25-based lexical search over chunk text.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from opensearchpy import AsyncOpenSearch, OpenSearchException
from opensearchpy.helpers import async_bulk

from app.config import settings

logger = logging.getLogger(__name__)


class LexicalStoreException(Exception):
    """Base exception for lexical store operations."""

    pass


class OpenSearchStore:
    """Service for indexing and searching chunks in OpenSearch."""

    def __init__(
        self,
        url: Optional[str] = None,
        index_name: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_certs: Optional[bool] = None,
    ):
        self.url = url or settings.OPENSEARCH_URL
        self.index_name = index_name or settings.OPENSEARCH_INDEX
        self.username = username if username is not None else settings.OPENSEARCH_USERNAME
        self.password = password if password is not None else settings.OPENSEARCH_PASSWORD
        self.verify_certs = (
            verify_certs if verify_certs is not None else settings.OPENSEARCH_VERIFY_CERTS
        )

        http_auth = None
        if self.username and self.password:
            http_auth = (self.username, self.password)

        self.client = AsyncOpenSearch(
            hosts=[self.url],
            http_auth=http_auth,
            verify_certs=self.verify_certs,
        )

        logger.info(f"Initialized OpenSearchStore at {self.url} (index={self.index_name})")

    async def close(self) -> None:
        await self.client.close()

    async def ensure_index(self) -> None:
        """Ensure the OpenSearch index exists with correct mapping."""
        try:
            exists = await self.client.indices.exists(index=self.index_name)
            if exists:
                return

            index_body = {
                "settings": {
                    "analysis": {
                        "filter": {
                            "russian_stop": {"type": "stop", "stopwords": "_russian_"},
                            "russian_stemmer": {"type": "stemmer", "language": "russian"},
                            "english_stop": {"type": "stop", "stopwords": "_english_"},
                            "english_stemmer": {"type": "stemmer", "language": "english"},
                        },
                        "analyzer": {
                            "kb_analyzer": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": [
                                    "lowercase",
                                    "russian_stop",
                                    "russian_stemmer",
                                    "english_stop",
                                    "english_stemmer",
                                ],
                            },
                            "kb_analyzer_ru": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": [
                                    "lowercase",
                                    "russian_stop",
                                    "russian_stemmer",
                                ],
                            },
                            "kb_analyzer_en": {
                                "type": "custom",
                                "tokenizer": "standard",
                                "filter": [
                                    "lowercase",
                                    "english_stop",
                                    "english_stemmer",
                                ],
                            },
                        },
                    }
                },
                "mappings": {
                    "properties": {
                        "knowledge_base_id": {"type": "keyword"},
                        "document_id": {"type": "keyword"},
                        "chunk_index": {"type": "integer"},
                        "filename": {"type": "keyword"},
                        "file_type": {"type": "keyword"},
                        "content": {"type": "text", "analyzer": "kb_analyzer"},
                        "char_count": {"type": "integer"},
                        "word_count": {"type": "integer"},
                        "indexed_at": {"type": "date"},
                    }
                },
            }

            await self.client.indices.create(index=self.index_name, body=index_body)
            logger.info(f"Created OpenSearch index '{self.index_name}'")

        except OpenSearchException as e:
            logger.error(f"Failed to ensure OpenSearch index: {e}")
            raise LexicalStoreException(f"OpenSearch index error: {e}") from e

    async def index_chunks(
        self,
        *,
        knowledge_base_id: str,
        document_id: str,
        filename: str,
        file_type: str,
        chunks: Iterable[Dict[str, Any]],
        batch_size: int = 256,
    ) -> int:
        """Index document chunks in OpenSearch."""
        await self.ensure_index()

        actions = []
        for chunk in chunks:
            chunk_index = int(chunk["chunk_index"])
            chunk_id = f"{document_id}:{chunk_index}"
            actions.append(
                {
                    "_op_type": "index",
                    "_index": self.index_name,
                    "_id": chunk_id,
                    "knowledge_base_id": knowledge_base_id,
                    "document_id": document_id,
                    "chunk_index": chunk_index,
                    "filename": filename,
                    "file_type": file_type,
                    "content": chunk["text"],
                    "char_count": chunk.get("char_count"),
                    "word_count": chunk.get("word_count"),
                    "indexed_at": datetime.utcnow().isoformat(),
                }
            )

        if not actions:
            return 0

        try:
            success, _ = await async_bulk(
                self.client,
                actions,
                chunk_size=batch_size,
                request_timeout=60,
            )
            logger.info(
                f"Indexed {success} chunks in OpenSearch (doc={document_id}, kb={knowledge_base_id})"
            )
            return success
        except OpenSearchException as e:
            logger.error(f"OpenSearch bulk index failed: {e}")
            raise LexicalStoreException(f"OpenSearch bulk index failed: {e}") from e

    async def search(
        self,
        query: str,
        *,
        knowledge_base_id: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        match_mode: Optional[str] = None,
        min_should_match: Optional[int] = None,
        use_phrase: Optional[bool] = None,
        analyzer: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search chunks lexically with BM25."""
        await self.ensure_index()

        filter_clauses = [{"term": {"knowledge_base_id": knowledge_base_id}}]
        if filters:
            document_id = filters.get("document_id")
            if document_id:
                if isinstance(document_id, list):
                    filter_clauses.append({"terms": {"document_id": document_id}})
                else:
                    filter_clauses.append({"term": {"document_id": document_id}})
            chunk_index = filters.get("chunk_index")
            if isinstance(chunk_index, dict):
                filter_clauses.append({"range": {"chunk_index": chunk_index}})

        analyzer_map = {
            "mixed": "kb_analyzer",
            "ru": "kb_analyzer_ru",
            "en": "kb_analyzer_en",
        }
        analyzer_name = analyzer_map.get(str(analyzer).lower()) if analyzer else None

        operator = "and" if (match_mode or "").lower() == "strict" else "or"
        msm_value: Optional[str] = None
        if min_should_match is not None and min_should_match > 0:
            msm_value = f"{min_should_match}%"
        elif (match_mode or "").lower() == "balanced":
            msm_value = "50%"

        match_body: Dict[str, Any] = {"query": query, "operator": operator}
        if msm_value:
            match_body["minimum_should_match"] = msm_value
        if analyzer_name:
            match_body["analyzer"] = analyzer_name

        should_clauses = [
            {"match": {"content": match_body}},
        ]
        if use_phrase is not False:
            phrase_body: Dict[str, Any] = {"query": query}
            if analyzer_name:
                phrase_body["analyzer"] = analyzer_name
            should_clauses.append({"match_phrase": {"content": phrase_body}})

        body = {
            "size": limit,
            "query": {
                "bool": {
                    "should": should_clauses,
                    "minimum_should_match": 1,
                    "filter": filter_clauses,
                }
            },
        }

        try:
            response = await self.client.search(index=self.index_name, body=body)
            hits = response.get("hits", {}).get("hits", [])
            return [
                {
                    "score": hit.get("_score", 0.0),
                    "source": hit.get("_source", {}),
                }
                for hit in hits
            ]
        except OpenSearchException as e:
            if analyzer_name:
                logger.warning(
                    f"OpenSearch query failed with analyzer '{analyzer_name}', retrying without analyzer: {e}"
                )
                try:
                    match_body.pop("analyzer", None)
                    for clause in should_clauses:
                        if "match_phrase" in clause:
                            clause["match_phrase"]["content"].pop("analyzer", None)
                    response = await self.client.search(index=self.index_name, body=body)
                    hits = response.get("hits", {}).get("hits", [])
                    return [
                        {
                            "score": hit.get("_score", 0.0),
                            "source": hit.get("_source", {}),
                        }
                        for hit in hits
                    ]
                except OpenSearchException as retry_err:
                    logger.error(f"OpenSearch query failed after analyzer retry: {retry_err}")
                    raise LexicalStoreException(
                        f"OpenSearch query failed: {retry_err}"
                    ) from retry_err
            logger.error(f"OpenSearch query failed: {e}")
            raise LexicalStoreException(f"OpenSearch query failed: {e}") from e

    async def delete_by_document_id(self, document_id: str) -> None:
        await self.ensure_index()
        try:
            await self.client.delete_by_query(
                index=self.index_name,
                body={"query": {"term": {"document_id": document_id}}},
                refresh=True,
            )
            logger.info(f"Deleted OpenSearch chunks for document {document_id}")
        except OpenSearchException as e:
            logger.error(f"Failed to delete document in OpenSearch: {e}")
            raise LexicalStoreException(f"OpenSearch delete failed: {e}") from e

    async def delete_by_kb_id(self, knowledge_base_id: str) -> None:
        await self.ensure_index()
        try:
            await self.client.delete_by_query(
                index=self.index_name,
                body={"query": {"term": {"knowledge_base_id": knowledge_base_id}}},
                refresh=True,
            )
            logger.info(f"Deleted OpenSearch chunks for KB {knowledge_base_id}")
        except OpenSearchException as e:
            logger.error(f"Failed to delete KB in OpenSearch: {e}")
            raise LexicalStoreException(f"OpenSearch delete failed: {e}") from e


_lexical_store: Optional[OpenSearchStore] = None


def get_lexical_store() -> OpenSearchStore:
    global _lexical_store
    if _lexical_store is None:
        _lexical_store = OpenSearchStore()
    return _lexical_store
