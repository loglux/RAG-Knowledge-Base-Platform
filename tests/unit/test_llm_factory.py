"""Unit tests for app/core/llm_factory.py - provider selection logic.

No real network calls: provider SDK clients (AsyncOpenAI, AsyncAnthropic, ...)
are lazy at construction time, so passing a syntactically-plausible dummy API
key is enough to exercise the full factory without hitting the network.
"""

import pytest

from app.config import settings
from app.core.llm_anthropic import AnthropicLLMService
from app.core.llm_base import LLM_MODELS, LLMProvider
from app.core.llm_factory import (
    create_llm_service,
    get_model_info,
    get_models_by_provider,
    list_available_models,
)
from app.core.llm_ollama import OllamaLLMService
from app.core.llm_openai import OpenAILLMService


@pytest.fixture(autouse=True)
def _dummy_credentials(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test-openai")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "sk-test-anthropic")
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "sk-test-deepseek")
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://ollama-test:11434")


class TestProviderSelection:
    def test_infers_provider_from_known_model_name(self):
        service = create_llm_service(model="claude-sonnet-5")
        assert isinstance(service, AnthropicLLMService)
        assert service.model == "claude-sonnet-5"

    def test_explicit_provider_with_no_model_uses_that_providers_default(self, monkeypatch):
        # LLM_PROVIDER default would pick OpenAI; passing provider= explicitly
        # should override that and pick the Anthropic default model instead.
        monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
        monkeypatch.setattr(settings, "ANTHROPIC_CHAT_MODEL", "claude-sonnet-5")
        service = create_llm_service(provider="anthropic")
        assert isinstance(service, AnthropicLLMService)
        assert service.model == "claude-sonnet-5"

    def test_explicit_provider_wins_over_model_catalog_mismatch(self):
        # "claude-sonnet-5" is catalogued as Anthropic; forcing provider=openai
        # while naming an Anthropic model is a genuine misconfiguration and
        # OpenAILLMService's own cross-check must reject it, not silently
        # pick a provider.
        with pytest.raises(ValueError, match="not an OpenAI model"):
            create_llm_service(model="claude-sonnet-5", provider="openai")

    def test_explicit_openai_provider_with_no_model_uses_openai_default(self, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "anthropic")
        monkeypatch.setattr(settings, "OPENAI_CHAT_MODEL", "gpt-5.1")
        service = create_llm_service(provider="openai")
        assert isinstance(service, OpenAILLMService)
        assert service.model == "gpt-5.1"

    def test_unknown_model_assumes_dynamic_ollama(self):
        service = create_llm_service(model="some-locally-pulled-model")
        assert isinstance(service, OllamaLLMService)
        assert service.model_config is None

    def test_no_model_or_provider_uses_settings_default(self, monkeypatch):
        monkeypatch.setattr(settings, "LLM_PROVIDER", "anthropic")
        monkeypatch.setattr(settings, "ANTHROPIC_CHAT_MODEL", "claude-sonnet-5")
        service = create_llm_service()
        assert isinstance(service, AnthropicLLMService)
        assert service.model == "claude-sonnet-5"

    def test_missing_anthropic_key_raises(self, monkeypatch):
        monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None)
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            create_llm_service(model="claude-sonnet-5")

    def test_missing_ollama_base_url_raises(self, monkeypatch):
        monkeypatch.setattr(settings, "OLLAMA_BASE_URL", None)
        with pytest.raises(ValueError, match="OLLAMA_BASE_URL"):
            create_llm_service(model="llama3.1")

    def test_unsupported_provider_string_raises(self):
        with pytest.raises(ValueError):
            create_llm_service(provider="not-a-real-provider")

    def test_infers_deepseek_provider_from_known_model(self):
        from app.core.llm_deepseek import DeepSeekLLMService

        service = create_llm_service(model="deepseek-chat")
        assert isinstance(service, DeepSeekLLMService)

    def test_missing_deepseek_key_raises(self, monkeypatch):
        monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", None)
        with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
            create_llm_service(model="deepseek-chat")

    @pytest.mark.parametrize(
        "provider_name,settings_attr,default_model",
        [
            ("deepseek", "DEEPSEEK_CHAT_MODEL", "deepseek-chat"),
            ("ollama", "OLLAMA_CHAT_MODEL", "llama3.1"),
        ],
    )
    def test_default_model_resolved_per_provider_from_settings(
        self, monkeypatch, provider_name, settings_attr, default_model
    ):
        monkeypatch.setattr(settings, "LLM_PROVIDER", provider_name)
        monkeypatch.setattr(settings, settings_attr, default_model)
        service = create_llm_service()
        assert service.model == default_model


class TestCatalogHelpers:
    def test_get_model_info_known_model(self):
        info = get_model_info("claude-sonnet-5")
        assert info["provider"] == "anthropic"
        assert info["context_window"] == 1_000_000

    def test_get_model_info_unknown_model_raises(self):
        with pytest.raises(ValueError, match="Unknown model"):
            get_model_info("not-a-real-model")

    def test_list_available_models_covers_whole_catalog(self):
        assert len(list_available_models()) == len(LLM_MODELS)

    def test_get_models_by_provider_filters_correctly(self):
        anthropic_models = get_models_by_provider(LLMProvider.ANTHROPIC)
        assert "claude-sonnet-5" in anthropic_models
        assert all(LLM_MODELS[m].provider == LLMProvider.ANTHROPIC for m in anthropic_models)
        assert "gpt-5.1" not in anthropic_models
