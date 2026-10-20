#!/usr/bin/env bash
# Backup script for Knowledge Base Platform.
#
# Works for any of the 3 deployments (local kb-platform, remote kb-platform,
# remote rag-lab) - it never guesses Docker volume names or project names.
# Instead it finds the actual running/stopped container for each service via
# `docker compose ps` and reads its mounted volume directly with
# `--volumes-from`, so it's immune to project-name / volume-name drift.
#
# Usage (run from the project directory you want to back up):
#   ./scripts/backup.sh
#
# For the rag-lab deployment, point it at the right compose file/project:
#   COMPOSE_ARGS="-p raglab -f docker-compose.rag-lab.yml" ./scripts/backup.sh

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
COMPOSE_ARGS="${COMPOSE_ARGS:-}"
KEEP_BACKUPS="${KEEP_BACKUPS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="kb_backup_${TIMESTAMP}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

compose() {
    # shellcheck disable=SC2086
    docker compose ${COMPOSE_ARGS} "$@"
}

container_id() {
    # Service container id, running or stopped; empty if the service was
    # never created (e.g. url2md, which is an optional profile).
    compose ps -a -q "$1"
}

echo -e "${GREEN}=== Knowledge Base Platform Backup ===${NC}"
echo "Timestamp: $(date)"
echo "Backup directory: ${BACKUP_DIR}"
echo ""

mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

echo -e "${GREEN}[1/5] Backing up PostgreSQL database...${NC}"
compose exec -T db pg_dump \
    -U "${POSTGRES_USER:-kb_user}" \
    -d "${POSTGRES_DB:-knowledge_base}" \
    --clean --if-exists \
    >"${BACKUP_DIR}/${BACKUP_NAME}/postgres.sql"
echo "✓ Database backup completed ($(du -h "${BACKUP_DIR}/${BACKUP_NAME}/postgres.sql" | cut -f1))"

echo -e "${GREEN}[2/5] Backing up Qdrant vectors...${NC}"
QDRANT_CID=$(container_id qdrant)
if [ -z "${QDRANT_CID}" ]; then
    echo -e "${RED}Error: qdrant container not found (is it created? try: docker compose up -d)${NC}"
    exit 1
fi
docker run --rm \
    --volumes-from "${QDRANT_CID}" \
    -v "$(pwd)/${BACKUP_DIR}/${BACKUP_NAME}:/backup" \
    alpine \
    tar czf /backup/qdrant_data.tar.gz -C /qdrant/storage .
echo "✓ Qdrant backup completed ($(du -h "${BACKUP_DIR}/${BACKUP_NAME}/qdrant_data.tar.gz" | cut -f1))"

echo -e "${GREEN}[3/5] Backing up OpenSearch data...${NC}"
OS_CID=$(container_id opensearch)
if [ -z "${OS_CID}" ]; then
    echo -e "${RED}Error: opensearch container not found (is it created? try: docker compose up -d)${NC}"
    exit 1
fi
docker run --rm \
    --volumes-from "${OS_CID}" \
    -v "$(pwd)/${BACKUP_DIR}/${BACKUP_NAME}:/backup" \
    alpine \
    tar czf /backup/opensearch_data.tar.gz -C /usr/share/opensearch/data .
echo "✓ OpenSearch backup completed ($(du -h "${BACKUP_DIR}/${BACKUP_NAME}/opensearch_data.tar.gz" | cut -f1))"

echo -e "${GREEN}[4/5] Backing up uploaded documents and secrets...${NC}"
# ./uploads and ./secrets are host bind mounts (not Docker volumes), so tar
# them directly - no container needed.
tar czf "${BACKUP_DIR}/${BACKUP_NAME}/uploads.tar.gz" -C ./uploads .
tar czf "${BACKUP_DIR}/${BACKUP_NAME}/secrets.tar.gz" -C ./secrets .
echo "✓ Uploads + secrets backup completed"
echo -e "${YELLOW}  Note: secrets.tar.gz contains db_password and secret_key - treat the whole archive as sensitive.${NC}"

echo -e "${GREEN}[5/5] Creating backup metadata...${NC}"
cat >"${BACKUP_DIR}/${BACKUP_NAME}/metadata.txt" <<EOF
Knowledge Base Platform Backup
================================
Timestamp: $(date)
Backup Name: ${BACKUP_NAME}
Platform: $(uname -a)
Compose args: ${COMPOSE_ARGS:-<default>}

Contents:
- postgres.sql           PostgreSQL database dump
- qdrant_data.tar.gz      Qdrant vector storage
- opensearch_data.tar.gz  OpenSearch lexical index
- uploads.tar.gz          Uploaded documents
- secrets.tar.gz          db_password + secret_key (SENSITIVE)

Container versions:
$(compose ps --format "table {{.Service}}\t{{.Image}}\t{{.Status}}")

Backup size: $(du -sh "${BACKUP_DIR}/${BACKUP_NAME}" | cut -f1)
EOF
echo "✓ Metadata created"

echo -e "${GREEN}Creating compressed backup archive...${NC}"
(
    cd "${BACKUP_DIR}"
    tar czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
    rm -rf "${BACKUP_NAME}"
)
BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)

echo ""
echo -e "${GREEN}=== Backup Completed Successfully ===${NC}"
echo "Backup file: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo "Size: ${BACKUP_SIZE}"
echo ""
echo "To restore this backup, run:"
echo "  ./scripts/restore.sh ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo ""

if [ "${KEEP_BACKUPS}" -gt 0 ]; then
    echo "Cleaning up old backups (keeping last ${KEEP_BACKUPS})..."
    (
        cd "${BACKUP_DIR}"
        ls -t kb_backup_*.tar.gz 2>/dev/null | tail -n +$((KEEP_BACKUPS + 1)) | xargs -r rm
    )
    echo "✓ Cleanup completed"
fi
