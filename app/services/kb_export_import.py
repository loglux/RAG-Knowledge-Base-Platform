"""KB export/import helpers (MVP)."""
from __future__ import annotations

import json
import os
import tarfile
import zipfile
import tempfile
import shutil
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from qdrant_client.models import Filter, FieldCondition, MatchValue, PointStruct, Distance
from opensearchpy.helpers import async_bulk

from app.api.v1.knowledge_bases import kb_id_to_collection_name
from app.core.vector_store import get_vector_store
from app.core.lexical_store import get_lexical_store
from app.models.database import (
    KnowledgeBase as KnowledgeBaseModel,
    Document as DocumentModel,
    DocumentStructure as DocumentStructureModel,
    Conversation as ConversationModel,
    ChatMessage as ChatMessageModel,
)
from app.models.enums import DocumentStatus, ChunkingStrategy, FileType
from app.models.schemas import KBExportInclude, KBImportOptions


EXPORT_VERSION = "1.0"


class KBExportImportError(RuntimeError):
    pass


def _ensure_include(include: Optional[KBExportInclude]) -> KBExportInclude:
    return include or KBExportInclude()


def _dt(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _write_jsonl(path: str, rows: Iterable[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


async def export_kbs(
    db: AsyncSession,
    kb_ids: List[UUID],
    include: Optional[KBExportInclude],
) -> tuple[str, str]:
    include = _ensure_include(include)
    if not include.documents and (include.vectors or include.bm25):
        raise KBExportImportError("documents must be included when exporting vectors or BM25 data")
    if include.chats and not include.documents:
        raise KBExportImportError("documents must be included when exporting chats")

    kb_query = select(KnowledgeBaseModel).where(
        KnowledgeBaseModel.id.in_(kb_ids),
        KnowledgeBaseModel.is_deleted == False,
    )
    kb_result = await db.execute(kb_query)
    kbs = kb_result.scalars().all()
    if len(kbs) != len(kb_ids):
        raise KBExportImportError("One or more knowledge bases not found")

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    export_root = tempfile.mkdtemp(prefix="kb_export_")
    export_dir = os.path.join(export_root, f"kb_export_{timestamp}")
    os.makedirs(export_dir, exist_ok=True)

    metadata = {
        "export_version": EXPORT_VERSION,
        "created_at": datetime.utcnow().isoformat(),
        "kb_ids": [str(kb.id) for kb in kbs],
        "include": include.model_dump(),
        "source": {
            "app_version": "unknown",
            "schema_version": "unknown",
        },
    }
    with open(os.path.join(export_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    db_dir = os.path.join(export_dir, "db")
    os.makedirs(db_dir, exist_ok=True)

    kb_rows = []
    for kb in kbs:
        kb_rows.append({
            "id": str(kb.id),
            "name": kb.name,
            "description": kb.description,
            "collection_name": kb.collection_name,
            "embedding_model": kb.embedding_model,
            "embedding_provider": kb.embedding_provider,
            "embedding_dimension": kb.embedding_dimension,
            "chunk_size": kb.chunk_size,
            "chunk_overlap": kb.chunk_overlap,
            "chunking_strategy": kb.chunking_strategy.value if kb.chunking_strategy else None,
            "upsert_batch_size": kb.upsert_batch_size,
            "bm25_match_mode": kb.bm25_match_mode,
            "bm25_min_should_match": kb.bm25_min_should_match,
            "bm25_use_phrase": kb.bm25_use_phrase,
            "bm25_analyzer": kb.bm25_analyzer,
            "structure_llm_model": kb.structure_llm_model,
            "use_llm_chat_titles": kb.use_llm_chat_titles,
            "retrieval_settings_json": kb.retrieval_settings_json,
            "document_count": kb.document_count,
            "total_chunks": kb.total_chunks,
            "user_id": str(kb.user_id) if kb.user_id else None,
            "created_at": _dt(kb.created_at),
            "updated_at": _dt(kb.updated_at),
            "is_deleted": kb.is_deleted,
        })
    _write_jsonl(os.path.join(db_dir, "knowledge_bases.jsonl"), kb_rows)

    documents = []
    doc_rows = []
    if include.documents:
        doc_query = select(DocumentModel).where(
            DocumentModel.knowledge_base_id.in_(kb_ids),
            DocumentModel.is_deleted == False,
        )
        doc_result = await db.execute(doc_query)
        doc_rows = doc_result.scalars().all()
        for doc in doc_rows:
            documents.append({
                "id": str(doc.id),
                "knowledge_base_id": str(doc.knowledge_base_id),
                "filename": doc.filename,
                "file_type": doc.file_type.value if doc.file_type else None,
                "file_size": doc.file_size,
                "content": doc.content,
                "content_hash": doc.content_hash,
                "status": doc.status.value if doc.status else None,
                "embeddings_status": doc.embeddings_status.value if doc.embeddings_status else None,
                "bm25_status": doc.bm25_status.value if doc.bm25_status else None,
                "error_message": doc.error_message,
                "processing_stage": doc.processing_stage,
                "progress_percentage": doc.progress_percentage,
                "chunk_count": doc.chunk_count,
                "vector_ids": doc.vector_ids,
                "user_id": str(doc.user_id) if doc.user_id else None,
                "created_at": _dt(doc.created_at),
                "updated_at": _dt(doc.updated_at),
                "processed_at": _dt(doc.processed_at),
                "is_deleted": doc.is_deleted,
            })
    _write_jsonl(os.path.join(db_dir, "documents.jsonl"), documents)

    structures = []
    if include.documents:
        doc_ids = [doc.id for doc in doc_rows]
        if doc_ids:
            struct_query = select(DocumentStructureModel).where(
                DocumentStructureModel.document_id.in_(doc_ids)
            )
            struct_result = await db.execute(struct_query)
            struct_rows = struct_result.scalars().all()
        else:
            struct_rows = []

        for struct in struct_rows:
            structures.append({
                "id": str(struct.id),
                "document_id": str(struct.document_id),
                "toc_json": struct.toc_json,
                "document_type": struct.document_type,
                "approved_by_user": struct.approved_by_user,
                "created_at": _dt(struct.created_at),
                "updated_at": _dt(struct.updated_at),
            })
    _write_jsonl(os.path.join(db_dir, "document_structures.jsonl"), structures)

    conversations = []
    messages = []
    if include.chats:
        convo_query = select(ConversationModel).where(
            ConversationModel.knowledge_base_id.in_(kb_ids),
            ConversationModel.is_deleted == False,
        )
        convo_result = await db.execute(convo_query)
        convo_rows = convo_result.scalars().all()
        convo_ids = [c.id for c in convo_rows]

        for convo in convo_rows:
            conversations.append({
                "id": str(convo.id),
                "knowledge_base_id": str(convo.knowledge_base_id),
                "title": convo.title,
                "settings_json": convo.settings_json,
                "user_id": str(convo.user_id) if convo.user_id else None,
                "created_at": _dt(convo.created_at),
                "updated_at": _dt(convo.updated_at),
                "is_deleted": convo.is_deleted,
            })

        if convo_ids:
            msg_query = select(ChatMessageModel).where(
                ChatMessageModel.conversation_id.in_(convo_ids)
            )
            msg_result = await db.execute(msg_query)
            msg_rows = msg_result.scalars().all()
        else:
            msg_rows = []

        for msg in msg_rows:
            messages.append({
                "id": str(msg.id),
                "conversation_id": str(msg.conversation_id),
                "role": msg.role,
                "content": msg.content,
                "sources_json": msg.sources_json,
                "model": msg.model,
                "use_self_check": msg.use_self_check,
                "prompt_version_id": str(msg.prompt_version_id) if msg.prompt_version_id else None,
                "message_index": msg.message_index,
                "created_at": _dt(msg.created_at),
            })

        _write_jsonl(os.path.join(db_dir, "conversations.jsonl"), conversations)
        _write_jsonl(os.path.join(db_dir, "chat_messages.jsonl"), messages)

    if include.vectors:
        qdrant_dir = os.path.join(export_dir, "qdrant")
        os.makedirs(qdrant_dir, exist_ok=True)
        vector_store = get_vector_store()
        client = vector_store.client

        for kb in kbs:
            out_path = os.path.join(qdrant_dir, f"{kb.collection_name}.jsonl")
            with open(out_path, "w", encoding="utf-8") as f:
                next_offset = None
                while True:
                    result = await client.scroll(
                        collection_name=kb.collection_name,
                        scroll_filter=Filter(
                            must=[FieldCondition(
                                key="knowledge_base_id",
                                match=MatchValue(value=str(kb.id)),
                            )]
                        ),
                        limit=200,
                        offset=next_offset,
                        with_payload=True,
                        with_vectors=True,
                    )
                    if isinstance(result, tuple):
                        points, next_offset = result
                    else:
                        points = result
                        next_offset = None

                    if not points:
                        break

                    for point in points:
                        record = {
                            "id": str(point.id),
                            "vector": point.vector,
                            "payload": point.payload or {},
                        }
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")

                    if next_offset is None:
                        break

    if include.bm25:
        opensearch_dir = os.path.join(export_dir, "opensearch")
        os.makedirs(opensearch_dir, exist_ok=True)
        lexical_store = get_lexical_store()
        client = lexical_store.client
        index_name = lexical_store.index_name

        for kb in kbs:
            out_path = os.path.join(opensearch_dir, f"{index_name}_{kb.id}.jsonl")
            with open(out_path, "w", encoding="utf-8") as f:
                resp = await client.search(
                    index=index_name,
                    body={"query": {"term": {"knowledge_base_id": str(kb.id)}}},
                    scroll="2m",
                    size=200,
                )
                scroll_id = resp.get("_scroll_id")
                while True:
                    hits = resp.get("hits", {}).get("hits", [])
                    if not hits:
                        break
                    for hit in hits:
                        record = {
                            "_id": hit.get("_id"),
                            "_source": hit.get("_source", {}),
                        }
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    resp = await client.scroll(scroll_id=scroll_id, scroll="2m")
                    scroll_id = resp.get("_scroll_id")

                if scroll_id:
                    try:
                        await client.clear_scroll(scroll_id=scroll_id)
                    except Exception:
                        pass

    if include.uploads:
        uploads_src = os.path.join(os.getcwd(), "uploads")
        uploads_dst = os.path.join(export_dir, "uploads")
        if os.path.isdir(uploads_src):
            shutil.copytree(uploads_src, uploads_dst)

    archive_name = f"kb_export_{timestamp}.tar.gz"
    archive_path = os.path.join(export_root, archive_name)
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(export_dir, arcname=os.path.basename(export_dir))

    shutil.rmtree(export_dir, ignore_errors=True)
    return archive_path, archive_name


async def export_chats_markdown(
    db: AsyncSession,
    kb_ids: List[UUID],
) -> tuple[str, str]:
    kb_query = select(KnowledgeBaseModel).where(
        KnowledgeBaseModel.id.in_(kb_ids),
        KnowledgeBaseModel.is_deleted == False,
    )
    kb_result = await db.execute(kb_query)
    kbs = kb_result.scalars().all()
    if len(kbs) != len(kb_ids):
        raise KBExportImportError("One or more knowledge bases not found")

    convo_query = select(ConversationModel).where(
        ConversationModel.knowledge_base_id.in_(kb_ids),
        ConversationModel.is_deleted == False,
    )
    convo_result = await db.execute(convo_query)
    convo_rows = convo_result.scalars().all()
    convo_ids = [c.id for c in convo_rows]

    if convo_ids:
        msg_query = select(ChatMessageModel).where(
            ChatMessageModel.conversation_id.in_(convo_ids)
        )
        msg_result = await db.execute(msg_query)
        msg_rows = msg_result.scalars().all()
    else:
        msg_rows = []

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    export_root = tempfile.mkdtemp(prefix="kb_chats_md_")
    export_dir = os.path.join(export_root, f"kb_chats_md_{timestamp}")
    os.makedirs(export_dir, exist_ok=True)

    messages_by_convo: Dict[str, List[ChatMessageModel]] = {}
    for msg in msg_rows:
        messages_by_convo.setdefault(str(msg.conversation_id), []).append(msg)

    for convo in convo_rows:
        convo_id = str(convo.id)
        convo_msgs = sorted(
            messages_by_convo.get(convo_id, []),
            key=lambda m: m.message_index,
        )
        title = convo.title or f"Conversation {convo_id}"
        filename = f"{convo_id}.md"
        out_path = os.path.join(export_dir, filename)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(f"- KB: {convo.knowledge_base_id}\n")
            f.write(f"- Conversation ID: {convo_id}\n")
            f.write(f"- Created: {_dt(convo.created_at)}\n")
            f.write(f"- Updated: {_dt(convo.updated_at)}\n")
            if convo.settings_json:
                f.write("\n## Settings\n\n")
                f.write("```json\n")
                f.write(convo.settings_json)
                f.write("\n```\n")
            f.write("\n## Messages\n\n")
            for msg in convo_msgs:
                role = (msg.role or "assistant").capitalize()
                f.write(f"**{role}:** {msg.content}\n\n")
                if msg.sources_json:
                    try:
                        sources = json.loads(msg.sources_json)
                    except Exception:
                        sources = []
                    if sources:
                        f.write("> Sources:\n")
                        for source in sources:
                            doc_id = source.get("document_id")
                            filename = source.get("filename")
                            chunk_index = source.get("chunk_index")
                            f.write(f"> - {filename} (doc_id={doc_id}, chunk={chunk_index})\n")
                        f.write("\n")

    archive_name = f"kb_chats_{timestamp}.zip"
    archive_path = os.path.join(export_root, archive_name)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in os.listdir(export_dir):
            full = os.path.join(export_dir, name)
            if os.path.isfile(full):
                zf.write(full, arcname=name)

    shutil.rmtree(export_dir, ignore_errors=True)
    return archive_path, archive_name


async def import_kbs(
    db: AsyncSession,
    archive_path: str,
    options: KBImportOptions,
) -> Dict[str, Any]:
    include = _ensure_include(options.include)
    if not include.documents and (include.vectors or include.bm25):
        raise KBExportImportError("documents must be included when importing vectors or BM25 data")
    if include.chats and not include.documents:
        raise KBExportImportError("documents must be included when importing chats")

    if options.mode not in {"create", "merge"}:
        raise KBExportImportError("Only create/merge modes are supported in MVP")

    temp_dir = tempfile.mkdtemp(prefix="kb_import_")
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(temp_dir)

        roots = [d for d in os.listdir(temp_dir) if d.startswith("kb_export_")]
        if not roots:
            raise KBExportImportError("Invalid archive: missing export root")
        root = os.path.join(temp_dir, roots[0])

        meta_path = os.path.join(root, "metadata.json")
        if not os.path.exists(meta_path):
            raise KBExportImportError("Invalid archive: missing metadata.json")
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        if options.include is None:
            include = KBExportInclude(**metadata.get("include", {}))

        db_dir = os.path.join(root, "db")
        kb_rows = _read_jsonl(os.path.join(db_dir, "knowledge_bases.jsonl"))
        doc_rows = _read_jsonl(os.path.join(db_dir, "documents.jsonl"))
        struct_rows = _read_jsonl(os.path.join(db_dir, "document_structures.jsonl"))
        convo_path = os.path.join(db_dir, "conversations.jsonl")
        msg_path = os.path.join(db_dir, "chat_messages.jsonl")
        if include.chats and (not os.path.exists(convo_path) or not os.path.exists(msg_path)):
            raise KBExportImportError("Chat export files missing from archive")
        convo_rows = _read_jsonl(convo_path)
        msg_rows = _read_jsonl(msg_path)

        if not include.documents:
            doc_rows = []
            struct_rows = []
            convo_rows = []
            msg_rows = []
    
        target_kb = None
        if options.target_kb_id:
            if options.mode != "merge":
                raise KBExportImportError("target_kb_id is only valid for merge mode")
            if len(kb_rows) != 1:
                raise KBExportImportError("target_kb_id requires a single-KB archive")
            existing_result = await db.execute(
                select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == options.target_kb_id)
            )
            target_kb = existing_result.scalar_one_or_none()
            if not target_kb:
                raise KBExportImportError(f"Target KB not found: {options.target_kb_id}")
    
        kb_id_map: Dict[str, str] = {}
        doc_id_map: Dict[str, str] = {}
        for kb in kb_rows:
            old_id = kb["id"]
            new_id = str(target_kb.id) if target_kb else (str(uuid4()) if options.remap_ids else old_id)
            kb_id_map[old_id] = new_id
        for doc in doc_rows:
            old_id = doc["id"]
            new_id = str(uuid4()) if options.remap_ids else old_id
            doc_id_map[old_id] = new_id

        kb_created = 0
        kb_updated = 0
        for kb in kb_rows:
            kb_id = UUID(kb_id_map[kb["id"]])
            collection_name = (
                target_kb.collection_name
                if target_kb
                else (kb_id_to_collection_name(kb_id) if options.remap_ids else kb["collection_name"])
            )

            existing = None
            if target_kb:
                existing = target_kb
            elif options.mode == "merge" and not options.remap_ids:
                existing_result = await db.execute(
                    select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id)
                )
                existing = existing_result.scalar_one_or_none()

            if target_kb:
                if include.vectors:
                    if (
                        target_kb.embedding_dimension != kb["embedding_dimension"]
                        or target_kb.embedding_model != kb["embedding_model"]
                        or target_kb.embedding_provider != kb["embedding_provider"]
                    ):
                        raise KBExportImportError(
                            "Target KB embedding settings do not match archive (model/provider/dimension). "
                            "Choose a KB with the same embedding setup, or import without vectors and reindex."
                        )
                kb_updated += 1
                continue

            if existing:
                existing.name = kb["name"]
                existing.description = kb.get("description")
                existing.collection_name = collection_name
                existing.embedding_model = kb["embedding_model"]
                existing.embedding_provider = kb["embedding_provider"]
                existing.embedding_dimension = kb["embedding_dimension"]
                existing.chunk_size = kb["chunk_size"]
                existing.chunk_overlap = kb["chunk_overlap"]
                if kb.get("chunking_strategy"):
                    existing.chunking_strategy = ChunkingStrategy(kb["chunking_strategy"])
                existing.upsert_batch_size = kb["upsert_batch_size"]
                existing.bm25_match_mode = kb.get("bm25_match_mode")
                existing.bm25_min_should_match = kb.get("bm25_min_should_match")
                existing.bm25_use_phrase = kb.get("bm25_use_phrase")
                existing.bm25_analyzer = kb.get("bm25_analyzer")
                existing.structure_llm_model = kb.get("structure_llm_model")
                existing.use_llm_chat_titles = kb.get("use_llm_chat_titles")
                existing.retrieval_settings_json = kb.get("retrieval_settings_json")
                existing.document_count = kb.get("document_count", 0)
                existing.total_chunks = kb.get("total_chunks", 0)
                kb_updated += 1
            else:
                kb_model = KnowledgeBaseModel(
                    id=kb_id,
                    name=kb["name"],
                    description=kb.get("description"),
                    collection_name=collection_name,
                    embedding_model=kb["embedding_model"],
                    embedding_provider=kb["embedding_provider"],
                    embedding_dimension=kb["embedding_dimension"],
                    chunk_size=kb["chunk_size"],
                    chunk_overlap=kb["chunk_overlap"],
                    chunking_strategy=ChunkingStrategy(kb["chunking_strategy"])
                    if kb.get("chunking_strategy") else None,
                    upsert_batch_size=kb["upsert_batch_size"],
                    bm25_match_mode=kb.get("bm25_match_mode"),
                    bm25_min_should_match=kb.get("bm25_min_should_match"),
                    bm25_use_phrase=kb.get("bm25_use_phrase"),
                    bm25_analyzer=kb.get("bm25_analyzer"),
                    structure_llm_model=kb.get("structure_llm_model"),
                    use_llm_chat_titles=kb.get("use_llm_chat_titles"),
                    retrieval_settings_json=kb.get("retrieval_settings_json"),
                    document_count=kb.get("document_count", 0),
                    total_chunks=kb.get("total_chunks", 0),
                )
                db.add(kb_model)
                kb_created += 1
    
        for doc in doc_rows:
            doc_id = UUID(doc_id_map[doc["id"]])
            kb_id = UUID(kb_id_map[doc["knowledge_base_id"]])
            existing = None
            if options.mode == "merge" and not options.remap_ids:
                existing_result = await db.execute(
                    select(DocumentModel).where(DocumentModel.id == doc_id)
                )
                existing = existing_result.scalar_one_or_none()

            file_type = FileType(doc["file_type"]) if doc.get("file_type") else None
            status = DocumentStatus(doc["status"]) if doc.get("status") else None
            embeddings_status = DocumentStatus(doc["embeddings_status"]) if doc.get("embeddings_status") else None
            bm25_status = DocumentStatus(doc["bm25_status"]) if doc.get("bm25_status") else None

            if existing:
                existing.knowledge_base_id = kb_id
                existing.filename = doc["filename"]
                existing.file_type = file_type
                existing.file_size = doc["file_size"]
                existing.content = doc["content"]
                existing.content_hash = doc["content_hash"]
                existing.status = status
                existing.embeddings_status = embeddings_status
                existing.bm25_status = bm25_status
                existing.error_message = doc.get("error_message")
                existing.processing_stage = doc.get("processing_stage")
                existing.progress_percentage = doc.get("progress_percentage", 0)
                existing.chunk_count = doc.get("chunk_count", 0)
                existing.vector_ids = doc.get("vector_ids")
            else:
                doc_model = DocumentModel(
                    id=doc_id,
                    knowledge_base_id=kb_id,
                    filename=doc["filename"],
                    file_type=file_type,
                    file_size=doc["file_size"],
                    content=doc["content"],
                    content_hash=doc["content_hash"],
                    status=status,
                    embeddings_status=embeddings_status,
                    bm25_status=bm25_status,
                    error_message=doc.get("error_message"),
                    processing_stage=doc.get("processing_stage"),
                    progress_percentage=doc.get("progress_percentage", 0),
                    chunk_count=doc.get("chunk_count", 0),
                    vector_ids=doc.get("vector_ids"),
                )
                db.add(doc_model)

        for struct in struct_rows:
            doc_id = UUID(doc_id_map[struct["document_id"]])
            if options.mode == "merge" and not options.remap_ids:
                existing_result = await db.execute(
                    select(DocumentStructureModel).where(DocumentStructureModel.document_id == doc_id)
                )
                existing = existing_result.scalar_one_or_none()
            else:
                existing = None

            if existing:
                existing.toc_json = struct["toc_json"]
                existing.document_type = struct.get("document_type")
                existing.approved_by_user = struct.get("approved_by_user", False)
            else:
                struct_id = uuid4() if options.remap_ids else UUID(struct["id"])
                model = DocumentStructureModel(
                    id=struct_id,
                    document_id=doc_id,
                    toc_json=struct["toc_json"],
                    document_type=struct.get("document_type"),
                    approved_by_user=struct.get("approved_by_user", False),
                )
                db.add(model)

        convo_id_map: Dict[str, str] = {}
        if include.chats and convo_rows:
            valid_kb_ids = {str(kb["id"]) for kb in kb_rows}
            for convo in convo_rows:
                old_id = convo["id"]
                new_id = str(uuid4()) if options.remap_ids else old_id
                convo_id_map[old_id] = new_id

            for convo in convo_rows:
                new_convo_id = UUID(convo_id_map[convo["id"]])
                old_kb_id = str(convo["knowledge_base_id"])
                if target_kb:
                    new_kb_id = str(target_kb.id)
                else:
                    if old_kb_id not in valid_kb_ids:
                        raise KBExportImportError(
                            f"Conversation references KB not in archive: {old_kb_id}"
                        )
                    new_kb_id = kb_id_map.get(old_kb_id)
                    if not new_kb_id:
                        raise KBExportImportError(
                            f"Conversation references KB not in archive: {old_kb_id}"
                        )

                convo_model = ConversationModel(
                    id=new_convo_id,
                    knowledge_base_id=UUID(new_kb_id),
                    title=convo.get("title"),
                    settings_json=convo.get("settings_json"),
                    user_id=None,
                    created_at=_parse_dt(convo.get("created_at")) or datetime.utcnow(),
                    updated_at=_parse_dt(convo.get("updated_at")) or datetime.utcnow(),
                    is_deleted=convo.get("is_deleted", False),
                )
                db.add(convo_model)

            for msg in msg_rows:
                old_convo_id = msg["conversation_id"]
                if old_convo_id not in convo_id_map:
                    continue
                new_convo_id = UUID(convo_id_map[old_convo_id])

                sources_json = msg.get("sources_json")
                if sources_json:
                    try:
                        sources = json.loads(sources_json)
                        for source in sources:
                            old_doc_id = source.get("document_id")
                            if old_doc_id in doc_id_map:
                                source["document_id"] = doc_id_map[old_doc_id]
                        sources_json = json.dumps(sources, ensure_ascii=False)
                    except Exception:
                        sources_json = None

                msg_model = ChatMessageModel(
                    id=uuid4() if options.remap_ids else UUID(msg["id"]),
                    conversation_id=new_convo_id,
                    role=msg.get("role", "assistant"),
                    content=msg.get("content", ""),
                    sources_json=sources_json,
                    model=msg.get("model"),
                    use_self_check=msg.get("use_self_check"),
                    prompt_version_id=None,
                    message_index=msg.get("message_index", 0),
                    created_at=_parse_dt(msg.get("created_at")) or datetime.utcnow(),
                )
                db.add(msg_model)

        await db.commit()

        if include.vectors:
            qdrant_dir = os.path.join(root, "qdrant")
            vector_store = get_vector_store()
            client = vector_store.client

            for kb in kb_rows:
                old_collection = kb["collection_name"]
                new_kb_id = kb_id_map[kb["id"]]
                if target_kb:
                    new_collection = target_kb.collection_name
                else:
                    new_collection = kb_id_to_collection_name(UUID(new_kb_id)) if options.remap_ids else old_collection

                await vector_store.create_collection(
                    collection_name=new_collection,
                    vector_size=kb["embedding_dimension"],
                    distance=Distance.COSINE,
                )

                file_path = os.path.join(qdrant_dir, f"{old_collection}.jsonl")
                if not os.path.exists(file_path):
                    raise KBExportImportError(f"Missing Qdrant data for {old_collection}")

                batch: List[PointStruct] = []
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        record = json.loads(line)
                        payload = record.get("payload", {})
                        old_doc_id = str(payload.get("document_id"))
                        if old_doc_id in doc_id_map:
                            payload["document_id"] = doc_id_map[old_doc_id]
                        payload["knowledge_base_id"] = new_kb_id
                        batch.append(PointStruct(
                            id=record["id"],
                            vector=record["vector"],
                            payload=payload,
                        ))
                        if len(batch) >= 200:
                            await client.upsert(collection_name=new_collection, points=batch)
                            batch = []
                if batch:
                    await client.upsert(collection_name=new_collection, points=batch)

        if include.bm25:
            opensearch_dir = os.path.join(root, "opensearch")
            lexical_store = get_lexical_store()
            client = lexical_store.client
            index_name = lexical_store.index_name
            await lexical_store.ensure_index()

            for kb in kb_rows:
                new_kb_id = kb_id_map[kb["id"]]
                file_path = os.path.join(opensearch_dir, f"{index_name}_{kb['id']}.jsonl")
                if not os.path.exists(file_path):
                    raise KBExportImportError(f"Missing OpenSearch data for {kb['id']}")

                actions = []
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        record = json.loads(line)
                        source = record.get("_source", {})
                        old_doc_id = str(source.get("document_id"))
                        new_doc_id = doc_id_map.get(old_doc_id, old_doc_id)
                        source["document_id"] = new_doc_id
                        source["knowledge_base_id"] = new_kb_id
                        chunk_index = source.get("chunk_index")
                        chunk_id = f"{new_doc_id}:{chunk_index}"
                        actions.append({
                            "_op_type": "index",
                            "_index": index_name,
                            "_id": chunk_id,
                            **source,
                        })
                        if len(actions) >= 500:
                            await async_bulk(client, actions, request_timeout=60)
                            actions = []
                if actions:
                    await async_bulk(client, actions, request_timeout=60)

        if include.uploads:
            uploads_src = os.path.join(root, "uploads")
            uploads_dst = os.path.join(os.getcwd(), "uploads")
            if os.path.isdir(uploads_src):
                os.makedirs(uploads_dst, exist_ok=True)
                for item in os.listdir(uploads_src):
                    src = os.path.join(uploads_src, item)
                    dst = os.path.join(uploads_dst, item)
                    if os.path.isdir(src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)

        return {
            "status": "ok",
            "kb_imported": len(kb_rows),
            "kb_created": kb_created,
            "kb_updated": kb_updated,
            "warnings": [],
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
