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
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
