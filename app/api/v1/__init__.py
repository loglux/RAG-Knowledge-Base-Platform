"""API v1 router configuration."""
from fastapi import APIRouter

from app.api.v1 import health, knowledge_bases, documents, chat, embeddings, ollama, llm

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(knowledge_bases.router, prefix="/knowledge-bases", tags=["knowledge-bases"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(embeddings.router, prefix="/embeddings", tags=["embeddings"])
api_router.include_router(ollama.router, prefix="/ollama", tags=["ollama"])
api_router.include_router(llm.router, prefix="/llm", tags=["llm"])

__all__ = ["api_router"]