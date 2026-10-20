"""Unit tests for the LLM provider catalog and base-class validation logic.

No network access, no DB - these only exercise app/core/llm_base.py, which is
pure Python (a dict catalog + an ABC). This is the layer that broke silently
in production (ANTHROPIC_CHAT_MODEL default pointed at a model absent from
LLM_MODELS, causing a crash on first use) with nothing catching it - these
tests exist to make that class of bug fail CI instead.
"""

from typing import List, Optional

import pytest

from app.core.llm_base import LLM_MODELS, BaseLLMService, LLMProvider, LLMResponse, Message


class _FakeLLMService(BaseLLMService):
    """Minimal concrete subclass - BaseLLMService is abstract."""

    async def generate(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        return LLMResponse(
            content="fake",
            model=self.model,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            cache_hit_tokens=None,
            cache_miss_tokens=None,
            cache_create_tokens=None,
        )

    async def close(self):
        pass


class TestLLMModelsCatalog:
    """Every entry in LLM_MODELS must be internally consistent."""

    @pytest.mark.parametrize("key", list(LLM_MODELS.keys()))
    def test_dict_key_matches_model_name(self, key):
        assert LLM_MODELS[key].model_name == key

    @pytest.mark.parametrize("key", list(LLM_MODELS.keys()))
    def test_provider_is_valid_enum_member(self, key):
        assert isinstance(LLM_MODELS[key].provider, LLMProvider)

    @pytest.mark.parametrize("key", list(LLM_MODELS.keys()))
    def test_context_window_is_positive(self, key):
        assert LLM_MODELS[key].context_window > 0

    @pytest.mark.parametrize("key", list(LLM_MODELS.keys()))
    def test_costs_are_non_negative(self, key):
        model = LLM_MODELS[key]
        assert model.cost_per_million_input_tokens >= 0
        assert model.cost_per_million_output_tokens >= 0

    @pytest.mark.parametrize("key", list(LLM_MODELS.keys()))
    def test_description_is_non_empty(self, key):
        assert LLM_MODELS[key].description.strip()

    def test_ollama_models_are_free(self):
        for model in LLM_MODELS.values():
            if model.provider == LLMProvider.OLLAMA:
                assert model.cost_per_million_input_tokens == 0.0
                assert model.cost_per_million_output_tokens == 0.0

    def test_default_chat_models_are_catalogued(self):
        # Regression guard for the exact bug fixed this session: a *_CHAT_MODEL
        # default in app/config.py that isn't in LLM_MODELS crashes on first
        # use with "Unknown LLM model" (ValueError), silently, in production.
        from app.config import Settings

        defaults = Settings.model_fields
        for field_name in ("OPENAI_CHAT_MODEL", "ANTHROPIC_CHAT_MODEL"):
            default_model = defaults[field_name].default
            assert (
                default_model in LLM_MODELS
            ), f"{field_name} default {default_model!r} is not in LLM_MODELS"


class TestBaseLLMServiceValidation:
    def test_unknown_model_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM model"):
            _FakeLLMService(api_key="k", model="not-a-real-model")

    def test_known_model_populates_config(self):
        svc = _FakeLLMService(api_key="k", model="claude-sonnet-5")
        assert svc.provider == LLMProvider.ANTHROPIC
        assert svc.context_window == 1_000_000

    def test_skip_validation_bypasses_catalog_lookup(self):
        svc = _FakeLLMService(api_key="k", model="some-locally-pulled-model", skip_validation=True)
        assert svc.model_config is None
        assert svc.provider is None
        assert svc.context_window is None

    def test_skip_validation_still_works_for_catalogued_model(self):
        # skip_validation is used for dynamic Ollama models, but shouldn't
        # break if someone passes a catalogued name through it too.
        svc = _FakeLLMService(api_key="k", model="llama3.1", skip_validation=True)
        assert svc.model_config is None
