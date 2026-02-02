#!/bin/bash
# Fix Enum Case Mismatch
# Adds lowercase enum values if they're missing (for backward compatibility)

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Enum Case Compatibility Fix ===${NC}"
echo ""

# Check if container is running
if ! docker ps | grep -q kb-platform-db-prod; then
    echo "Error: Production database container is not running"
    echo "Start it with: docker-compose -f docker-compose.production.yml up -d db"
    exit 1
fi

echo "Checking and adding missing enum values..."
echo ""

# ChunkingStrategy enum
echo "ChunkingStrategy enum:"
docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base \
    -c "SELECT unnest(enum_range(NULL::chunkingstrategy))::text;" -t | sort

echo ""
echo "Adding lowercase values if missing..."
docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base \
    -c "ALTER TYPE chunkingstrategy ADD VALUE IF NOT EXISTS 'simple';" 2>/dev/null || true
docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base \
    -c "ALTER TYPE chunkingstrategy ADD VALUE IF NOT EXISTS 'smart';" 2>/dev/null || true
docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base \
    -c "ALTER TYPE chunkingstrategy ADD VALUE IF NOT EXISTS 'semantic';" 2>/dev/null || true

echo -e "${GREEN}✓ ChunkingStrategy updated${NC}"
echo ""

# DocumentStatus enum (should be lowercase from migrations)
echo "DocumentStatus enum:"
docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base \
    -c "SELECT unnest(enum_range(NULL::documentstatus))::text;" -t | sort

if docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base -t \
    -c "SELECT 'PENDING'::documentstatus;" 2>/dev/null | grep -q "PENDING"; then
    echo -e "${YELLOW}⚠ DocumentStatus enum has UPPERCASE values${NC}"
    echo "This is incorrect! The migrations should create lowercase values."
    echo "Run: ./scripts/migrate_dev_to_prod.sh to rebuild with correct schema"
else
    echo -e "${GREEN}✓ DocumentStatus is correct (lowercase)${NC}"
fi
echo ""

# FileType enum (should be lowercase from migrations)
echo "FileType enum:"
docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base \
    -c "SELECT unnest(enum_range(NULL::filetype))::text;" -t | sort

if docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base -t \
    -c "SELECT 'TXT'::filetype;" 2>/dev/null | grep -q "TXT"; then
    echo -e "${YELLOW}⚠ FileType enum has UPPERCASE values${NC}"
    echo "This is incorrect! The migrations should create lowercase values."
    echo "Run: ./scripts/migrate_dev_to_prod.sh to rebuild with correct schema"
else
    echo -e "${GREEN}✓ FileType is correct (lowercase)${NC}"
fi
echo ""

echo -e "${GREEN}=== Check Complete ===${NC}"
echo ""
echo "Expected enum values (from app/models/enums.py):"
echo "  - documentstatus: pending, processing, completed, failed"
echo "  - filetype: txt, md"
echo "  - chunkingstrategy: simple, smart, semantic, FIXED_SIZE, PARAGRAPH"
echo ""
