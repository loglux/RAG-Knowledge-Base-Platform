"""Unit tests for validators."""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.enums import FileType
from app.utils.validators import (
    sanitize_text_content,
    validate_file_size,
    validate_file_type,
    validate_filename,
    validate_pagination,
    validate_uuid,
)


@pytest.mark.unit
class TestValidateFileSize:
    """Test file size validation."""

    def test_valid_file_size(self):
        """Test validation passes for valid file size."""
        content = "Small content"
        size = validate_file_size(content, max_size_bytes=1000)
        assert size == len(content.encode("utf-8"))

    def test_file_size_exceeds_limit(self):
        """Test validation fails for oversized file."""
        content = "x" * 1000
        with pytest.raises(HTTPException) as exc_info:
            validate_file_size(content, max_size_bytes=100)
        assert exc_info.value.status_code == 413


@pytest.mark.unit
class TestValidateFileType:
    """Test file type validation."""

    def test_valid_txt_file(self):
        """Test validation passes for .txt file."""
        file_type = validate_file_type("document.txt")
        assert file_type == FileType.TXT

    def test_valid_md_file(self):
        """Test validation passes for .md file."""
        file_type = validate_file_type("README.md")
        assert file_type == FileType.MD

    def test_unsupported_file_type(self):
        """Test validation fails for unsupported file type."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_type("document.pdf")
        assert exc_info.value.status_code == 415

    def test_no_extension(self):
        """Test validation fails for filename without extension."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_type("noextension")
        assert exc_info.value.status_code == 400


@pytest.mark.unit
class TestValidateFilename:
    """Test filename validation."""

    def test_valid_filename(self):
        """Test validation passes for valid filename."""
        filename = validate_filename("document.txt")
        assert filename == "document.txt"

    def test_path_traversal_attack(self):
        """Test validation blocks path traversal."""
        with pytest.raises(HTTPException):
            validate_filename("../../../etc/passwd")

    def test_invalid_characters(self):
        """Test validation blocks invalid characters."""
        with pytest.raises(HTTPException):
            validate_filename("file<>name.txt")

    def test_filename_too_long(self):
        """Test validation blocks too long filenames."""
        long_name = "x" * 300 + ".txt"
        with pytest.raises(HTTPException):
            validate_filename(long_name)


@pytest.mark.unit
class TestValidateUUID:
    """Test UUID validation."""

    def test_valid_uuid(self):
        """Test validation passes for valid UUID."""
        test_uuid = uuid4()
        result = validate_uuid(str(test_uuid))
        assert result == test_uuid

    def test_invalid_uuid(self):
        """Test validation fails for invalid UUID."""
        with pytest.raises(HTTPException) as exc_info:
            validate_uuid("not-a-uuid")
        assert exc_info.value.status_code == 400


@pytest.mark.unit
class TestValidatePagination:
    """Test pagination validation."""

    def test_valid_pagination(self):
        """Test validation passes for valid pagination."""
        page, page_size = validate_pagination(1, 10)
        assert page == 1
        assert page_size == 10

    def test_invalid_page_number(self):
        """Test validation fails for page < 1."""
        with pytest.raises(HTTPException):
            validate_pagination(0, 10)

    def test_invalid_page_size(self):
        """Test validation fails for invalid page_size."""
        with pytest.raises(HTTPException):
            validate_pagination(1, 0)

        with pytest.raises(HTTPException):
            validate_pagination(1, 101)


@pytest.mark.unit
class TestSanitizeTextContent:
    """Test text content sanitization."""

    def test_remove_null_bytes(self):
        """Test null bytes are removed."""
        content = "Hello\x00World"
        sanitized = sanitize_text_content(content)
        assert "\x00" not in sanitized

    def test_remove_control_characters(self):
        """Test control characters are removed."""
        content = "Hello\x01\x02World"
        sanitized = sanitize_text_content(content)
        assert sanitized == "HelloWorld"

    def test_preserve_newlines_and_tabs(self):
        """Test newlines and tabs are preserved."""
        content = "Hello\nWorld\tTest"
        sanitized = sanitize_text_content(content)
        assert "\n" in sanitized
        assert "\t" in sanitized
