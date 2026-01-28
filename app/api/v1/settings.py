"""Global application settings endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.db.session import get_db
from app.models.database import AppSettings as AppSettingsModel
from app.models.schemas import AppSettingsResponse, AppSettingsUpdate

router = APIRouter()


def _default_app_settings() -> dict:
    return {
        "llm_model": app_settings.OPENAI_CHAT_MODEL,
        "llm_provider": app_settings.LLM_PROVIDER,
        "temperature": app_settings.OPENAI_TEMPERATURE,
        "top_k": 5,
        "max_context_chars": 0,
        "score_threshold": 0.0,
        "use_structure": False,
        "retrieval_mode": "dense",
        "lexical_top_k": 20,
        "hybrid_dense_weight": 0.6,
        "hybrid_lexical_weight": 0.4,
        "bm25_match_mode": app_settings.BM25_DEFAULT_MATCH_MODE,
        "bm25_min_should_match": app_settings.BM25_DEFAULT_MIN_SHOULD_MATCH,
        "bm25_use_phrase": app_settings.BM25_DEFAULT_USE_PHRASE,
        "bm25_analyzer": app_settings.BM25_DEFAULT_ANALYZER,
        "structure_requests_per_minute": app_settings.STRUCTURE_ANALYSIS_REQUESTS_PER_MINUTE,
        "kb_chunk_size": 1000,
        "kb_chunk_overlap": 200,
        "kb_upsert_batch_size": 256,
    }


@router.get("/metadata")
async def get_settings_metadata():
    """Get allowed options for settings controls."""
    return {
        "bm25_match_modes": app_settings.BM25_MATCH_MODES,
        "bm25_analyzers": app_settings.BM25_ANALYZERS,
    }


@router.get("/", response_model=AppSettingsResponse)
async def get_app_settings(db: AsyncSession = Depends(get_db)):
    """Get global application settings (single row)."""
    result = await db.execute(select(AppSettingsModel).order_by(AppSettingsModel.id).limit(1))
    row = result.scalar_one_or_none()
    if row is None:
        defaults = _default_app_settings()
        row = AppSettingsModel(**defaults)
        db.add(row)
        await db.flush()

    return AppSettingsResponse(
        id=row.id,
        llm_model=row.llm_model,
        llm_provider=row.llm_provider,
        temperature=row.temperature,
        top_k=row.top_k,
        max_context_chars=row.max_context_chars,
        score_threshold=row.score_threshold,
        use_structure=row.use_structure,
        retrieval_mode=row.retrieval_mode,
        lexical_top_k=row.lexical_top_k,
        hybrid_dense_weight=row.hybrid_dense_weight,
        hybrid_lexical_weight=row.hybrid_lexical_weight,
        bm25_match_mode=row.bm25_match_mode,
        bm25_min_should_match=row.bm25_min_should_match,
        bm25_use_phrase=row.bm25_use_phrase,
        bm25_analyzer=row.bm25_analyzer,
        structure_requests_per_minute=row.structure_requests_per_minute,
        kb_chunk_size=row.kb_chunk_size,
        kb_chunk_overlap=row.kb_chunk_overlap,
        kb_upsert_batch_size=row.kb_upsert_batch_size,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.put("/", response_model=AppSettingsResponse)
async def update_app_settings(
    payload: AppSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update global application settings."""
    result = await db.execute(select(AppSettingsModel).order_by(AppSettingsModel.id).limit(1))
    row = result.scalar_one_or_none()
    if row is None:
        row = AppSettingsModel()
        db.add(row)
        await db.flush()

    data = payload.model_dump(exclude_none=True)
    for key, value in data.items():
        setattr(row, key, value)

    return AppSettingsResponse(
        id=row.id,
        llm_model=row.llm_model,
        llm_provider=row.llm_provider,
        temperature=row.temperature,
        top_k=row.top_k,
        max_context_chars=row.max_context_chars,
        score_threshold=row.score_threshold,
        use_structure=row.use_structure,
        retrieval_mode=row.retrieval_mode,
        lexical_top_k=row.lexical_top_k,
        hybrid_dense_weight=row.hybrid_dense_weight,
        hybrid_lexical_weight=row.hybrid_lexical_weight,
        bm25_match_mode=row.bm25_match_mode,
        bm25_min_should_match=row.bm25_min_should_match,
        bm25_use_phrase=row.bm25_use_phrase,
        bm25_analyzer=row.bm25_analyzer,
        structure_requests_per_minute=row.structure_requests_per_minute,
        kb_chunk_size=row.kb_chunk_size,
        kb_chunk_overlap=row.kb_chunk_overlap,
        kb_upsert_batch_size=row.kb_upsert_batch_size,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("/reset", response_model=AppSettingsResponse)
async def reset_app_settings(db: AsyncSession = Depends(get_db)):
    """Reset global application settings to defaults from environment."""
    result = await db.execute(select(AppSettingsModel).order_by(AppSettingsModel.id).limit(1))
    row = result.scalar_one_or_none()
    defaults = _default_app_settings()
    if row is None:
        row = AppSettingsModel(**defaults)
        db.add(row)
        await db.flush()
    else:
        for key, value in defaults.items():
            setattr(row, key, value)
    await db.flush()

    return AppSettingsResponse(
        id=row.id,
        llm_model=row.llm_model,
        llm_provider=row.llm_provider,
        temperature=row.temperature,
        top_k=row.top_k,
        max_context_chars=row.max_context_chars,
        score_threshold=row.score_threshold,
        use_structure=row.use_structure,
        retrieval_mode=row.retrieval_mode,
        lexical_top_k=row.lexical_top_k,
        hybrid_dense_weight=row.hybrid_dense_weight,
        hybrid_lexical_weight=row.hybrid_lexical_weight,
        bm25_match_mode=row.bm25_match_mode,
        bm25_min_should_match=row.bm25_min_should_match,
        bm25_use_phrase=row.bm25_use_phrase,
        bm25_analyzer=row.bm25_analyzer,
        structure_requests_per_minute=row.structure_requests_per_minute,
        kb_chunk_size=row.kb_chunk_size,
        kb_chunk_overlap=row.kb_chunk_overlap,
        kb_upsert_batch_size=row.kb_upsert_batch_size,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
