"""Knowledge Base CRUD endpoints."""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.database import KnowledgeBase as KnowledgeBaseModel, AppSettings as AppSettingsModel, Document as DocumentModel
from app.models.enums import DocumentStatus
from app.models.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse,
    KnowledgeBaseList,
)
from app.dependencies import get_current_user_id
from app.core.embeddings_base import EMBEDDING_MODELS
from app.core.vector_store import get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter()


def kb_id_to_collection_name(kb_id: UUID) -> str:
    """
    Convert KB ID to Qdrant collection name.

    This ensures deterministic mapping between KB and its Qdrant collection.

    Args:
        kb_id: Knowledge base UUID

    Returns:
        Collection name in format: kb_{uuid_without_dashes}
    """
    return f"kb_{str(kb_id).replace('-', '')}"


@router.post("/", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    kb: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    Create a new knowledge base.

    Creates a new knowledge base with specified configuration.
    Collection name is derived from KB ID for deterministic mapping.
    """
    # Validate embedding model
    if kb.embedding_model not in EMBEDDING_MODELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown embedding model: {kb.embedding_model}. "
                   f"Available models: {', '.join(EMBEDDING_MODELS.keys())}"
        )

    # Get embedding model configuration
    model_config = EMBEDDING_MODELS[kb.embedding_model]

    # Generate KB ID and collection name (deterministic)
    import uuid
    kb_id = uuid.uuid4()
    collection_name = kb_id_to_collection_name(kb_id)

    # Resolve KB defaults from app settings if not provided
    default_chunk_size = 1000
    default_chunk_overlap = 200
    default_upsert_batch_size = 256

    settings_result = await db.execute(select(AppSettingsModel).order_by(AppSettingsModel.id).limit(1))
    settings_row = settings_result.scalar_one_or_none()
    if settings_row:
        if settings_row.kb_chunk_size is not None:
            default_chunk_size = settings_row.kb_chunk_size
        if settings_row.kb_chunk_overlap is not None:
            default_chunk_overlap = settings_row.kb_chunk_overlap
        if settings_row.kb_upsert_batch_size is not None:
            default_upsert_batch_size = settings_row.kb_upsert_batch_size

    # Create KB
    kb_model = KnowledgeBaseModel(
        id=kb_id,
        name=kb.name,
        description=kb.description,
        collection_name=collection_name,
        embedding_model=kb.embedding_model,
        embedding_provider=model_config.provider.value,
        embedding_dimension=model_config.dimension,
        chunk_size=kb.chunk_size if kb.chunk_size is not None else default_chunk_size,
        chunk_overlap=kb.chunk_overlap if kb.chunk_overlap is not None else default_chunk_overlap,
        chunking_strategy=kb.chunking_strategy,
        upsert_batch_size=kb.upsert_batch_size if kb.upsert_batch_size is not None else default_upsert_batch_size,
        user_id=user_id,
    )

    db.add(kb_model)
    await db.commit()
    await db.refresh(kb_model)

    # Create Qdrant collection
    try:
        vector_store = get_vector_store()
        logger.info(
            f"Creating Qdrant collection '{collection_name}' "
            f"for KB '{kb.name}' (dimension={model_config.dimension})"
        )

        await vector_store.create_collection(
            collection_name=collection_name,
            vector_size=model_config.dimension,
        )

        logger.info(f"Successfully created Qdrant collection '{collection_name}'")

    except Exception as e:
        # Rollback: delete KB from database if Qdrant collection creation fails
        logger.error(
            f"Failed to create Qdrant collection '{collection_name}': {e}. "
            f"Rolling back KB creation."
        )
        await db.delete(kb_model)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create vector store collection: {str(e)}"
        )

    return kb_model


@router.get("/", response_model=KnowledgeBaseList)
async def list_knowledge_bases(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    List all knowledge bases.

    Returns paginated list of knowledge bases.
    In MVP: returns all KBs (no user filtering).
    Future: filter by user_id when auth is implemented.
    """
    # Build query
    query = select(KnowledgeBaseModel).where(KnowledgeBaseModel.is_deleted == False)

    # Future: Add user filter when auth is implemented
    # if user_id:
    #     query = query.where(KnowledgeBaseModel.user_id == user_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute
    result = await db.execute(query)
    items = result.scalars().all()

    return KnowledgeBaseList(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get("/deleted", response_model=KnowledgeBaseList)
async def list_deleted_knowledge_bases(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    List deleted knowledge bases (trash).
    """
    query = select(KnowledgeBaseModel).where(KnowledgeBaseModel.is_deleted == True)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return KnowledgeBaseList(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    Get knowledge base by ID.

    Returns detailed information about a specific knowledge base.
    """
    query = select(KnowledgeBaseModel).where(
        KnowledgeBaseModel.id == kb_id,
        KnowledgeBaseModel.is_deleted == False,
    )

    result = await db.execute(query)
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge base {kb_id} not found"
        )

    # Future: Check user ownership when auth is implemented

    return kb


@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: UUID,
    kb_update: KnowledgeBaseUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    Update knowledge base.

    Updates knowledge base configuration.
    Note: Changing chunking config won't re-process existing documents.
    """
    # Get existing KB
    query = select(KnowledgeBaseModel).where(
        KnowledgeBaseModel.id == kb_id,
        KnowledgeBaseModel.is_deleted == False,
    )
    result = await db.execute(query)
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge base {kb_id} not found"
        )

    # Future: Check user ownership

    # Update fields
    update_data = kb_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(kb, field, value)

    await db.commit()
    await db.refresh(kb)

    return kb


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    Delete knowledge base (soft delete).

    Marks knowledge base and all associated documents as deleted.
    Deletes Qdrant collection and all vectors.
    """
    from app.models.database import Document as DocumentModel
    from app.core.vector_store import get_vector_store
    from app.core.lexical_store import get_lexical_store

    # Get existing KB
    query = select(KnowledgeBaseModel).where(
        KnowledgeBaseModel.id == kb_id,
        KnowledgeBaseModel.is_deleted == False,
    )
    result = await db.execute(query)
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge base {kb_id} not found"
        )

    # Future: Check user ownership

    logger.info(f"Deleting KB '{kb.name}' (id={kb_id}, collection={kb.collection_name})")

    # 1. Soft delete all documents in this KB
    doc_query = select(DocumentModel).where(
        DocumentModel.knowledge_base_id == kb_id,
        DocumentModel.is_deleted == False,
    )
    doc_result = await db.execute(doc_query)
    documents = doc_result.scalars().all()

    doc_count = len(documents)
    for doc in documents:
        doc.is_deleted = True

    logger.info(f"Marked {doc_count} documents as deleted")

    # 2. Soft delete KB
    kb.is_deleted = True
    await db.commit()

    logger.info(f"Marked KB as deleted")

    # 3. Delete Qdrant collection
    try:
        vector_store = get_vector_store()
        collection_exists = await vector_store.collection_exists(kb.collection_name)

        if collection_exists:
            await vector_store.delete_collection(kb.collection_name)
            logger.info(f"Deleted Qdrant collection '{kb.collection_name}'")
        else:
            logger.warning(f"Qdrant collection '{kb.collection_name}' not found (already deleted?)")

    except Exception as e:
        logger.error(f"Failed to delete Qdrant collection '{kb.collection_name}': {e}")
        # Don't fail the request if Qdrant deletion fails - KB is already marked deleted

    # 4. Delete OpenSearch chunks
    try:
        lexical_store = get_lexical_store()
        await lexical_store.delete_by_kb_id(str(kb_id))
        logger.info(f"Deleted OpenSearch chunks for KB '{kb.name}'")
    except Exception as e:
        logger.error(f"Failed to delete OpenSearch chunks for KB '{kb.name}': {e}")

    return None


@router.post("/{kb_id}/restore", response_model=dict)
async def restore_knowledge_base(
    kb_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    Restore a soft-deleted knowledge base and reindex its documents.
    """
    query = select(KnowledgeBaseModel).where(
        KnowledgeBaseModel.id == kb_id,
        KnowledgeBaseModel.is_deleted == True,
    )
    result = await db.execute(query)
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deleted knowledge base {kb_id} not found",
        )

    # Restore KB and documents
    kb.is_deleted = False
    docs_query = select(DocumentModel).where(
        DocumentModel.knowledge_base_id == kb_id,
        DocumentModel.is_deleted == True,
    )
    docs_result = await db.execute(docs_query)
    documents = docs_result.scalars().all()
    for doc in documents:
        doc.is_deleted = False
        doc.status = DocumentStatus.PENDING
        doc.embeddings_status = DocumentStatus.PENDING
        doc.bm25_status = DocumentStatus.PENDING
        doc.error_message = None

    await db.commit()

    # Recreate Qdrant collection if needed
    try:
        vector_store = get_vector_store()
        await vector_store.create_collection(
            collection_name=kb.collection_name,
            vector_size=kb.embedding_dimension,
        )
    except Exception as e:
        logger.error(f"Failed to ensure Qdrant collection for restore: {e}")

    # Queue reprocessing
    from app.api.v1.documents import _reprocess_document_background

    queued = 0
    for doc in documents:
        background_tasks.add_task(
            _reprocess_document_background,
            document_id=doc.id,
        )
        queued += 1

    logger.info(f"Restored KB {kb_id}, queued {queued} documents for reprocessing")
    return {"restored": True, "queued": queued, "knowledge_base_id": str(kb_id)}


@router.delete("/{kb_id}/purge", status_code=status.HTTP_204_NO_CONTENT)
async def purge_knowledge_base(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    Permanently delete a knowledge base and its documents from the database.
    """
    query = select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id)
    result = await db.execute(query)
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge base {kb_id} not found",
        )

    # Delete documents (hard delete)
    docs_query = select(DocumentModel).where(
        DocumentModel.knowledge_base_id == kb_id,
    )
    docs_result = await db.execute(docs_query)
    documents = docs_result.scalars().all()
    for doc in documents:
        await db.delete(doc)

    await db.delete(kb)
    await db.commit()

    # Best-effort index cleanup
    try:
        vector_store = get_vector_store()
        await vector_store.delete_collection(kb.collection_name)
    except Exception as e:
        logger.error(f"Failed to delete Qdrant collection '{kb.collection_name}': {e}")

    try:
        lexical_store = get_lexical_store()
        await lexical_store.delete_by_kb_id(str(kb_id))
    except Exception as e:
        logger.error(f"Failed to delete OpenSearch chunks for KB '{kb.name}': {e}")

    return None


