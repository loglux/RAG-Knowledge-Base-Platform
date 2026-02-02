# Migration and Export/Import Guide

## Overview

This guide covers proper procedures for migrating, exporting, and importing data in the Knowledge Base Platform. The system has complex relationships between three data stores that must be maintained:

- **PostgreSQL**: KB metadata, documents, settings
- **Qdrant**: Vector embeddings for semantic search
- **OpenSearch**: BM25 lexical search indices

**CRITICAL**: Collection names in Qdrant MUST match the `collection_name` field in PostgreSQL for the system to function correctly.

## System Architecture

```
Knowledge Base (PostgreSQL)
    ├── id: UUID (primary key)
    ├── collection_name: str (deterministic from KB ID)
    └── Documents
            ├── id: UUID
            ├── knowledge_base_id: FK to KB
            └── Chunks (stored in Qdrant & OpenSearch)
                    ├── Vector embeddings (Qdrant collection)
                    └── BM25 index (OpenSearch)
```

## Collection Name Format

**Current (Correct) Format**:
```python
def kb_id_to_collection_name(kb_id: UUID) -> str:
    """Convert KB ID to deterministic collection name."""
    return f"kb_{str(kb_id).replace('-', '')}"

# Example:
# KB ID:           5fa35044-2bbf-4bfa-8fc4-b6588d5da08d
# Collection name: kb_5fa350442bbf4bfa8fc4b6588d5da08d
```

**Historical Issue** (before 2026-02-02):
- Used random UUID for collection_name: `f"kb_{uuid.uuid4().hex[:16]}"`
- No way to derive collection_name from KB ID
- Made migration/export/import extremely difficult
- **Fixed**: commit 72c7a81

## Pre-Migration Checklist

Before any migration, export, or import:

1. **Verify system consistency**:
   ```bash
   ./check_databases.sh
   ```
   - Should show equal counts: PostgreSQL KB = Qdrant collections
   - Identifies orphaned data needing cleanup

2. **Backup all data**:
   ```bash
   # PostgreSQL dump
   docker exec kb-platform-db pg_dump -U kb_user knowledge_base > backup_postgres_$(date +%Y%m%d).sql

   # Qdrant snapshot
   docker exec kb-platform-qdrant curl -X POST http://localhost:6333/collections/snapshot

   # OpenSearch snapshot (via API)
   curl -X PUT "http://localhost:9200/_snapshot/backup_$(date +%Y%m%d)"
   ```

3. **Document current state**:
   ```bash
   # Count records
   docker exec kb-platform-db psql -U kb_user -d knowledge_base -c "SELECT COUNT(*) FROM knowledge_bases WHERE is_deleted=false;"

   # List Qdrant collections
   curl http://localhost:6334/collections | jq '.result.collections[].name'

   # Count OpenSearch documents
   curl http://localhost:9200/chunks/_count | jq .
   ```

4. **Stop application** (to prevent writes during migration):
   ```bash
   docker-compose -f docker-compose.production.yml stop api
   ```

## Export Procedures

### Full System Export

