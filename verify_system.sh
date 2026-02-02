#!/bin/bash
# verify_system.sh - Comprehensive system verification after migration
#
# This script verifies:
# 1. Collection name format (deterministic)
# 2. Data consistency across PostgreSQL, Qdrant, OpenSearch
# 3. Qdrant aliases functioning properly
# 4. API functionality
# 5. Self-check default setting

set -e

# Environment detection
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.production.yml}"
if [[ "$COMPOSE_FILE" == *"production"* ]]; then
    ENV="production"
    DB_CONTAINER="kb-platform-db-prod"
    QDRANT_CONTAINER="kb-platform-qdrant-prod"
    OPENSEARCH_CONTAINER="kb-platform-opensearch-prod"
    BACKEND_CONTAINER="kb-platform-backend-prod"
else
    ENV="development"
    DB_CONTAINER="kb-platform-db"
    QDRANT_CONTAINER="kb-platform-qdrant"
    OPENSEARCH_CONTAINER="kb-platform-opensearch"
    BACKEND_CONTAINER="kb-platform-api"
fi

API_BASE="http://localhost:8004/api/v1"
QDRANT_URL="http://qdrant:6333"  # Internal network URL
OPENSEARCH_URL="http://opensearch:9200"  # Internal network URL

echo "========================================"
echo "SYSTEM VERIFICATION"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
    echo -e "${GREEN}✓${NC} $1"
}

