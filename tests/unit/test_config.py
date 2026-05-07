"""Unit tests for application configuration."""

import pytest

from app.config import Settings

# ============================================================================
# Helpers
# ============================================================================


def make_settings(**kwargs) -> Settings:
    """Create a Settings instance with test overrides, bypassing .env file."""
    defaults = dict(
        ENVIRONMENT="development",
        SECRET_KEY="test-secret-key-32chars-xxxxxxxxxx",
        DATABASE_URL="postgresql+asyncpg://u:p@localhost:5432/test",
        OPENAI_API_KEY=None,
    )
    defaults.update(kwargs)
    return Settings.model_validate(defaults)


# ============================================================================
# Properties
# ============================================================================


@pytest.mark.unit
class TestSettingsProperties:
    def test_is_production_true_when_production(self):
        s = make_settings(ENVIRONMENT="production")
        assert s.is_production is True
        assert s.is_development is False

    def test_is_development_true_when_development(self):
        s = make_settings(ENVIRONMENT="development")
        assert s.is_development is True
        assert s.is_production is False

    def test_staging_is_neither_production_nor_development(self):
        s = make_settings(ENVIRONMENT="staging")
        assert s.is_production is False
        assert s.is_development is False

    def test_cors_origins_list_splits_on_comma(self):
        s = make_settings(CORS_ORIGINS="http://a.com,http://b.com,http://c.com")
        origins = s.cors_origins_list
        assert origins == ["http://a.com", "http://b.com", "http://c.com"]

    def test_cors_origins_list_strips_whitespace(self):
        s = make_settings(CORS_ORIGINS="http://a.com , http://b.com")
        origins = s.cors_origins_list
        assert "http://a.com" in origins
        assert "http://b.com" in origins

    def test_allowed_file_types_list_lowercased(self):
        s = make_settings(ALLOWED_FILE_TYPES="TXT,MD,DOCX")
        types = s.allowed_file_types_list
        assert types == ["txt", "md", "docx"]

    def test_allowed_file_types_list_splits_on_comma(self):
        s = make_settings(ALLOWED_FILE_TYPES="txt,md,fb2,docx")
        assert s.allowed_file_types_list == ["txt", "md", "fb2", "docx"]

    def test_max_file_size_bytes_converts_mb(self):
        s = make_settings(MAX_FILE_SIZE_MB=10)
        assert s.max_file_size_bytes == 10 * 1024 * 1024

    def test_max_file_size_bytes_50mb(self):
        s = make_settings(MAX_FILE_SIZE_MB=50)
        assert s.max_file_size_bytes == 50 * 1024 * 1024


# ============================================================================
# Validators
# ============================================================================


@pytest.mark.unit
class TestSettingsValidators:
    def test_environment_validated_lowercase(self):
        s = make_settings(ENVIRONMENT="Production")
        assert s.ENVIRONMENT == "production"

    def test_invalid_environment_raises(self):
        with pytest.raises(Exception):
            make_settings(ENVIRONMENT="invalid_env")

    def test_log_level_validated_uppercase(self):
        s = make_settings(LOG_LEVEL="debug")
        assert s.LOG_LEVEL == "DEBUG"

    def test_invalid_log_level_raises(self):
        with pytest.raises(Exception):
            make_settings(LOG_LEVEL="VERBOSE")

    def test_bm25_match_modes_from_csv_string(self):
        s = make_settings(BM25_MATCH_MODES="strict,balanced,loose")
        assert s.BM25_MATCH_MODES == ["strict", "balanced", "loose"]

    def test_bm25_analyzers_from_csv_string(self):
        s = make_settings(BM25_ANALYZERS="auto,ru,en")
        assert s.BM25_ANALYZERS == ["auto", "ru", "en"]

    def test_bm25_match_modes_from_list_passthrough(self):
        s = make_settings(BM25_MATCH_MODES=["strict", "loose"])
        assert s.BM25_MATCH_MODES == ["strict", "loose"]

    def test_mcp_tools_from_csv_string(self):
        s = make_settings(MCP_TOOLS_ENABLED="rag_query,list_documents")
        assert s.MCP_TOOLS_ENABLED == ["rag_query", "list_documents"]

    def test_mcp_tools_from_json_string(self):
        s = make_settings(MCP_TOOLS_ENABLED='["rag_query", "retrieve_chunks"]')
        assert s.MCP_TOOLS_ENABLED == ["rag_query", "retrieve_chunks"]

    def test_mcp_tools_empty_string_gives_empty_list(self):
        s = make_settings(MCP_TOOLS_ENABLED="")
        assert s.MCP_TOOLS_ENABLED == []

    def test_mcp_tools_from_list_passthrough(self):
        s = make_settings(MCP_TOOLS_ENABLED=["rag_query"])
        assert s.MCP_TOOLS_ENABLED == ["rag_query"]


# ============================================================================
# update_from_dict
# ============================================================================


@pytest.mark.unit
class TestUpdateFromDict:
    def test_update_int_field(self):
        s = make_settings(MAX_FILE_SIZE_MB=50)
        s.update_from_dict({"MAX_FILE_SIZE_MB": "25"})
        assert s.MAX_FILE_SIZE_MB == 25
        assert isinstance(s.MAX_FILE_SIZE_MB, int)

    def test_update_float_field(self):
        s = make_settings(OPENAI_TEMPERATURE=0.7)
        s.update_from_dict({"OPENAI_TEMPERATURE": "0.3"})
        assert s.OPENAI_TEMPERATURE == pytest.approx(0.3)
        assert isinstance(s.OPENAI_TEMPERATURE, float)

    def test_update_bool_field_true_values(self):
        s = make_settings(DEBUG=False)
        for truthy in ("true", "1", "yes"):
            s.update_from_dict({"DEBUG": truthy})
            assert s.DEBUG is True

    def test_update_bool_field_false_values(self):
        s = make_settings(DEBUG=True)
        for falsy in ("false", "0", "no"):
            s.update_from_dict({"DEBUG": falsy})
            assert s.DEBUG is False

    def test_update_bool_from_actual_bool(self):
        s = make_settings(DEBUG=False)
        s.update_from_dict({"DEBUG": True})
        assert s.DEBUG is True

    def test_update_string_field(self):
        s = make_settings()
        s.update_from_dict({"SYSTEM_NAME": "My Platform"})
        assert s.SYSTEM_NAME == "My Platform"

    def test_update_list_field_from_csv(self):
        s = make_settings()
        s.update_from_dict({"BM25_ANALYZERS": "ru,en"})
        assert s.BM25_ANALYZERS == ["ru", "en"]

    def test_update_list_field_from_json(self):
        s = make_settings()
        s.update_from_dict({"BM25_ANALYZERS": '["ru", "en", "auto"]'})
        assert s.BM25_ANALYZERS == ["ru", "en", "auto"]

    def test_unknown_key_is_ignored(self):
        s = make_settings()
        # Should not raise
        s.update_from_dict({"NONEXISTENT_FIELD_XYZ": "value"})

    def test_multiple_fields_updated_at_once(self):
        s = make_settings(MAX_CHUNK_SIZE=1000, DEBUG=False)
        s.update_from_dict({"MAX_CHUNK_SIZE": "500", "DEBUG": "true"})
        assert s.MAX_CHUNK_SIZE == 500
        assert s.DEBUG is True
