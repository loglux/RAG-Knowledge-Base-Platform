"""Resolve PDF parsing overrides: KB → app_settings → built-in defaults.

PDF parsing happens at ingestion time, not query time, so the resolution
chain is simpler than for chat/retrieval settings: there is no request or
conversation scope. Only KB-level and app-level overrides apply.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AppSettings, KnowledgeBase

# Names mirror PDFExtractionProfile fields, with one rename:
# size_ratio_threshold ↔ pdf_heading_size_sensitivity (the user-facing name).
PDF_PARSING_KEY_MAP: Dict[str, str] = {
    "pdf_table_strategy": "table_strategy",
    "pdf_heading_size_sensitivity": "size_ratio_threshold",
    "pdf_min_doc_length": "min_doc_length",
}


def _collect_overrides(source: Any) -> Dict[str, Any]:
    """Pull non-None PDF override fields off a model/dict source."""
    out: Dict[str, Any] = {}
    if source is None:
        return out
    for column_name, profile_field in PDF_PARSING_KEY_MAP.items():
        value = (
            getattr(source, column_name, None)
            if not isinstance(source, dict)
            else source.get(column_name)
        )
        if value is not None:
            out[profile_field] = value
    return out


async def resolve_pdf_parsing_overrides(
    db: AsyncSession, kb: Optional[KnowledgeBase]
) -> Dict[str, Any]:
    """
    Resolve the PDF parsing overrides dict that should be passed to
    PDFFileHandler.extract_all(..., profile_overrides=...).

    Precedence: KB override → app_settings → empty (built-in defaults).
    KB-level keys always win over app-level for the same field.
    """
    # Start from app-level defaults so KB can selectively override.
    app_row = (
        await db.execute(select(AppSettings).order_by(AppSettings.id).limit(1))
    ).scalar_one_or_none()
    overrides = _collect_overrides(app_row)

    kb_overrides = _collect_overrides(kb)
    overrides.update(kb_overrides)
    return overrides
