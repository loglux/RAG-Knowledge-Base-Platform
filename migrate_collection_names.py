#!/usr/bin/env python3
"""
Migrate existing KB collection_name to deterministic format.

This script:
1. Reads all active KBs from PostgreSQL
2. For each KB, calculates correct collection_name from KB ID
3. Creates Qdrant alias: old_name -> new_name
4. Updates collection_name in PostgreSQL
5. Verifies migration
"""
import asyncio
import sys
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

# Add app to path
sys.path.insert(0, '/app')

from app.db.session import AsyncSessionLocal
from app.models.database import KnowledgeBase as KnowledgeBaseModel


def kb_id_to_collection_name(kb_id: UUID) -> str:
    """Convert KB ID to collection name (deterministic)."""
    return f"kb_{str(kb_id).replace('-', '')}"


async def migrate_collection_names():
    """Migrate all KB collection names to deterministic format."""
    print("=" * 60)
    print("MIGRATION: Collection Names -> Deterministic Format")
    print("=" * 60)
    print()

    # Connect to Qdrant
    qdrant = QdrantClient(url="http://qdrant:6333")
    print("✓ Connected to Qdrant")

    # Get all active KBs
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(KnowledgeBaseModel).where(
                KnowledgeBaseModel.is_deleted == False
            ).order_by(KnowledgeBaseModel.created_at)
        )
        kbs = result.scalars().all()

    print(f"✓ Found {len(kbs)} active knowledge bases\n")

    migrated = 0
    skipped = 0
    errors = 0

    for i, kb in enumerate(kbs, 1):
        old_name = kb.collection_name
        new_name = kb_id_to_collection_name(kb.id)

        print(f"[{i}/{len(kbs)}] {kb.name}")
        print(f"  Old: {old_name}")
        print(f"  New: {new_name}")

        # Check if already migrated
        if old_name == new_name:
            print(f"  → Already migrated, skipping")
            skipped += 1
            print()
            continue

        try:
            # Check if old collection exists
            collections = qdrant.get_collections().collections
            collection_names = [c.name for c in collections]

            if old_name not in collection_names:
                print(f"  ⚠ Old collection not found in Qdrant, updating DB only")
                async with AsyncSessionLocal() as db:
                    await db.execute(
                        update(KnowledgeBaseModel)
                        .where(KnowledgeBaseModel.id == kb.id)
                        .values(collection_name=new_name)
                    )
                    await db.commit()
                migrated += 1
                print(f"  ✓ Updated DB")
                print()
                continue

            # Create alias: new_name -> old_name
            # This allows accessing old collection via new name
            qdrant.update_collection_aliases(
                change_aliases_operations=[
                    qdrant_models.CreateAliasOperation(
                        create_alias=qdrant_models.CreateAlias(
                            collection_name=old_name,
                            alias_name=new_name
                        )
                    )
                ]
            )
            print(f"  ✓ Created Qdrant alias: {new_name} -> {old_name}")

            # Update PostgreSQL
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(KnowledgeBaseModel)
                    .where(KnowledgeBaseModel.id == kb.id)
                    .values(collection_name=new_name)
                )
                await db.commit()
            print(f"  ✓ Updated PostgreSQL")

            migrated += 1
            print()

        except Exception as e:
            print(f"  ✗ Error: {e}")
            errors += 1
            print()
            continue

    print("=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Total:    {len(kbs)}")
    print(f"Migrated: {migrated}")
    print(f"Skipped:  {skipped}")
    print(f"Errors:   {errors}")
    print()

    if errors == 0:
        print("✓ Migration completed successfully!")
    else:
        print(f"⚠ Migration completed with {errors} errors")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(migrate_collection_names())
    sys.exit(exit_code)
