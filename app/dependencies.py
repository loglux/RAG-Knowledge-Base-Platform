"""FastAPI dependencies for dependency injection."""
from typing import Optional, AsyncGenerator
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db


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

async def get_current_user() -> Optional[UUID]:
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
    # TODO: Implement JWT authentication in Phase 6
    # For now, return None to indicate no authentication
    return None


async def get_current_user_id() -> Optional[UUID]:
    """
    Get current user ID or None if not authenticated.
    Alias for get_current_user for clarity.
    """
    return await get_current_user()


# ============================================================================
# Service Dependencies (to be implemented)
# ============================================================================

# Example for future service injection:
# def get_document_service(
#     db: AsyncSession = Depends(get_db_session)
# ) -> DocumentService:
#     return DocumentService(db)