```bash
#!/bin/bash
# export_full_system.sh

EXPORT_DIR="export_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$EXPORT_DIR"

echo "Exporting Knowledge Base Platform..."

# 1. Export PostgreSQL
echo "1/3 Exporting PostgreSQL..."
docker exec kb-platform-db pg_dump -U kb_user knowledge_base > "$EXPORT_DIR/postgres.sql"

# 2. Export Qdrant collections
echo "2/3 Exporting Qdrant collections..."
COLLECTIONS=$(curl -s http://localhost:6334/collections | jq -r '.result.collections[].name')

mkdir -p "$EXPORT_DIR/qdrant"
for collection in $COLLECTIONS; do
    echo "  Exporting collection: $collection"
    # Create snapshot for each collection
    docker exec kb-platform-qdrant curl -X POST \
        "http://localhost:6333/collections/$collection/snapshots"

    # Copy snapshot from container
    SNAPSHOT=$(docker exec kb-platform-qdrant ls /qdrant/storage/collections/$collection/snapshots | tail -1)
    docker cp "kb-platform-qdrant:/qdrant/storage/collections/$collection/snapshots/$SNAPSHOT" \
        "$EXPORT_DIR/qdrant/${collection}.snapshot"
done

# 3. Export OpenSearch indices
echo "3/3 Exporting OpenSearch..."
docker exec kb-platform-opensearch curl -X GET "http://localhost:9200/chunks/_search?size=10000" \
    > "$EXPORT_DIR/opensearch_chunks.json"

# 4. Export mapping (critical for recovery)
echo "Creating mapping file..."
docker exec kb-platform-db psql -U kb_user -d knowledge_base -c \
    "SELECT id, collection_name, name FROM knowledge_bases WHERE is_deleted=false;" \
    > "$EXPORT_DIR/kb_collection_mapping.txt"

# 5. Create metadata
echo "Creating metadata..."
cat > "$EXPORT_DIR/METADATA.txt" <<EOF
Export Date: $(date)
PostgreSQL KB Count: $(docker exec kb-platform-db psql -U kb_user -d knowledge_base -t -c "SELECT COUNT(*) FROM knowledge_bases WHERE is_deleted=false;")
Qdrant Collections: $(echo "$COLLECTIONS" | wc -l)
OpenSearch Docs: $(curl -s http://localhost:9200/chunks/_count | jq .count)
Collection Name Format: kb_{uuid_without_dashes}
EOF

echo "Export complete: $EXPORT_DIR"
tar -czf "${EXPORT_DIR}.tar.gz" "$EXPORT_DIR"
echo "Archive created: ${EXPORT_DIR}.tar.gz"
```

### Single Knowledge Base Export

```bash
#!/bin/bash
# export_single_kb.sh <kb_id>

KB_ID=$1
if [ -z "$KB_ID" ]; then
    echo "Usage: $0 <kb_id>"
    exit 1
fi

EXPORT_DIR="kb_${KB_ID}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$EXPORT_DIR"

# Get collection name from PostgreSQL
COLLECTION_NAME=$(docker exec kb-platform-db psql -U kb_user -d knowledge_base -t -c \
    "SELECT collection_name FROM knowledge_bases WHERE id='$KB_ID';")

if [ -z "$COLLECTION_NAME" ]; then
    echo "ERROR: KB $KB_ID not found"
    exit 1
fi

echo "Exporting KB: $KB_ID"
echo "Collection: $COLLECTION_NAME"

# 1. Export KB metadata
docker exec kb-platform-db psql -U kb_user -d knowledge_base -c \
    "COPY (SELECT * FROM knowledge_bases WHERE id='$KB_ID') TO STDOUT WITH CSV HEADER;" \
    > "$EXPORT_DIR/kb_metadata.csv"

# 2. Export documents
docker exec kb-platform-db psql -U kb_user -d knowledge_base -c \
    "COPY (SELECT * FROM documents WHERE knowledge_base_id='$KB_ID' AND is_deleted=false) TO STDOUT WITH CSV HEADER;" \
    > "$EXPORT_DIR/documents.csv"

# 3. Export Qdrant collection
docker exec kb-platform-qdrant curl -X POST \
    "http://localhost:6333/collections/$COLLECTION_NAME/snapshots"

SNAPSHOT=$(docker exec kb-platform-qdrant ls /qdrant/storage/collections/$COLLECTION_NAME/snapshots | tail -1)
docker cp "kb-platform-qdrant:/qdrant/storage/collections/$COLLECTION_NAME/snapshots/$SNAPSHOT" \
    "$EXPORT_DIR/vectors.snapshot"

# 4. Export OpenSearch chunks
curl -X GET "http://localhost:9200/chunks/_search" -H 'Content-Type: application/json' -d '{
  "query": {
    "term": {
      "kb_id": "'$KB_ID'"
    }
  },
  "size": 10000
}' > "$EXPORT_DIR/opensearch_chunks.json"

echo "Export complete: $EXPORT_DIR"
```

