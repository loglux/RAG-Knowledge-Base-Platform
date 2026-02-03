"""QA-based evaluation utilities for RAG auto-tuning."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import KnowledgeBase as KnowledgeBaseModel, QASample, QAEvalRun, QAEvalResult
from app.services.rag import RAGService


_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
NO_ANSWER_SENTINEL = "__NO_ANSWER__"
EVAL_QUERY_TIMEOUT_S = 90

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    text = text.lower().strip()
    tokens = _TOKEN_RE.findall(text)
    return " ".join(tokens)


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def compute_exact_match(pred: str, gold: str) -> float:
    return 1.0 if _normalize_text(pred) == _normalize_text(gold) else 0.0


def compute_f1(pred: str, gold: str) -> float:
    pred_tokens = _tokenize(pred)
    gold_tokens = _tokenize(gold)
    if not pred_tokens or not gold_tokens:
        return 0.0
    common = {}
    for t in pred_tokens:
        common[t] = common.get(t, 0) + 1
    overlap = 0
    for t in gold_tokens:
        if common.get(t, 0) > 0:
            overlap += 1
            common[t] -= 1
    if overlap == 0:
        return 0.0
    precision = overlap / len(pred_tokens)
    recall = overlap / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def _first_sentence(text: str) -> str:
    if not text:
        return ""
    for sep in [". ", "?\n", "!\n", "? ", "! ", ".\n"]:
        idx = text.find(sep)
        if idx != -1:
            return text[:idx].strip()
    return text.strip()


def compute_concise_f1(pred: str, gold: str) -> float:
    return compute_f1(_first_sentence(pred), _first_sentence(gold))


def is_no_answer_expected(gold: str) -> bool:
    return gold.strip() == NO_ANSWER_SENTINEL


def compute_no_answer_match(pred: str) -> float:
    if not pred:
        return 0.0
    text = pred.lower()
    phrases = [
        "i don't know",
        "i do not know",
        "not provided in the context",
        "not in the context",
        "not mentioned in the context",
        "the context does not provide",
        "cannot be answered",
        "no information",
    ]
    return 1.0 if any(p in text for p in phrases) else 0.0


def compute_recall_from_sources(
    sources: List[Dict[str, Any]],
    document_id: Optional[str],
    chunk_index: Optional[int],
) -> Optional[float]:
    if not document_id and chunk_index is None:
        return None
    for source in sources:
        if document_id and str(source.get("document_id")) != str(document_id):
            continue
        if chunk_index is not None and source.get("chunk_index") != chunk_index:
            continue
        return 1.0
    return 0.0


@dataclass
class GoldEvalConfig:
    top_k: int = 5
    retrieval_mode: str = "dense"
    lexical_top_k: Optional[int] = None
    dense_weight: float = 0.6
    lexical_weight: float = 0.4
    bm25_match_mode: Optional[str] = None
    bm25_min_should_match: Optional[int] = None
    bm25_use_phrase: Optional[bool] = None
    bm25_analyzer: Optional[str] = None
    max_context_chars: Optional[int] = None
    score_threshold: Optional[float] = None
    llm_model: Optional[str] = None
    llm_provider: Optional[str] = None
    temperature: float = 0.0
    use_mmr: bool = False
    mmr_diversity: float = 0.5
    sample_limit: Optional[int] = None


async def replace_gold_samples(db: AsyncSession, kb_id, samples: List[QASample]) -> int:
    await db.execute(
        delete(QASample).where(
            QASample.knowledge_base_id == kb_id,
            QASample.sample_type == "gold",
        )
    )
    db.add_all(samples)
    await db.flush()
    return len(samples)


async def _load_gold_samples(
    db: AsyncSession,
    kb_id,
    sample_limit: Optional[int],
) -> List[QASample]:
    query = select(QASample).where(
        QASample.knowledge_base_id == kb_id,
        QASample.sample_type == "gold",
    ).order_by(QASample.created_at.asc())
    if sample_limit:
        query = query.limit(sample_limit)
    result = await db.execute(query)
    return result.scalars().all()


async def run_gold_evaluation_on_run(
    db: AsyncSession,
    kb: KnowledgeBaseModel,
    run: QAEvalRun,
    config: GoldEvalConfig,
) -> QAEvalRun:
    samples = await _load_gold_samples(db, kb.id, config.sample_limit)
    if not samples:
        raise ValueError("No gold QA samples found for this knowledge base.")

    run.sample_count = len(samples)
    run.processed_count = 0
    await db.flush()

    rag = RAGService()

    exact_scores: List[float] = []
    f1_scores: List[float] = []
    concise_scores: List[float] = []
    recall_scores: List[float] = []
    no_answer_scores: List[float] = []
    answerable_count = 0
    no_answer_count = 0
    errors = 0

    for idx, sample in enumerate(samples, 1):
        try:
            logger.info("Gold eval run %s: processing sample %s/%s (id=%s)", run.id, idx, len(samples), sample.id)
            response = await asyncio.wait_for(
                rag.query(
                    question=sample.question,
                    collection_name=kb.collection_name,
                    embedding_model=kb.embedding_model,
                    top_k=config.top_k,
                    retrieval_mode=config.retrieval_mode,
                    lexical_top_k=config.lexical_top_k,
                    dense_weight=config.dense_weight,
                    lexical_weight=config.lexical_weight,
                    bm25_match_mode=config.bm25_match_mode,
                    bm25_min_should_match=config.bm25_min_should_match,
                    bm25_use_phrase=config.bm25_use_phrase,
                    bm25_analyzer=config.bm25_analyzer,
                    max_context_chars=config.max_context_chars,
                    score_threshold=config.score_threshold,
                    llm_model=config.llm_model,
                    llm_provider=config.llm_provider,
                    temperature=config.temperature,
                    use_mmr=config.use_mmr,
                    mmr_diversity=config.mmr_diversity,
                    db=db,
                    kb_id=kb.id,
                ),
                timeout=EVAL_QUERY_TIMEOUT_S,
            )
            answer_text = response.answer
            sources = [
                {
                    "text": chunk.text,
                    "score": chunk.score,
                    "document_id": chunk.document_id,
                    "filename": chunk.filename,
                    "chunk_index": chunk.chunk_index,
                    "metadata": chunk.metadata,
                }
                for chunk in response.sources
            ]

            if is_no_answer_expected(sample.answer):
                no_answer_count += 1
                no_answer = compute_no_answer_match(answer_text or "")
                no_answer_scores.append(no_answer)
                metrics = {"no_answer_match": no_answer}
            else:
                answerable_count += 1
                exact = compute_exact_match(answer_text, sample.answer)
                f1 = compute_f1(answer_text, sample.answer)
                concise = compute_concise_f1(answer_text, sample.answer)
                recall = compute_recall_from_sources(
                    sources,
                    str(sample.document_id) if sample.document_id else None,
                    sample.chunk_index,
                )

                exact_scores.append(exact)
                f1_scores.append(f1)
                concise_scores.append(concise)
                if recall is not None:
                    recall_scores.append(recall)

                metrics = {
                    "exact_match": exact,
                    "f1": f1,
                    "concise_f1": concise,
                    "recall": recall,
                }
        except asyncio.TimeoutError:
            errors += 1
            answer_text = None
            sources = []
            metrics = {"error": f"timeout after {EVAL_QUERY_TIMEOUT_S}s"}
            logger.warning(
                "Gold eval run %s: sample %s/%s timed out after %ss (id=%s)",
                run.id,
                idx,
                len(samples),
                EVAL_QUERY_TIMEOUT_S,
                sample.id,
            )
        except Exception as exc:
            errors += 1
            answer_text = None
            sources = []
            metrics = {"error": str(exc)}

        db.add(
            QAEvalResult(
                run_id=run.id,
                sample_id=sample.id,
                answer=answer_text,
                sources_json=json.dumps(sources) if sources else None,
                metrics_json=json.dumps(metrics),
            )
        )
        run.processed_count = idx
        if idx % 5 == 0:
            await db.flush()
            await db.commit()

    metrics_summary = {
        "answerable_count": answerable_count,
        "no_answer_count": no_answer_count,
        "exact_match_avg": sum(exact_scores) / len(exact_scores) if exact_scores else 0.0,
        "f1_avg": sum(f1_scores) / len(f1_scores) if f1_scores else 0.0,
        "concise_f1_avg": sum(concise_scores) / len(concise_scores) if concise_scores else 0.0,
        "recall_avg": sum(recall_scores) / len(recall_scores) if recall_scores else None,
        "no_answer_accuracy": sum(no_answer_scores) / len(no_answer_scores) if no_answer_scores else None,
        "errors": errors,
    }

    run.status = "completed"
    run.completed_at = datetime.utcnow()
    run.metrics_json = json.dumps(metrics_summary)

    await db.flush()
    await db.commit()
    return run


async def create_gold_run(
    db: AsyncSession,
    kb: KnowledgeBaseModel,
    config: GoldEvalConfig,
) -> QAEvalRun:
    count_query = select(QASample.id).where(
        QASample.knowledge_base_id == kb.id,
        QASample.sample_type == "gold",
    )
    result = await db.execute(count_query)
    total = len(result.scalars().all())
    if total == 0:
        raise ValueError("No gold QA samples found for this knowledge base.")
    sample_count = min(total, config.sample_limit) if config.sample_limit else total

    run = QAEvalRun(
        knowledge_base_id=kb.id,
        mode="gold",
        status="running",
        config_json=json.dumps(asdict(config)),
        sample_count=sample_count,
        processed_count=0,
        started_at=datetime.utcnow(),
    )
    db.add(run)
    await db.flush()
    return run
