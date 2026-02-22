"""Chat/Query endpoints for RAG."""

import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.models.database import AppSettings as AppSettingsModel
from app.models.database import ChatMessage as ChatMessageModel
from app.models.database import Conversation as ConversationModel
from app.models.database import KnowledgeBase as KnowledgeBaseModel
from app.models.schemas import (
    ChatDeleteResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationSettings,
    ConversationSummary,
    ConversationTitleUpdate,
    SourceChunk,
)
from app.services.chat_titles import build_conversation_title
from app.services.prompts import get_active_chat_prompt
from app.services.rag import RAGService, get_rag_service
from app.services.retrieval_settings import (
    BM25_FIELDS,
    RETRIEVAL_FIELDS,
    resolve_retrieval_settings_scoped,
)
from app.services.settings_resolution import parse_uuid_list, resolve_scoped_value

logger = logging.getLogger(__name__)
router = APIRouter()


def _format_chat_error(exc: Exception) -> tuple[int, str]:
    """Map internal errors to safe user-facing messages."""
    if isinstance(exc, httpx.ReadTimeout):
        return (
            status.HTTP_504_GATEWAY_TIMEOUT,
            "Ollama timed out while generating a response. Try a smaller model or reduce context.",
        )
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code if exc.response else status.HTTP_502_BAD_GATEWAY
        if code == status.HTTP_400_BAD_REQUEST:
            return (
                status.HTTP_400_BAD_REQUEST,
                "Ollama rejected the request (400). Try reducing context or checking model availability.",
            )
        return (
            status.HTTP_502_BAD_GATEWAY,
            "Ollama returned an upstream error. Try again or switch models.",
        )
    return (status.HTTP_500_INTERNAL_SERVER_ERROR, "Query failed. Please try again.")


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
                detail=f"Knowledge base {request.knowledge_base_id} not found",
            )

        # 2. Check if KB has any documents
        if kb.document_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Knowledge base is empty. Please add documents first.",
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
                    detail=f"Conversation {request.conversation_id} not found",
                )
            if conversation.knowledge_base_id != request.knowledge_base_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Conversation does not belong to this knowledge base",
                )

        # 4. Perform RAG query
        logger.debug(f"Querying collection: {kb.collection_name}")

        # Ensure prompt templates are configured
        system_content, _ = await get_active_chat_prompt(db)
        if not system_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt templates are not configured. Please set an active prompt.",
            )

        # Resolve conversation-level settings payload (if any)
        conversation_settings_payload: dict = {}
        if conversation and conversation.settings_json:
            try:
                loaded = json.loads(conversation.settings_json)
                if isinstance(loaded, dict):
                    conversation_settings_payload = loaded
            except Exception:
                conversation_settings_payload = {}

        request_payload = request.model_dump(exclude_unset=True, exclude_none=True)

        # Resolve conversation history behavior
        history_dicts = None
        use_history = resolve_scoped_value(
            key="use_conversation_history",
            request_overrides=request_payload,
            request_value=request.use_conversation_history,
            conversation_overrides=conversation_settings_payload,
            fallback=True,
        )
        history_limit = resolve_scoped_value(
            key="conversation_history_limit",
            request_overrides=request_payload,
            request_value=request.conversation_history_limit,
            conversation_overrides=conversation_settings_payload,
            fallback=10,
        )

        if use_history is None:
            use_history = True
        if history_limit is None:
            history_limit = 10
        if history_limit < 0:
            history_limit = 0

        if request.conversation_history:
            history_dicts = [
                {"role": msg.role, "content": msg.content} for msg in request.conversation_history
            ]
        elif conversation and use_history and history_limit > 0:
            history_query = (
                select(ChatMessageModel)
                .where(ChatMessageModel.conversation_id == conversation.id)
                .order_by(desc(ChatMessageModel.message_index))
                .limit(history_limit)
            )
            history_result = await db.execute(history_query)
            history_messages = list(reversed(history_result.scalars().all()))
            if history_messages:
                history_dicts = [
                    {"role": msg.role, "content": msg.content} for msg in history_messages
                ]

        settings_result = await db.execute(
            select(AppSettingsModel).order_by(AppSettingsModel.id).limit(1)
        )
        app_settings_row = settings_result.scalar_one_or_none()
        app_scope = (
            {
                "llm_provider": app_settings_row.llm_provider,
                "llm_model": app_settings_row.llm_model,
                "temperature": app_settings_row.temperature,
            }
            if app_settings_row
            else {}
        )

        # Resolve retrieval settings via shared resolver used by /retrieve and MCP.
        retrieval_fields = set(RETRIEVAL_FIELDS + BM25_FIELDS)
        conversation_retrieval_overrides = {
            key: value
            for key, value in conversation_settings_payload.items()
            if key in retrieval_fields and value is not None
        }
        request_retrieval_overrides = {
            key: value for key, value in request_payload.items() if key in retrieval_fields
        }
        effective = resolve_retrieval_settings_scoped(
            kb=kb,
            app_settings=app_settings_row,
            conversation_overrides=conversation_retrieval_overrides or None,
            request_overrides=request_retrieval_overrides or None,
        )

        llm_provider = resolve_scoped_value(
            key="llm_provider",
            request_overrides=request_payload,
            request_value=request.llm_provider,
            conversation_overrides=conversation_settings_payload,
            app_overrides=app_scope,
            fallback=app_settings.LLM_PROVIDER,
        )
        llm_model = resolve_scoped_value(
            key="llm_model",
            request_overrides=request_payload,
            request_value=request.llm_model,
            conversation_overrides=conversation_settings_payload,
            app_overrides=app_scope,
            fallback=app_settings.OPENAI_CHAT_MODEL,
        )
        temperature = resolve_scoped_value(
            key="temperature",
            request_overrides=request_payload,
            request_value=request.temperature,
            conversation_overrides=conversation_settings_payload,
            app_overrides=app_scope,
            fallback=app_settings.OPENAI_TEMPERATURE,
        )
        use_self_check = resolve_scoped_value(
            key="use_self_check",
            request_overrides=request_payload,
            request_value=request.use_self_check,
            conversation_overrides=conversation_settings_payload,
            fallback=False,
        )

        # Optional document filter inheritance from conversation settings.
        # Explicit request.document_ids always has priority.
        effective_document_ids = request.document_ids
        if (
            effective_document_ids is None
            and conversation_settings_payload.get("use_document_filter")
            and conversation_settings_payload.get("document_ids")
        ):
            parsed_doc_ids = parse_uuid_list(conversation_settings_payload.get("document_ids"))
            effective_document_ids = parsed_doc_ids or None

        rag_response = await rag_service.query(
            question=request.question,
            collection_name=kb.collection_name,
            embedding_model=kb.embedding_model,  # Pass KB's embedding model
            top_k=effective.get("top_k", 5),
            retrieval_mode=effective.get("retrieval_mode"),
            lexical_top_k=effective.get("lexical_top_k"),
            dense_weight=effective.get("hybrid_dense_weight", 0.6),
            lexical_weight=effective.get("hybrid_lexical_weight", 0.4),
            bm25_match_mode=effective.get("bm25_match_mode"),
            bm25_min_should_match=effective.get("bm25_min_should_match"),
            bm25_use_phrase=effective.get("bm25_use_phrase"),
            bm25_analyzer=effective.get("bm25_analyzer"),
            temperature=temperature,
            max_tokens=request.max_tokens,
            max_context_chars=effective.get("max_context_chars"),
            score_threshold=effective.get("score_threshold"),
            llm_model=llm_model,
            llm_provider=llm_provider,
            conversation_history=history_dicts,
            use_structure=effective.get("use_structure", False),
            rerank_enabled=effective.get("rerank_enabled", False),
            rerank_provider=effective.get("rerank_provider"),
            rerank_model=effective.get("rerank_model"),
            rerank_candidate_pool=effective.get("rerank_candidate_pool"),
            rerank_top_n=effective.get("rerank_top_n"),
            rerank_min_score=effective.get("rerank_min_score"),
            use_mmr=effective.get("use_mmr", False),
            mmr_diversity=effective.get("mmr_diversity", 0.5),
            use_self_check=bool(use_self_check),
            document_ids=(
                [str(doc_id) for doc_id in effective_document_ids]
                if effective_document_ids
                else None
            ),
            context_expansion=effective.get("context_expansion"),
            context_window=effective.get("context_window"),
            db=db,
            kb_id=request.knowledge_base_id,
        )

        # 5. Ensure conversation exists (create if needed)
        if conversation is None:
            settings_payload = {
                "top_k": effective.get("top_k", 5),
                "temperature": temperature,
                "max_context_chars": effective.get("max_context_chars"),
                "score_threshold": effective.get("score_threshold"),
                "llm_model": llm_model,
                "llm_provider": llm_provider,
                "use_structure": effective.get("use_structure", False),
                "rerank_enabled": effective.get("rerank_enabled", False),
                "rerank_provider": effective.get("rerank_provider"),
                "rerank_model": effective.get("rerank_model"),
                "rerank_candidate_pool": effective.get("rerank_candidate_pool"),
                "rerank_top_n": effective.get("rerank_top_n"),
                "rerank_min_score": effective.get("rerank_min_score"),
                "retrieval_mode": effective.get("retrieval_mode"),
                "lexical_top_k": effective.get("lexical_top_k"),
                "hybrid_dense_weight": effective.get("hybrid_dense_weight", 0.6),
                "hybrid_lexical_weight": effective.get("hybrid_lexical_weight", 0.4),
                "bm25_match_mode": effective.get("bm25_match_mode"),
                "bm25_min_should_match": effective.get("bm25_min_should_match"),
                "bm25_use_phrase": effective.get("bm25_use_phrase"),
                "bm25_analyzer": effective.get("bm25_analyzer"),
                "use_mmr": effective.get("use_mmr", False),
                "mmr_diversity": effective.get("mmr_diversity", 0.5),
                "use_self_check": bool(use_self_check),
                "use_conversation_history": bool(use_history),
                "conversation_history_limit": history_limit,
                "context_expansion": effective.get("context_expansion"),
                "context_window": effective.get("context_window"),
            }
            conversation = ConversationModel(
                knowledge_base_id=request.knowledge_base_id,
                title=None,
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
            existing_settings.update(
                {
                    "top_k": effective.get("top_k", 5),
                    "temperature": temperature,
                    "max_context_chars": effective.get("max_context_chars"),
                    "score_threshold": effective.get("score_threshold"),
                    "llm_model": llm_model,
                    "llm_provider": llm_provider,
                    "use_structure": effective.get("use_structure", False),
                    "rerank_enabled": effective.get("rerank_enabled", False),
                    "rerank_provider": effective.get("rerank_provider"),
                    "rerank_model": effective.get("rerank_model"),
                    "rerank_candidate_pool": effective.get("rerank_candidate_pool"),
                    "rerank_top_n": effective.get("rerank_top_n"),
                    "rerank_min_score": effective.get("rerank_min_score"),
                    "retrieval_mode": effective.get("retrieval_mode"),
                    "lexical_top_k": effective.get("lexical_top_k"),
                    "hybrid_dense_weight": effective.get("hybrid_dense_weight", 0.6),
                    "hybrid_lexical_weight": effective.get("hybrid_lexical_weight", 0.4),
                    "bm25_match_mode": effective.get("bm25_match_mode"),
                    "bm25_min_should_match": effective.get("bm25_min_should_match"),
                    "bm25_use_phrase": effective.get("bm25_use_phrase"),
                    "bm25_analyzer": effective.get("bm25_analyzer"),
                    "use_mmr": effective.get("use_mmr", False),
                    "mmr_diversity": effective.get("mmr_diversity", 0.5),
                    "use_self_check": bool(use_self_check),
                    "use_conversation_history": bool(use_history),
                    "conversation_history_limit": history_limit,
                    "use_document_filter": bool(effective_document_ids),
                    "document_ids": (
                        [str(doc_id) for doc_id in effective_document_ids]
                        if effective_document_ids
                        else None
                    ),
                    "context_expansion": effective.get("context_expansion"),
                    "context_window": effective.get("context_window"),
                }
            )
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
            prompt_version_id=rag_response.prompt_version_id,
            message_index=assistant_index,
        )
        db.add(assistant_message)
        await db.flush()
        conversation.updated_at = datetime.utcnow()

        if conversation.title is None:
            conversation.title = await build_conversation_title(
                db=db,
                kb_id=request.knowledge_base_id,
                question=request.question,
                answer=rag_response.answer,
                llm_model=request.llm_model,
                llm_provider=request.llm_provider,
            )
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
            prompt_version_id=rag_response.prompt_version_id,
            use_mmr=effective.get("use_mmr") if effective.get("use_mmr") else None,
            mmr_diversity=effective.get("mmr_diversity") if effective.get("use_mmr") else None,
            use_self_check=bool(use_self_check) if use_self_check else None,
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
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Knowledge base {kb_id} not found"
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
            detail=f"Conversation {conversation_id} not found",
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
            detail=f"Conversation {conversation_id} not found",
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


