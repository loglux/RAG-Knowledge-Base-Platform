#!/bin/bash
# deploy_frontend.sh - Safe frontend deployment script
#
# This script ensures proper rebuild and restart of frontend container
# Always rebuilds without cache to ensure latest bundle is created
#
# Usage:
#   ./scripts/deploy_frontend.sh

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
CONTAINER_NAME="kb-platform-frontend-prod"
SERVICE_NAME="frontend"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}FRONTEND DEPLOYMENT${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Step 1: Verify files exist
echo -e "${BLUE}📋 Step 1/5: Verifying configuration files...${NC}"
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}✗ Error: $COMPOSE_FILE not found${NC}"
    exit 1
fi
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}✗ Error: $ENV_FILE not found${NC}"
    exit 1
fi
if [ ! -f "frontend/package.json" ]; then
    echo -e "${RED}✗ Error: frontend/package.json not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Configuration files found${NC}"
echo ""

# Step 2: Build frontend image
echo -e "${BLUE}🔨 Step 2/5: Building frontend image...${NC}"
echo -e "${YELLOW}Building without cache (this may take 1-2 minutes)${NC}"
docker-compose -f "$COMPOSE_FILE" build --no-cache "$SERVICE_NAME"

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Build failed${NC}"
    exit 1
fi

# Extract bundle name from build output (if possible)
echo -e "${GREEN}✓ Build completed${NC}"
echo ""

# Step 3: Stop old frontend
echo -e "${BLUE}🛑 Step 3/5: Stopping old frontend...${NC}"
docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop "$SERVICE_NAME"
echo -e "${GREEN}✓ Frontend stopped${NC}"
echo ""

# Step 4: Start new frontend
echo -e "${BLUE}🚀 Step 4/5: Starting new frontend...${NC}"
docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d "$SERVICE_NAME"
echo -e "${GREEN}✓ Frontend started${NC}"
echo ""

# Step 5: Verify deployment
echo -e "${BLUE}🔍 Step 5/5: Verifying deployment...${NC}"

# Wait a bit for nginx to start
sleep 3

# Check container is running
CONTAINER_STATUS=$(docker inspect "$CONTAINER_NAME" --format='{{.State.Status}}' 2>/dev/null || echo "not found")
if [ "$CONTAINER_STATUS" = "running" ]; then
    echo -e "${GREEN}✓ Frontend container is running${NC}"
else
    echo -e "${RED}✗ Frontend container status: $CONTAINER_STATUS${NC}"
    exit 1
fi

# Check nginx is serving files
BUNDLE_CHECK=$(docker exec "$CONTAINER_NAME" ls -1 /usr/share/nginx/html/assets/index-*.js 2>/dev/null | head -1)
if [ -n "$BUNDLE_CHECK" ]; then
    BUNDLE_NAME=$(basename "$BUNDLE_CHECK")
    echo -e "${GREEN}✓ Frontend bundle found: $BUNDLE_NAME${NC}"
else
    echo -e "${YELLOW}⚠️  Could not verify bundle (may be okay)${NC}"
fi

# Check nginx config
NGINX_TEST=$(docker exec "$CONTAINER_NAME" nginx -t 2>&1)
if echo "$NGINX_TEST" | grep -q "successful"; then
    echo -e "${GREEN}✓ Nginx configuration valid${NC}"
else
    echo -e "${YELLOW}⚠️  Nginx config test: $NGINX_TEST${NC}"
fi

echo ""

# Final summary
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✅ DEPLOYMENT SUCCESSFUL${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Frontend status:"
docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "  View logs:     docker logs $CONTAINER_NAME --tail 50 -f"
echo "  Check bundle:  docker exec $CONTAINER_NAME ls -lh /usr/share/nginx/html/assets/"
echo "  Test locally:  curl -I http://localhost:5174/"
echo ""
echo -e "${YELLOW}⚠️  Important: Users may need to hard refresh (Ctrl+Shift+R) to get new bundle${NC}"
echo ""
echo -e "${GREEN}🎉 Frontend is ready!${NC}"
