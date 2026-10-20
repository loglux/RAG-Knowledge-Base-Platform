"""
Live model discovery for providers that expose a models-list API.

Supplements the hand-maintained LLM_MODELS catalog (app/core/llm_base.py) with
whatever the provider actually reports as available right now, so a new model
release shows up in the UI before anyone edits the static dict. Pricing and
context-window metadata are still only known for catalogued models - dynamic
entries are surfaced with that metadata missing rather than guessed.
"""

import logging
from typing import List

from app.config import settings

logger = logging.getLogger(__name__)

# OpenAI's /v1/models lists every model on the account - TTS, Whisper, image/
# video generation, embeddings, moderation, and legacy base-completion models
# are not chat models and would just be noise in a chat-model picker.
_OPENAI_NON_CHAT_PREFIXES = (
    "tts-",
    "whisper-",
    "dall-e",
    "sora-",
    "text-embedding-",
    "omni-moderation-",
    "text-moderation-",
    "davinci-",
    "babbage-",
)


def _looks_like_chat_model(model_id: str) -> bool:
    return not model_id.startswith(_OPENAI_NON_CHAT_PREFIXES)


async def fetch_openai_model_ids() -> List[str]:
    """
    Fetch chat-capable model IDs currently available to this OpenAI account.

    Returns:
        List of model id strings, or [] if no API key is configured or the
        call fails (caller treats this as best-effort).
    """
    if not settings.OPENAI_API_KEY:
        return []

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        try:
            response = await client.models.list()
            return [m.id for m in response.data if _looks_like_chat_model(m.id)]
        finally:
            await client.close()
    except Exception as e:
        logger.warning(f"Failed to fetch OpenAI model list: {e}")
        return []


async def fetch_anthropic_model_ids() -> List[str]:
    """
    Fetch the list of model IDs currently available to this Anthropic account.

    Returns:
        List of model id strings, or [] if no API key is configured or the
        call fails (caller treats this as best-effort).
    """
    if not settings.ANTHROPIC_API_KEY:
        return []

    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        try:
            response = await client.models.list()
            return [model.id for model in response.data]
        finally:
            await client.close()
    except Exception as e:
        logger.warning(f"Failed to fetch Anthropic model list: {e}")
        return []
