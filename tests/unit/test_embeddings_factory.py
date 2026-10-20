"""Unit tests for app/core/embeddings_factory.py - provider selection logic.

Mirrors tests/unit/test_llm_factory.py. No real network calls.
"""

import pytest

from app.config import settings
from app.core.embeddings import OpenAIEmbeddingService
from app.core.embeddings_base import EMBEDDING_MODELS, EmbeddingProvider
from app.core.embeddings_factory import (
    _service_cache,
    create_embedding_service,
    get_embedding_service,
    get_model_info,
    get_models_by_provider,
    list_available_models,
)
from app.core.embeddings_ollama import OllamaEmbeddingService
from app.core.embeddings_voyage import VoyageEmbeddingService


@pytest.fixture(autouse=True)
def _dummy_credentials(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test-openai")
    monkeypatch.setattr(settings, "VOYAGE_API_KEY", "voyage-test-key")
    monkeypatch.setattr(settings, "OLLAMA_BASE_URL", "http://ollama-test:11434")
    _service_cache.clear()
    yield
    _service_cache.clear()


class TestProviderSelection:
    def test_infers_provider_from_known_model_name(self):
        service = create_embedding_service(model="voyage-4")
        assert isinstance(service, VoyageEmbeddingService)
        assert service.model == "voyage-4"

    def test_unknown_model_assumes_dynamic_ollama(self):
        service = create_embedding_service(model="some-locally-pulled-embedder")
        assert isinstance(service, OllamaEmbeddingService)
        assert service.model_config is None

    def test_missing_voyage_key_raises(self, monkeypatch):
        monkeypatch.setattr(settings, "VOYAGE_API_KEY", None)
        with pytest.raises(ValueError, match="VOYAGE_API_KEY"):
            create_embedding_service(model="voyage-4")

    def test_missing_ollama_base_url_raises(self, monkeypatch):
        monkeypatch.setattr(settings, "OLLAMA_BASE_URL", None)
        with pytest.raises(ValueError, match="OLLAMA_BASE_URL"):
            create_embedding_service(model="nomic-embed-text")

    def test_create_embedding_service_openai_path(self):
        service = create_embedding_service(model="text-embedding-3-small")
        assert isinstance(service, OpenAIEmbeddingService)


class TestGetEmbeddingServiceProviderBranches:
    """get_embedding_service() has its own copy of the provider-branch logic
    (for cache-key construction before create) - exercise it directly rather
    than relying on create_embedding_service() coverage to imply it."""

    def test_openai_path(self):
        service = get_embedding_service(model="text-embedding-3-small")
        assert isinstance(service, OpenAIEmbeddingService)

    def test_unknown_model_assumes_dynamic_ollama(self):
        service = get_embedding_service(model="some-locally-pulled-embedder")
        assert isinstance(service, OllamaEmbeddingService)

    def test_missing_voyage_key_raises(self, monkeypatch):
        monkeypatch.setattr(settings, "VOYAGE_API_KEY", None)
        with pytest.raises(ValueError, match="VOYAGE_API_KEY"):
            get_embedding_service(model="voyage-4")

    def test_missing_ollama_base_url_raises(self, monkeypatch):
        monkeypatch.setattr(settings, "OLLAMA_BASE_URL", None)
        with pytest.raises(ValueError, match="OLLAMA_BASE_URL"):
            get_embedding_service(model="nomic-embed-text")


class TestGetEmbeddingServiceCaching:
    def test_same_arguments_return_cached_instance(self):
        first = get_embedding_service(model="voyage-4")
        second = get_embedding_service(model="voyage-4")
        assert first is second

    def test_different_model_is_not_cached_together(self):
        voyage_service = get_embedding_service(model="voyage-4")
        ollama_service = get_embedding_service(model="nomic-embed-text")
        assert voyage_service is not ollama_service


class TestCatalogHelpers:
    def test_get_model_info_known_model(self):
        info = get_model_info("text-embedding-3-large")
        assert info["provider"] == "openai"
        assert info["dimension"] == 3072

    def test_get_model_info_unknown_model_raises(self):
        with pytest.raises(ValueError, match="Unknown model"):
            get_model_info("not-a-real-model")

    def test_list_available_models_covers_whole_catalog(self):
        assert len(list_available_models()) == len(EMBEDDING_MODELS)

    def test_get_models_by_provider_filters_correctly(self):
        ollama_models = get_models_by_provider(EmbeddingProvider.OLLAMA)
        assert "nomic-embed-text" in ollama_models
        assert all(EMBEDDING_MODELS[m].provider == EmbeddingProvider.OLLAMA for m in ollama_models)
        assert "voyage-4" not in ollama_models
