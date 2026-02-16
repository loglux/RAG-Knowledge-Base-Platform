"""Database session management with async SQLAlchemy."""

from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import settings

# Global engine and session factory (initialized lazily)
engine: Optional[AsyncEngine] = None
AsyncSessionLocal: Optional[async_sessionmaker] = None


def _create_engine(database_url: str) -> AsyncEngine:
    """
    Create async engine with given database URL.

    Args:
        database_url: PostgreSQL connection URL

    Returns:
        AsyncEngine instance
    """
    return create_async_engine(
        database_url,
        echo=settings.DB_ECHO,
        pool_pre_ping=True,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        poolclass=NullPool if settings.ENVIRONMENT == "testing" else None,
    )


def init_engine(database_url: Optional[str] = None) -> None:
    """
    Initialize database engine and session factory.

    Called during application startup in main.py lifespan.

    Args:
        database_url: Optional database URL override (uses settings.DATABASE_URL if not provided)
    """
    global engine, AsyncSessionLocal

    url = database_url or settings.DATABASE_URL

    engine = _create_engine(url)

    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.

    Usage in FastAPI:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_engine() first.")

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_db_session() -> AsyncSession:
    """
    Get a database session for standalone use (not FastAPI dependency).

    Usage:
        async with get_db_session() as db:
            result = await db.execute(select(Item))
            items = result.scalars().all()

    Returns:
        AsyncSession context manager
    """
    if AsyncSessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_engine() first.")

    return AsyncSessionLocal()


async def init_db() -> None:
    """
    Initialize database - create all tables.

    Note: In production, use Alembic migrations instead.
    This is mainly for testing purposes.
    """
    if engine is None:
        raise RuntimeError("Database not initialized. Call init_engine() first.")

    from app.models.database import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connection pool."""
    if engine is not None:
        await engine.dispose()


async def recreate_engine(new_database_url: str) -> None:
    """
    Recreate database engine and session factory with new connection URL.

    This is used when PostgreSQL password is changed via Setup Wizard.
    The old connection pool must be disposed and recreated with new credentials.

    Args:
        new_database_url: New PostgreSQL connection URL with updated credentials

    Example:
        await recreate_engine("postgresql+asyncpg://kb_user:new_pass@db:5432/knowledge_base")
    """
    global engine, AsyncSessionLocal

    import logging

    logger = logging.getLogger(__name__)

    try:
        # 1. Dispose old engine (close all connections)
        if engine is not None:
            logger.info("Disposing old database connection pool...")
            await engine.dispose()

        # 2. Update settings with new DATABASE_URL
        logger.info("Updating settings with new DATABASE_URL...")
        settings.update_from_dict({"DATABASE_URL": new_database_url})

        # 3. Create new engine with new credentials
        logger.info("Creating new database engine with updated credentials...")
        engine = _create_engine(new_database_url)

        # 4. Create new session factory
        logger.info("Creating new session factory...")
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        logger.info("✅ Database connection pool successfully recreated with new credentials")

    except Exception as e:
        logger.error(f"Failed to recreate database engine: {e}")
        raise