@router.patch("/conversations/{conversation_id}", response_model=ConversationDetail)
async def update_conversation(
    conversation_id: UUID,
    payload: ConversationTitleUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
):
    """Update conversation metadata (title)."""
    convo_query = select(ConversationModel).where(
        ConversationModel.id == conversation_id,
        ConversationModel.is_deleted == False,
    )
    convo_result = await db.execute(convo_query)
    conversation = convo_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found",
        )

    title = payload.title.strip() if payload.title else None
    conversation.title = title if title else None
    conversation.updated_at = datetime.utcnow()

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
            detail=f"Conversation {conversation_id} not found",
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
        response_messages.append(
            ChatMessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                sources=sources,
                model=msg.model,
                use_self_check=msg.use_self_check,
                prompt_version_id=msg.prompt_version_id,
                timestamp=msg.created_at,
                message_index=msg.message_index,
            )
        )

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
            detail=f"Conversation {conversation_id} not found",
        )

    msg_query = select(ChatMessageModel).where(
        ChatMessageModel.id == message_id,
        ChatMessageModel.conversation_id == conversation_id,
    )
    msg_result = await db.execute(msg_query)
    target_message = msg_result.scalar_one_or_none()
    if not target_message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Message {message_id} not found"
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

    await db.execute(delete(ChatMessageModel).where(ChatMessageModel.id.in_(deleted_ids)))
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
            detail=f"Conversation {conversation_id} not found",
        )

    conversation.is_deleted = True
    return {"status": "deleted", "id": str(conversation_id)}
