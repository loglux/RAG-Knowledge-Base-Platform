"""Thin async HTTP client for the url2md extraction service."""

import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class Url2mdUnavailable(Exception):
    """url2md service is unreachable or returned an unexpected HTTP error."""


class Url2mdExtractionError(Exception):
    """url2md reported status=error for this URL."""


class Url2mdEmptyResult(Exception):
    """url2md returned status=empty — no extractable content (JS-rendered / paywalled?)."""


@dataclass
class ExtractedPage:
    content_md: str
    title: str | None = None
    raw_html: str | None = None
    author: str | None = None
    publish_date: str | None = None
    sitename: str | None = None
    language: str | None = None
    canonical_url: str | None = None
    description: str | None = None


async def extract_url(url: str) -> ExtractedPage:
    """Call url2md /v1/extract and return a typed result.

    Raises:
        Url2mdUnavailable: service unreachable or HTTP error
        Url2mdExtractionError: url2md reported status=error (bad URL, SSRF block, etc.)
        Url2mdEmptyResult: url2md returned status=empty (no text content extractable)
    """
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(settings.URL2MD_TIMEOUT)) as client:
            response = await client.post(
                f"{settings.URL2MD_URL}/v1/extract",
                json={"url": url},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.ConnectError as exc:
        raise Url2mdUnavailable(
            f"url2md service is not available at {settings.URL2MD_URL} — start it first"
        ) from exc
    except httpx.TimeoutException as exc:
        raise Url2mdUnavailable("url2md service timed out") from exc
    except httpx.HTTPStatusError as exc:
        raise Url2mdUnavailable(f"url2md service returned HTTP {exc.response.status_code}") from exc

    status = data.get("status")
    if status == "error":
        raise Url2mdExtractionError(data.get("error") or "url2md reported extraction failure")
    if status == "empty":
        raise Url2mdEmptyResult(
            data.get("error") or "No extractable content (JS-rendered or paywalled page?)"
        )

    metadata = data.get("metadata") or {}
    return ExtractedPage(
        content_md=data["content_md"],
        title=data.get("title"),
        raw_html=data.get("raw_html"),
        author=metadata.get("author"),
        publish_date=metadata.get("publish_date"),
        sitename=metadata.get("sitename"),
        language=metadata.get("language"),
        canonical_url=metadata.get("canonical_url"),
        description=metadata.get("description"),
    )
