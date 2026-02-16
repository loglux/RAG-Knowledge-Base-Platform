"""Retrieve-only endpoint (no LLM generation)."""

import logging
import time
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.retrieval import get_retrieval_engine
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.models.database import AppSettings as AppSettingsModel
from app.models.database import KnowledgeBase as KnowledgeBaseModel
from app.models.schemas import (
    EffectiveRetrievalSettings,
    RetrieveRequest,
    RetrieveResponse,
    SourceChunk,
)
from app.services.rag import RAGService, get_rag_service
from app.services.retrieval_settings import resolve_retrieval_settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=RetrieveResponse)
async def retrieve_only(
    request: RetrieveRequest,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[UUID] = Depends(get_current_user_id),
    rag_service: RAGService = Depends(get_rag_service),
):
    """
    Retrieve relevant chunks from a knowledge base without generating an answer.
    """
    start_ts = time.perf_counter()

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

    if kb.document_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Knowledge base is empty. Please add documents first.",
        )

    settings_result = await db.execute(
        select(AppSettingsModel).order_by(AppSettingsModel.id).limit(1)
    )
    app_settings = settings_result.scalar_one_or_none()

    overrides = request.model_dump(exclude_none=True)
    overrides.pop("query", None)
    overrides.pop("knowledge_base_id", None)
    document_ids = overrides.pop("document_ids", None)
    debug_enabled = bool(overrides.pop("debug", False))

    effective = resolve_retrieval_settings(
        kb=kb,
        app_settings=app_settings,
        overrides=overrides,
    )

    document_filter = None
    if document_ids:
        document_ids = [str(doc_id) for doc_id in document_ids]
        document_filter = {
            "document_id": document_ids if len(document_ids) > 1 else document_ids[0]
        }

    chunk_filters = None
    if effective.get("use_structure"):
        try:
            chunk_filters = await rag_service._extract_structure_filters(
                question=request.query,
                kb_id=request.knowledge_base_id,
                db=db,
            )
        except Exception as exc:
            logger.warning("Structure filter extraction failed: %s", exc)
            chunk_filters = None

    if document_filter and chunk_filters and "document_id" in chunk_filters:
        if chunk_filters["document_id"] not in document_ids:
            return RetrieveResponse(
                query=request.query,
                knowledge_base_id=request.knowledge_base_id,
                total_found=0,
                chunks=[],
                context="",
                settings=EffectiveRetrievalSettings(**effective),
            )

    merged_filters = None
    if chunk_filters and document_filter:
        merged_filters = {**document_filter, **chunk_filters}
    elif chunk_filters:
        merged_filters = chunk_filters
    elif document_filter:
        merged_filters = document_filter

    retrieval_engine = get_retrieval_engine()

    mode = effective.get("retrieval_mode")
    if hasattr(mode, "value"):
        mode = mode.value

    mode_used = mode
    if mode == "hybrid":
        retrieval_result = await retrieval_engine.retrieve_hybrid(
            query=request.query,
            collection_name=kb.collection_name,
            embedding_model=kb.embedding_model,
            knowledge_base_id=str(request.knowledge_base_id),
            top_k=effective["top_k"],
            lexical_top_k=effective.get("lexical_top_k"),
            score_threshold=effective.get("score_threshold"),
            filters=merged_filters,
            dense_weight=effective.get("hybrid_dense_weight", 0.6),
            lexical_weight=effective.get("hybrid_lexical_weight", 0.4),
            bm25_match_mode=effective.get("bm25_match_mode"),
            bm25_min_should_match=effective.get("bm25_min_should_match"),
            bm25_use_phrase=effective.get("bm25_use_phrase"),
            bm25_analyzer=effective.get("bm25_analyzer"),
            use_mmr=effective.get("use_mmr", False),
            mmr_diversity=effective.get("mmr_diversity", 0.5),
        )
    else:
        retrieval_result = await retrieval_engine.retrieve(
            query=request.query,
            collection_name=kb.collection_name,
            embedding_model=kb.embedding_model,
            top_k=effective["top_k"],
            score_threshold=effective.get("score_threshold"),
            filters=merged_filters,
            use_mmr=effective.get("use_mmr", False),
            mmr_diversity=effective.get("mmr_diversity", 0.5),
        )

    chunks = retrieval_result.chunks
    expansion_modes = effective.get("context_expansion") or []
    window_size = effective.get("context_window") or 0
    if "window" in expansion_modes and window_size > 0:
        chunks = await retrieval_engine.expand_windowed(
            collection_name=kb.collection_name,
            chunks=chunks,
            window_size=window_size,
        )

    max_context_chars = effective.get("max_context_chars")
    if max_context_chars is not None:
        context = retrieval_engine._assemble_context(chunks, max_length=max_context_chars)
    else:
        context = retrieval_engine._assemble_context(chunks)

    response_chunks = [
        SourceChunk(
            text=chunk.text,
            score=chunk.score,
            document_id=chunk.document_id,
            filename=chunk.filename,
            chunk_index=chunk.chunk_index,
            metadata=chunk.metadata,
        )
        for chunk in chunks
    ]

    debug_payload = None
    if debug_enabled:
        debug_payload = {
            "mode_requested": mode,
            "mode_used": mode_used,
            "collection_name": kb.collection_name,
            "embedding_model": kb.embedding_model,
            "filters": merged_filters,
            "document_filter": document_filter,
            "structure_filters": chunk_filters,
            "context_chars": len(context),
            "chunks_before_expansion": len(retrieval_result.chunks),
            "chunks_after_expansion": len(chunks),
            "context_window": window_size if "window" in expansion_modes else 0,
            "elapsed_ms": int((time.perf_counter() - start_ts) * 1000),
        }

    return RetrieveResponse(
        query=request.query,
        knowledge_base_id=request.knowledge_base_id,
        total_found=len(chunks),
        chunks=response_chunks,
        context=context,
        settings=EffectiveRetrievalSettings(**effective),
        debug=debug_payload,
    )
