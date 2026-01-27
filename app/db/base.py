"""Import all models here for Alembic to detect them."""

# Import Base first
from app.models.database import Base

# Import all models so Alembic can detect them
from app.models.database import KnowledgeBase, Document, DocumentStructure, Conversation, ChatMessage, AppSettings

__all__ = [
    "Base",
    "KnowledgeBase",
    "Document",
    "DocumentStructure",
    "Conversation",
    "ChatMessage",
    "AppSettings",
]
