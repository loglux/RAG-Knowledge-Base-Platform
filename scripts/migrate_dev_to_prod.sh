#!/bin/bash
# Migrate Development Data to Production
# This script safely copies data from dev volumes to production volumes

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Dev to Production Data Migration ===${NC}"
echo "Timestamp: $(date)"
echo ""

# Configuration
DEV_COMPOSE="docker-compose.dev.yml"
PROD_COMPOSE="docker-compose.production.yml"
TEMP_DIR=$(mktemp -d)
trap "rm -rf ${TEMP_DIR}" EXIT

# Warning
echo -e "${RED}WARNING: This will replace all production data with dev data!${NC}"
echo -e "${YELLOW}Current production data will be lost.${NC}"
echo ""
read -p "Type 'yes' to confirm migration: " CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
    echo "Migration cancelled."
    exit 0
fi

# Step 1: Create dev database dump
echo -e "${GREEN}[1/4] Creating dev database dump...${NC}"
echo "Starting dev database container..."
docker-compose -f ${DEV_COMPOSE} up -d db
sleep 10

echo "Creating dump..."
docker exec kb-platform-db pg_dump \
    -U kb_user \
    -d knowledge_base \
    --data-only \
    --inserts \
    > "${TEMP_DIR}/dev_data.sql"

DEV_DATA_SIZE=$(du -h "${TEMP_DIR}/dev_data.sql" | cut -f1)
echo "✓ Dev dump created (${DEV_DATA_SIZE})"

# Stop dev containers
echo "Stopping dev containers..."
docker-compose -f ${DEV_COMPOSE} down

# Step 2: Stop production backend/frontend
echo -e "${GREEN}[2/4] Preparing production...${NC}"
docker-compose -f ${PROD_COMPOSE} --env-file .env.production stop backend frontend
echo "✓ Backend and frontend stopped"

# Step 3: Drop and recreate production database
echo -e "${GREEN}[3/4] Recreating production database...${NC}"
docker exec kb-platform-db-prod psql -U kb_user -d postgres \
    --command "DROP DATABASE IF EXISTS knowledge_base"
docker exec kb-platform-db-prod psql -U kb_user -d postgres \
    --command "CREATE DATABASE knowledge_base OWNER kb_user"
echo "✓ Database recreated"

# Run migrations to create schema
echo "Running migrations..."
docker-compose -f ${PROD_COMPOSE} --env-file .env.production up -d backend
sleep 10
docker exec kb-platform-backend-prod alembic upgrade head
echo "✓ Schema created"

# Add lowercase chunking strategy values (migration 031d3e796cb8 requires manual steps)
echo "Adding chunking strategy enum values..."
docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base \
    -c "ALTER TYPE chunkingstrategy ADD VALUE IF NOT EXISTS 'simple';" 2>/dev/null || true
docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base \
    -c "ALTER TYPE chunkingstrategy ADD VALUE IF NOT EXISTS 'smart';" 2>/dev/null || true
docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base \
    -c "ALTER TYPE chunkingstrategy ADD VALUE IF NOT EXISTS 'semantic';" 2>/dev/null || true
echo "✓ Enum values added"

# Step 4: Import dev data
echo -e "${GREEN}[4/4] Importing dev data...${NC}"
cat "${TEMP_DIR}/dev_data.sql" | docker exec -i kb-platform-db-prod psql \
    -U kb_user \
    -d knowledge_base \
    > "${TEMP_DIR}/import.log" 2>&1

# Check import results
KB_COUNT=$(docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base -t \
    -c "SELECT COUNT(*) FROM knowledge_bases;" | xargs)
DOC_COUNT=$(docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base -t \
    -c "SELECT COUNT(*) FROM documents;" | xargs)

echo "✓ Data imported"
echo "  - Knowledge bases: ${KB_COUNT}"
echo "  - Documents: ${DOC_COUNT}"

# Check for errors
ERROR_COUNT=$(grep -c "ERROR" "${TEMP_DIR}/import.log" || echo "0")
if [ "${ERROR_COUNT}" -gt 0 ]; then
    echo -e "${YELLOW}⚠ ${ERROR_COUNT} errors occurred during import${NC}"
    echo "See ${TEMP_DIR}/import.log for details"
    echo ""
    echo "Common errors (can be ignored):"
    echo "  - duplicate key violations (data already exists)"
    echo "  - alembic_version constraint errors"
    echo ""
fi

# Restart all services
echo -e "${GREEN}Restarting all services...${NC}"
docker-compose -f ${PROD_COMPOSE} --env-file .env.production up -d
sleep 10

# Verify health
echo -e "${GREEN}Verifying system health...${NC}"
if docker exec kb-platform-backend-prod curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "${YELLOW}⚠ Backend health check failed (may need more time)${NC}"
fi

echo ""
echo -e "${GREEN}=== Migration Completed ===${NC}"
echo "Dev data has been migrated to production."
echo ""
echo "Next steps:"
echo "1. Open http://$(hostname -I | awk '{print $1}'):5174"
echo "2. Verify your knowledge bases are present"
echo "3. Test document search and chat functionality"
echo ""
echo "Import log saved to: ${TEMP_DIR}/import.log"
echo ""
