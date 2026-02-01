#!/bin/bash
# Production Restore Script for Knowledge Base Platform
# Restores all persistent data from a backup

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.production.yml"

# Check arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No backup file specified${NC}"
    echo "Usage: $0 <backup-file.tar.gz>"
    echo ""
    echo "Available backups:"
    ls -lh ./backups/kb_backup_*.tar.gz 2>/dev/null || echo "  No backups found in ./backups/"
    exit 1
fi

BACKUP_FILE="$1"

# Validate backup file
if [ ! -f "${BACKUP_FILE}" ]; then
    echo -e "${RED}Error: Backup file not found: ${BACKUP_FILE}${NC}"
    exit 1
fi

echo -e "${GREEN}=== Knowledge Base Platform Restore ===${NC}"
echo "Backup file: ${BACKUP_FILE}"
echo "Timestamp: $(date)"
echo ""

# Warning
echo -e "${RED}WARNING: This will replace all current data!${NC}"
echo -e "${YELLOW}Make sure you have a recent backup before proceeding.${NC}"
echo ""
read -p "Are you sure you want to continue? Type 'yes' to confirm: " CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

# Extract backup
TEMP_DIR=$(mktemp -d)
trap "rm -rf ${TEMP_DIR}" EXIT

echo -e "${GREEN}Extracting backup...${NC}"
tar xzf "${BACKUP_FILE}" -C "${TEMP_DIR}"
BACKUP_DIR=$(ls -d ${TEMP_DIR}/kb_backup_*)

# Display backup metadata
if [ -f "${BACKUP_DIR}/metadata.txt" ]; then
    echo ""
    cat "${BACKUP_DIR}/metadata.txt"
    echo ""
fi

# Check if containers are running
echo -e "${YELLOW}Checking container status...${NC}"
if docker-compose -f ${COMPOSE_FILE} ps | grep -q "Up"; then
    echo -e "${YELLOW}Containers are running. They will be restarted after restore.${NC}"
    RESTART_CONTAINERS=true
else
    echo "Containers are not running. Starting them for restore..."
    docker-compose -f ${COMPOSE_FILE} up -d
    sleep 10  # Wait for containers to be ready
    RESTART_CONTAINERS=false
fi

# Stop backend to prevent writes during restore
echo -e "${GREEN}Stopping backend temporarily...${NC}"
docker-compose -f ${COMPOSE_FILE} stop backend frontend

echo -e "${GREEN}[1/4] Restoring PostgreSQL database...${NC}"
# Drop and recreate database
docker-compose -f ${COMPOSE_FILE} exec -T db psql -U ${POSTGRES_USER:-kb_user} -d postgres -c "DROP DATABASE IF EXISTS ${POSTGRES_DB:-knowledge_base};"
docker-compose -f ${COMPOSE_FILE} exec -T db psql -U ${POSTGRES_USER:-kb_user} -d postgres -c "CREATE DATABASE ${POSTGRES_DB:-knowledge_base};"

# Restore database
cat "${BACKUP_DIR}/postgres.sql" | docker-compose -f ${COMPOSE_FILE} exec -T db psql \
    -U ${POSTGRES_USER:-kb_user} \
    -d ${POSTGRES_DB:-knowledge_base}
echo "✓ Database restored"

echo -e "${GREEN}[2/4] Restoring Qdrant vectors...${NC}"
# Stop Qdrant, restore data, restart
docker-compose -f ${COMPOSE_FILE} stop qdrant
docker run --rm \
    -v kb_qdrant_data_prod:/data \
    -v "${BACKUP_DIR}":/backup:ro \
    alpine \
    sh -c "rm -rf /data/* && tar xzf /backup/qdrant_data.tar.gz -C /data"
docker-compose -f ${COMPOSE_FILE} start qdrant
sleep 5  # Wait for Qdrant to start
echo "✓ Qdrant vectors restored"

echo -e "${GREEN}[3/4] Restoring OpenSearch data...${NC}"
# Stop OpenSearch, restore data, restart
docker-compose -f ${COMPOSE_FILE} stop opensearch
docker run --rm \
    -v kb_opensearch_data_prod:/data \
    -v "${BACKUP_DIR}":/backup:ro \
    alpine \
    sh -c "rm -rf /data/* && tar xzf /backup/opensearch_data.tar.gz -C /data"
docker-compose -f ${COMPOSE_FILE} start opensearch
sleep 15  # Wait for OpenSearch to start (takes longer)
echo "✓ OpenSearch data restored"

echo -e "${GREEN}[4/4] Restoring uploaded documents...${NC}"
docker run --rm \
    -v kb_uploads_prod:/data \
    -v "${BACKUP_DIR}":/backup:ro \
    alpine \
    sh -c "rm -rf /data/* && tar xzf /backup/uploads.tar.gz -C /data"
echo "✓ Uploads restored"

# Restart all services
echo -e "${GREEN}Restarting all services...${NC}"
if [ "${RESTART_CONTAINERS}" = "true" ]; then
    docker-compose -f ${COMPOSE_FILE} restart
else
    docker-compose -f ${COMPOSE_FILE} start backend frontend
fi

# Wait for health checks
echo "Waiting for services to become healthy..."
sleep 10

# Verify health
echo -e "${GREEN}Verifying system health...${NC}"
if docker-compose -f ${COMPOSE_FILE} exec -T backend curl -sf http://localhost:8000/api/v1/health > /dev/null; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "${YELLOW}⚠ Backend health check failed (may need more time)${NC}"
fi

echo ""
echo -e "${GREEN}=== Restore Completed Successfully ===${NC}"
echo "All data has been restored from: ${BACKUP_FILE}"
echo ""
echo "Next steps:"
echo "1. Verify system health: curl http://localhost:8004/api/v1/health/ready"
echo "2. Check logs: docker-compose -f ${COMPOSE_FILE} logs -f"
echo "3. Test functionality through the UI"
echo ""
