"""API v1 router configuration."""
from fastapi import APIRouter, Depends

from app.api.v1 import (
    health,
    knowledge_bases,
    kb_transfer,
    documents,
    chat,
    retrieve,
    embeddings,
    ollama,
    llm,
    settings,
    prompts,
    setup,
    system_settings,
    auth,
    auto_tune,
    mcp_tokens,
    mcp_refresh_tokens,
    mcp_oauth_events,
)
from app.dependencies import get_current_user_id

# Create main API router
api_router = APIRouter()
protected_router = APIRouter(dependencies=[Depends(get_current_user_id)])

# Public routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(setup.router, tags=["setup"])  # Setup wizard (no auth required)
api_router.include_router(auth.router)

# Protected routers
protected_router.include_router(knowledge_bases.router, prefix="/knowledge-bases", tags=["knowledge-bases"])
protected_router.include_router(kb_transfer.router)
protected_router.include_router(documents.router, prefix="/documents", tags=["documents"])
protected_router.include_router(chat.router, prefix="/chat", tags=["chat"])
protected_router.include_router(retrieve.router, prefix="/retrieve", tags=["retrieve"])
protected_router.include_router(settings.router, prefix="/settings", tags=["settings"])
protected_router.include_router(prompts.router, prefix="/prompts", tags=["prompts"])
protected_router.include_router(system_settings.router, prefix="/system-settings", tags=["system-settings"])
protected_router.include_router(embeddings.router, prefix="/embeddings", tags=["embeddings"])
protected_router.include_router(ollama.router, prefix="/ollama", tags=["ollama"])
protected_router.include_router(llm.router, prefix="/llm", tags=["llm"])
protected_router.include_router(auto_tune.router, tags=["auto-tune"])
protected_router.include_router(mcp_tokens.router)
protected_router.include_router(mcp_refresh_tokens.router)
protected_router.include_router(mcp_oauth_events.router)

api_router.include_router(protected_router)

__all__ = ["api_router"]
