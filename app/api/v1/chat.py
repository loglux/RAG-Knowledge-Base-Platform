"""Chat/Query endpoints for RAG."""
import json
import logging
from datetime import datetime
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.config import settings as app_settings
from app.db.session import get_db
from app.models.database import (
    KnowledgeBase as KnowledgeBaseModel,
    AppSettings as AppSettingsModel,
    Conversation as ConversationModel,
    ChatMessage as ChatMessageModel,
)
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatDeleteResponse,
    SourceChunk,
    ConversationSummary,
    ChatMessageResponse,
    ConversationDetail,
    ConversationSettings,
)
from app.services.rag import get_rag_service, RAGService
from app.dependencies import get_current_user_id


logger = logging.getLogger(__name__)
router = APIRouter()


def _bm25_defaults() -> dict:
    return {
        "bm25_match_mode": app_settings.BM25_DEFAULT_MATCH_MODE,
        "bm25_min_should_match": app_settings.BM25_DEFAULT_MIN_SHOULD_MATCH,
        "bm25_use_phrase": app_settings.BM25_DEFAULT_USE_PHRASE,
        "bm25_analyzer": app_settings.BM25_DEFAULT_ANALYZER,
    }


def _format_chat_error(exc: Exception) -> tuple[int, str]:
    """Map internal errors to safe user-facing messages."""
    if isinstance(exc, httpx.ReadTimeout):
        return (
            status.HTTP_504_GATEWAY_TIMEOUT,
            "Ollama timed out while generating a response. Try a smaller model or reduce context."
        )
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code if exc.response else status.HTTP_502_BAD_GATEWAY
        if code == status.HTTP_400_BAD_REQUEST:
            return (
                status.HTTP_400_BAD_REQUEST,
                "Ollama rejected the request (400). Try reducing context or checking model availability."
            )
        return (
            status.HTTP_502_BAD_GATEWAY,
            "Ollama returned an upstream error. Try again or switch models."
        )
    return (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Query failed. Please try again."
    )


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
        "Chat query: '%s...' (KB: %s, model: %s, provider: %s)",
        request.question[:50],
        request.knowledge_base_id,
        request.llm_model or "default",
        request.llm_provider or "default",
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

        # 3. Load conversation (optional)
        conversation = None
        if request.conversation_id:
            convo_query = select(ConversationModel).where(
                ConversationModel.id == request.conversation_id,
                ConversationModel.is_deleted == False,
            )
            convo_result = await db.execute(convo_query)
            conversation = convo_result.scalar_one_or_none()
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conversation {request.conversation_id} not found"
                )
            if conversation.knowledge_base_id != request.knowledge_base_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Conversation does not belong to this knowledge base"
                )

        # 4. Perform RAG query
        logger.debug(f"Querying collection: {kb.collection_name}")

        # Convert conversation history to dict format
        history_dicts = None
        if request.conversation_history:
            history_dicts = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]
        elif conversation:
            history_query = (
                select(ChatMessageModel)
                .where(ChatMessageModel.conversation_id == conversation.id)
                .order_by(desc(ChatMessageModel.message_index))
                .limit(10)
            )
            history_result = await db.execute(history_query)
            history_messages = list(reversed(history_result.scalars().all()))
            if history_messages:
                history_dicts = [
                    {"role": msg.role, "content": msg.content}
                    for msg in history_messages
                ]

        # Resolve BM25 settings (request > KB override > global defaults > hard defaults)
        settings_result = await db.execute(select(AppSettingsModel).order_by(AppSettingsModel.id).limit(1))
        app_settings = settings_result.scalar_one_or_none()
        bm25_defaults = _bm25_defaults()

        def _resolve_bm25(field: str):
            req_val = getattr(request, field, None)
            if req_val is not None:
                return req_val
            kb_val = getattr(kb, field, None)
            if kb_val is not None:
                return kb_val
            if app_settings is not None:
                app_val = getattr(app_settings, field, None)
                if app_val is not None:
                    return app_val
            return bm25_defaults[field]

        bm25_match_mode = _resolve_bm25("bm25_match_mode")
        bm25_min_should_match = _resolve_bm25("bm25_min_should_match")
        bm25_use_phrase = _resolve_bm25("bm25_use_phrase")
        bm25_analyzer = _resolve_bm25("bm25_analyzer")

        rag_response = await rag_service.query(
            question=request.question,
            collection_name=kb.collection_name,
            embedding_model=kb.embedding_model,  # Pass KB's embedding model
            top_k=request.top_k,
            retrieval_mode=request.retrieval_mode,
            lexical_top_k=request.lexical_top_k,
            dense_weight=request.hybrid_dense_weight,
            lexical_weight=request.hybrid_lexical_weight,
            bm25_match_mode=bm25_match_mode,
            bm25_min_should_match=bm25_min_should_match,
            bm25_use_phrase=bm25_use_phrase,
            bm25_analyzer=bm25_analyzer,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            max_context_chars=request.max_context_chars,
            score_threshold=request.score_threshold,
            llm_model=request.llm_model,
            llm_provider=request.llm_provider,
            conversation_history=history_dicts,
            use_structure=request.use_structure,
            use_mmr=request.use_mmr,
            mmr_diversity=request.mmr_diversity,
            use_self_check=request.use_self_check,
            db=db,
            kb_id=request.knowledge_base_id,
        )

        # 5. Ensure conversation exists (create if needed)
        if conversation is None:
            title = request.question.strip()[:120] if request.question else "New conversation"
            settings_payload = {
                "top_k": request.top_k,
                "temperature": request.temperature,
                "max_context_chars": request.max_context_chars,
                "score_threshold": request.score_threshold,
                "llm_model": request.llm_model,
                "llm_provider": request.llm_provider,
                "use_structure": request.use_structure,
                "retrieval_mode": request.retrieval_mode,
                "lexical_top_k": request.lexical_top_k,
                "hybrid_dense_weight": request.hybrid_dense_weight,
                "hybrid_lexical_weight": request.hybrid_lexical_weight,
                "bm25_match_mode": bm25_match_mode,
                "bm25_min_should_match": bm25_min_should_match,
                "bm25_use_phrase": bm25_use_phrase,
                "bm25_analyzer": bm25_analyzer,
                "use_mmr": request.use_mmr,
                "mmr_diversity": request.mmr_diversity,
                "use_self_check": request.use_self_check,
            }
            conversation = ConversationModel(
                knowledge_base_id=request.knowledge_base_id,
                title=title,
                user_id=user_id,
                settings_json=json.dumps(settings_payload),
            )
            db.add(conversation)
            await db.flush()
        else:
            existing_settings = {}
            if conversation.settings_json:
                try:
                    existing_settings = json.loads(conversation.settings_json)
                except Exception:
                    existing_settings = {}
            existing_settings.update({
                "top_k": request.top_k,
                "temperature": request.temperature,
                "max_context_chars": request.max_context_chars,
                "score_threshold": request.score_threshold,
                "llm_model": request.llm_model,
                "llm_provider": request.llm_provider,
                "use_structure": request.use_structure,
                "retrieval_mode": request.retrieval_mode,
                "lexical_top_k": request.lexical_top_k,
                "hybrid_dense_weight": request.hybrid_dense_weight,
                "hybrid_lexical_weight": request.hybrid_lexical_weight,
                "bm25_match_mode": bm25_match_mode,
                "bm25_min_should_match": bm25_min_should_match,
                "bm25_use_phrase": bm25_use_phrase,
                "bm25_analyzer": bm25_analyzer,
                "use_mmr": request.use_mmr,
                "mmr_diversity": request.mmr_diversity,
                "use_self_check": request.use_self_check,
            })
            conversation.settings_json = json.dumps(existing_settings)

        # 6. Persist messages
        max_index_query = select(func.max(ChatMessageModel.message_index)).where(
            ChatMessageModel.conversation_id == conversation.id
        )
        max_index_result = await db.execute(max_index_query)
        max_index = max_index_result.scalar_one_or_none() or 0
        user_index = max_index + 1
        assistant_index = max_index + 2

        user_message = ChatMessageModel(
            conversation_id=conversation.id,
            role="user",
            content=request.question,
            message_index=user_index,
        )
        db.add(user_message)

        sources_payload = [
            {
                "text": chunk.text,
                "score": chunk.score,
                "document_id": chunk.document_id,
                "filename": chunk.filename,
                "chunk_index": chunk.chunk_index,
                "metadata": chunk.metadata,
            }
            for chunk in rag_response.sources
        ]

        assistant_message = ChatMessageModel(
            conversation_id=conversation.id,
            role="assistant",
            content=rag_response.answer,
            sources_json=json.dumps(sources_payload),
            model=rag_response.model,
            use_self_check=request.use_self_check if request.use_self_check else None,
            message_index=assistant_index,
        )
        db.add(assistant_message)
        await db.flush()
        conversation.updated_at = datetime.utcnow()

        # 7. Convert to API response format
        sources = [
            SourceChunk(
                text=chunk.text,
                score=chunk.score,
                document_id=chunk.document_id,
                filename=chunk.filename,
                chunk_index=chunk.chunk_index,
                metadata=chunk.metadata,
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
            conversation_id=conversation.id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            use_mmr=request.use_mmr if request.use_mmr else None,
            mmr_diversity=request.mmr_diversity if request.use_mmr else None,
            use_self_check=request.use_self_check if request.use_self_check else None,
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
        logger.exception("Chat query failed")
        status_code, message = _format_chat_error(e)
        raise HTTPException(status_code=status_code, detail=message)


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


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    knowledge_base_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """List conversations for a knowledge base."""
    convo_query = (
        select(ConversationModel)
        .where(
            ConversationModel.knowledge_base_id == knowledge_base_id,
            ConversationModel.is_deleted == False,
        )
        .order_by(desc(ConversationModel.updated_at))
    )
    convo_result = await db.execute(convo_query)
    conversations = convo_result.scalars().all()

    return [
        ConversationSummary(
            id=convo.id,
            knowledge_base_id=convo.knowledge_base_id,
            title=convo.title,
            created_at=convo.created_at,
            updated_at=convo.updated_at,
        )
        for convo in conversations
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """Get conversation details including settings."""
    convo_query = select(ConversationModel).where(
        ConversationModel.id == conversation_id,
        ConversationModel.is_deleted == False,
    )
    convo_result = await db.execute(convo_query)
    conversation = convo_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )

    settings = None
    if conversation.settings_json:
        try:
            settings = ConversationSettings(**json.loads(conversation.settings_json))
        except Exception:
            settings = None

    return ConversationDetail(
        id=conversation.id,
        knowledge_base_id=conversation.knowledge_base_id,
        title=conversation.title,
        settings=settings,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.patch("/conversations/{conversation_id}/settings", response_model=ConversationDetail)
async def update_conversation_settings(
    conversation_id: UUID,
    payload: ConversationSettings,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """Update conversation settings."""
    convo_query = select(ConversationModel).where(
        ConversationModel.id == conversation_id,
        ConversationModel.is_deleted == False,
    )
    convo_result = await db.execute(convo_query)
    conversation = convo_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )

    conversation.settings_json = payload.model_dump_json(exclude_none=True)
    conversation.updated_at = datetime.utcnow()

    return ConversationDetail(
        id=conversation.id,
        knowledge_base_id=conversation.knowledge_base_id,
        title=conversation.title,
        settings=payload,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.get("/conversations/{conversation_id}/messages", response_model=list[ChatMessageResponse])
async def get_conversation_messages(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """Get messages for a conversation."""
    convo_query = select(ConversationModel).where(
        ConversationModel.id == conversation_id,
        ConversationModel.is_deleted == False,
    )
    convo_result = await db.execute(convo_query)
    conversation = convo_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )

    msg_query = (
        select(ChatMessageModel)
        .where(ChatMessageModel.conversation_id == conversation_id)
        .order_by(ChatMessageModel.message_index)
    )
    msg_result = await db.execute(msg_query)
    messages = msg_result.scalars().all()

    response_messages: list[ChatMessageResponse] = []
    for msg in messages:
        sources = None
        if msg.sources_json:
            try:
                raw_sources = json.loads(msg.sources_json)
                sources = [SourceChunk(**source) for source in raw_sources]
            except Exception:
                sources = None
        response_messages.append(ChatMessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            sources=sources,
            model=msg.model,
            use_self_check=msg.use_self_check,
            timestamp=msg.created_at,
            message_index=msg.message_index,
        ))

    return response_messages


@router.delete(
    "/conversations/{conversation_id}/messages/{message_id}",
    response_model=ChatDeleteResponse,
)
async def delete_conversation_message(
    conversation_id: UUID,
    message_id: UUID,
    pair: bool = True,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """Delete a message (optionally with its paired question/answer)."""
    convo_query = select(ConversationModel).where(
        ConversationModel.id == conversation_id,
        ConversationModel.is_deleted == False,
    )
    convo_result = await db.execute(convo_query)
    conversation = convo_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )

    msg_query = select(ChatMessageModel).where(
        ChatMessageModel.id == message_id,
        ChatMessageModel.conversation_id == conversation_id,
    )
    msg_result = await db.execute(msg_query)
    target_message = msg_result.scalar_one_or_none()
    if not target_message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found"
        )

    deleted_ids = {target_message.id}
    if pair:
        adjacent_index = (
            target_message.message_index + 1
            if target_message.role == "user"
            else target_message.message_index - 1
        )
        if adjacent_index > 0:
            adjacent_query = select(ChatMessageModel).where(
                ChatMessageModel.conversation_id == conversation_id,
                ChatMessageModel.message_index == adjacent_index,
            )
            adjacent_result = await db.execute(adjacent_query)
            adjacent_message = adjacent_result.scalar_one_or_none()
            if adjacent_message:
                deleted_ids.add(adjacent_message.id)

    await db.execute(
        delete(ChatMessageModel).where(ChatMessageModel.id.in_(deleted_ids))
    )
    conversation.updated_at = datetime.utcnow()

    return ChatDeleteResponse(
        status="deleted",
        deleted_ids=list(deleted_ids),
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """Soft-delete a conversation."""
    convo_query = select(ConversationModel).where(
        ConversationModel.id == conversation_id,
        ConversationModel.is_deleted == False,
    )
    convo_result = await db.execute(convo_query)
    conversation = convo_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )

    conversation.is_deleted = True
    return {"status": "deleted", "id": str(conversation_id)}
