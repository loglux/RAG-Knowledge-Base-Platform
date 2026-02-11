"""FastMCP server exposing RAG tools."""

import json
import logging
from typing import Any, Dict, Optional, List
from uuid import UUID

from sqlalchemy import select

from mcp.server.fastmcp import FastMCP

from app.config import settings
from app.db.session import get_db_session
from app.models.database import KnowledgeBase as KnowledgeBaseModel, Document as DocumentModel, AppSettings as AppSettingsModel
from app.services.rag import get_rag_service
from app.services.retrieval_settings import resolve_retrieval_settings, load_kb_retrieval_settings
from app.core.retrieval import get_retrieval_engine
from app.core.system_settings import SystemSettingsManager

logger = logging.getLogger(__name__)

MCP_TOOL_NAMES = [
    "rag_query",
    "list_knowledge_bases",
    "list_documents",
    "retrieve_chunks",
    "get_kb_retrieval_settings",
    "set_kb_retrieval_settings",
    "clear_kb_retrieval_settings",
]


async def _get_enabled_tools() -> List[str]:
    async with get_db_session() as db:
        raw = await SystemSettingsManager.get_setting(db, "mcp_tools_enabled")
    if raw is None:
        return settings.MCP_TOOLS_ENABLED
    raw = raw.strip()
    if raw.startswith("["):
        try:
            return json.loads(raw)
        except Exception:
            return settings.MCP_TOOLS_ENABLED
    return [item.strip() for item in raw.split(",") if item.strip()]


async def _ensure_tool_enabled(name: str) -> Optional[str]:
    enabled = await _get_enabled_tools()
    if name not in enabled:
        return f"Error: MCP tool '{name}' is disabled."
    return None


async def _get_kb(db, kb_id: Optional[str]) -> Optional[KnowledgeBaseModel]:
    if not kb_id:
        kb_id = settings.MCP_DEFAULT_KB_ID
    if not kb_id:
        return None
    try:
        kb_uuid = UUID(str(kb_id))
    except Exception:
        return None
    return await db.get(KnowledgeBaseModel, kb_uuid)


