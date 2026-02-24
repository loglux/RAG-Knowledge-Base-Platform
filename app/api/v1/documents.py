"""Document management endpoints."""

import hashlib
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.models.database import Document as DocumentModel
from app.models.database import KnowledgeBase as KnowledgeBaseModel
from app.models.enums import DocumentStatus, FileType
from app.models.schemas import (
    DocumentList,
    DocumentResponse,
    DocumentWithContent,
)
from app.services.document_processor import get_document_processor
from app.services.duplicate_chunks import compute_duplicate_chunks_for_document, json_dumps

logger = logging.getLogger(__name__)

router = APIRouter()


async def _process_document_background(document_id: UUID, detect_duplicates: bool = False):
    """
    Background task to process a document.

    Args:
        document_id: Document ID to process

    Note: Always updates document status to FAILED if processing fails,
    even if the main error handler couldn't commit the status change.
    """
    logger.info(f"[BACKGROUND] Starting background processing for document {document_id}")
    try:
        # Create a new DB session for background task
        from app.db.session import AsyncSessionLocal

        logger.info("[BACKGROUND] Creating DB session...")
        async with AsyncSessionLocal() as db:
            logger.info("[BACKGROUND] Getting document processor...")
            processor = get_document_processor()
            logger.info("[BACKGROUND] Calling process_document()...")
            result = await processor.process_document(
                document_id, db, detect_duplicates=detect_duplicates
            )
            logger.info(f"[BACKGROUND] Background processing completed: {result}")

    except Exception as e:
        logger.error(f"Background processing failed for document {document_id}: {e}")

        # Ensure document status is updated to FAILED
        # Use a fresh DB session in case the previous one is in a bad state
        try:
            from app.db.session import AsyncSessionLocal
            from app.models.enums import DocumentStatus

            async with AsyncSessionLocal() as db:
                query = select(DocumentModel).where(DocumentModel.id == document_id)
                result = await db.execute(query)
                doc = result.scalar_one_or_none()

                if doc:
                    doc.status = DocumentStatus.FAILED
                    doc.error_message = f"Processing failed: {str(e)}"
                    db.add(doc)
                    await db.commit()
                    logger.info(f"Updated document {document_id} status to FAILED")
                else:
                    logger.error(f"Could not find document {document_id} to update status")

        except Exception as update_error:
            logger.error(f"Failed to update document status to FAILED: {update_error}")


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    file: UploadFile = File(...),
    knowledge_base_id: UUID = Form(...),
    detect_duplicates: bool = Form(False),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    Upload and process a document file.

    Accepts file upload via multipart/form-data and processes it:
    - Chunks the document text
    - Generates embeddings for each chunk
    - Indexes chunks in Qdrant vector database

    Processing happens in the background. Check document status to monitor progress.

    Supported formats (MVP): txt, md, fb2, docx
    """
    # Verify KB exists
    kb_query = select(KnowledgeBaseModel).where(
        KnowledgeBaseModel.id == knowledge_base_id,
        KnowledgeBaseModel.is_deleted == False,
    )
    kb_result = await db.execute(kb_query)
    kb = kb_result.scalar_one_or_none()

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge base {knowledge_base_id} not found",
        )

    # Detect file type
    filename = file.filename or "unnamed"
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension == "txt":
        file_type = FileType.TXT
    elif extension == "md":
        file_type = FileType.MD
    elif extension == "fb2":
        file_type = FileType.FB2
    elif extension == "docx":
        file_type = FileType.DOCX
    elif extension == "pdf":
        file_type = FileType.PDF
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {extension}. Supported: txt, md, fb2, docx, pdf",
        )

    # Read file content
    content_bytes = await file.read()
    content: str
    heading_map_json: str | None = None
    if file_type in (FileType.DOCX, FileType.FB2, FileType.PDF):
        from app.utils.file_handlers import FileHandlerFactory, process_file

        type_label = file_type.value.upper()
        try:
            processed = process_file(content_bytes, filename, file_type)
            content = processed["text"]
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse {type_label}: {exc}",
            ) from exc

        # Extract heading map for structural metadata indexing
        try:
            handler = FileHandlerFactory.get_handler(file_type)
            headings = handler.extract_heading_map(content_bytes)
            if headings:
                heading_map_json = json.dumps(headings, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"Failed to extract {type_label} heading map for '{filename}': {exc}")
    else:
        try:
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            import chardet

            detected = chardet.detect(content_bytes)
            encoding = detected.get("encoding")
            if not encoding:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File must be UTF-8 or a detectable text encoding",
                )
            content = content_bytes.decode(encoding, errors="replace")

    # Validate file size
    from app.config import settings

    file_size = len(content_bytes)
    if file_size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size {file_size} bytes exceeds limit of {settings.MAX_FILE_SIZE_MB}MB",
        )

    # Calculate content hash for deduplication
    content_hash = hashlib.sha256(content_bytes).hexdigest()

    # Check for duplicate
    dup_query = select(DocumentModel).where(
        DocumentModel.knowledge_base_id == knowledge_base_id,
        DocumentModel.content_hash == content_hash,
        DocumentModel.is_deleted == False,
    )
    dup_result = await db.execute(dup_query)
    if dup_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document with identical content already exists in this knowledge base",
        )

    # Create document
    doc_model = DocumentModel(
        knowledge_base_id=knowledge_base_id,
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        content=content,
        content_hash=content_hash,
        status=DocumentStatus.PENDING,
        user_id=user_id,
        heading_map_json=heading_map_json,
    )

    db.add(doc_model)
    await db.flush()  # Flush to make doc_model visible in queries

    # Recalculate KB document count (prevents desync from incremental updates)
    doc_count = await db.scalar(
        select(func.count(DocumentModel.id)).where(
            DocumentModel.knowledge_base_id == kb.id, DocumentModel.is_deleted == False
        )
    )
    kb.document_count = doc_count or 0

    await db.commit()
    await db.refresh(doc_model)

    # Process document in background
    logger.info(f"[UPLOAD] Adding background task for document {doc_model.id}")
    background_tasks.add_task(
        _process_document_background,
        document_id=doc_model.id,
        detect_duplicates=detect_duplicates,
    )
    logger.info(f"[UPLOAD] Background task added successfully for document {doc_model.id}")

    logger.info(f"Document {doc_model.id} ({filename}) uploaded and queued for processing")

    return doc_model


@router.get("/", response_model=DocumentList)
async def list_documents(
    knowledge_base_id: Optional[UUID] = Query(None, description="Filter by knowledge base"),
    status_filter: Optional[DocumentStatus] = Query(
        None, alias="status", description="Filter by status"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    List documents with optional filtering.

    Returns paginated list of documents.
    Can filter by knowledge base and/or processing status.
    """
    # Build query
    query = select(DocumentModel).where(DocumentModel.is_deleted == False)

    if knowledge_base_id:
        query = query.where(DocumentModel.knowledge_base_id == knowledge_base_id)

    if status_filter:
        query = query.where(DocumentModel.status == status_filter)

    # Future: Add user filter when auth is implemented

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute
    result = await db.execute(query)
    items = result.scalars().all()

    return DocumentList(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total else 0,
    )


