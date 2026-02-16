"""Import all models here for Alembic to detect them."""

# Import Base first
# Import all models so Alembic can detect them
from app.models.database import (
    AppSettings,
    Base,
    ChatMessage,
    Conversation,
    Document,
    DocumentStructure,
    KnowledgeBase,
    MCPAuthCode,
    MCPAuthEvent,
    MCPRefreshToken,
    MCPToken,
    PromptVersion,
    QAEvalResult,
    QAEvalRun,
    QASample,
    SelfCheckPromptVersion,
)

__all__ = [
    "Base",
    "KnowledgeBase",
    "Document",
    "DocumentStructure",
    "Conversation",
    "ChatMessage",
    "PromptVersion",
    "SelfCheckPromptVersion",
    "AppSettings",
    "MCPToken",
    "MCPRefreshToken",
    "MCPAuthCode",
    "MCPAuthEvent",
    "QASample",
    "QAEvalRun",
    "QAEvalResult",
]