## Import Procedures

### Full System Import

```bash
#!/bin/bash
# import_full_system.sh <export_archive.tar.gz>

ARCHIVE=$1
if [ -z "$ARCHIVE" ]; then
    echo "Usage: $0 <export_archive.tar.gz>"
    exit 1
fi

# Extract archive
tar -xzf "$ARCHIVE"
EXPORT_DIR=$(basename "$ARCHIVE" .tar.gz)

echo "Importing from: $EXPORT_DIR"

# CRITICAL: Stop API to prevent conflicts
docker-compose -f docker-compose.production.yml stop api

# 1. Import PostgreSQL
echo "1/3 Importing PostgreSQL..."
docker exec -i kb-platform-db psql -U kb_user knowledge_base < "$EXPORT_DIR/postgres.sql"

# 2. Import Qdrant collections
echo "2/3 Importing Qdrant collections..."
for snapshot in "$EXPORT_DIR/qdrant"/*.snapshot; do
    collection=$(basename "$snapshot" .snapshot)
    echo "  Importing collection: $collection"

    # Copy snapshot to container
    docker cp "$snapshot" "kb-platform-qdrant:/tmp/$(basename $snapshot)"

    # Recover from snapshot
    docker exec kb-platform-qdrant curl -X POST \
        "http://localhost:6333/collections/$collection/snapshots/recover" \
        -H 'Content-Type: application/json' \
        -d '{"location": "/tmp/'$(basename $snapshot)'"}'
done

# 3. Import OpenSearch
echo "3/3 Importing OpenSearch..."
# Bulk import chunks
cat "$EXPORT_DIR/opensearch_chunks.json" | \
    jq -c '.hits.hits[] | {"index": {"_index": "chunks", "_id": ._id}}, ._source' | \
    curl -X POST "http://localhost:9200/_bulk" -H 'Content-Type: application/json' --data-binary @-

# 4. Verify import
echo "Verifying import..."
PG_COUNT=$(docker exec kb-platform-db psql -U kb_user -d knowledge_base -t -c \
    "SELECT COUNT(*) FROM knowledge_bases WHERE is_deleted=false;")
QDRANT_COUNT=$(curl -s http://localhost:6334/collections | jq '.result.collections | length')
OS_COUNT=$(curl -s http://localhost:9200/chunks/_count | jq .count)

echo "Import verification:"
echo "  PostgreSQL KB: $PG_COUNT"
echo "  Qdrant collections: $QDRANT_COUNT"
echo "  OpenSearch docs: $OS_COUNT"

# Restart API
docker-compose -f docker-compose.production.yml --env-file .env.production start api

echo "Import complete!"
```

### Important Import Notes

1. **Document ID Compatibility**: Ensure `document_id` field format matches between systems:
   - PostgreSQL stores as UUID
   - Qdrant metadata uses string UUID
   - OpenSearch uses string UUID
   - **Always verify with sample query before bulk import**

2. **Collection Name Validation**: Before import, verify collection_name format:
   ```python
   # Check if collection names are deterministic
   import re
   pattern = r'^kb_[a-f0-9]{32}$'  # kb_ + 32 hex chars (UUID without dashes)

   for kb in knowledge_bases:
       if not re.match(pattern, kb.collection_name):
           print(f"WARNING: Non-standard collection_name: {kb.collection_name}")
           # Calculate correct name
           correct_name = kb_id_to_collection_name(kb.id)
           print(f"  Should be: {correct_name}")
   ```

3. **Alias Handling**: If importing data with old (random) collection names:
   ```bash
   # Create alias for backward compatibility
   curl -X POST http://localhost:6334/collections/aliases -H 'Content-Type: application/json' -d '{
     "actions": [
       {
         "create_alias": {
           "collection_name": "old_random_collection_name",
           "alias_name": "kb_5fa350442bbf4bfa8fc4b6588d5da08d"
         }
       }
     ]
   }'
   ```

## Migration from Random to Deterministic Collection Names

If you have existing KB with random collection_name format, use the migration script:

