"""Helpers for generating chat titles."""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm_base import Message
from app.core.llm_factory import create_llm_service
from app.models.database import AppSettings as AppSettingsModel
from app.models.database import KnowledgeBase as KnowledgeBaseModel


def clean_title(title: str) -> str:
    cleaned = title.strip().strip('"').strip("'").strip()
    if not cleaned:
        return ""
    if cleaned.endswith((".", "!", "?", ":", ";")):
        cleaned = cleaned[:-1].strip()
    return cleaned[:120]


def fallback_title(question: str) -> str:
    if question:
        return question.strip()[:120]
    return "New conversation"


async def resolve_use_llm_titles(db: AsyncSession, kb_id: Optional[UUID]) -> bool:
    if kb_id:
        kb_result = await db.execute(
            select(KnowledgeBaseModel).where(KnowledgeBaseModel.id == kb_id)
        )
        kb = kb_result.scalar_one_or_none()
        if kb and kb.use_llm_chat_titles is not None:
            return bool(kb.use_llm_chat_titles)

    settings_result = await db.execute(
        select(AppSettingsModel).order_by(AppSettingsModel.id).limit(1)
    )
    settings_row = settings_result.scalar_one_or_none()
    if settings_row and settings_row.use_llm_chat_titles is not None:
        return bool(settings_row.use_llm_chat_titles)

    return True


async def generate_title(
    question: str,
    answer: Optional[str],
    llm_model: Optional[str],
    llm_provider: Optional[str],
) -> Optional[str]:
    if not question:
        return None
    prompt = (
        "Create a short, specific title for this conversation.\n"
        "- 3 to 8 words\n"
        "- same language as the question\n"
        "- no quotes\n"
        "- no trailing punctuation\n"
    )
    answer_snippet = (answer or "").strip()
    if len(answer_snippet) > 500:
        answer_snippet = answer_snippet[:500]
    user_content = f"Question: {question.strip()}"
    if answer_snippet:
        user_content += f"\nAnswer: {answer_snippet}"

    llm = create_llm_service(model=llm_model, provider=llm_provider)
    response = await llm.generate(
        messages=[
            Message(role="system", content=prompt),
            Message(role="user", content=user_content),
        ],
        temperature=0.2,
        max_tokens=24,
    )
    cleaned = clean_title(response.content)
    return cleaned or None


async def build_conversation_title(
    db: AsyncSession,
    kb_id: Optional[UUID],
    question: str,
    answer: Optional[str],
    llm_model: Optional[str],
    llm_provider: Optional[str],
) -> str:
    use_llm = await resolve_use_llm_titles(db, kb_id)
    if use_llm:
        try:
            title = await generate_title(question, answer, llm_model, llm_provider)
            if title:
                return title
        except Exception:
            pass
    return fallback_title(question)
