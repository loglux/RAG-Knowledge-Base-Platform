"""Unit tests for the embedding provider catalog and base-class validation.

Mirrors tests/unit/test_llm_base.py - no network, no DB.
"""

from typing import List

import pytest

from app.core.embeddings_base import (
    EMBEDDING_MODELS,
    BaseEmbeddingService,
    EmbeddingProvider,
    EmbeddingResult,
)


class _FakeEmbeddingService(BaseEmbeddingService):
    """Minimal concrete subclass - BaseEmbeddingService is abstract."""

    async def generate_embedding(self, text: str) -> List[float]:
        return [0.0]

    async def generate_embeddings(
        self, texts: List[str], batch_size: int = 100
    ) -> List[EmbeddingResult]:
        return [EmbeddingResult(text=t, embedding=[0.0], index=i) for i, t in enumerate(texts)]

    async def get_embedding_dimension(self) -> int:
        return self.dimension or 0

    async def close(self):
        pass


class TestEmbeddingModelsCatalog:
    @pytest.mark.parametrize("key", list(EMBEDDING_MODELS.keys()))
    def test_dict_key_matches_model_name(self, key):
        assert EMBEDDING_MODELS[key].model_name == key

    @pytest.mark.parametrize("key", list(EMBEDDING_MODELS.keys()))
    def test_provider_is_valid_enum_member(self, key):
        assert isinstance(EMBEDDING_MODELS[key].provider, EmbeddingProvider)

    @pytest.mark.parametrize("key", list(EMBEDDING_MODELS.keys()))
    def test_dimension_is_positive(self, key):
        assert EMBEDDING_MODELS[key].dimension > 0

    @pytest.mark.parametrize("key", list(EMBEDDING_MODELS.keys()))
    def test_cost_is_non_negative(self, key):
        assert EMBEDDING_MODELS[key].cost_per_million_tokens >= 0

    def test_ollama_models_are_free(self):
        for model in EMBEDDING_MODELS.values():
            if model.provider == EmbeddingProvider.OLLAMA:
                assert model.cost_per_million_tokens == 0.0

    def test_default_embedding_model_is_catalogued(self):
        from app.config import Settings

        default_model = Settings.model_fields["OPENAI_EMBEDDING_MODEL"].default
        assert default_model in EMBEDDING_MODELS


class TestBaseEmbeddingServiceValidation:
    def test_unknown_model_raises(self):
        with pytest.raises(ValueError, match="Unknown embedding model"):
            _FakeEmbeddingService(api_key="k", model="not-a-real-model")

    def test_known_model_populates_config(self):
        svc = _FakeEmbeddingService(api_key="k", model="text-embedding-3-large")
        assert svc.provider == EmbeddingProvider.OPENAI
        assert svc.dimension == 3072

    def test_skip_validation_bypasses_catalog_lookup(self):
        # This is the exact mechanism that unblocked dynamic Ollama embedding
        # models this session - a model absent from EMBEDDING_MODELS must not
        # raise, and provider/dimension must degrade to None rather than
        # crash, so callers can resolve them live instead (app/api/v1/ollama.py).
        svc = _FakeEmbeddingService(
            api_key="k", model="some-locally-pulled-embedder", skip_validation=True
        )
        assert svc.model_config is None
        assert svc.provider is None
        assert svc.dimension is None
