"""Global application settings endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.db.session import get_db
from app.models.database import AppSettings as AppSettingsModel
from app.models.database import PromptVersion as PromptVersionModel
from app.models.database import SelfCheckPromptVersion as SelfCheckPromptVersionModel
from app.models.schemas import AppSettingsResponse, AppSettingsUpdate

router = APIRouter()

RERANK_PROVIDERS = [
    {"id": "auto", "label": "Auto (recommended)"},
    {"id": "voyage", "label": "Voyage"},
    {"id": "cohere", "label": "Cohere"},
]

RERANK_MODELS_BY_PROVIDER = {
    "voyage": [
        {
            "id": "rerank-2.5",
            "label": "rerank-2.5",
            "pricing_unit": "tokens",
            "price_per_million_tokens_usd": 0.05,
            "notes": "Quality-optimized general reranker",
        },
        {
            "id": "rerank-2.5-lite",
            "label": "rerank-2.5-lite",
            "pricing_unit": "tokens",
            "price_per_million_tokens_usd": 0.02,
            "notes": "Latency/cost-optimized general reranker",
        },
    ],
    "cohere": [
        {
            "id": "rerank-v3.5",
            "label": "rerank-v3.5",
            "pricing_unit": "searches",
            "notes": "High-quality reranker",
        },
        {
            "id": "rerank-multilingual-v3.0",
            "label": "rerank-multilingual-v3.0",
            "pricing_unit": "searches",
            "notes": "Multilingual reranker",
        },
    ],
}


def _default_app_settings() -> dict:
    return {
        "llm_model": app_settings.OPENAI_CHAT_MODEL,
        "llm_provider": app_settings.LLM_PROVIDER,
        "temperature": app_settings.OPENAI_TEMPERATURE,
        "top_k": 5,
        "max_context_chars": 0,
        "score_threshold": 0.0,
        "use_structure": False,
        "rerank_enabled": False,
        "rerank_provider": "auto",
        "rerank_model": "rerank-2.5-lite",
        "rerank_candidate_pool": 20,
        "rerank_top_n": None,
        "rerank_min_score": None,
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
        "use_llm_chat_titles": True,
        "show_prompt_versions": False,
    }


@router.get("/metadata")
async def get_settings_metadata():
    """Get allowed options for settings controls."""
    return {
        "bm25_match_modes": app_settings.BM25_MATCH_MODES,
        "bm25_analyzers": app_settings.BM25_ANALYZERS,
        "rerank_providers": RERANK_PROVIDERS,
        "rerank_models_by_provider": RERANK_MODELS_BY_PROVIDER,
        "rerank_pricing_formula": (
            "(query_tokens * num_documents) + sum(document_tokens)"
        ),
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
    if row.active_prompt_version_id is None:
        prompt_result = await db.execute(
            select(PromptVersionModel).order_by(desc(PromptVersionModel.created_at)).limit(1)
        )
        prompt = prompt_result.scalar_one_or_none()
        if prompt:
            row.active_prompt_version_id = prompt.id
    if row.active_self_check_prompt_version_id is None:
        prompt_result = await db.execute(
            select(SelfCheckPromptVersionModel)
            .order_by(desc(SelfCheckPromptVersionModel.created_at))
            .limit(1)
        )
        prompt = prompt_result.scalar_one_or_none()
        if prompt:
            row.active_self_check_prompt_version_id = prompt.id

    return AppSettingsResponse(
        id=row.id,
        llm_model=row.llm_model,
        llm_provider=row.llm_provider,
        temperature=row.temperature,
        top_k=row.top_k,
        max_context_chars=row.max_context_chars,
        score_threshold=row.score_threshold,
        use_structure=row.use_structure,
        rerank_enabled=row.rerank_enabled,
        rerank_provider=row.rerank_provider,
        rerank_model=row.rerank_model,
        rerank_candidate_pool=row.rerank_candidate_pool,
        rerank_top_n=row.rerank_top_n,
        rerank_min_score=row.rerank_min_score,
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
        use_llm_chat_titles=row.use_llm_chat_titles,
        active_prompt_version_id=row.active_prompt_version_id,
        active_self_check_prompt_version_id=row.active_self_check_prompt_version_id,
        show_prompt_versions=row.show_prompt_versions,
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
    if row.active_prompt_version_id is None:
        prompt_result = await db.execute(
            select(PromptVersionModel).order_by(desc(PromptVersionModel.created_at)).limit(1)
        )
        prompt = prompt_result.scalar_one_or_none()
        if prompt:
            row.active_prompt_version_id = prompt.id
    if row.active_self_check_prompt_version_id is None:
        prompt_result = await db.execute(
            select(SelfCheckPromptVersionModel)
            .order_by(desc(SelfCheckPromptVersionModel.created_at))
            .limit(1)
        )
        prompt = prompt_result.scalar_one_or_none()
        if prompt:
            row.active_self_check_prompt_version_id = prompt.id

    return AppSettingsResponse(
        id=row.id,
        llm_model=row.llm_model,
        llm_provider=row.llm_provider,
        temperature=row.temperature,
        top_k=row.top_k,
        max_context_chars=row.max_context_chars,
        score_threshold=row.score_threshold,
        use_structure=row.use_structure,
        rerank_enabled=row.rerank_enabled,
        rerank_provider=row.rerank_provider,
        rerank_model=row.rerank_model,
        rerank_candidate_pool=row.rerank_candidate_pool,
        rerank_top_n=row.rerank_top_n,
        rerank_min_score=row.rerank_min_score,
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
        use_llm_chat_titles=row.use_llm_chat_titles,
        active_prompt_version_id=row.active_prompt_version_id,
        active_self_check_prompt_version_id=row.active_self_check_prompt_version_id,
        show_prompt_versions=row.show_prompt_versions,
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
    if row.active_prompt_version_id is None:
        prompt_result = await db.execute(
            select(PromptVersionModel).order_by(desc(PromptVersionModel.created_at)).limit(1)
        )
        prompt = prompt_result.scalar_one_or_none()
        if prompt:
            row.active_prompt_version_id = prompt.id
    if row.active_self_check_prompt_version_id is None:
        prompt_result = await db.execute(
            select(SelfCheckPromptVersionModel)
            .order_by(desc(SelfCheckPromptVersionModel.created_at))
            .limit(1)
        )
        prompt = prompt_result.scalar_one_or_none()
        if prompt:
            row.active_self_check_prompt_version_id = prompt.id
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
        rerank_enabled=row.rerank_enabled,
        rerank_provider=row.rerank_provider,
        rerank_model=row.rerank_model,
        rerank_candidate_pool=row.rerank_candidate_pool,
        rerank_top_n=row.rerank_top_n,
        rerank_min_score=row.rerank_min_score,
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
        use_llm_chat_titles=row.use_llm_chat_titles,
        active_prompt_version_id=row.active_prompt_version_id,
        active_self_check_prompt_version_id=row.active_self_check_prompt_version_id,
        show_prompt_versions=row.show_prompt_versions,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
