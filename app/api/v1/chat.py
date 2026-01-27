"""Chat/Query endpoints for RAG."""
import logging
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.database import KnowledgeBase as KnowledgeBaseModel
from app.models.schemas import ChatRequest, ChatResponse, SourceChunk
from app.services.rag import get_rag_service, RAGService
from app.dependencies import get_current_user_id


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
    rag_service: RAGService = Depends(get_rag_service),
):
    """
    Query a knowledge base using RAG.

    Performs semantic search over the knowledge base and generates an answer
    using retrieved context.

    Process:
    1. Retrieves relevant chunks from vector store
    2. Assembles context from retrieved chunks
    3. Generates answer using LLM with context
    4. Returns answer with source attribution

    Returns answer with sources and confidence scores.
    """
    logger.info(
        f"Chat query: '{request.question[:50]}...' "
        f"(KB: {request.knowledge_base_id})"
    )

    try:
        # 1. Verify knowledge base exists
        kb_query = select(KnowledgeBaseModel).where(
            KnowledgeBaseModel.id == request.knowledge_base_id,
            KnowledgeBaseModel.is_deleted == False,
        )
        kb_result = await db.execute(kb_query)
        kb = kb_result.scalar_one_or_none()

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Knowledge base {request.knowledge_base_id} not found"
            )

        # 2. Check if KB has any documents
        if kb.document_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Knowledge base is empty. Please add documents first."
            )

        # 3. Perform RAG query
        logger.debug(f"Querying collection: {kb.collection_name}")

        # Convert conversation history to dict format
        history_dicts = None
        if request.conversation_history:
            history_dicts = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]

        rag_response = await rag_service.query(
            question=request.question,
            collection_name=kb.collection_name,
            embedding_model=kb.embedding_model,  # Pass KB's embedding model
            top_k=request.top_k,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            max_context_chars=request.max_context_chars,
            score_threshold=request.score_threshold,
            llm_model=request.llm_model,
            llm_provider=request.llm_provider,
            conversation_history=history_dicts,
            use_structure=request.use_structure,
            db=db,
            kb_id=request.knowledge_base_id,
        )

        # 4. Convert to API response format
        sources = [
            SourceChunk(
                text=chunk.text,
                score=chunk.score,
                document_id=chunk.document_id,
                filename=chunk.filename,
                chunk_index=chunk.chunk_index,
            )
            for chunk in rag_response.sources
        ]

        response = ChatResponse(
            answer=rag_response.answer,
            sources=sources,
            query=rag_response.query,
            confidence_score=rag_response.confidence_score,
            model=rag_response.model,
            knowledge_base_id=request.knowledge_base_id,
        )

        logger.info(
            f"Chat query completed: {len(rag_response.answer)} chars answer, "
            f"{len(sources)} sources, "
            f"confidence: {response.confidence_score:.3f}"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}"
        )


@router.get("/knowledge-bases/{kb_id}/stats")
async def get_knowledge_base_stats(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """
    Get statistics about a knowledge base.

    Returns information useful for querying:
    - Total documents
    - Total chunks indexed
    - Collection name
    - Configuration
    """
    kb_query = select(KnowledgeBaseModel).where(
        KnowledgeBaseModel.id == kb_id,
        KnowledgeBaseModel.is_deleted == False,
    )
    kb_result = await db.execute(kb_query)
    kb = kb_result.scalar_one_or_none()

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge base {kb_id} not found"
        )

    return {
        "id": str(kb.id),
        "name": kb.name,
        "description": kb.description,
        "document_count": kb.document_count,
        "total_chunks": kb.total_chunks,
        "collection_name": kb.collection_name,
        "chunking_config": {
            "chunk_size": kb.chunk_size,
            "chunk_overlap": kb.chunk_overlap,
            "strategy": kb.chunking_strategy.value,
        },
        "created_at": kb.created_at.isoformat() if kb.created_at else None,
        "ready_for_queries": kb.document_count > 0,
    }