@router.post("/{kb_id}/reprocess", response_model=dict)
async def reprocess_knowledge_base(
    kb_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    Reprocess all documents in a knowledge base.

    This re-chunks and re-embeds documents to keep vector and BM25 indices aligned.
    """
    # Get KB
    query = select(KnowledgeBaseModel).where(
        KnowledgeBaseModel.id == kb_id,
        KnowledgeBaseModel.is_deleted == False,
    )
    result = await db.execute(query)
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge base {kb_id} not found",
        )

    # Get documents
    doc_query = select(DocumentModel).where(
        DocumentModel.knowledge_base_id == kb_id,
        DocumentModel.is_deleted == False,
    )
    doc_result = await db.execute(doc_query)
    documents = doc_result.scalars().all()

    from app.api.v1.documents import _reprocess_document_background

    queued = 0
    for doc in documents:
        if doc.status == DocumentStatus.PROCESSING:
            continue
        doc.status = DocumentStatus.PENDING
        doc.embeddings_status = DocumentStatus.PENDING
        doc.bm25_status = DocumentStatus.PENDING
        doc.error_message = None
        background_tasks.add_task(
            _reprocess_document_background,
            document_id=doc.id,
        )
        queued += 1

    await db.commit()

    logger.info(f"Queued {queued} documents for reprocessing (kb={kb_id})")

    return {"queued": queued, "knowledge_base_id": str(kb_id)}


@router.post("/{kb_id}/cleanup-orphaned-chunks", response_model=dict)
async def cleanup_orphaned_chunks(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    Clean up orphaned chunks in Qdrant for deleted documents.

    Removes vector embeddings from Qdrant for documents that are marked
    as deleted (is_deleted=true) in PostgreSQL.
    """
    from app.core.vector_store import QdrantVectorStore

    # Get KB
    query = select(KnowledgeBaseModel).where(
        KnowledgeBaseModel.id == kb_id,
        KnowledgeBaseModel.is_deleted == False,
    )
    result = await db.execute(query)
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge base {kb_id} not found",
        )

    # Get deleted document IDs
    deleted_query = select(DocumentModel.id).where(
        DocumentModel.knowledge_base_id == kb_id,
        DocumentModel.is_deleted == True,
    )
    deleted_result = await db.execute(deleted_query)
    deleted_doc_ids = [str(doc_id) for doc_id in deleted_result.scalars().all()]

    if not deleted_doc_ids:
        return {
            "deleted_chunks": 0,
            "deleted_documents": 0,
            "message": "No deleted documents found"
        }

    # Delete chunks from Qdrant for each deleted document
    vector_store = QdrantVectorStore()
    total_deleted = 0

    for doc_id in deleted_doc_ids:
        try:
            count = await vector_store.delete_by_document_id(
                collection_name=kb.collection_name,
                document_id=doc_id,
            )
            total_deleted += count
            logger.info(f"Deleted {count} chunks for document {doc_id}")
        except Exception as e:
            logger.error(f"Failed to delete chunks for document {doc_id}: {e}")

    logger.info(
        f"Cleanup completed for KB {kb_id}: "
        f"deleted {total_deleted} chunks from {len(deleted_doc_ids)} documents"
    )

    return {
        "deleted_chunks": total_deleted,
        "deleted_documents": len(deleted_doc_ids),
        "knowledge_base_id": str(kb_id),
    }
