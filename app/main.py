"""FastAPI application entry point."""

import logging
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import oauth
from app.api.v1 import api_router
from app.config import settings
from app.db.session import close_db
from app.mcp.manager import reload_mcp_routes
from app.mcp.server import get_mcp_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)

# In Docker: /app/secrets/secret_key (mounted volume)
# Local dev: <project_root>/secrets/secret_key
SECRET_KEY_FILE = Path(
    os.environ.get(
        "SECRET_KEY_FILE", Path(__file__).resolve().parent.parent / "secrets" / "secret_key"
    )
)


def _ensure_secret_key() -> None:
    """Load or auto-generate SECRET_KEY from secrets/secret_key file."""
    default_marker = "change-this"

    # 1. If already set to a real value (e.g. via env var), keep it
    if default_marker not in settings.SECRET_KEY:
        return

    # 2. Try to read from file
    if SECRET_KEY_FILE.is_file():
        key = SECRET_KEY_FILE.read_text().strip()
        if key:
            settings.SECRET_KEY = key
            logger.info("SECRET_KEY loaded from %s", SECRET_KEY_FILE)
            return

    # 3. Generate, persist, apply
    SECRET_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_hex(32)
    SECRET_KEY_FILE.write_text(key)
    os.chmod(SECRET_KEY_FILE, 0o600)
    settings.SECRET_KEY = key
    logger.info("Generated new SECRET_KEY → %s", SECRET_KEY_FILE)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup — ensure SECRET_KEY is set
    _ensure_secret_key()

    logger.info(f"Starting Knowledge Base Platform in {settings.ENVIRONMENT} mode")
    logger.info(f"Qdrant: {settings.QDRANT_URL}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")

    # CRITICAL: Initialize database engine with correct credentials
    import asyncpg
    from sqlalchemy import text

    from app.db.session import get_db_session, init_engine

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
        from app.config import is_setup_complete, load_settings_from_db

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

    try:
        await reload_mcp_routes(app)
    except Exception as exc:
        logger.warning("Failed to initialize MCP routes: %s", exc)
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
    logger.warning("Failed to initialize MCP app for lifespan: %s", exc)

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

# Include OAuth routers (no API prefix)
app.include_router(oauth.router)
app.include_router(oauth.public_router)

# Include API router
app.include_router(api_router, prefix=settings.API_PREFIX)

if mcp_app is not None:
    app.state.mcp_app = mcp_app


@app.middleware("http")
async def mcp_slash_middleware(request, call_next):
    mount_path = settings.MCP_PATH if settings.MCP_PATH.startswith("/") else f"/{settings.MCP_PATH}"
    mount_path = mount_path.rstrip("/") or "/mcp"
    if request.url.path == mount_path:
        request.scope["path"] = mount_path + "/"
    return await call_next(request)


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
            "suggestion": "Check /docs for available endpoints",
        },
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