def _format_sources(sources: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for source in sources[:100]:
        filename = source.get("filename", "unknown")
        chunk_index = source.get("chunk_index", "?")
        score = source.get("score", "?")
        snippet = source.get("text", "").strip().replace("\n", " ")
        if len(snippet) > 200:
            snippet = snippet[:200] + "…"
        lines.append(f"- {filename} (chunk {chunk_index}, score {score}): {snippet}")
    return "\n".join(lines)


def build_mcp_app() -> FastMCP:
    mcp = FastMCP(
        "RAG MCP Server",
        stateless_http=True,
        json_response=True,
        streamable_http_path="/",
    )

    @mcp.tool()
    async def rag_query(
        question: str,
        knowledge_base_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Query the RAG backend and return answer with sources."""
        disabled = await _ensure_tool_enabled("rag_query")
        if disabled:
            return disabled

        async with get_db_session() as db:
            kb = await _get_kb(db, knowledge_base_id)
            if not kb:
                return "Error: knowledge_base_id is required (no default configured)."
            if kb.is_deleted:
                return f"Error: knowledge base {kb.id} is deleted."
            if kb.document_count == 0:
                return "Error: knowledge base is empty."

            settings_result = await db.execute(
                select(AppSettingsModel).order_by(AppSettingsModel.id).limit(1)
            )
            app_settings = settings_result.scalar_one_or_none()

            overrides = options or {}
            effective = resolve_retrieval_settings(kb=kb, app_settings=app_settings, overrides=overrides)

            rag_service = get_rag_service()
            response = await rag_service.query(
                question=question,
                collection_name=kb.collection_name,
                embedding_model=kb.embedding_model,
                top_k=effective.get("top_k", 5),
                retrieval_mode=effective.get("retrieval_mode", "dense"),
                lexical_top_k=effective.get("lexical_top_k"),
                dense_weight=effective.get("hybrid_dense_weight", 0.6),
                lexical_weight=effective.get("hybrid_lexical_weight", 0.4),
                bm25_match_mode=effective.get("bm25_match_mode"),
                bm25_min_should_match=effective.get("bm25_min_should_match"),
                bm25_use_phrase=effective.get("bm25_use_phrase"),
                bm25_analyzer=effective.get("bm25_analyzer"),
                temperature=effective.get("temperature", 0.7),
                max_tokens=effective.get("max_tokens"),
                max_context_chars=effective.get("max_context_chars"),
                score_threshold=effective.get("score_threshold"),
                llm_model=effective.get("llm_model"),
                llm_provider=effective.get("llm_provider"),
                use_structure=effective.get("use_structure", False),
                use_mmr=effective.get("use_mmr", False),
                mmr_diversity=effective.get("mmr_diversity", 0.5),
                document_ids=effective.get("document_ids"),
                context_expansion=effective.get("context_expansion"),
                context_window=effective.get("context_window"),
                db=db,
                kb_id=kb.id,
            )

        parts = [response.answer]
        if conversation_id:
            parts.append(f"\nConversation ID: {conversation_id}")
        if response.sources:
            source_lines = _format_sources([s.model_dump() for s in response.sources])
            if source_lines:
                parts.append("\nSources:\n" + source_lines)
        return "\n".join(p for p in parts if p)

    @mcp.tool()
    async def list_knowledge_bases(page: int = 1, page_size: int = 50) -> str:
        """List knowledge bases in the backend."""
        disabled = await _ensure_tool_enabled("list_knowledge_bases")
        if disabled:
            return disabled

        async with get_db_session() as db:
            result = await db.execute(
                select(KnowledgeBaseModel)
                .where(KnowledgeBaseModel.is_deleted == False)
                .order_by(KnowledgeBaseModel.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            items = result.scalars().all()

        if not items:
            return "No knowledge bases found."

        lines = []
        for kb in items:
            lines.append(f"- {kb.name} (id={kb.id}, documents={kb.document_count})")
        return "\n".join(lines)

    @mcp.tool()
    async def list_documents(knowledge_base_id: str, page: int = 1, page_size: int = 100) -> str:
        """List documents for a knowledge base."""
        disabled = await _ensure_tool_enabled("list_documents")
        if disabled:
            return disabled

        async with get_db_session() as db:
            kb = await _get_kb(db, knowledge_base_id)
            if not kb:
                return "Error: knowledge_base_id is required."
            result = await db.execute(
                select(DocumentModel)
                .where(DocumentModel.knowledge_base_id == kb.id, DocumentModel.is_deleted == False)
                .order_by(DocumentModel.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            rows = result.scalars().all()

        if not rows:
            return "No documents found for this knowledge base."

        lines = []
        for doc in rows:
            lines.append(f"- {doc.filename} (id={doc.id}, status={doc.status})")
        return "\n".join(lines)

    @mcp.tool()
    async def retrieve_chunks(
        query: str,
        knowledge_base_id: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Retrieve relevant chunks without generating an answer."""
        disabled = await _ensure_tool_enabled("retrieve_chunks")
        if disabled:
            return disabled

        async with get_db_session() as db:
            kb = await _get_kb(db, knowledge_base_id)
            if not kb:
                return "Error: knowledge_base_id is required."
            if kb.document_count == 0:
                return "Error: knowledge base is empty."

            settings_result = await db.execute(
                select(AppSettingsModel).order_by(AppSettingsModel.id).limit(1)
            )
            app_settings = settings_result.scalar_one_or_none()

            overrides = options or {}
            effective = resolve_retrieval_settings(kb=kb, app_settings=app_settings, overrides=overrides)

            retrieval_engine = get_retrieval_engine()
            mode = effective.get("retrieval_mode")
            if hasattr(mode, "value"):
                mode = mode.value

            if mode == "hybrid":
                retrieval_result = await retrieval_engine.retrieve_hybrid(
                    query=query,
                    collection_name=kb.collection_name,
                    embedding_model=kb.embedding_model,
                    knowledge_base_id=str(kb.id),
                    top_k=effective.get("top_k", 5),
                    lexical_top_k=effective.get("lexical_top_k"),
                    score_threshold=effective.get("score_threshold"),
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
                    query=query,
                    collection_name=kb.collection_name,
                    embedding_model=kb.embedding_model,
                    top_k=effective.get("top_k", 5),
                    score_threshold=effective.get("score_threshold"),
                    use_mmr=effective.get("use_mmr", False),
                    mmr_diversity=effective.get("mmr_diversity", 0.5),
                )

            chunks = retrieval_result.chunks
            context = retrieval_engine._assemble_context(chunks, max_length=effective.get("max_context_chars"))

        if not chunks:
            return "No results."

        lines = []
        lines.append(f"Total found: {len(chunks)}")
        if context:
            lines.append("Context used:")
            lines.append(context)
        source_lines = _format_sources([chunk.model_dump() for chunk in chunks])
        if source_lines:
            lines.append("Sources:")
            lines.append(source_lines)
        return "\n".join(lines)

    @mcp.tool()
    async def get_kb_retrieval_settings(knowledge_base_id: str) -> str:
        """Get retrieval settings for a knowledge base."""
        disabled = await _ensure_tool_enabled("get_kb_retrieval_settings")
        if disabled:
            return disabled

        async with get_db_session() as db:
            kb = await _get_kb(db, knowledge_base_id)
            if not kb:
                return "Error: knowledge_base_id is required."
            settings_result = await db.execute(
                select(AppSettingsModel).order_by(AppSettingsModel.id).limit(1)
            )
            app_settings = settings_result.scalar_one_or_none()
            stored = load_kb_retrieval_settings(kb)
            effective = resolve_retrieval_settings(kb=kb, app_settings=app_settings, overrides=None)

        payload = {
            "stored": stored,
            "effective": effective,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    @mcp.tool()
    async def set_kb_retrieval_settings(knowledge_base_id: str, settings_payload: Dict[str, Any]) -> str:
        """Set retrieval settings for a knowledge base."""
        disabled = await _ensure_tool_enabled("set_kb_retrieval_settings")
        if disabled:
            return disabled

        async with get_db_session() as db:
            kb = await _get_kb(db, knowledge_base_id)
            if not kb:
                return "Error: knowledge_base_id is required."
            kb.retrieval_settings_json = json.dumps(settings_payload) if settings_payload else None
            await db.commit()
        return "OK"

    @mcp.tool()
    async def clear_kb_retrieval_settings(knowledge_base_id: str) -> str:
        """Clear retrieval settings for a knowledge base."""
        disabled = await _ensure_tool_enabled("clear_kb_retrieval_settings")
        if disabled:
            return disabled

        async with get_db_session() as db:
            kb = await _get_kb(db, knowledge_base_id)
            if not kb:
                return "Error: knowledge_base_id is required."
            kb.retrieval_settings_json = None
            await db.commit()
        return "OK"

    return mcp


def get_mcp_app():
    mcp = build_mcp_app()
    if hasattr(mcp, "streamable_http_app"):
        return mcp.streamable_http_app()
    if hasattr(mcp, "http_app"):
        return mcp.http_app()
    raise RuntimeError("FastMCP does not expose an HTTP app factory")
