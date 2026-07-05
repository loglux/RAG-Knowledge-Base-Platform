"""HMAC signing for presigned document-upload URLs.

Lets an MCP client push a large binary file directly via HTTP PUT instead of
routing it through content_base64 in a tool-call payload — see
app.mcp.server::create_upload_url (issues signed URLs) and
app.api.v1.uploads (verifies and consumes them).
"""

import hashlib
import hmac

from app.config import settings

UPLOAD_URL_TTL_SECONDS = 300  # 5 minutes


def _canonical_payload(
    upload_id: str, knowledge_base_id: str, filename: str, expires: int
) -> bytes:
    return f"{upload_id}:{knowledge_base_id}:{filename}:{expires}".encode("utf-8")


def sign_upload(upload_id: str, knowledge_base_id: str, filename: str, expires: int) -> str:
    """Compute the HMAC-SHA256 signature for a presigned upload URL."""
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        _canonical_payload(upload_id, knowledge_base_id, filename, expires),
        hashlib.sha256,
    ).hexdigest()


def verify_upload_signature(
    upload_id: str, knowledge_base_id: str, filename: str, expires: int, signature: str
) -> bool:
    """Constant-time check that `signature` matches the expected HMAC for these fields."""
    expected = sign_upload(upload_id, knowledge_base_id, filename, expires)
    return hmac.compare_digest(expected, signature)
