"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.session import close_db
from app.api.v1 import api_router
from app.mcp.server import get_mcp_app
from app.mcp.middleware import MCPAcceptMiddleware, MCPAuthMiddleware

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
    from app.db.session import init_engine, get_db_session, recreate_engine
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

    except (asyncpg.InvalidPasswordError, asyncpg.PostgresError) as e:
        logger.error(f"❌ Authentication failed with DATABASE_URL from environment: {e}")
        logger.error("💥 FATAL: Cannot connect to database with provided credentials")
        logger.error("    Please check:")
        logger.error("    1. PostgreSQL container is running: docker ps | grep kb-platform-db")
        logger.error("    2. DATABASE_URL/secret matches database password")
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

def build_combined_lifespan(
    primary: Callable,
    secondary: Callable | None,
):
    if secondary is None:
        return primary

    @asynccontextmanager
    async def _combined(app: FastAPI):
        async with primary(app):
            async with secondary(app):
                yield

    return _combined

# Build MCP app early so we can combine lifespans.
mcp_app = None
combined_lifespan = lifespan
try:
    mcp_app = get_mcp_app()
    mcp_lifespan = getattr(mcp_app, "lifespan", None)
    combined_lifespan = build_combined_lifespan(lifespan, mcp_lifespan)
except Exception as exc:
    logger.warning("Failed to initialize MCP app: %s", exc)

# Create FastAPI application
app = FastAPI(
    title="Knowledge Base Platform",
    description="Universal platform for creating and managing knowledge bases using RAG",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    lifespan=combined_lifespan,
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

# MCP endpoint (mounted separately, uses its own auth middleware)
if mcp_app:
    try:
        mcp_app.add_middleware(MCPAcceptMiddleware)
        mcp_app.add_middleware(MCPAuthMiddleware)
        if hasattr(mcp_app, "router"):
            mcp_app.router.redirect_slashes = False
        mount_path = settings.MCP_PATH if settings.MCP_PATH.startswith("/") else f"/{settings.MCP_PATH}"
        mount_path = mount_path.rstrip("/") or "/mcp"

        @app.middleware("http")
        async def mcp_slash_middleware(request, call_next):
            if request.url.path == mount_path:
                request.scope["path"] = mount_path + "/"
            return await call_next(request)

        app.mount(mount_path, mcp_app)
        logger.info("Mounted MCP endpoint at %s", mount_path)
    except Exception as exc:
        logger.warning("Failed to mount MCP endpoint: %s", exc)

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