@router.get("/{doc_id}", response_model=DocumentWithContent)
async def get_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    Get document by ID including full content.

    Returns complete document information including the original content.
    """
    query = select(DocumentModel).where(
        DocumentModel.id == doc_id,
        DocumentModel.is_deleted == False,
    )

    result = await db.execute(query)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Document {doc_id} not found"
        )

    # Future: Check user ownership

    return doc


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    Delete document (soft delete).

    Marks document as deleted and updates knowledge base statistics.
    Associated vectors in Qdrant will also be deleted.
    """
    # Get document
    query = select(DocumentModel).where(
        DocumentModel.id == doc_id,
        DocumentModel.is_deleted == False,
    )
    result = await db.execute(query)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Document {doc_id} not found"
        )

    # Future: Check user ownership

    # Get KB to update stats
    kb_query = select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == doc.knowledge_base_id)
    kb_result = await db.execute(kb_query)
    kb = kb_result.scalar_one_or_none()

    # Soft delete document
    doc.is_deleted = True

    # Recalculate KB statistics (prevents desync from incremental updates)
    if kb:
        doc_count = await db.scalar(
            select(func.count(DocumentModel.id)).where(
                DocumentModel.knowledge_base_id == kb.id, DocumentModel.is_deleted == False
            )
        )
        total_chunks = await db.scalar(
            select(func.coalesce(func.sum(DocumentModel.chunk_count), 0)).where(
                DocumentModel.knowledge_base_id == kb.id, DocumentModel.is_deleted == False
            )
        )
        kb.document_count = doc_count or 0
        kb.total_chunks = total_chunks or 0

    await db.commit()

    # Delete vectors from Qdrant
    try:
        processor = get_document_processor()
        await processor.delete_document_vectors(
            document_id=doc_id,
            collection_name=kb.collection_name,
        )
        logger.info(f"Deleted vectors for document {doc_id} from Qdrant")
    except Exception as e:
        logger.error(f"Failed to delete vectors from Qdrant: {e}")
        # Continue even if vector deletion fails (vectors will be orphaned)

    return None


