"""
Multi-page URL crawler.

url2md (the extraction service behind app/services/url_extractor_client.py)
is deliberately single-URL-in/single-document-out by design - see its own
GOALS.md: "Not a crawler... belongs upstream, in the consuming project's
orchestration layer." This module is that orchestration layer: given a seed
URL, it discovers same-scope links from each fetched page's HTML (stdlib
parser, no new dependency), walks them breadth-first up to max_depth/
max_pages, and imports each successfully-fetched page via
app.services.url_ingest - the same path a single manual "import from URL"
uses, so behavior (dedup, filename derivation, raw-HTML persistence) is
identical either way.

Runs as a background task (app/api/v1/url_crawl.py queues it via
BackgroundTasks) - a crawl of even 30 pages can take minutes, which doesn't
belong in a request/response cycle.
"""

import asyncio
import json
import logging
import urllib.robotparser
from html.parser import HTMLParser
from typing import List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
from uuid import UUID

from app.models.database import KnowledgeBase as KnowledgeBaseModel
from app.models.database import UrlCrawlJob
from app.models.enums import CrawlJobStatus, CrawlScope
from app.services.url_extractor_client import (
    ExtractedPage,
    Url2mdEmptyResult,
    Url2mdExtractionError,
    Url2mdUnavailable,
    extract_url,
)
from app.services.url_ingest import (
    DuplicateContentError,
    DuplicateUrlError,
    create_document_from_extracted_page,
)
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

# Politeness delay between fetches to the same crawl's target site(s).
_FETCH_DELAY_SECONDS = 1.0


class _LinkExtractor(HTMLParser):
    """Collects every <a href="..."> target on a page. No new dependency -
    stdlib html.parser is forgiving enough for real-world (even malformed)
    HTML for this narrow purpose."""

    def __init__(self) -> None:
        super().__init__()
        self.hrefs: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.hrefs.append(value)


def extract_links(html: str, base_url: str) -> List[str]:
    """Return absolute http(s) URLs linked from the page, de-duplicated, in
    document order. Fragment-only/mailto/javascript links are dropped."""
    parser = _LinkExtractor()
    try:
        parser.feed(html)
    except Exception as exc:
        logger.warning(f"Link extraction failed for {base_url}: {exc}")
        return []

    seen: Set[str] = set()
    links: List[str] = []
    for href in parser.hrefs:
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        normalized = parsed._replace(fragment="").geturl()
        if normalized not in seen:
            seen.add(normalized)
            links.append(normalized)
    return links


def _in_scope(candidate: str, seed: str, scope: CrawlScope) -> bool:
    if scope == CrawlScope.UNRESTRICTED:
        return True

    candidate_p = urlparse(candidate)
    seed_p = urlparse(seed)

    if candidate_p.netloc != seed_p.netloc:
        return False
    if scope == CrawlScope.DOMAIN:
        return True

    # PATH_PREFIX: same host AND under the seed's path prefix (directory of
    # the seed URL - e.g. seed "/docs/intro" allows "/docs/*" but not "/blog/*").
    seed_prefix = seed_p.path.rsplit("/", 1)[0] + "/"
    return candidate_p.path.startswith(seed_prefix)


class _RobotsCache:
    """Best-effort robots.txt compliance, one fetch per host per crawl job.

    Any failure (robots.txt missing, unreachable, malformed) is treated as
    "allowed" - we don't want a broken robots.txt to silently empty a crawl,
    and plenty of sites don't bother serving one at all.
    """

    def __init__(self) -> None:
        self._parsers: dict[str, Optional[urllib.robotparser.RobotFileParser]] = {}

    async def allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        if host not in self._parsers:
            self._parsers[host] = await self._fetch(host)
        parser = self._parsers[host]
        if parser is None:
            return True
        try:
            return parser.can_fetch("*", url)
        except Exception:
            return True

    async def _fetch(self, host: str) -> Optional[urllib.robotparser.RobotFileParser]:
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(f"{host}/robots.txt")
        try:
            # RobotFileParser.read() is blocking urllib I/O - push it off the
            # event loop so one slow/unreachable robots.txt doesn't stall
            # every other request this server is handling concurrently.
            await asyncio.get_event_loop().run_in_executor(None, parser.read)
            return parser
        except Exception as exc:
            logger.info(f"Could not fetch robots.txt for {host}, treating as allow-all: {exc}")
            return None


async def _append_page_result(db_session, job: UrlCrawlJob, result: dict) -> None:
    pages = json.loads(job.pages_json) if job.pages_json else []
    pages.append(result)
    job.pages_json = json.dumps(pages, ensure_ascii=False)
    await db_session.commit()