fail() {
    echo -e "${RED}✗${NC} $1"
    FAILED=1
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

FAILED=0

# ========================================
# 1. DATABASE CONNECTIVITY
# ========================================
echo "1. Checking database connectivity..."

# PostgreSQL
if docker exec $DB_CONTAINER pg_isready -U kb_user -d knowledge_base > /dev/null 2>&1; then
    pass "PostgreSQL is ready"
else
    fail "PostgreSQL is not responding"
fi

# Qdrant (access via backend container's network)
QDRANT_STATUS=$(docker exec $BACKEND_CONTAINER curl -s "$QDRANT_URL/collections" | jq -r '.status // "error"')
if [ "$QDRANT_STATUS" = "ok" ]; then
    pass "Qdrant is healthy"
else
    fail "Qdrant is not responding"
fi

# OpenSearch (access via backend container's network)
if docker exec $BACKEND_CONTAINER curl -s -f "$OPENSEARCH_URL/_cluster/health" > /dev/null 2>&1; then
    pass "OpenSearch is healthy"
else
    fail "OpenSearch is not responding"
fi

echo ""

# ========================================
# 2. COLLECTION NAME FORMAT
# ========================================
echo "2. Verifying collection name format..."

# Get all KB from PostgreSQL
KB_DATA=$(docker exec $DB_CONTAINER psql -U kb_user -d knowledge_base -t -c \
    "SELECT id, collection_name FROM knowledge_bases WHERE is_deleted=false;")

TOTAL_KB=0
CORRECT_FORMAT=0
WRONG_FORMAT=0

while IFS='|' read -r kb_id collection_name; do
    # Trim whitespace
    kb_id=$(echo "$kb_id" | xargs)
    collection_name=$(echo "$collection_name" | xargs)

    if [ -z "$kb_id" ]; then
        continue
    fi

    TOTAL_KB=$((TOTAL_KB + 1))

    # Calculate expected collection name
    expected="kb_$(echo "$kb_id" | tr -d '-')"

    if [ "$collection_name" = "$expected" ]; then
        CORRECT_FORMAT=$((CORRECT_FORMAT + 1))
    else
        WRONG_FORMAT=$((WRONG_FORMAT + 1))
        warn "KB $kb_id has wrong format: $collection_name (expected: $expected)"
    fi
done <<< "$KB_DATA"

if [ $WRONG_FORMAT -eq 0 ]; then
    pass "All $TOTAL_KB KB have correct collection_name format"
else
    fail "$WRONG_FORMAT/$TOTAL_KB KB have incorrect collection_name format"
fi

echo ""

# ========================================
# 3. DATA CONSISTENCY
# ========================================
echo "3. Checking data consistency..."

# Count in PostgreSQL
PG_KB_COUNT=$(docker exec $DB_CONTAINER psql -U kb_user -d knowledge_base -t -c \
    "SELECT COUNT(*) FROM knowledge_bases WHERE is_deleted=false;" | xargs)

PG_DOC_COUNT=$(docker exec $DB_CONTAINER psql -U kb_user -d knowledge_base -t -c \
    "SELECT COUNT(*) FROM documents WHERE is_deleted=false;" | xargs)

# Count Qdrant collections
QDRANT_COLLECTIONS=$(docker exec $BACKEND_CONTAINER curl -s "$QDRANT_URL/collections" | jq -r '.result.collections[].name' | wc -l)

# Count OpenSearch documents
OS_DOC_COUNT=$(docker exec $BACKEND_CONTAINER curl -s "$OPENSEARCH_URL/kb_chunks/_count" | jq .count)

echo "  PostgreSQL:"
echo "    - Knowledge Bases: $PG_KB_COUNT"
echo "    - Documents: $PG_DOC_COUNT"
echo "  Qdrant:"
echo "    - Collections: $QDRANT_COLLECTIONS"
echo "  OpenSearch:"
echo "    - Chunks: $OS_DOC_COUNT"

# Verify KB count matches Qdrant collections (excluding system collections)
# Note: Qdrant may have more collections due to aliases and old collections
if [ "$PG_KB_COUNT" -le "$QDRANT_COLLECTIONS" ]; then
    pass "KB count ($PG_KB_COUNT) ≤ Qdrant collections ($QDRANT_COLLECTIONS)"
else
    warn "KB count ($PG_KB_COUNT) > Qdrant collections ($QDRANT_COLLECTIONS) - some collections may be missing"
fi

# Check OpenSearch has reasonable document count
if [ "$OS_DOC_COUNT" -gt 1000 ]; then
    pass "OpenSearch has $OS_DOC_COUNT chunks (healthy)"
elif [ "$OS_DOC_COUNT" -gt 0 ]; then
    warn "OpenSearch has only $OS_DOC_COUNT chunks (may be incomplete)"
else
    fail "OpenSearch has no documents"
fi

echo ""

# ========================================
# 4. QDRANT ALIASES
# ========================================
echo "4. Checking Qdrant aliases..."

ALIAS_COUNT=0
WORKING_ALIASES=0
BROKEN_ALIASES=0

# Get sample KB to test
SAMPLE_KB=$(docker exec $DB_CONTAINER psql -U kb_user -d knowledge_base -t -c \
    "SELECT id, collection_name FROM knowledge_bases WHERE is_deleted=false LIMIT 1;")

if [ -n "$SAMPLE_KB" ]; then
    kb_id=$(echo "$SAMPLE_KB" | cut -d'|' -f1 | xargs)
    collection_name=$(echo "$SAMPLE_KB" | cut -d'|' -f2 | xargs)

    # Try to access collection via alias/name
    RESPONSE=$(docker exec $BACKEND_CONTAINER curl -s "$QDRANT_URL/collections/$collection_name")

    if echo "$RESPONSE" | jq -e '.result' > /dev/null 2>&1; then
        pass "Collection '$collection_name' is accessible"
        WORKING_ALIASES=$((WORKING_ALIASES + 1))
    else
        fail "Collection '$collection_name' is not accessible"
        BROKEN_ALIASES=$((BROKEN_ALIASES + 1))
    fi
else
    warn "No KB found to test Qdrant aliases"
fi

echo ""

# ========================================
# 5. API FUNCTIONALITY
# ========================================
echo "5. Testing API functionality..."

# Health check
HEALTH=$(curl -s -f "$API_BASE/health/" 2>/dev/null || echo "failed")
if [ "$HEALTH" != "failed" ]; then
    pass "API health check passed"
else
    fail "API health check failed"
fi

# List KB
KB_LIST=$(curl -s -f "$API_BASE/knowledge-bases/?page=1&page_size=10" 2>/dev/null || echo "failed")
if [ "$KB_LIST" != "failed" ]; then
    API_KB_COUNT=$(echo "$KB_LIST" | jq -r '.total // 0')
    if [ "$API_KB_COUNT" -eq "$PG_KB_COUNT" ]; then
        pass "API returns correct KB count ($API_KB_COUNT)"
    else
        warn "API KB count ($API_KB_COUNT) differs from PostgreSQL ($PG_KB_COUNT)"
    fi
else
    fail "API knowledge-bases endpoint failed"
fi

echo ""

# ========================================
# 6. SELF-CHECK DEFAULT SETTING
# ========================================
echo "6. Verifying self-check default setting..."

# Check API schema documentation
API_SCHEMA=$(curl -s "$API_BASE/../openapi.json" 2>/dev/null || echo "failed")
if [ "$API_SCHEMA" != "failed" ]; then
    # Extract default value for use_self_check from ChatRequest schema
    SELF_CHECK_DEFAULT=$(echo "$API_SCHEMA" | jq -r '.components.schemas.ChatRequest.properties.use_self_check.default // "not_found"')

    if [ "$SELF_CHECK_DEFAULT" = "false" ]; then
        pass "Self-check default is disabled (false)"
    elif [ "$SELF_CHECK_DEFAULT" = "true" ]; then
        fail "Self-check default is enabled (true) - should be false"
    else
        warn "Could not verify self-check default setting"
    fi
else
    warn "Could not fetch API schema to verify self-check setting"
fi

echo ""

# ========================================
# 7. APPLICATION LOGS
# ========================================
echo "7. Checking application logs..."

# Get last 20 lines of API logs
RECENT_LOGS=$(docker-compose -f $COMPOSE_FILE logs --tail=20 backend 2>&1)

# Check for app.* logger output (not just uvicorn)
if echo "$RECENT_LOGS" | grep -q "app\\."; then
    pass "Application logging is working (found app.* logs)"
else
    warn "No app.* logs found in recent output (may need activity to generate logs)"
fi

# Check for errors
ERROR_COUNT=$(echo "$RECENT_LOGS" | grep -i "error" | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    pass "No errors in recent logs"
else
    warn "Found $ERROR_COUNT error messages in recent logs"
fi

echo ""

# ========================================
# 8. ORPHANED DATA CHECK
# ========================================
echo "8. Checking for orphaned data..."

# Get all Qdrant collections
QDRANT_COLLECTION_LIST=$(docker exec $BACKEND_CONTAINER curl -s "$QDRANT_URL/collections" | jq -r '.result.collections[].name')

# Get all collection_names from PostgreSQL
PG_COLLECTION_LIST=$(docker exec $DB_CONTAINER psql -U kb_user -d knowledge_base -t -c \
    "SELECT collection_name FROM knowledge_bases WHERE is_deleted=false;")

ORPHANED_COLLECTIONS=0

for qdrant_col in $QDRANT_COLLECTION_LIST; do
    # Check if this collection is referenced in PostgreSQL
    if ! echo "$PG_COLLECTION_LIST" | grep -q "$qdrant_col"; then
        # Check if it's an alias by trying to get collection info
        COL_INFO=$(docker exec $BACKEND_CONTAINER curl -s "$QDRANT_URL/collections/$qdrant_col")
        IS_ALIAS=$(echo "$COL_INFO" | jq -r '.result.config // "null"')

        if [ "$IS_ALIAS" = "null" ]; then
            # This might be an orphaned collection
            warn "Potentially orphaned collection: $qdrant_col (not in PostgreSQL)"
            ORPHANED_COLLECTIONS=$((ORPHANED_COLLECTIONS + 1))
        fi
    fi
done

if [ $ORPHANED_COLLECTIONS -eq 0 ]; then
    pass "No orphaned Qdrant collections found"
else
    warn "Found $ORPHANED_COLLECTIONS potentially orphaned Qdrant collections"
fi

echo ""

# ========================================
# SUMMARY
# ========================================
echo "========================================"
echo "VERIFICATION SUMMARY"
echo "========================================"
echo ""
echo "System Statistics:"
echo "  - Knowledge Bases: $PG_KB_COUNT"
echo "  - Documents: $PG_DOC_COUNT"
echo "  - Qdrant Collections: $QDRANT_COLLECTIONS"
echo "  - OpenSearch Chunks: $OS_DOC_COUNT"
echo ""
echo "Collection Name Format:"
echo "  - Correct: $CORRECT_FORMAT/$TOTAL_KB"
echo "  - Wrong: $WRONG_FORMAT/$TOTAL_KB"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All verification checks passed!${NC}"
    echo ""
    echo "System is ready for production use."
    exit 0
else
    echo -e "${RED}✗ Some verification checks failed${NC}"
    echo ""
    echo "Please review the warnings and errors above."
    exit 1
fi
