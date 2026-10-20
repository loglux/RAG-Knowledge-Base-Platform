"""
Shared logic for turning an already-extracted web page into a Document row.

Used by both the single-URL import endpoint (app/api/v1/documents.py) and the
multi-page crawler (app/services/url_crawler.py) - factored out so the two
paths can't silently drift (duplicate detection, raw HTML persistence,
web_metadata shape, filename derivation all stay identical either way).
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document as DocumentModel
from app.models.database import KnowledgeBase as KnowledgeBaseModel
from app.models.enums import DocumentStatus, FileType
from app.services.url_extractor_client import ExtractedPage

logger = logging.getLogger(__name__)

_TRACKING_PREFIXES = ("utm_", "cx_", "mc_", "yclid")
_TRACKING_PARAMS = frozenset({"fbclid", "gclid", "gclsrc", "msclkid", "igshid", "_ga", "twclid"})


class DuplicateUrlError(Exception):
    """A document from this (cleaned) URL already exists in the knowledge base."""


class DuplicateContentError(Exception):
    """A document with identical content already exists in the knowledge base."""


def clean_url(raw: str, canonical: Optional[str] = None) -> str:
    """Prefer canonical URL from page; otherwise strip known tracking params and fragment."""
    from urllib.parse import parse_qs, urlencode, urlunparse

    if canonical:
        try:
            raw_p = urlparse(raw)
            can_p = urlparse(canonical)
            if can_p.scheme in ("http", "https") and can_p.netloc == raw_p.netloc:
                return canonical
        except Exception:
            pass

    try:
        parsed = urlparse(raw)
        params = parse_qs(parsed.query, keep_blank_values=True)
        clean = {
            k: v
            for k, v in params.items()
            if not any(k.lower().startswith(p) for p in _TRACKING_PREFIXES)
            and k.lower() not in _TRACKING_PARAMS
        }
        return urlunparse(parsed._replace(query=urlencode(clean, doseq=True), fragment=""))
    except Exception:
        return raw


async def create_document_from_extracted_page(
    db: AsyncSession,
    kb: KnowledgeBaseModel,
    url: str,
    page: ExtractedPage,
    user_id: Optional[UUID],
) -> DocumentModel:
    """
    Persist an already-fetched page as a Document (status=PENDING).

    Does NOT queue the chunking/embedding background task - callers do that
    themselves (single-URL import vs. crawl queue the same work differently).

    Raises:
        DuplicateUrlError: a document from this URL already exists in the KB
        DuplicateContentError: a document with identical content already exists
    """
    clean = clean_url(url, page.canonical_url)

    url_dup_query = select(DocumentModel).where(
        DocumentModel.knowledge_base_id == kb.id,
        DocumentModel.source_url == clean,
        DocumentModel.is_deleted == False,  # noqa: E712
    )
    if (await db.execute(url_dup_query)).scalar_one_or_none():
        raise DuplicateUrlError(f"A document from {clean} already exists in this knowledge base")

    content = page.content_md or ""
    content_bytes = content.encode("utf-8")
    content_hash = hashlib.sha256(content_bytes).hexdigest()

    dup_query = select(DocumentModel).where(
        DocumentModel.knowledge_base_id == kb.id,
        DocumentModel.content_hash == content_hash,
        DocumentModel.is_deleted == False,  # noqa: E712
    )
    if (await db.execute(dup_query)).scalar_one_or_none():
        raise DuplicateContentError(
            "A document with identical content already exists in this knowledge base"
        )

    if page.title:
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in page.title)[:80]
        filename = f"{safe_title.strip()}.md"
    else:
        hostname = urlparse(url).hostname or "web"
        filename = f"{hostname}.md"

    web_metadata_dict = {
        k: v
        for k, v in {
            "author": page.author,
            "publish_date": page.publish_date,
            "sitename": page.sitename,
            "description": page.description,
            "canonical_url": page.canonical_url,
        }.items()
        if v is not None
    }

    doc_model = DocumentModel(
        knowledge_base_id=kb.id,
        filename=filename,
        file_type=FileType.MD,
        file_size=len(content_bytes),
        content=content,
        content_hash=content_hash,
        status=DocumentStatus.PENDING,
        user_id=user_id,
        language=page.language,
        source_url=clean,
        web_metadata=(
            json.dumps(web_metadata_dict, ensure_ascii=False) if web_metadata_dict else None
        ),
    )

    db.add(doc_model)
    await db.flush()

    if page.raw_html:
        html_path = Path("/app/uploads") / str(kb.id) / f"{doc_model.id}.html"
        try:
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(page.raw_html, encoding="utf-8")
            doc_model.file_path = str(html_path)
        except Exception as exc:
            logger.warning(f"Failed to save raw HTML to disk: {exc}")

    doc_count = await db.scalar(
        select(func.count(DocumentModel.id)).where(
            DocumentModel.knowledge_base_id == kb.id,
            DocumentModel.is_deleted == False,  # noqa: E712
        )
    )
    kb.document_count = doc_count or 0

    await db.commit()
    await db.refresh(doc_model)
    return doc_model
