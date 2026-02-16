"""Input validation utilities."""

import re
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status

from app.config import settings
from app.models.enums import FileType


def validate_file_size(content: str, max_size_bytes: Optional[int] = None) -> int:
    """
    Validate file content size.

    Args:
        content: File content as string
        max_size_bytes: Maximum allowed size in bytes
                       If None, uses settings.max_file_size_bytes

    Returns:
        File size in bytes

    Raises:
        HTTPException: If file size exceeds limit
    """
    size = len(content.encode("utf-8"))
    max_size = max_size_bytes or settings.max_file_size_bytes

    if size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size {size} bytes exceeds limit of {max_size} bytes",
        )

    return size


def validate_file_type(filename: str) -> FileType:
    """
    Validate and detect file type from filename.

    Args:
        filename: Name of the file

    Returns:
        FileType enum value

    Raises:
        HTTPException: If file type is not supported
    """
    if "." not in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Filename must have an extension"
        )

    extension = filename.rsplit(".", 1)[-1].lower()

    # Check if extension is allowed
    if extension not in settings.allowed_file_types_list:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type .{extension} not supported. Allowed: {settings.allowed_file_types_list}",
        )

    # Map to FileType enum
    try:
        return FileType(extension)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type .{extension} not supported in current version",
        )


def validate_filename(filename: str) -> str:
    """
    Validate filename for security and compatibility.

    Checks for:
    - Path traversal attempts (../)
    - Invalid characters
    - Reasonable length

    Args:
        filename: Filename to validate

    Returns:
        Sanitized filename

    Raises:
        HTTPException: If filename is invalid
    """
    # Check for path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename contains invalid path characters",
        )

    # Check length
    if len(filename) < 1 or len(filename) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must be between 1 and 255 characters",
        )

    # Check for invalid characters (basic check)
    if re.search(r'[<>:"|?*]', filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Filename contains invalid characters"
        )

    return filename.strip()


def validate_uuid(value: str, field_name: str = "ID") -> UUID:
    """
    Validate and parse UUID string.

    Args:
        value: String to validate as UUID
        field_name: Name of the field (for error messages)

    Returns:
        UUID object

    Raises:
        HTTPException: If value is not a valid UUID
    """
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format. Must be a valid UUID",
        )


def validate_pagination(page: int, page_size: int) -> tuple[int, int]:
    """
    Validate pagination parameters.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Tuple of (validated_page, validated_page_size)

    Raises:
        HTTPException: If pagination parameters are invalid
    """
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Page number must be >= 1"
        )

    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Page size must be between 1 and 100"
        )

    return page, page_size


def sanitize_text_content(content: str) -> str:
    """
    Sanitize text content by removing potentially dangerous content.

    For MVP: Basic cleanup of null bytes and control characters.
    Future: More sophisticated sanitization for HTML/scripts.

    Args:
        content: Text content to sanitize

    Returns:
        Sanitized content
    """
    # Remove null bytes
    content = content.replace("\x00", "")

    # Remove other control characters except newlines and tabs
    content = "".join(char for char in content if char == "\n" or char == "\t" or ord(char) >= 32)

    return content.strip()
