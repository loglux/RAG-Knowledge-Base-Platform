"""Multi-page URL crawl endpoints (see app/services/url_crawler.py)."""

import json
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ownership import check_ownership, ownership_filter
from app.db.session import get_db
from app.dependencies import get_current_user_id
from app.models.database import KnowledgeBase as KnowledgeBaseModel
from app.models.database import UrlCrawlJob
from app.models.enums import CrawlJobStatus, CrawlScope
from app.models.schemas import UrlCrawlJobResponse, UrlCrawlRequest
from app.services.url_crawler import run_crawl_job

logger = logging.getLogger(__name__)
router = APIRouter()


def _job_to_response(job: UrlCrawlJob) -> UrlCrawlJobResponse:
    pages = json.loads(job.pages_json) if job.pages_json else []
    return UrlCrawlJobResponse(
        id=job.id,
        knowledge_base_id=job.knowledge_base_id,
        seed_url=job.seed_url,
        scope=CrawlScope(job.scope),
        max_depth=job.max_depth,
        max_pages=job.max_pages,
        status=CrawlJobStatus(job.status),
        pages_discovered=job.pages_discovered,
        pages_processed=job.pages_processed,
        pages_duplicate=job.pages_duplicate,
        pages_failed=job.pages_failed,
        pages=pages,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.post("/", response_model=UrlCrawlJobResponse, status_code=status.HTTP_201_CREATED)
async def start_crawl(
    request: UrlCrawlRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    user_id: Optional[int] = Depends(get_current_user_id),
):
    """
    Start a multi-page crawl from a seed URL.

    Discovers and imports linked pages breadth-first, up to `max_depth` /
    `max_pages`, scoped by `scope` (same domain, same path prefix, or
    unrestricted). Runs as a background job - poll `GET /{job_id}` for
    progress. Each page is imported exactly like a single-URL import
    (app/services/url_ingest.py): duplicates (by URL or content) are
    skipped, not treated as fatal.
    """
    kb_query = select(KnowledgeBaseModel).where(
        KnowledgeBaseModel.id == request.knowledge_base_id,
        KnowledgeBaseModel.is_deleted == False,  # noqa: E712
    )
    kb = (await db.execute(kb_query)).scalar_one_or_none()
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge base {request.knowledge_base_id} not found",
        )

    check_ownership(kb.user_id, user_id, resource="knowledge base")

    job = UrlCrawlJob(
        knowledge_base_id=request.knowledge_base_id,
        user_id=user_id,
        seed_url=request.seed_url,
        scope=request.scope.value,
        max_depth=request.max_depth,
        max_pages=request.max_pages,
        detect_duplicates=request.detect_duplicates,
        contextual_description_enabled=request.contextual_description_enabled,
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(run_crawl_job, job_id=job.id)

    logger.info(
        f"Crawl job {job.id} queued for {request.seed_url} (KB {request.knowledge_base_id})"
    )

    return _job_to_response(job)


@router.get("/{job_id}", response_model=UrlCrawlJobResponse)
async def get_crawl_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: Optional[int] = Depends(get_current_user_id),
):
    """Poll a crawl job's status and per-page results."""
    job = await db.get(UrlCrawlJob, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Crawl job {job_id} not found"
        )
    check_ownership(job.user_id, user_id, resource="crawl job")
    return _job_to_response(job)


@router.get("/", response_model=List[UrlCrawlJobResponse])
async def list_crawl_jobs(
    knowledge_base_id: Optional[UUID] = Query(None, description="Filter by knowledge base"),
    db: AsyncSession = Depends(get_db),
    user_id: Optional[int] = Depends(get_current_user_id),
):
    """List crawl jobs, most recent first."""
    query = (
        select(UrlCrawlJob)
        .where(ownership_filter(UrlCrawlJob.user_id, user_id))
        .order_by(UrlCrawlJob.created_at.desc())
    )
    if knowledge_base_id:
        query = query.where(UrlCrawlJob.knowledge_base_id == knowledge_base_id)
    jobs = (await db.execute(query)).scalars().all()
    return [_job_to_response(job) for job in jobs]
