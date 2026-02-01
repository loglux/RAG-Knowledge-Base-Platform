#!/bin/bash
# Production Backup Script for Knowledge Base Platform
# Creates backups of all persistent data (database, vectors, documents)

set -e  # Exit on error

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="kb_backup_${TIMESTAMP}"
COMPOSE_FILE="docker-compose.production.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Knowledge Base Platform Backup ===${NC}"
echo "Timestamp: $(date)"
echo "Backup directory: ${BACKUP_DIR}"
echo ""

# Create backup directory
mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

# Check if containers are running
if ! docker-compose -f ${COMPOSE_FILE} ps | grep -q "Up"; then
    echo -e "${YELLOW}Warning: Some containers may not be running${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}[1/5] Backing up PostgreSQL database...${NC}"
docker-compose -f ${COMPOSE_FILE} exec -T db pg_dump \
    -U ${POSTGRES_USER:-kb_user} \
    -d ${POSTGRES_DB:-knowledge_base} \
    --clean --if-exists \
    > "${BACKUP_DIR}/${BACKUP_NAME}/postgres.sql"
echo "✓ Database backup completed ($(du -h "${BACKUP_DIR}/${BACKUP_NAME}/postgres.sql" | cut -f1))"

echo -e "${GREEN}[2/5] Backing up Qdrant vectors...${NC}"
docker run --rm \
    -v kb_qdrant_data_prod:/data:ro \
    -v "$(pwd)/${BACKUP_DIR}/${BACKUP_NAME}":/backup \
    alpine \
    tar czf /backup/qdrant_data.tar.gz -C /data .
echo "✓ Qdrant backup completed ($(du -h "${BACKUP_DIR}/${BACKUP_NAME}/qdrant_data.tar.gz" | cut -f1))"

echo -e "${GREEN}[3/5] Backing up OpenSearch data...${NC}"
docker run --rm \
    -v kb_opensearch_data_prod:/data:ro \
    -v "$(pwd)/${BACKUP_DIR}/${BACKUP_NAME}":/backup \
    alpine \
    tar czf /backup/opensearch_data.tar.gz -C /data .
echo "✓ OpenSearch backup completed ($(du -h "${BACKUP_DIR}/${BACKUP_NAME}/opensearch_data.tar.gz" | cut -f1))"

echo -e "${GREEN}[4/5] Backing up uploaded documents...${NC}"
docker run --rm \
    -v kb_uploads_prod:/data:ro \
    -v "$(pwd)/${BACKUP_DIR}/${BACKUP_NAME}":/backup \
    alpine \
    tar czf /backup/uploads.tar.gz -C /data .
echo "✓ Uploads backup completed ($(du -h "${BACKUP_DIR}/${BACKUP_NAME}/uploads.tar.gz" | cut -f1))"

echo -e "${GREEN}[5/5] Creating backup metadata...${NC}"
cat > "${BACKUP_DIR}/${BACKUP_NAME}/metadata.txt" <<EOF
Knowledge Base Platform Backup
================================
Timestamp: $(date)
Backup Name: ${BACKUP_NAME}
Platform: $(uname -a)

Contents:
- postgres.sql          PostgreSQL database dump
- qdrant_data.tar.gz    Qdrant vector storage
- opensearch_data.tar.gz OpenSearch lexical index
- uploads.tar.gz        Uploaded documents

Container Versions:
$(docker-compose -f ${COMPOSE_FILE} ps --format "table {{.Service}}\t{{.Image}}\t{{.Status}}")

Backup Size: $(du -sh "${BACKUP_DIR}/${BACKUP_NAME}" | cut -f1)
EOF
echo "✓ Metadata created"

# Create a compressed archive of the entire backup
echo -e "${GREEN}Creating compressed backup archive...${NC}"
cd "${BACKUP_DIR}"
tar czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
BACKUP_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)
rm -rf "${BACKUP_NAME}"

echo ""
echo -e "${GREEN}=== Backup Completed Successfully ===${NC}"
echo "Backup file: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo "Size: ${BACKUP_SIZE}"
echo ""
echo "To restore this backup, run:"
echo "  ./scripts/restore.sh ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo ""

# Optional: Remove old backups (keep last 7 days)
if [ "${KEEP_BACKUPS:-7}" -gt 0 ]; then
    echo "Cleaning up old backups (keeping last ${KEEP_BACKUPS:-7})..."
    cd "${BACKUP_DIR}"
    ls -t kb_backup_*.tar.gz 2>/dev/null | tail -n +$((${KEEP_BACKUPS:-7} + 1)) | xargs -r rm
    echo "✓ Cleanup completed"
fi
