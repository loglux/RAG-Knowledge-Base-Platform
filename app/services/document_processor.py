"""
Document Processing Service.

Handles the complete pipeline of document ingestion:
1. Load document content
2. Split into chunks
3. Generate embeddings
4. Store in vector database
5. Update document status
"""
import logging
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, KnowledgeBase
from app.models.enums import DocumentStatus
from app.core.embeddings_factory import create_embedding_service
from app.core.embeddings_base import BaseEmbeddingService
from app.core.vector_store import (
    get_vector_store,
    QdrantVectorStore,
    VectorStoreException,
)
from app.core.lexical_store import get_lexical_store, OpenSearchStore
from app.services.chunking import get_chunking_service, ChunkingService, Chunk


logger = logging.getLogger(__name__)


class DocumentProcessingError(Exception):
    """Base exception for document processing errors."""
    pass


class DocumentProcessor:
    """
    Service for processing documents into vectorized chunks.

    Orchestrates the entire pipeline from document loading to vector storage.
    """

    def __init__(
        self,
        vector_store: Optional[QdrantVectorStore] = None,
        lexical_store: Optional[OpenSearchStore] = None,
        chunking_service: Optional[ChunkingService] = None,
    ):
        """
        Initialize document processor.

        Args:
            vector_store: Vector store for indexing
            chunking_service: Service for text chunking

        Note:
            Embedding service is created per-document based on KB's embedding model.
        """
        self.vector_store = vector_store or get_vector_store()
        self.lexical_store = lexical_store or get_lexical_store()
        self.chunking = chunking_service or get_chunking_service()

        logger.info("Initialized DocumentProcessor")

    async def process_document(
        self,
        document_id: UUID,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Process a document through the complete ingestion pipeline.

        Args:
            document_id: ID of document to process
            db: Database session

        Returns:
            Dictionary with processing results

        Raises:
            DocumentProcessingError: If processing fails
        """
        logger.info(f"Starting processing for document {document_id}")

        try:
            # 1. Load document from database
            document = await self._load_document(document_id, db)

            # 2. Get knowledge base info
            kb = await self._load_knowledge_base(document.knowledge_base_id, db)

            # 3. Create embedding service for this KB's model
            logger.info(f"Creating embedding service for model: {kb.embedding_model}")
            embeddings_service = create_embedding_service(model=kb.embedding_model)

            # 4. Update status to processing
            await self._update_document_status(
                document,
                DocumentStatus.PROCESSING,
                db,
                embeddings_status=DocumentStatus.PROCESSING,
                bm25_status=DocumentStatus.PENDING,
            )

            # 5. Ensure collection exists
            await self._ensure_collection_exists(kb)

            # 6. Create chunking service with KB-specific settings
            from app.services.chunking import get_chunking_service
            chunking_service = get_chunking_service(
                chunk_size=kb.chunk_size,
                chunk_overlap=kb.chunk_overlap,
            )

            # 7. Split document into chunks
            logger.info(
                f"Chunking document content ({len(document.content)} chars) "
                f"with chunk_size={kb.chunk_size}, overlap={kb.chunk_overlap}"
            )
            chunks = chunking_service.chunk_text(
                text=document.content,
                metadata={
                    "document_id": str(document.id),
                    "document_filename": document.filename,
                    "knowledge_base_id": str(kb.id),
                },
            )

            if not chunks:
                raise DocumentProcessingError("No chunks generated from document")

            chunk_sizes = [len(chunk.content) for chunk in chunks]
            logger.info(
                "Generated %s chunks (min=%s, max=%s, avg=%.0f chars)",
                len(chunks),
                min(chunk_sizes),
                max(chunk_sizes),
                sum(chunk_sizes) / len(chunk_sizes),
            )

            # 8. Generate embeddings for all chunks
            logger.info(
                "Generating embeddings for %s chunks using %s",
                len(chunks),
                kb.embedding_model,
            )
            chunk_texts = [chunk.content for chunk in chunks]
            embedding_results = await embeddings_service.generate_embeddings(
                texts=chunk_texts,
                batch_size=100,
            )

            logger.info(f"Generated {len(embedding_results)} embeddings")

            # 9. Prepare vectors and payloads for Qdrant
            vectors = [result.embedding for result in embedding_results]
            payloads = self._build_payloads(chunks, document, kb)

            # 10. Store vectors in Qdrant
            logger.info(f"Storing {len(vectors)} vectors in collection '{kb.collection_name}'")
            vector_ids = await self.vector_store.insert_vectors(
                collection_name=kb.collection_name,
                vectors=vectors,
                payloads=payloads,
                batch_size=kb.upsert_batch_size,
            )

            # Mark embeddings as completed once Qdrant insert succeeds
            await self._update_index_statuses(
                document,
                db,
                embeddings_status=DocumentStatus.COMPLETED,
            )

            # 11. Index chunks in OpenSearch (lexical)
            try:
                await self._update_index_statuses(
                    document,
                    db,
                    bm25_status=DocumentStatus.PROCESSING,
                )
                lexical_chunks = self._build_lexical_chunks(chunks)
                await self.lexical_store.index_chunks(
                    knowledge_base_id=str(kb.id),
                    document_id=str(document.id),
                    filename=document.filename,
                    file_type=str(document.file_type),
                    chunks=lexical_chunks,
                    batch_size=kb.upsert_batch_size,
                )
                await self._update_index_statuses(
                    document,
                    db,
                    bm25_status=DocumentStatus.COMPLETED,
                )
            except Exception as e:
                logger.warning(f"OpenSearch indexing failed: {e}")
                await self._update_index_statuses(
                    document,
                    db,
                    bm25_status=DocumentStatus.FAILED,
                )

            # 12. Update document status to completed
            document.chunk_count = len(chunks)
            document.processed_at = datetime.utcnow()
            await self._update_document_status(
                document, DocumentStatus.COMPLETED, db
            )

            # 13. Recalculate KB statistics (prevents desync from incremental updates)
            total_chunks = await db.scalar(
                select(func.coalesce(func.sum(Document.chunk_count), 0)).where(
                    Document.knowledge_base_id == kb.id,
                    Document.is_deleted == False
                )
            )
            kb.total_chunks = total_chunks or 0
            await db.commit()

            logger.info(f"Successfully processed document {document_id}")

            return {
                "document_id": str(document.id),
                "status": "completed",
                "chunks_count": len(chunks),
                "vectors_stored": len(vector_ids),
                "collection_name": kb.collection_name,
            }

        except Exception as e:
            logger.error(f"Failed to process document {document_id}: {e}")

            # Update document status to failed
            try:
                document = await self._load_document(document_id, db)
                document.error_message = str(e)
                await self._update_document_status(
                    document,
                    DocumentStatus.FAILED,
                    db,
                    embeddings_status=DocumentStatus.FAILED,
                    bm25_status=DocumentStatus.FAILED,
                )
            except Exception as update_error:
                logger.error(f"Failed to update document status: {update_error}")

            raise DocumentProcessingError(
                f"Document processing failed: {e}"
            ) from e

    async def reprocess_document(
        self,
        document_id: UUID,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Reprocess an existing document.

        Deletes old vectors and processes the document again.

        Args:
            document_id: ID of document to reprocess
            db: Database session

        Returns:
            Dictionary with processing results
        """
        logger.info(f"Reprocessing document {document_id}")

        try:
            # Load document and KB
            document = await self._load_document(document_id, db)
            kb = await self._load_knowledge_base(document.knowledge_base_id, db)

            # Delete old vectors
            logger.info(f"Deleting old vectors for document {document_id}")
            try:
                await self.vector_store.delete_by_document_id(
                    collection_name=kb.collection_name,
                    document_id=str(document_id),
                )
            except Exception as e:
                logger.warning(f"Failed to delete old vectors: {e}")

            try:
                await self.lexical_store.delete_by_document_id(str(document_id))
            except Exception as e:
                logger.warning(f"Failed to delete OpenSearch chunks: {e}")

            # Process document
            return await self.process_document(document_id, db)

        except Exception as e:
            logger.error(f"Failed to reprocess document {document_id}: {e}")
            raise DocumentProcessingError(
                f"Document reprocessing failed: {e}"
            ) from e

    async def delete_document_vectors(
        self,
        document_id: UUID,
        collection_name: str,
    ):
        """
        Delete all vectors for a document from the vector store.

        Args:
            document_id: Document ID
            collection_name: Collection name
        """
        try:
            logger.info(f"Deleting vectors for document {document_id}")
            await self.vector_store.delete_by_document_id(
                collection_name=collection_name,
                document_id=str(document_id),
            )
            logger.info(f"Successfully deleted vectors for document {document_id}")

            await self.lexical_store.delete_by_document_id(str(document_id))
            logger.info(f"Successfully deleted OpenSearch chunks for document {document_id}")

        except Exception as e:
            logger.error(f"Failed to delete vectors for document {document_id}: {e}")
            raise DocumentProcessingError(
                f"Failed to delete document vectors: {e}"
            ) from e

    async def _load_document(
        self,
        document_id: UUID,
        db: AsyncSession,
    ) -> Document:
        """Load document from database."""
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            raise DocumentProcessingError(f"Document {document_id} not found")

        return document

    async def _load_knowledge_base(
        self,
        kb_id: UUID,
        db: AsyncSession,
    ) -> KnowledgeBase:
        """Load knowledge base from database."""
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        kb = result.scalar_one_or_none()

        if not kb:
            raise DocumentProcessingError(f"Knowledge base {kb_id} not found")

        return kb

    async def _update_document_status(
        self,
        document: Document,
        status: DocumentStatus,
        db: AsyncSession,
        embeddings_status: Optional[DocumentStatus] = None,
        bm25_status: Optional[DocumentStatus] = None,
    ):
        """Update document status in database."""
        document.status = status
        if embeddings_status is not None:
            document.embeddings_status = embeddings_status
        if bm25_status is not None:
            document.bm25_status = bm25_status
        db.add(document)
        await db.commit()
        await db.refresh(document)

        logger.info(f"Updated document {document.id} status to {status.value}")

    async def _update_index_statuses(
        self,
        document: Document,
        db: AsyncSession,
        embeddings_status: Optional[DocumentStatus] = None,
        bm25_status: Optional[DocumentStatus] = None,
    ):
        """Update per-index statuses without changing overall status."""
        if embeddings_status is not None:
            document.embeddings_status = embeddings_status
        if bm25_status is not None:
            document.bm25_status = bm25_status
        db.add(document)
        await db.commit()
        await db.refresh(document)

    async def _ensure_collection_exists(self, kb: KnowledgeBase):
        """Ensure Qdrant collection exists for the knowledge base."""
        exists = await self.vector_store.collection_exists(kb.collection_name)

        if not exists:
            logger.info(
                f"Creating collection '{kb.collection_name}' "
                f"with vector_size={kb.embedding_dimension} for model '{kb.embedding_model}'"
            )
            await self.vector_store.create_collection(
                collection_name=kb.collection_name,
                vector_size=kb.embedding_dimension,  # Use dimension from KB model config
            )

    def _build_payloads(
        self,
        chunks: List[Chunk],
        document: Document,
        kb: KnowledgeBase,
    ) -> List[Dict[str, Any]]:
        """
        Build metadata payloads for vector storage.

        Args:
            chunks: List of text chunks
            document: Document model
            kb: Knowledge base model

        Returns:
            List of payload dictionaries
        """
        payloads = []

        for chunk in chunks:
            payload = {
                # Core identifiers
                "document_id": str(document.id),
                "knowledge_base_id": str(kb.id),
                "chunk_index": chunk.index,

                # Content
                "text": chunk.content,
                "char_count": chunk.char_count,
                "word_count": chunk.word_count,

                # Position in original document
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,

                # Document metadata
                "filename": document.filename,
                "file_type": document.file_type,

                # Timestamps
                "indexed_at": datetime.utcnow().isoformat(),
            }

            payloads.append(payload)

        return payloads

    @staticmethod
    def _build_lexical_chunks(chunks: List[Chunk]) -> List[Dict[str, Any]]:
        """Build OpenSearch chunk documents."""
        lexical_chunks = []
        for chunk in chunks:
            lexical_chunks.append(
                {
                    "chunk_index": chunk.index,
                    "text": chunk.content,
                    "char_count": chunk.char_count,
                    "word_count": chunk.word_count,
                }
            )
        return lexical_chunks


# Dependency injection
def get_document_processor() -> DocumentProcessor:
    """
    Get document processor instance.

    Returns:
        DocumentProcessor instance
    """
    return DocumentProcessor()
