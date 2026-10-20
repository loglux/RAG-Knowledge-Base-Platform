"""Unit tests for app/core/model_pricing.py.

The real httpx GET to GitHub's raw LiteLLM cost map is replaced with a fake
async client - these tests never touch the network.
"""

import time

import pytest

import app.core.model_pricing as model_pricing
from app.core.model_pricing import get_litellm_pricing_map, get_live_pricing


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner


class _FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class _FakeAsyncClient:
    def __init__(self, data=None, raise_on_get=None, **kwargs):
        self._data = data
        self._raise_on_get = raise_on_get

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url):
        if self._raise_on_get:
            raise self._raise_on_get
        return _FakeResponse(self._data)


@pytest.fixture(autouse=True)
def _reset_cache():
    model_pricing._cache = {}
    model_pricing._cache_fetched_at = 0.0
    yield
    model_pricing._cache = {}
    model_pricing._cache_fetched_at = 0.0


class TestGetLitellmPricingMap:
    async def test_fetch_success_populates_cache_and_drops_sample_spec(self, monkeypatch):
        data = {"gpt-5.1": {"input_cost_per_token": 1e-6}, "sample_spec": {"placeholder": True}}
        monkeypatch.setattr("httpx.AsyncClient", lambda **kw: _FakeAsyncClient(data=data))
        result = await get_litellm_pricing_map()
        assert "sample_spec" not in result
        assert result["gpt-5.1"]["input_cost_per_token"] == 1e-6

    async def test_reuses_cache_within_ttl(self, monkeypatch):
        calls = {"count": 0}

        def make_client(**kw):
            calls["count"] += 1
            return _FakeAsyncClient(data={"a": {}})

        monkeypatch.setattr("httpx.AsyncClient", make_client)
        await get_litellm_pricing_map()
        await get_litellm_pricing_map()
        assert calls["count"] == 1

    async def test_refetches_after_ttl_expires(self, monkeypatch):
        calls = {"count": 0}

        def make_client(**kw):
            calls["count"] += 1
            return _FakeAsyncClient(data={"a": {}})

        monkeypatch.setattr("httpx.AsyncClient", make_client)
        await get_litellm_pricing_map()
        model_pricing._cache_fetched_at = time.time() - model_pricing._CACHE_TTL_SECONDS - 1
        await get_litellm_pricing_map()
        assert calls["count"] == 2

    async def test_fetch_failure_falls_back_to_stale_cache(self, monkeypatch):
        model_pricing._cache = {"old": {"input_cost_per_token": 1.0}}
        model_pricing._cache_fetched_at = time.time() - model_pricing._CACHE_TTL_SECONDS - 1
        monkeypatch.setattr(
            "httpx.AsyncClient",
            lambda **kw: _FakeAsyncClient(raise_on_get=RuntimeError("github is down")),
        )
        result = await get_litellm_pricing_map()
        assert result == {"old": {"input_cost_per_token": 1.0}}

    async def test_fetch_failure_with_empty_cache_returns_empty(self, monkeypatch):
        monkeypatch.setattr(
            "httpx.AsyncClient",
            lambda **kw: _FakeAsyncClient(raise_on_get=RuntimeError("github is down")),
        )
        assert await get_litellm_pricing_map() == {}


class TestGetLivePricing:
    async def test_known_model_converts_per_token_to_per_million(self, monkeypatch):
        monkeypatch.setattr(
            model_pricing,
            "get_litellm_pricing_map",
            _async_return(
                {
                    "gpt-5.1": {
                        "input_cost_per_token": 1.25e-6,
                        "output_cost_per_token": 10e-6,
                        "max_input_tokens": 400000,
                    }
                }
            ),
        )
        result = await get_live_pricing("gpt-5.1")
        assert result is not None
        assert result["cost_per_million_input_tokens"] == pytest.approx(1.25)
        assert result["cost_per_million_output_tokens"] == pytest.approx(10.0)
        assert result["context_window"] == 400000

    async def test_unknown_model_returns_none(self, monkeypatch):
        monkeypatch.setattr(model_pricing, "get_litellm_pricing_map", _async_return({}))
        assert await get_live_pricing("not-a-real-model") is None

    async def test_missing_cost_fields_left_as_none(self, monkeypatch):
        monkeypatch.setattr(
            model_pricing,
            "get_litellm_pricing_map",
            _async_return({"some-model": {"max_input_tokens": 1000}}),
        )
        result = await get_live_pricing("some-model")
        assert result is not None
        assert result["cost_per_million_input_tokens"] is None
        assert result["cost_per_million_output_tokens"] is None
        assert result["context_window"] == 1000

    async def test_falls_back_to_max_tokens_when_max_input_tokens_absent(self, monkeypatch):
        monkeypatch.setattr(
            model_pricing,
            "get_litellm_pricing_map",
            _async_return({"some-model": {"max_tokens": 8192}}),
        )
        result = await get_live_pricing("some-model")
        assert result is not None
        assert result["context_window"] == 8192
