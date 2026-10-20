"""Unit tests for app/core/model_discovery.py.

Live provider SDK calls (AsyncOpenAI().models.list(), AsyncAnthropic().models.list())
are replaced with fakes - these tests never touch the network.
"""

from types import SimpleNamespace

import pytest

from app.config import settings
from app.core.model_discovery import (
    _looks_like_chat_model,
    fetch_anthropic_model_ids,
    fetch_openai_model_ids,
)


class _FakeModelsList:
    def __init__(self, ids):
        self._ids = ids

    async def list(self):
        return SimpleNamespace(data=[SimpleNamespace(id=i) for i in self._ids])


class _FakeAsyncClient:
    """Stands in for AsyncOpenAI()/AsyncAnthropic()."""

    def __init__(self, ids=(), raise_on_list=None, **kwargs):
        self.models = _FakeModelsList(ids)
        self._raise_on_list = raise_on_list
        if raise_on_list:
            self.models.list = self._raise  # type: ignore[method-assign]

    async def _raise(self):
        raise self._raise_on_list

    async def close(self):
        pass


class TestLooksLikeChatModel:
    @pytest.mark.parametrize(
        "model_id",
        ["gpt-5.1", "gpt-4.1-mini", "o3", "o3-mini"],
    )
    def test_chat_models_pass(self, model_id):
        assert _looks_like_chat_model(model_id) is True

    @pytest.mark.parametrize(
        "model_id",
        [
            "tts-1-hd",
            "whisper-1",
            "dall-e-3",
            "sora-2",
            "text-embedding-3-small",
            "omni-moderation-latest",
            "text-moderation-stable",
            "davinci-002",
            "babbage-002",
        ],
    )
    def test_non_chat_models_filtered(self, model_id):
        assert _looks_like_chat_model(model_id) is False


class TestFetchOpenAIModelIds:
    async def test_no_api_key_returns_empty(self, monkeypatch):
        monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
        assert await fetch_openai_model_ids() == []

    async def test_filters_non_chat_models(self, monkeypatch):
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr(
            "openai.AsyncOpenAI",
            lambda **kw: _FakeAsyncClient(ids=["gpt-5.1", "whisper-1", "tts-1-hd", "o3"]),
        )
        result = await fetch_openai_model_ids()
        assert result == ["gpt-5.1", "o3"]

    async def test_sdk_exception_returns_empty(self, monkeypatch):
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr(
            "openai.AsyncOpenAI",
            lambda **kw: _FakeAsyncClient(raise_on_list=RuntimeError("boom")),
        )
        assert await fetch_openai_model_ids() == []


class TestFetchAnthropicModelIds:
    async def test_no_api_key_returns_empty(self, monkeypatch):
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None)
        assert await fetch_anthropic_model_ids() == []

    async def test_returns_all_reported_ids_unfiltered(self, monkeypatch):
        # Unlike OpenAI, Anthropic's list isn't filtered - every model it
        # reports is chat-capable.
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setattr(
            "anthropic.AsyncAnthropic",
            lambda **kw: _FakeAsyncClient(ids=["claude-opus-5-5", "claude-sonnet-5-5"]),
        )
        result = await fetch_anthropic_model_ids()
        assert result == ["claude-opus-5-5", "claude-sonnet-5-5"]

    async def test_sdk_exception_returns_empty(self, monkeypatch):
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setattr(
            "anthropic.AsyncAnthropic",
            lambda **kw: _FakeAsyncClient(raise_on_list=RuntimeError("boom")),
        )
        assert await fetch_anthropic_model_ids() == []
