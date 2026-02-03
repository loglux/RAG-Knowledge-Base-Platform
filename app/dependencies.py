"""FastAPI dependencies for dependency injection."""
from typing import Optional, AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.auth import decode_token, is_token_type, get_admin_id, ACCESS_TOKEN_TYPE


# ============================================================================
# Database Dependencies
# ============================================================================

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session.
    Alias for get_db for clarity.
    """
    async for session in get_db():
        yield session


# ============================================================================
# Authentication Dependencies (prepared for future)
# ============================================================================

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> int:
    """
    Get current authenticated user.

    MVP: Returns None (no authentication)
    Future: Parse JWT token and return user_id

    Usage:
        @app.get("/protected")
        async def protected_route(user_id: UUID = Depends(get_current_user)):
            if user_id is None:
                # Handle unauthenticated access
                pass
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if not is_token_type(payload, ACCESS_TOKEN_TYPE):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    admin_id = get_admin_id(payload)
    if admin_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    return admin_id


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> Optional[UUID]:
    """
    Validate current user and return None (user_id is not stored yet).
    Keeps auth enforcement without writing admin int IDs into UUID columns.
    """
    await get_current_user(credentials)
    return None


# ============================================================================
# Service Dependencies (to be implemented)
# ============================================================================

# Example for future service injection:
# def get_document_service(
#     db: AsyncSession = Depends(get_db_session)
# ) -> DocumentService:
#     return DocumentService(db)
