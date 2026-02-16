"""QA-based auto-tuning endpoints."""

import asyncio
import csv
import io
import json
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, get_db_session
from app.models.database import KnowledgeBase as KnowledgeBaseModel
from app.models.database import (
    QAEvalResult,
    QAEvalRun,
    QASample,
)
from app.models.schemas import (
    QAEvalResultResponse,
    QAEvalRunDetailResponse,
    QAEvalRunRequest,
    QAEvalRunResponse,
    QASampleUploadResponse,
)
from app.services.qa_eval import (
    NO_ANSWER_SENTINEL,
    GoldEvalConfig,
    create_gold_run,
    replace_gold_samples,
    run_gold_evaluation_on_run,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_uuid(value: Optional[str]) -> Optional[UUID]:
    if not value:
        return None
    try:
        return UUID(str(value))
    except Exception:
        return None


def _parse_csv_samples(content: str, kb_id: UUID) -> List[QASample]:
    reader = csv.DictReader(io.StringIO(content))
    samples: List[QASample] = []
    for row in reader:
        question = (row.get("question") or "").strip()
        answer = (row.get("answer") or "").strip()
        if not question:
            continue
        if not answer:
            answer = NO_ANSWER_SENTINEL
        document_id = _parse_uuid((row.get("document_id") or "").strip())
        chunk_index_raw = (row.get("chunk_index") or "").strip()
        chunk_index = int(chunk_index_raw) if chunk_index_raw.isdigit() else None
        source_span = (row.get("source_span") or "").strip() or None

        samples.append(
            QASample(
                knowledge_base_id=kb_id,
                question=question,
                answer=answer,
                document_id=document_id,
                chunk_index=chunk_index,
                source_span=source_span,
                sample_type="gold",
            )
        )
    return samples


def _parse_json_samples(payload: list, kb_id: UUID) -> List[QASample]:
    samples: List[QASample] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        if not question:
            continue
        if not answer:
            answer = NO_ANSWER_SENTINEL
        document_id = _parse_uuid(item.get("document_id"))
        chunk_index = item.get("chunk_index")
        if isinstance(chunk_index, str) and chunk_index.isdigit():
            chunk_index = int(chunk_index)
        elif not isinstance(chunk_index, int):
            chunk_index = None
        source_span = item.get("source_span") or None

        samples.append(
            QASample(
                knowledge_base_id=kb_id,
                question=question,
                answer=answer,
                document_id=document_id,
                chunk_index=chunk_index,
                source_span=source_span,
                sample_type="gold",
            )
        )
    return samples


@router.post(
    "/knowledge-bases/{kb_id}/auto-tune/gold/upload",
    response_model=QASampleUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_gold_samples(
    kb_id: UUID,
    file: UploadFile = File(...),
    replace_existing: bool = Query(True, description="Replace existing gold samples"),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBaseModel, kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
        )

    content = (await file.read()).decode("utf-8", errors="ignore")
    filename = (file.filename or "").lower()
    try:
        if filename.endswith(".json"):
            payload = json.loads(content)
            if not isinstance(payload, list):
                raise ValueError("JSON must be an array of samples")
            samples = _parse_json_samples(payload, kb_id)
        else:
            samples = _parse_csv_samples(content, kb_id)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not samples:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No valid samples found"
        )

    if replace_existing:
        added = await replace_gold_samples(db, kb_id, samples)
    else:
        db.add_all(samples)
        await db.flush()
        added = len(samples)

    return QASampleUploadResponse(
        knowledge_base_id=kb_id,
        added_count=added,
        replaced=replace_existing,
    )


@router.get(
    "/knowledge-bases/{kb_id}/auto-tune/gold/count",
)
async def get_gold_sample_count(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBaseModel, kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
        )

    count = await db.scalar(
        select(func.count()).select_from(
            select(QASample.id)
            .where(
                QASample.knowledge_base_id == kb_id,
                QASample.sample_type == "gold",
            )
            .subquery()
        )
    )
    return {"knowledge_base_id": kb_id, "count": count}


@router.post(
    "/knowledge-bases/{kb_id}/auto-tune/gold/run",
    response_model=QAEvalRunResponse,
)
async def run_gold_eval(
    kb_id: UUID,
    payload: QAEvalRunRequest,
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBaseModel, kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
        )

    config = GoldEvalConfig(
        top_k=payload.top_k,
        retrieval_mode=(
            payload.retrieval_mode.value
            if hasattr(payload.retrieval_mode, "value")
            else str(payload.retrieval_mode)
        ),
        lexical_top_k=payload.lexical_top_k,
        dense_weight=payload.hybrid_dense_weight,
        lexical_weight=payload.hybrid_lexical_weight,
        bm25_match_mode=payload.bm25_match_mode,
        bm25_min_should_match=payload.bm25_min_should_match,
        bm25_use_phrase=payload.bm25_use_phrase,
        bm25_analyzer=payload.bm25_analyzer,
        max_context_chars=payload.max_context_chars,
        score_threshold=payload.score_threshold,
        llm_model=payload.llm_model,
        llm_provider=payload.llm_provider,
        use_mmr=payload.use_mmr,
        mmr_diversity=payload.mmr_diversity,
        sample_limit=payload.sample_limit,
    )

    try:
        run = await create_gold_run(db, kb, config)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    async def _background_eval(run_id: UUID):
        async with get_db_session() as session:
            run_row = await session.get(QAEvalRun, run_id)
            if not run_row:
                return
            kb_row = await session.get(KnowledgeBaseModel, run_row.knowledge_base_id)
            if not kb_row:
                run_row.status = "failed"
                run_row.error_message = "Knowledge base not found"
                await session.commit()
                return
            config_data = json.loads(run_row.config_json) if run_row.config_json else {}
            config_obj = GoldEvalConfig(**config_data)
            logger.info(f"Starting gold eval run {run_id}")
            try:
                await run_gold_evaluation_on_run(session, kb_row, run_row, config_obj)
            except Exception as exc:
                run_row.status = "failed"
                run_row.error_message = str(exc)
                await session.commit()

    asyncio.create_task(_background_eval(run.id))

    return QAEvalRunResponse(
        id=run.id,
        knowledge_base_id=run.knowledge_base_id,
        mode=run.mode,
        status=run.status,
        config=json.loads(run.config_json) if run.config_json else None,
        metrics=json.loads(run.metrics_json) if run.metrics_json else None,
        sample_count=run.sample_count,
        processed_count=run.processed_count,
        error_message=run.error_message,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


@router.get(
    "/knowledge-bases/{kb_id}/auto-tune/runs",
    response_model=list[QAEvalRunResponse],
)
async def list_eval_runs(
    kb_id: UUID,
    limit: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBaseModel, kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
        )

    result = await db.execute(
        select(QAEvalRun)
        .where(QAEvalRun.knowledge_base_id == kb_id)
        .order_by(QAEvalRun.created_at.desc())
        .limit(limit)
    )
    runs = result.scalars().all()

    return [
        QAEvalRunResponse(
            id=run.id,
            knowledge_base_id=run.knowledge_base_id,
            mode=run.mode,
            status=run.status,
            config=json.loads(run.config_json) if run.config_json else None,
            metrics=json.loads(run.metrics_json) if run.metrics_json else None,
            sample_count=run.sample_count,
            processed_count=run.processed_count,
            error_message=run.error_message,
            created_at=run.created_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
        )
        for run in runs
    ]


@router.get(
    "/knowledge-bases/{kb_id}/auto-tune/runs/{run_id}",
    response_model=QAEvalRunDetailResponse,
)
async def get_eval_run(
    kb_id: UUID,
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    run = await db.get(QAEvalRun, run_id)
    if not run or run.knowledge_base_id != kb_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    results_query = (
        select(QAEvalResult, QASample)
        .join(QASample, QAEvalResult.sample_id == QASample.id, isouter=True)
        .where(QAEvalResult.run_id == run_id)
        .order_by(QAEvalResult.created_at.asc())
    )
    result = await db.execute(results_query)
    rows = result.all()

    results: list[QAEvalResultResponse] = []
    for eval_row, sample in rows:
        metrics = json.loads(eval_row.metrics_json) if eval_row.metrics_json else None
        results.append(
            QAEvalResultResponse(
                id=eval_row.id,
                sample_id=eval_row.sample_id,
                question=sample.question if sample else "",
                expected_answer=sample.answer if sample else "",
                answer=eval_row.answer,
                document_id=sample.document_id if sample else None,
                chunk_index=sample.chunk_index if sample else None,
                source_span=sample.source_span if sample else None,
                metrics=metrics,
                created_at=eval_row.created_at,
            )
        )

    run_response = QAEvalRunResponse(
        id=run.id,
        knowledge_base_id=run.knowledge_base_id,
        mode=run.mode,
        status=run.status,
        config=json.loads(run.config_json) if run.config_json else None,
        metrics=json.loads(run.metrics_json) if run.metrics_json else None,
        sample_count=run.sample_count,
        processed_count=run.processed_count,
        error_message=run.error_message,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )

    return QAEvalRunDetailResponse(run=run_response, results=results)


@router.delete(
    "/knowledge-bases/{kb_id}/auto-tune/runs/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_eval_run(
    kb_id: UUID,
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    run = await db.get(QAEvalRun, run_id)
    if not run or run.knowledge_base_id != kb_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    await db.delete(run)
    await db.flush()
    return None


@router.delete(
    "/knowledge-bases/{kb_id}/auto-tune/runs",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_all_eval_runs(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    kb = await db.get(KnowledgeBaseModel, kb_id)
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
        )

    result = await db.execute(select(QAEvalRun).where(QAEvalRun.knowledge_base_id == kb_id))
    runs = result.scalars().all()
    for run in runs:
        await db.delete(run)
    await db.flush()
    return None