```bash
# Run migration script
python migrate_collection_names.py

# Expected output:
# [1/19] KB Name
#   Old: kb_28baec01e7514e16
#   New: kb_5fa350442bbf4bfa8fc4b6588d5da08d
#   ✓ Created Qdrant alias
#   ✓ Updated PostgreSQL
#
# MIGRATION SUMMARY
# Total:    19
# Migrated: 19
# Skipped:  0
# Errors:   0
```

**What the script does**:
1. Reads all active KB from PostgreSQL
2. Calculates correct `collection_name` from KB ID
3. Creates Qdrant alias: `new_name` → `old_collection`
4. Updates PostgreSQL `collection_name` field
5. Verifies each migration step

**After migration**:
- Old Qdrant collections still exist (not deleted for safety)
- Aliases allow seamless access via new names
- New KB automatically use deterministic format

**Optional cleanup** (after verifying system works):
```bash
# List old collections
curl http://localhost:6334/collections | jq '.result.collections[].name'

# Delete old collection (after confirming alias works)
curl -X DELETE http://localhost:6334/collections/kb_28baec01e7514e16
```

## Troubleshooting

### Issue: Collection Not Found

**Symptom**: Error when querying KB: "Collection kb_xxx not found"

**Diagnosis**:
```bash
# Check PostgreSQL collection_name
docker exec kb-platform-db psql -U kb_user -d knowledge_base -c \
    "SELECT id, collection_name FROM knowledge_bases WHERE id='<kb_id>';"

# Check Qdrant collections
curl http://localhost:6334/collections | jq '.result.collections[].name'

# Check for aliases
curl http://localhost:6334/collections/<collection_name>
```

**Solution**:
1. If collection exists with different name → Create alias
2. If collection missing → Restore from backup or reindex documents
3. If collection_name format wrong → Run migration script

### Issue: Document Count Mismatch

**Symptom**: Different counts in PostgreSQL vs Qdrant/OpenSearch

**Diagnosis**:
```bash
# Count in PostgreSQL
docker exec kb-platform-db psql -U kb_user -d knowledge_base -c \
    "SELECT kb.name, COUNT(d.id) FROM knowledge_bases kb
     LEFT JOIN documents d ON kb.id = d.knowledge_base_id AND d.is_deleted=false
     WHERE kb.is_deleted=false GROUP BY kb.id, kb.name;"

# Count in Qdrant
for collection in $(curl -s http://localhost:6334/collections | jq -r '.result.collections[].name'); do
    count=$(curl -s "http://localhost:6334/collections/$collection" | jq .result.points_count)
    echo "$collection: $count"
done

# Count in OpenSearch
curl -X GET "http://localhost:9200/chunks/_search" -H 'Content-Type: application/json' -d '{
  "aggs": {
    "kb_counts": {
      "terms": {
        "field": "kb_id",
        "size": 100
      }
    }
  },
  "size": 0
}'
```

**Solution**:
- If Qdrant/OpenSearch missing chunks → Reprocess documents via API:
  ```bash
  curl -X POST http://localhost:8004/api/v1/knowledge-bases/<kb_id>/reprocess
  ```
- If orphaned chunks exist → Clean up:
  ```bash
  curl -X POST http://localhost:8004/api/v1/knowledge-bases/<kb_id>/cleanup-orphaned-chunks
  ```

### Issue: Import Fails with "Duplicate Key"

**Symptom**: PostgreSQL import fails with "duplicate key value violates unique constraint"

**Cause**: Target database already has data with same IDs

**Solution**:
```bash
# Option 1: Clear target database first (DESTRUCTIVE)
docker exec kb-platform-db psql -U kb_user -d knowledge_base -c "TRUNCATE knowledge_bases, documents CASCADE;"

# Option 2: Import only missing records
# Extract IDs from target DB
docker exec kb-platform-db psql -U kb_user -d knowledge_base -t -c \
    "SELECT id FROM knowledge_bases;" > existing_ids.txt

# Filter export to exclude existing IDs (manual SQL editing)
```

