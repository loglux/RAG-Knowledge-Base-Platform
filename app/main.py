"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.session import close_db
from app.api.v1 import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting Knowledge Base Platform in {settings.ENVIRONMENT} mode")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'configured'}")
    logger.info(f"Qdrant: {settings.QDRANT_URL}")
    logger.info(f"OpenAI Model: {settings.OPENAI_CHAT_MODEL}")

    # CRITICAL: Initialize database engine with correct credentials
    # Try environment DATABASE_URL first, fallback to checking system_settings if authentication fails
    from app.db.session import init_engine, get_db_session, recreate_engine
    from app.core.system_settings import SystemSettingsManager
    from sqlalchemy import text
    import asyncpg

    logger.info("Initializing database connection...")

    # Try to connect with DATABASE_URL from environment
    try:
        init_engine(settings.DATABASE_URL)
        logger.info("✓ Engine initialized with DATABASE_URL from environment")

        # Test connection
        async with get_db_session() as db:
            await db.execute(text("SELECT 1"))
            logger.info("✓ Database connection test successful")

            # Check if there's a different password in system_settings
            try:
                saved_db_url = await SystemSettingsManager.get_setting(db, "database_url")
                if saved_db_url and saved_db_url != settings.DATABASE_URL:
                    logger.warning("⚠ DATABASE_URL mismatch detected in system_settings")
                    logger.warning(f"  ENV: {settings.DATABASE_URL.split('@')[0]}@...")
                    logger.warning(f"  DB:  {saved_db_url.split('@')[0]}@...")
                    logger.info("🔄 Recreating connection pool with saved credentials...")
                    await recreate_engine(saved_db_url)
                    logger.info("✅ Connection pool updated with credentials from system_settings")
            except Exception as e:
                logger.debug(f"Could not check system_settings for database_url: {e}")

    except (asyncpg.InvalidPasswordError, asyncpg.PostgresError) as e:
        logger.error(f"❌ Authentication failed with DATABASE_URL from environment: {e}")
        logger.info("🔄 Attempting to connect with default credentials to check system_settings...")

        # Try default credentials as fallback
        default_url = "postgresql+asyncpg://kb_user:kb_pass_change_me@db:5432/knowledge_base"
        try:
            init_engine(default_url)
            async with get_db_session() as db:
                await db.execute(text("SELECT 1"))
                logger.info("✓ Connected with default credentials")

                # Read saved DATABASE_URL from system_settings
                saved_db_url = await SystemSettingsManager.get_setting(db, "database_url")
                if saved_db_url:
                    logger.info(f"✅ Found saved DATABASE_URL in system_settings")
                    logger.info("🔄 Recreating connection pool with correct credentials...")
                    await recreate_engine(saved_db_url)
                    logger.info("✅ Connection successful with credentials from system_settings")
                else:
                    logger.warning("⚠ No database_url in system_settings, using default")

        except Exception as fallback_error:
            logger.error(f"❌ Failed to connect with default credentials: {fallback_error}")
            logger.error("💥 FATAL: Cannot connect to database with any known credentials")
            logger.error("    Please check:")
            logger.error("    1. PostgreSQL container is running: docker ps | grep kb-platform-db")
            logger.error("    2. DATABASE_URL in environment matches database password")
            logger.error("    3. Run recovery script: ./scripts/recover_database_url.sh")
            raise

    # Load settings from database (overrides .env)
    try:
        from app.config import load_settings_from_db, is_setup_complete

        logger.info("Loading settings from database...")
        await load_settings_from_db()

        # Check if setup is complete
        setup_complete = await is_setup_complete()
        if setup_complete:
            logger.info("✓ Setup is complete - system ready")
        else:
            logger.warning("⚠ Setup not complete - please visit /api/v1/setup/status")

    except Exception as e:
        logger.warning(f"Could not load settings from database: {e}")
        logger.info("Using settings from environment variables")

    yield

    # Shutdown
    logger.info("Shutting down Knowledge Base Platform")
    await close_db()


# Create FastAPI application
app = FastAPI(
    title="Knowledge Base Platform",
    description="Universal platform for creating and managing knowledge bases using RAG",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint - API information."""
    return {
        "name": "Knowledge Base Platform API",
        "version": "0.1.0",
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": f"{settings.API_PREFIX}/health",
    }


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler."""
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Endpoint not found",
            "path": str(request.url.path),
            "suggestion": "Check /docs for available endpoints"
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
