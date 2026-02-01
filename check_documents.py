#!/usr/bin/env python3
"""Quick script to check documents in database."""
import asyncio
from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.models.database import Document, KnowledgeBase

async def check_documents():
    """List documents in database."""
    async with AsyncSessionLocal() as db:
        # Get documents with knowledge base info
        stmt = (
            select(
                Document.id,
                Document.filename,
                Document.file_type,
                func.length(Document.content).label('content_length'),
                func.substring(Document.content, 1, 200).label('preview'),
                KnowledgeBase.name.label('kb_name')
            )
            .join(KnowledgeBase, Document.knowledge_base_id == KnowledgeBase.id)
            .where(Document.is_deleted == False)
            .order_by(Document.created_at.desc())
            .limit(10)
        )

        result = await db.execute(stmt)
        documents = result.all()

        print("=" * 80)
        print("DOCUMENTS IN DATABASE")
        print("=" * 80)
        print()

        if not documents:
            print("No documents found.")
            return

        for i, doc in enumerate(documents, 1):
            print(f"{i}. {doc.filename} ({doc.file_type})")
            print(f"   KB: {doc.kb_name}")
            print(f"   Length: {doc.content_length} chars")
            print(f"   Preview: {doc.preview[:100]}...")
            print()

if __name__ == "__main__":
    asyncio.run(check_documents())
