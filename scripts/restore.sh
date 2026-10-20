#!/usr/bin/env bash
# Restore script for Knowledge Base Platform.
#
# Mirrors scripts/backup.sh - no hardcoded volume/project names, uses
# `docker compose ps` to find the right container for --volumes-from.
#
# Usage:
#   ./scripts/restore.sh ./backups/kb_backup_20261020_120000.tar.gz
#
# For the rag-lab deployment, point it at the right compose file/project:
#   COMPOSE_ARGS="-p raglab -f docker-compose.rag-lab.yml" ./scripts/restore.sh <file>

set -euo pipefail

COMPOSE_ARGS="${COMPOSE_ARGS:-}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

compose() {
    # shellcheck disable=SC2086
    docker compose ${COMPOSE_ARGS} "$@"
}

container_id() {
    compose ps -a -q "$1"
}

if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No backup file specified${NC}"
    echo "Usage: $0 <backup-file.tar.gz>"
    echo ""
    echo "Available backups:"
    ls -lh ./backups/kb_backup_*.tar.gz 2>/dev/null || echo "  No backups found in ./backups/"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo -e "${RED}Error: Backup file not found: ${BACKUP_FILE}${NC}"
    exit 1
fi

echo -e "${GREEN}=== Knowledge Base Platform Restore ===${NC}"
echo "Backup file: ${BACKUP_FILE}"
echo "Timestamp: $(date)"
echo ""

echo -e "${RED}WARNING: This will replace all current data!${NC}"
echo -e "${YELLOW}Make sure you have a recent backup before proceeding.${NC}"
echo ""
read -p "Are you sure you want to continue? Type 'yes' to confirm: " CONFIRM

if [ "${CONFIRM}" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

TEMP_DIR=$(mktemp -d)
trap 'rm -rf "${TEMP_DIR}"' EXIT

echo -e "${GREEN}Extracting backup...${NC}"
tar xzf "${BACKUP_FILE}" -C "${TEMP_DIR}"
BACKUP_DIR=$(ls -d "${TEMP_DIR}"/kb_backup_*)

if [ -f "${BACKUP_DIR}/metadata.txt" ]; then
    echo ""
    cat "${BACKUP_DIR}/metadata.txt"
    echo ""
fi

echo -e "${YELLOW}Ensuring containers exist...${NC}"
compose up -d db qdrant opensearch
sleep 5

echo -e "${GREEN}Stopping api/frontend temporarily...${NC}"
compose stop api frontend 2>/dev/null || true

echo -e "${GREEN}[1/4] Restoring PostgreSQL database...${NC}"
compose exec -T db psql -U "${POSTGRES_USER:-kb_user}" -d postgres \
    -c "DROP DATABASE IF EXISTS ${POSTGRES_DB:-knowledge_base};"
compose exec -T db psql -U "${POSTGRES_USER:-kb_user}" -d postgres \
    -c "CREATE DATABASE ${POSTGRES_DB:-knowledge_base};"
compose exec -T db psql \
    -U "${POSTGRES_USER:-kb_user}" \
    -d "${POSTGRES_DB:-knowledge_base}" \
    <"${BACKUP_DIR}/postgres.sql"
echo "✓ Database restored"

echo -e "${GREEN}[2/4] Restoring Qdrant vectors...${NC}"
compose stop qdrant
QDRANT_CID=$(container_id qdrant)
docker run --rm \
    --volumes-from "${QDRANT_CID}" \
    -v "${BACKUP_DIR}:/backup:ro" \
    alpine \
    sh -c "rm -rf /qdrant/storage/* && tar xzf /backup/qdrant_data.tar.gz -C /qdrant/storage"
compose start qdrant
sleep 5
echo "✓ Qdrant vectors restored"

echo -e "${GREEN}[3/4] Restoring OpenSearch data...${NC}"
compose stop opensearch
OS_CID=$(container_id opensearch)
docker run --rm \
    --volumes-from "${OS_CID}" \
    -v "${BACKUP_DIR}:/backup:ro" \
    alpine \
    sh -c "rm -rf /usr/share/opensearch/data/* && tar xzf /backup/opensearch_data.tar.gz -C /usr/share/opensearch/data"
compose start opensearch
sleep 15
echo "✓ OpenSearch data restored"

echo -e "${GREEN}[4/4] Restoring uploaded documents...${NC}"
rm -rf ./uploads/*
tar xzf "${BACKUP_DIR}/uploads.tar.gz" -C ./uploads
echo "✓ Uploads restored"

if [ -f "${BACKUP_DIR}/secrets.tar.gz" ]; then
    echo -e "${YELLOW}Note: backup also contains secrets.tar.gz (db_password, secret_key).${NC}"
    echo -e "${YELLOW}Not auto-restored - current secrets/ are left in place. Extract manually only if you know you need the old SECRET_KEY (e.g. to keep existing JWT/MCP tokens valid).${NC}"
fi

echo -e "${GREEN}Restarting all services...${NC}"
compose up -d

echo "Waiting for services to become healthy..."
sleep 10

echo -e "${GREEN}Verifying system health...${NC}"
if compose exec -T api curl -sf http://localhost:8000/api/v1/health >/dev/null; then
    echo -e "${GREEN}✓ API is healthy${NC}"
else
    echo -e "${YELLOW}⚠ API health check failed (may need more time)${NC}"
fi

echo ""
echo -e "${GREEN}=== Restore Completed Successfully ===${NC}"
echo "All data has been restored from: ${BACKUP_FILE}"
echo ""
echo "Next steps:"
echo "1. Verify system health: curl http://localhost:8004/api/v1/health/ready"
echo "2. Check logs: docker compose ${COMPOSE_ARGS} logs -f"
echo "3. Test functionality through the UI"
echo ""