@router.post("/{doc_id}/reprocess", response_model=DocumentResponse)
async def reprocess_document(
    doc_id: UUID,
    background_tasks: BackgroundTasks,
    detect_duplicates: bool = Query(
        False, description="Compute duplicate chunks after reprocessing"
    ),
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    Reprocess an existing document.

    Deletes old vectors and processes the document again:
    - Re-chunks the document
    - Regenerates embeddings
    - Re-indexes in Qdrant

    Useful if chunking strategy or embedding model has changed.
    """
    # Get document
    query = select(DocumentModel).where(
        DocumentModel.id == doc_id,
        DocumentModel.is_deleted == False,
    )
    result = await db.execute(query)
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Document {doc_id} not found"
        )

    # Check if document is currently processing
    if doc.status == DocumentStatus.PROCESSING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Document is currently being processed"
        )

    # Update status to pending
    doc.status = DocumentStatus.PENDING
    doc.embeddings_status = DocumentStatus.PENDING
    doc.bm25_status = DocumentStatus.PENDING
    doc.error_message = None
    await db.commit()
    await db.refresh(doc)

    # Queue reprocessing in background
    background_tasks.add_task(
        _reprocess_document_background,
        document_id=doc_id,
        detect_duplicates=detect_duplicates,
    )

    logger.info(f"Document {doc_id} queued for reprocessing")

    return doc


async def _reprocess_document_background(document_id: UUID, detect_duplicates: bool = False):
    """
    Background task to reprocess a document.

    Note: Always updates document status to FAILED if reprocessing fails,
    even if the main error handler couldn't commit the status change.
    """
    try:
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            processor = get_document_processor()
            result = await processor.reprocess_document(
                document_id, db, detect_duplicates=detect_duplicates
            )
            logger.info(f"Background reprocessing completed: {result}")

    except Exception as e:
        logger.error(f"Background reprocessing failed for document {document_id}: {e}")

        # Ensure document status is updated to FAILED
        # Use a fresh DB session in case the previous one is in a bad state
        try:
            from app.db.session import AsyncSessionLocal
            from app.models.enums import DocumentStatus

            async with AsyncSessionLocal() as db:
                query = select(DocumentModel).where(DocumentModel.id == document_id)
                result = await db.execute(query)
                doc = result.scalar_one_or_none()

                if doc:
                    doc.status = DocumentStatus.FAILED
                    doc.embeddings_status = DocumentStatus.FAILED
                    doc.bm25_status = DocumentStatus.FAILED
                    doc.error_message = f"Reprocessing failed: {str(e)}"
                    db.add(doc)
                    await db.commit()
                    logger.info(f"Updated document {document_id} status to FAILED")
                else:
                    logger.error(f"Could not find document {document_id} to update status")

        except Exception as update_error:
            logger.error(f"Failed to update document status to FAILED: {update_error}")


@router.get("/{doc_id}/status", response_model=dict)
async def get_document_status(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    Get processing status of a document.

    Returns current status and metadata about processing progress.
    Always returns 200 OK with status info, even if processing failed.
    """
    try:
        query = select(DocumentModel).where(
            DocumentModel.id == doc_id,
            DocumentModel.is_deleted == False,
        )
        result = await db.execute(query)
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Document {doc_id} not found"
            )

        # Safe status extraction
        doc_status = "unknown"
        if doc.status:
            try:
                doc_status = doc.status.value if hasattr(doc.status, "value") else str(doc.status)
            except Exception:
                doc_status = "unknown"

        return {
            "id": str(doc.id),
            "filename": doc.filename,
            "status": doc_status,
            "embeddings_status": (
                (
                    doc.embeddings_status.value
                    if hasattr(doc.embeddings_status, "value")
                    else str(doc.embeddings_status)
                )
                if doc.embeddings_status
                else None
            ),
            "bm25_status": (
                (
                    doc.bm25_status.value
                    if hasattr(doc.bm25_status, "value")
                    else str(doc.bm25_status)
                )
                if doc.bm25_status
                else None
            ),
            "chunk_count": doc.chunk_count or 0,
            "error_message": doc.error_message,
            "processing_stage": doc.processing_stage,
            "progress_percentage": doc.progress_percentage or 0,
        }

    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as e:
        # Catch any unexpected errors and return a safe response
        logger.error(f"Error getting status for document {doc_id}: {e}")
        return {
            "id": str(doc_id),
            "filename": "unknown",
            "status": "error",
            "chunk_count": 0,
            "error_message": f"Failed to get document status: {str(e)}",
        }


@router.post("/{doc_id}/duplicates/recompute", response_model=dict)
async def recompute_document_duplicates(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    Recompute duplicate chunk analysis for a document (Qdrant payload scan only).
    Stores summary in document metadata.
    """
    query = (
        select(DocumentModel, KnowledgeBaseModel)
        .join(
            KnowledgeBaseModel,
            DocumentModel.knowledge_base_id == KnowledgeBaseModel.id,
        )
        .where(
            DocumentModel.id == doc_id,
            DocumentModel.is_deleted == False,
        )
    )
    result = await db.execute(query)
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Document {doc_id} not found"
        )

    doc, kb = row
    summary = await compute_duplicate_chunks_for_document(doc.id, kb.collection_name)
    doc.duplicate_chunks_json = json_dumps(summary)
    await db.commit()
    await db.refresh(doc)

    return summary
