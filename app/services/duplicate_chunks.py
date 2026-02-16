"""Duplicate chunk analysis utilities."""

import hashlib
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional
from uuid import UUID

from qdrant_client.models import FieldCondition, Filter, MatchValue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.vector_store import get_vector_store
from app.models.database import Document as DocumentModel

_normalize_re = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    return _normalize_re.sub(" ", text.strip())


def _build_duplicate_summary(groups: Dict[str, List[int]]) -> Dict[str, Any]:
    group_list = []
    total_chunks = 0
    for h, indices in groups.items():
        uniq = sorted(set(indices))
        if len(uniq) < 2:
            continue
        group_list.append(
            {
                "hash": h,
                "chunks": uniq,
                "count": len(uniq),
            }
        )
        total_chunks += len(uniq)

    group_list.sort(key=lambda g: (-g["count"], g["chunks"][0] if g["chunks"] else 0))
    return {
        "total_groups": len(group_list),
        "total_chunks": total_chunks,
        "groups": group_list,
    }


async def compute_duplicate_chunks_for_document(
    document_id: UUID,
    collection_name: str,
) -> Dict[str, Any]:
    """Compute duplicate chunk groups for a document based on Qdrant payload text."""
    client = get_vector_store().client

    next_offset = None
    groups: Dict[str, List[int]] = defaultdict(list)

    doc_filter = Filter(
        must=[FieldCondition(key="document_id", match=MatchValue(value=str(document_id)))]
    )

    while True:
        points, next_offset = await client.scroll(
            collection_name=collection_name,
            limit=1000,
            offset=next_offset,
            with_payload=True,
            with_vectors=False,
            scroll_filter=doc_filter,
        )
        if not points:
            break
        for p in points:
            payload = p.payload or {}
            text = payload.get("text") or ""
            if not text:
                continue
            chunk_index = payload.get("chunk_index")
            if chunk_index is None:
                continue
            norm = _normalize_text(text)
            if not norm:
                continue
            h = hashlib.sha1(norm.encode("utf-8")).hexdigest()
            groups[h].append(int(chunk_index))
        if next_offset is None:
            break

    summary = _build_duplicate_summary(groups)
    return summary


async def store_duplicate_chunks(
    db: AsyncSession,
    document_id: UUID,
    summary: Dict[str, Any],
) -> Optional[DocumentModel]:
    result = await db.execute(select(DocumentModel).where(DocumentModel.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        return None
    doc.duplicate_chunks_json = json_dumps(summary)
    await db.commit()
    await db.refresh(doc)
    return doc


def json_dumps(data: Dict[str, Any]) -> str:
    import json

    return json.dumps(data, ensure_ascii=False)
