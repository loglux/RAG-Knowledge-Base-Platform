# Utility Scripts

Collection of utility scripts for managing the Knowledge Base Platform.

## 🔄 Data Management

### backup.sh
Creates a complete backup of all production data (database, vectors, documents, indexes).

```bash
./scripts/backup.sh
```

**Features:**
- Backs up PostgreSQL database
- Backs up Qdrant vector storage
- Backs up OpenSearch lexical index
- Backs up uploaded documents
- Creates compressed archive with metadata
- Automatically cleans up old backups (keeps last 7 by default)

**Environment Variables:**
- `BACKUP_DIR` - Backup directory (default: `./backups`)
- `KEEP_BACKUPS` - Number of backups to keep (default: 7)

**Output:** `./backups/kb_backup_YYYYMMDD_HHMMSS.tar.gz`

---

### restore.sh
Restores all production data from a backup archive.

```bash
./scripts/restore.sh <backup-file.tar.gz>
```

**Example:**
```bash
./scripts/restore.sh ./backups/kb_backup_20260202_120000.tar.gz
```

**Warning:** This will replace ALL current production data!

**Process:**
1. Extracts backup archive
2. Stops backend/frontend temporarily
3. Drops and recreates database
4. Restores all data (DB, vectors, indexes, uploads)
5. Restarts all services
6. Verifies system health

---

### migrate_dev_to_prod.sh
Migrates development data to production environment.

```bash
./scripts/migrate_dev_to_prod.sh
```

**Use Cases:**
- Initial production deployment with test data
- Refreshing production with latest dev data
- Testing production setup before go-live

**Process:**
1. Creates dump of dev database
2. Stops production backend/frontend
3. Recreates production database
4. Runs Alembic migrations to create schema
5. Adds enum values (handles migration 031d3e796cb8 manual steps)
6. Imports dev data
7. Restarts all services

**Important Notes:**
- Requires both dev and prod compose files
- Automatically handles enum case compatibility
- Shows import statistics and error count
- Safe to run multiple times (idempotent)

---

## 🔧 Maintenance

### fix_enum_case.sh
Checks and fixes enum case compatibility issues.

```bash
./scripts/fix_enum_case.sh
```

**What it does:**
- Verifies enum values match Python code definitions
- Adds missing lowercase chunking strategy values
- Detects incorrect uppercase DocumentStatus/FileType enums
- Provides remediation instructions

**When to use:**
- After fresh database creation
- If encountering enum-related errors
- Before data import/migration
- For troubleshooting

**Expected enum values:**
- `documentstatus`: pending, processing, completed, failed (lowercase)
- `filetype`: txt, md (lowercase)
- `chunkingstrategy`: simple, smart, semantic (lowercase), FIXED_SIZE, PARAGRAPH (uppercase legacy)

---

## 📚 Data Setup Scripts

### setup-wiki.sh / setup-wiki-simple.sh
Scripts for setting up test knowledge bases with Wikipedia data.

**Not covered here** - see script headers for usage.

---

## 🎯 Common Workflows

### Initial Production Setup
```bash
# 1. Start production containers
docker-compose -f docker-compose.production.yml --env-file .env.production up -d

# 2. Run migrations
docker exec kb-platform-backend-prod alembic upgrade head

# 3. Migrate dev data (optional)
./scripts/migrate_dev_to_prod.sh
```

### Regular Backup Schedule
```bash
# Add to crontab for daily backups at 2 AM
0 2 * * * cd /path/to/knowledge-base-platform && ./scripts/backup.sh
```

### Disaster Recovery
```bash
# 1. Stop all containers
docker-compose -f docker-compose.production.yml down

# 2. Restore from backup
./scripts/restore.sh ./backups/kb_backup_20260202_120000.tar.gz

# 3. Verify system health
curl http://localhost:8004/api/v1/health/ready
```

### Enum Compatibility Check
```bash
# Before data import
./scripts/fix_enum_case.sh

# If issues found, rebuild schema
docker exec kb-platform-db-prod psql -U kb_user -d postgres \
  --command "DROP DATABASE IF EXISTS knowledge_base"
docker exec kb-platform-db-prod psql -U kb_user -d postgres \
  --command "CREATE DATABASE knowledge_base OWNER kb_user"
docker exec kb-platform-backend-prod alembic upgrade head
./scripts/fix_enum_case.sh
```

---

## ⚠️ Important Notes

### Enum Case Sensitivity
- **Python enums use lowercase values** (e.g., `FileType.TXT = "txt"`)
- **Migrations MUST create lowercase enum values**
- Bug discovered 2026-02-02: Initial migrations had uppercase values
- Fixed in commit `60da4ed`

### Migration Best Practices
1. Always check enum compatibility before data import
2. Use `migrate_dev_to_prod.sh` for automated migrations
3. Keep backups before major changes
4. Verify system health after restore/migration

### Backup Strategy
- **Frequency**: Daily automated backups recommended
- **Retention**: Keep last 7 days by default
- **Storage**: Store backups on separate volume/server
- **Testing**: Regularly test restore process

---

## 🐛 Troubleshooting

### "invalid input value for enum"
```bash
# Check enum values
./scripts/fix_enum_case.sh

# If uppercase values found, rebuild schema
./scripts/migrate_dev_to_prod.sh
```

### "relation does not exist"
```bash
# Run migrations
docker exec kb-platform-backend-prod alembic upgrade head
```

### "container not running"
```bash
# Start services
docker-compose -f docker-compose.production.yml up -d
```

---

## 📝 Script Development

When creating new scripts:
1. Add shebang: `#!/bin/bash`
2. Add `set -e` for error handling
3. Use color output for clarity
4. Add comprehensive help text
5. Validate inputs and environment
6. Provide clear success/error messages
7. Make executable: `chmod +x script.sh`
8. Document in this README
