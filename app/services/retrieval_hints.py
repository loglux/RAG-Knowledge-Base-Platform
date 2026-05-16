"""Generate UX hints from retrieval signals.

The hybrid retriever already classifies identifier-style queries and lifts
lexical weight automatically. That works when the right chunk is in the
candidate pool but ranked too low. It does **not** work for the corpus
shape where the chunk gets filtered out of the lexical pool entirely
because many other chunks share cover/boilerplate language with the
query (the "homogeneous KB" case).

We detect that second case post-hoc — when the classifier fired, the
top-1 chunk score is low, *and* the top-K is visibly dominated by
cover-style chunks — and return a structured hint so the chat UI can
nudge the user toward the manual workaround (scope to a document,
raise Top K). Decision is intentionally conservative; if we are not
confident there is a problem, no hint is returned.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from app.services.query_classifier import classify_query

# Top-1 score below this is "low confidence" for identifier queries.
LOW_CONFIDENCE_TOP1_THRESHOLD: float = 0.7

# A chunk_index this small is *probably* a cover / front-matter / boilerplate
# chunk (intro page, copyright, GMC). When the top-K is dominated by these
# across many documents, identifier queries are almost certainly failing.
COVER_CHUNK_INDEX_CEILING: int = 2

# Fraction of top-K that must be cover-style chunks (and from ≥2 documents)
# before we consider the response "dominated by covers".
COVER_DOMINATION_FRACTION: float = 0.5


@dataclass(frozen=True)
class RetrievalHint:
    """Structured UX hint attached to a chat response.

    ``type`` is a stable machine identifier the frontend matches on.
    ``message`` is human-readable text the UI may render as-is.
    ``suggestions`` is an ordered list of quick actions the UI can offer
    as clickable chips.
    """

    type: str
    message: str
    suggestions: List[Dict[str, str]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _looks_like_cover(chunk: Any) -> bool:
    """Heuristic: this chunk is likely a document cover / boilerplate."""
    idx = getattr(chunk, "chunk_index", None)
    return idx is not None and idx <= COVER_CHUNK_INDEX_CEILING


def _is_dominated_by_covers(chunks: List[Any]) -> bool:
    """Top-K is mostly cover chunks from ≥2 different documents."""
    if not chunks:
        return False
    cover_chunks = [c for c in chunks if _looks_like_cover(c)]
    if len(cover_chunks) < max(2, int(len(chunks) * COVER_DOMINATION_FRACTION)):
        return False
    distinct_docs = {getattr(c, "document_id", None) for c in cover_chunks}
    distinct_docs.discard(None)
    return len(distinct_docs) >= 2


def build_hint_for_response(query: str, chunks: List[Any]) -> Optional[RetrievalHint]:
    """Return a hint if the response shows the homogeneous-KB failure pattern.

    Conditions (all must hold):
      1. Query is identifier-style (matched by the existing classifier).
      2. Either top-1 chunk score < threshold, or top-K is dominated by
         cover-style chunks from multiple documents.

    Returns None when no hint is warranted — that is the common case and
    keeps the response shape unchanged for the frontend.
    """
    if not chunks:
        return None

    classification = classify_query(query)
    if not classification.is_identifier_query:
        return None

    top1_score = getattr(chunks[0], "score", 0.0) or 0.0
    low_top1 = top1_score < LOW_CONFIDENCE_TOP1_THRESHOLD
    cover_dom = _is_dominated_by_covers(chunks)

    if not (low_top1 or cover_dom):
        return None

    identifier = classification.matched_pattern or "this identifier"
    return RetrievalHint(
        type="identifier_low_confidence",
        message=(
            f"Your query looks like a specific-item search "
            f"(“{identifier}”). Results may be incomplete because "
            f"cover-style chunks from other documents are crowding the "
            f"candidate pool. Try scoping to a single document or "
            f"increasing Top K."
        ),
        suggestions=[
            {
                "action": "scope_to_document",
                "label": "Scope to one document",
            },
            {
                "action": "raise_top_k",
                "label": "Raise Top K to 25",
                "value": "25",
            },
        ],
    )
