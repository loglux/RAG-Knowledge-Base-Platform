"""Promote thumbs-up chat messages into the qa_eval gold corpus.

Closes the chat → eval loop. When a user marks an assistant message 👍
the rating endpoint calls promote_message_to_gold(), which finds the
paired user question, extracts a source pointer from the first cited
chunk (when available), and upserts a `qa_sample` linked back to the
chat message via ``source_message_id``. Un-rating (back to 0) or
flipping to 👎 calls demote_message_from_gold(), which deletes the
linked sample.

The link via ``source_message_id`` keeps it idempotent: re-rating the
same message updates the existing row instead of duplicating it, and
``ON DELETE SET NULL`` on the FK means deleting the chat message later
leaves the gold sample intact (it stops being editable from chat but
stays as a frozen test case).
"""

from __future__ import annotations

import json
import logging
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import ChatMessage, Conversation, QASample

logger = logging.getLogger(__name__)


async def _find_paired_user_message(
    db: AsyncSession, conversation_id: UUID, assistant_index: int
) -> Optional[ChatMessage]:
    """Return the user message that prompted ``assistant_index`` in the same conversation."""
    if assistant_index <= 0:
        return None
    q = select(ChatMessage).where(
        ChatMessage.conversation_id == conversation_id,
        ChatMessage.message_index == assistant_index - 1,
        ChatMessage.role == "user",
    )
    return (await db.execute(q)).scalar_one_or_none()


def _first_source_pointer(
    sources_json: Optional[str],
) -> Tuple[Optional[UUID], Optional[int], Optional[str]]:
    """Pull (document_id, chunk_index, text_span) from the first cited source.

    Returns (None, None, None) when there are no sources or the field is
    malformed — those samples are still useful for answer-only metrics,
    just without grounding info.
    """
    if not sources_json:
        return None, None, None
    try:
        sources = json.loads(sources_json)
    except Exception:
        return None, None, None
    if not isinstance(sources, list) or not sources:
        return None, None, None
    first = sources[0]
    if not isinstance(first, dict):
        return None, None, None
    doc_id_raw = first.get("document_id")
    chunk_idx_raw = first.get("chunk_index")
    text_span = first.get("text") or first.get("content")
    try:
        doc_id = UUID(str(doc_id_raw)) if doc_id_raw else None
    except (TypeError, ValueError):
        doc_id = None
    try:
        chunk_idx = int(chunk_idx_raw) if chunk_idx_raw is not None else None
    except (TypeError, ValueError):
        chunk_idx = None
    return doc_id, chunk_idx, text_span if isinstance(text_span, str) else None


async def promote_message_to_gold(
    db: AsyncSession, message: ChatMessage, conversation: Conversation
) -> Optional[QASample]:
    """Create or update a gold sample from a 👍-rated assistant message.

    Returns the upserted QASample or None if promotion isn't possible
    (non-assistant role, no paired user message). The flush is left to
    the caller so this composes inside the existing rating transaction.
    """
    if message.role != "assistant":
        return None
    paired = await _find_paired_user_message(
        db, conversation_id=conversation.id, assistant_index=message.message_index
    )
    if paired is None:
        logger.info(
            "promote_message_to_gold: assistant message %s has no paired user message; skipping",
            message.id,
        )
        return None

    doc_id, chunk_idx, source_span = _first_source_pointer(message.sources_json)

    existing_q = select(QASample).where(QASample.source_message_id == message.id)
    existing = (await db.execute(existing_q)).scalar_one_or_none()

    if existing is not None:
        existing.question = paired.content
        existing.answer = message.content
        existing.document_id = doc_id
        existing.chunk_index = chunk_idx
        existing.source_span = source_span
        existing.knowledge_base_id = conversation.knowledge_base_id
        existing.sample_type = "gold"
        return existing

    sample = QASample(
        knowledge_base_id=conversation.knowledge_base_id,
        question=paired.content,
        answer=message.content,
        document_id=doc_id,
        chunk_index=chunk_idx,
        source_span=source_span,
        sample_type="gold",
        source_message_id=message.id,
    )
    db.add(sample)
    return sample


async def demote_message_from_gold(db: AsyncSession, message: ChatMessage) -> bool:
    """Delete the gold sample linked to ``message`` if one exists.

    Returns True when a sample was removed. Called whenever a rating
    moves away from +1 (clear or thumbs-down).
    """
    q = select(QASample).where(QASample.source_message_id == message.id)
    existing = (await db.execute(q)).scalar_one_or_none()
    if existing is None:
        return False
    await db.delete(existing)
    return True