async def run_crawl_job(job_id: UUID) -> None:
    """Entry point queued as a BackgroundTask by app/api/v1/url_crawl.py."""
    # Imported here, not at module level: AsyncSessionLocal is a global that
    # app.db.session rebinds once init_engine() runs at app startup. A
    # module-level import would capture the pre-init None permanently - see
    # the "standalone scripts" note in CLAUDE.md's troubleshooting section,
    # which is really about import timing, not just standalone scripts.
    from app.db.session import AsyncSessionLocal

    assert AsyncSessionLocal is not None, "DB engine not initialized (init_engine() hasn't run)"

    logger.info(f"[CRAWL] Starting crawl job {job_id}")
    async with AsyncSessionLocal() as db:
        job = await db.get(UrlCrawlJob, job_id)
        if job is None:
            logger.error(f"[CRAWL] Job {job_id} not found")
            return

        kb = await db.get(KnowledgeBaseModel, job.knowledge_base_id)
        if kb is None:
            job.status = CrawlJobStatus.FAILED.value
            job.error_message = "Knowledge base was deleted before the crawl started"
            await db.commit()
            return

        job.status = CrawlJobStatus.RUNNING.value
        job.started_at = utcnow()
        await db.commit()

        scope = CrawlScope(job.scope)
        robots = _RobotsCache()
        visited: Set[str] = {job.seed_url}
        queue: List[Tuple[str, int]] = [(job.seed_url, 0)]
        pages_taken = 0

        try:
            while queue and pages_taken < job.max_pages:
                url, depth = queue.pop(0)

                if not await robots.allowed(url):
                    await _append_page_result(
                        db,
                        job,
                        {
                            "url": url,
                            "depth": depth,
                            "status": "failed",
                            "error": "Disallowed by robots.txt",
                        },
                    )
                    job.pages_failed += 1
                    await db.commit()
                    continue

                pages_taken += 1
                if pages_taken > 1:
                    await asyncio.sleep(_FETCH_DELAY_SECONDS)

                page: Optional[ExtractedPage]
                try:
                    page = await extract_url(url)
                except (Url2mdUnavailable, Url2mdExtractionError, Url2mdEmptyResult) as exc:
                    await _append_page_result(
                        db, job, {"url": url, "depth": depth, "status": "failed", "error": str(exc)}
                    )
                    job.pages_failed += 1
                    await db.commit()
                    continue

                try:
                    doc = await create_document_from_extracted_page(
                        db=db, kb=kb, url=url, page=page, user_id=job.user_id
                    )
                except (DuplicateUrlError, DuplicateContentError) as exc:
                    await _append_page_result(
                        db,
                        job,
                        {"url": url, "depth": depth, "status": "duplicate", "error": str(exc)},
                    )
                    job.pages_duplicate += 1
                    await db.commit()
                    continue

                await _append_page_result(
                    db,
                    job,
                    {
                        "url": url,
                        "depth": depth,
                        "status": "imported",
                        "document_id": str(doc.id),
                    },
                )
                job.pages_processed += 1
                await db.commit()

                # Chunk/embed this page before moving to the next one - keeps
                # the crawl strictly sequential (one DB session, no detached
                # concurrent tasks to track), at the cost of total wall-clock
                # time. Acceptable: this already runs as a background job
                # the caller polls, not something blocking a request.
                from app.api.v1.documents import _process_document_background

                await _process_document_background(
                    document_id=doc.id,
                    detect_duplicates=job.detect_duplicates,
                    contextual_description_enabled_override=(job.contextual_description_enabled),
                )

                if depth < job.max_depth and page.raw_html:
                    for link in extract_links(page.raw_html, url):
                        if len(visited) >= job.max_pages:
                            break
                        if link in visited or not _in_scope(link, job.seed_url, scope):
                            continue
                        visited.add(link)
                        queue.append((link, depth + 1))
                        job.pages_discovered += 1

                await db.commit()

            job.status = CrawlJobStatus.COMPLETED.value
        except Exception as exc:
            logger.exception(f"[CRAWL] Job {job_id} failed")
            job.status = CrawlJobStatus.FAILED.value
            job.error_message = str(exc)
        finally:
            job.completed_at = utcnow()
            await db.commit()
            logger.info(
                f"[CRAWL] Job {job_id} finished: status={job.status} "
                f"processed={job.pages_processed} duplicate={job.pages_duplicate} "
                f"failed={job.pages_failed}"
            )
