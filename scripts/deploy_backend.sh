#!/bin/bash
# deploy_backend.sh - Safe backend deployment script
#
# This script ensures proper rebuild and restart of backend container
# avoiding Docker cache issues that can prevent code updates
#
# Usage:
#   ./scripts/deploy_backend.sh [--quick]
#
# Options:
#   --quick    Skip --no-cache (faster but may use cached layers)

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.production.yml"
ENV_FILE=".env.production"
CONTAINER_NAME="kb-platform-backend-prod"
SERVICE_NAME="backend"

# Parse arguments
USE_CACHE=false
if [ "$1" = "--quick" ]; then
    USE_CACHE=true
    echo -e "${YELLOW}⚠️  Quick mode: using cache (may not pick up all changes)${NC}"
fi

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}BACKEND DEPLOYMENT${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Step 1: Verify files exist
echo -e "${BLUE}📋 Step 1/6: Verifying configuration files...${NC}"
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}✗ Error: $COMPOSE_FILE not found${NC}"
    exit 1
fi
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}✗ Error: $ENV_FILE not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Configuration files found${NC}"
echo ""

# Step 2: Build backend image
echo -e "${BLUE}🔨 Step 2/6: Building backend image...${NC}"
if [ "$USE_CACHE" = true ]; then
    docker-compose -f "$COMPOSE_FILE" build "$SERVICE_NAME"
else
    echo -e "${YELLOW}Building without cache (this may take 2-3 minutes)${NC}"
    docker-compose -f "$COMPOSE_FILE" build --no-cache "$SERVICE_NAME"
fi

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Build completed${NC}"
echo ""

# Step 3: Stop old backend
echo -e "${BLUE}🛑 Step 3/6: Stopping old backend...${NC}"
docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop "$SERVICE_NAME"
echo -e "${GREEN}✓ Backend stopped${NC}"
echo ""

# Step 4: Start new backend
echo -e "${BLUE}🚀 Step 4/6: Starting new backend...${NC}"
docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d "$SERVICE_NAME"
echo -e "${GREEN}✓ Backend started${NC}"
echo ""

# Step 5: Wait for health check
echo -e "${BLUE}⏳ Step 5/6: Waiting for health check...${NC}"
HEALTHY=false
for i in {1..30}; do
    sleep 2
    STATUS=$(docker inspect "$CONTAINER_NAME" --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")

    if [ "$STATUS" = "healthy" ]; then
        echo -e "${GREEN}✓ Backend is healthy! (${i} attempts)${NC}"
        HEALTHY=true
        break
    elif [ "$STATUS" = "unhealthy" ]; then
        echo -e "${RED}✗ Backend is unhealthy${NC}"
        echo ""
        echo -e "${YELLOW}Recent logs:${NC}"
        docker logs "$CONTAINER_NAME" --tail 20
        exit 1
    else
        echo "  [$i/30] Status: $STATUS"
    fi
done

if [ "$HEALTHY" = false ]; then
    echo -e "${RED}✗ Timeout: Backend did not become healthy${NC}"
    echo ""
    echo -e "${YELLOW}Recent logs:${NC}"
    docker logs "$CONTAINER_NAME" --tail 30
    exit 1
fi
echo ""

# Step 6: Verify code changes
echo -e "${BLUE}🔍 Step 6/6: Verifying code changes...${NC}"

# Check that the new code is in the container
# This verifies the most recent change (alias checking in vector_store.py)
ALIAS_CHECK=$(docker exec "$CONTAINER_NAME" grep -c "Check aliases" /app/app/core/vector_store.py 2>/dev/null || echo "0")
if [ "$ALIAS_CHECK" -gt 0 ]; then
    echo -e "${GREEN}✓ Latest code changes verified in container${NC}"
else
    echo -e "${YELLOW}⚠️  Could not verify latest changes (may be okay for older deployments)${NC}"
fi

# Check Python version
PY_VERSION=$(docker exec "$CONTAINER_NAME" python --version 2>&1)
echo -e "  Python: ${PY_VERSION}"

# Check main imports work
IMPORT_CHECK=$(docker exec "$CONTAINER_NAME" python -c "from app.main import app; print('OK')" 2>&1)
if echo "$IMPORT_CHECK" | grep -q "OK"; then
    echo -e "${GREEN}✓ Backend imports working${NC}"
else
    echo -e "${YELLOW}⚠️  Import check failed: $IMPORT_CHECK${NC}"
fi

echo ""

# Final summary
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✅ DEPLOYMENT SUCCESSFUL${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Backend status:"
docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "  View logs:    docker logs $CONTAINER_NAME --tail 50 -f"
echo "  Check health: curl -s http://localhost:8004/api/v1/health | jq"
echo "  Restart:      docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE restart $SERVICE_NAME"
echo ""
echo -e "${GREEN}🎉 Backend is ready!${NC}"