### Issue: Qdrant Snapshot Recovery Fails

**Symptom**: "Failed to recover from snapshot"

**Diagnosis**:
```bash
# Check Qdrant logs
docker-compose -f docker-compose.production.yml logs qdrant | tail -50

# Verify snapshot file integrity
docker exec kb-platform-qdrant ls -lh /qdrant/storage/collections/*/snapshots/
```

**Solution**:
1. Ensure snapshot was created correctly during export
2. Check Qdrant version compatibility (export vs import)
3. Manually create collection first, then recover:
   ```bash
   # Create empty collection
   curl -X PUT "http://localhost:6334/collections/<collection_name>" \
        -H 'Content-Type: application/json' \
        -d '{
          "vectors": {
            "size": 1024,  # Match embedding dimension
            "distance": "Cosine"
          }
        }'

   # Then recover from snapshot
   curl -X POST "http://localhost:6334/collections/<collection_name>/snapshots/recover" \
        -H 'Content-Type: application/json' \
        -d '{"location": "/tmp/vectors.snapshot"}'
   ```

## Best Practices

1. **Always use `check_databases.sh` before and after migrations**
   - Verifies system consistency
   - Identifies orphaned data
   - Prevents silent data corruption

2. **Document all manual changes**
   - Keep log of collection renames, deletions, manual fixes
   - Helps troubleshoot future issues

3. **Test imports on dev environment first**
   - Never import directly to production without testing
   - Verify data integrity and application functionality

4. **Maintain backup retention policy**
   - Keep at least 3 recent backups
   - Store backups off-server
   - Test restore procedures regularly

5. **Use deterministic naming everywhere**
   - Never generate random UUIDs for system identifiers
   - Always derive related IDs from primary keys
   - Makes debugging and recovery much easier

6. **Version control configuration**
   - Commit `.env.example` with all required variables
   - Document any manual configuration steps
   - Track database schema changes with Alembic

## Historical Issues and Lessons Learned

### Issue 1: Random Collection Names (2026-01-23 to 2026-02-02)

**Problem**:
- Collection names generated with random UUID
- No way to derive collection_name from KB ID
- Made migration and recovery nearly impossible

**Impact**:
- Export/import required manual mapping files
- Dev→Prod migration very difficult
- Data recovery required extensive investigation

**Solution**:
- Changed to deterministic `kb_{uuid_without_dashes}` format
- Created migration script with Qdrant aliases
- Migrated all 19 existing KB successfully

**Lesson**: Always use deterministic, derivable identifiers for system components

### Issue 2: Container Restart Without --env-file

**Problem**:
- Running `docker-compose up -d <service>` recreates containers without environment variables
- Caused database authentication failures

**Impact**:
- Multiple service disruptions
- Confusion about why services suddenly failed

**Solution**:
- Created DEPLOY.md with proper procedures
- Always use: `docker-compose -f docker-compose.production.yml --env-file .env.production up -d`

**Lesson**: Document deployment procedures and enforce them

### Issue 3: Missing Application Logs

**Problem**:
- logging.basicConfig() not configured in main.py
- Only uvicorn HTTP logs visible
- Couldn't debug indexing issues

**Impact**:
- Difficult to troubleshoot Ollama connection failures
- No visibility into document processing errors

**Solution**:
- Added logging configuration to main.py
- Now see all app.* logger output

**Lesson**: Configure logging early in application startup

### Issue 4: OpenSearch Data Loss During Migration

**Problem**:
- Only 4 documents in OpenSearch after migration instead of 26,301
- Old documents indexed before system changes

**Impact**:
- BM25 search returned no results for most queries
- Hybrid search degraded to semantic-only

**Solution**:
- Restored from dev volume after verifying document_id compatibility
- Successfully recovered all 26,301 documents

**Lesson**: Verify data in ALL systems (PostgreSQL, Qdrant, OpenSearch) during migration

---

**Last Updated**: 2026-02-02
**Version**: 1.0
**Maintainer**: Knowledge Base Platform Team
