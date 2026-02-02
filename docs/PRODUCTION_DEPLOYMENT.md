# Production Deployment Guide

Complete guide for deploying the Knowledge Base Platform in production.

**Last Updated:** 2026-02-02
**Version:** 1.0

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Setup](#detailed-setup)
4. [Configuration](#configuration)
5. [Data Migration](#data-migration)
6. [Backup & Restore](#backup--restore)
7. [Health Checks](#health-checks)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)

---

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 4 cores
- RAM: 8 GB
- Disk: 50 GB (SSD recommended)
- OS: Linux (Ubuntu 20.04+, Debian 11+, or compatible)

**Recommended:**
- CPU: 8+ cores
- RAM: 16+ GB
- Disk: 100+ GB SSD
- OS: Ubuntu 22.04 LTS

### Software Requirements

1. **Docker Engine** (20.10+)
   ```bash
   docker --version
   # Docker version 20.10.0 or higher
   ```

2. **Docker Compose** (2.0+)
   ```bash
   docker-compose --version
   # Docker Compose version v2.0.0 or higher
   ```

3. **Git**
   ```bash
   git --version
   ```

### Network Requirements

**Required Ports:**
- `5174` - Frontend (HTTP)
- `8004` - Backend API (HTTP)

**Internal Ports** (container network only):
- `5432` - PostgreSQL
- `6333-6334` - Qdrant (HTTP API, gRPC)
- `9200` - OpenSearch

**Firewall Configuration:**
```bash
# Allow frontend and backend access
sudo ufw allow 5174/tcp
sudo ufw allow 8004/tcp
```

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/your-org/RAG-Knowledge-Base-Platform.git
cd RAG-Knowledge-Base-Platform
```

### 2. Create Environment File

```bash
cp .env.example .env.production
nano .env.production  # Edit with your configuration
```

**Minimum Required Settings:**
```env
# Security (MUST CHANGE!)
SECRET_KEY=your-secure-secret-key-here-min-32-chars
POSTGRES_PASSWORD=your-secure-database-password

# LLM Provider (at least one required)
OPENAI_API_KEY=sk-your-openai-key
# OR
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
# OR
OLLAMA_BASE_URL=http://your-ollama-host:11434
```

### 3. Deploy

```bash
docker-compose -f docker-compose.production.yml --env-file .env.production up -d
```

### 4. Run Migrations

```bash
docker exec kb-platform-backend-prod alembic upgrade head
```

### 5. Add Chunking Strategy Enum Values

```bash
# Required for migration 031d3e796cb8
docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base \
  -c "ALTER TYPE chunkingstrategy ADD VALUE IF NOT EXISTS 'simple';"
docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base \
  -c "ALTER TYPE chunkingstrategy ADD VALUE IF NOT EXISTS 'smart';"
docker exec kb-platform-db-prod psql -U kb_user -d knowledge_base \
  -c "ALTER TYPE chunkingstrategy ADD VALUE IF NOT EXISTS 'semantic';"
```

### 6. Verify

```bash
# Check all services are healthy
docker-compose -f docker-compose.production.yml ps

# Test API
curl http://localhost:8004/api/v1/health

# Open in browser
http://your-server-ip:5174
```

---

## Detailed Setup

### Step 1: Prepare Environment File

Create `.env.production` with all required settings:

```bash
# ======================
# Application Settings
# ======================
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# ======================
# Security (REQUIRED)
# ======================
# Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=CHANGE-THIS-TO-SECURE-RANDOM-STRING-MIN-32-CHARS

# Database password (strong password!)
POSTGRES_PASSWORD=CHANGE-THIS-TO-SECURE-DATABASE-PASSWORD

# OpenSearch admin password
OPENSEARCH_PASSWORD=Admin123!

# ======================
# LLM Providers
# ======================
# At least ONE provider required

# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key-here

# Anthropic (optional)
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here

# Voyage AI (optional, for embeddings)
VOYAGE_API_KEY=pa-your-voyage-api-key-here

# Ollama (optional, for local models)
OLLAMA_BASE_URL=http://your-ollama-server:11434

# ======================
# CORS Configuration
# ======================
# Add your domain(s), comma-separated
CORS_ORIGINS=http://your-domain.com:5174,http://your-ip:5174

# ======================
# Ports (Optional)
# ======================
FRONTEND_PORT=5174
BACKEND_PORT=8004

# ======================
# Database (Optional)
# ======================
POSTGRES_USER=kb_user
POSTGRES_DB=knowledge_base
```

### Step 2: Generate Secure Keys

```bash
# Generate SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# Generate strong database password
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(24))"
```

### Step 3: Start Services

```bash
# Start all services
docker-compose -f docker-compose.production.yml --env-file .env.production up -d

# Watch logs (Ctrl+C to exit)
docker-compose -f docker-compose.production.yml --env-file .env.production logs -f

# Check status
docker-compose -f docker-compose.production.yml --env-file .env.production ps
```

**Expected Output:**
```
NAME                          STATUS
kb-platform-backend-prod      Up (healthy)
kb-platform-db-prod           Up (healthy)
kb-platform-frontend-prod     Up (healthy)
kb-platform-opensearch-prod   Up (healthy)
kb-platform-qdrant-prod       Up
```

### Step 4: Initialize Database

```bash
# Apply all database migrations
docker exec kb-platform-backend-prod alembic upgrade head

# Add required enum values (manual step for migration 031d3e796cb8)
./scripts/fix_enum_case.sh
```

### Step 5: Verify Deployment

```bash
# Check backend health
curl http://localhost:8004/api/v1/health
# Expected: {"status":"ok"}

# Check service readiness
curl http://localhost:8004/api/v1/health/ready
# Expected: {"ready":true,"checks":{...}}

# Test frontend
curl -I http://localhost:5174
# Expected: HTTP/1.1 200 OK
```

---

## Configuration

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ | - | JWT signing key (min 32 chars) |
| `POSTGRES_PASSWORD` | ✅ | - | Database password |
| `OPENAI_API_KEY` | ⚠️ | - | OpenAI API key (or other provider) |
| `ANTHROPIC_API_KEY` | ❌ | - | Anthropic API key |
| `VOYAGE_API_KEY` | ❌ | - | Voyage AI API key |
| `OLLAMA_BASE_URL` | ❌ | - | Ollama server URL |
| `CORS_ORIGINS` | ❌ | `http://localhost:5174` | Allowed origins |
| `FRONTEND_PORT` | ❌ | `5174` | Frontend external port |
| `BACKEND_PORT` | ❌ | `8004` | Backend external port |
| `LOG_LEVEL` | ❌ | `INFO` | Logging level |

⚠️ = At least one LLM provider required

### Port Mapping

| Service | Internal Port | External Port | Configurable |
|---------|---------------|---------------|--------------|
| Frontend | 80 | 5174 | ✅ `FRONTEND_PORT` |
| Backend | 8000 | 8004 | ✅ `BACKEND_PORT` |
| PostgreSQL | 5432 | - | ❌ Internal only |
| Qdrant | 6333 | - | ❌ Internal only |
| OpenSearch | 9200 | - | ❌ Internal only |

### Volume Management

All data is stored in named Docker volumes:

| Volume | Purpose | Size (typical) |
|--------|---------|----------------|
| `kb_postgres_data_prod` | Database | 1-5 GB |
| `kb_qdrant_data_prod` | Vector embeddings | 5-50 GB |
| `kb_opensearch_data_prod` | Lexical index | 2-10 GB |
| `kb_uploads_prod` | Document files | 1-20 GB |
| `kb_app_logs_prod` | Backend logs | 100-500 MB |
| `kb_frontend_logs_prod` | Frontend logs | 10-100 MB |

**View volumes:**
```bash
docker volume ls | grep kb_
```

**Inspect volume:**
```bash
docker volume inspect kb_postgres_data_prod
```

---

## Data Migration

### Migrating from Development to Production

Use the automated migration script:

```bash
./scripts/migrate_dev_to_prod.sh
```

This script:
1. Dumps dev database
2. Recreates production database
3. Runs migrations
4. Adds enum values
5. Imports data
6. Verifies results

**Manual Migration (if needed):**

```bash
# 1. Create dev dump
docker-compose -f docker-compose.dev.yml up -d db
docker exec kb-platform-db pg_dump -U kb_user -d knowledge_base \
  --data-only --inserts > dev_data.sql

# 2. Stop production backend
docker-compose -f docker-compose.production.yml --env-file .env.production \
  stop backend frontend

# 3. Recreate production database
docker exec kb-platform-db-prod psql -U kb_user -d postgres \
  --command "DROP DATABASE IF EXISTS knowledge_base"
docker exec kb-platform-db-prod psql -U kb_user -d postgres \
  --command "CREATE DATABASE knowledge_base OWNER kb_user"

# 4. Run migrations
docker-compose -f docker-compose.production.yml --env-file .env.production up -d backend
sleep 10
docker exec kb-platform-backend-prod alembic upgrade head

# 5. Add enum values
./scripts/fix_enum_case.sh

# 6. Import data
cat dev_data.sql | docker exec -i kb-platform-db-prod psql \
  -U kb_user -d knowledge_base

# 7. Restart services
docker-compose -f docker-compose.production.yml --env-file .env.production up -d
```

---

## Backup & Restore

### Creating Backups

**Automated backup:**
```bash
./scripts/backup.sh
```

Output: `./backups/kb_backup_YYYYMMDD_HHMMSS.tar.gz`

**Scheduled backups (cron):**
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/knowledge-base-platform && ./scripts/backup.sh

# Add weekly backup on Sunday at 3 AM
0 3 * * 0 cd /path/to/knowledge-base-platform && ./scripts/backup.sh
```

### Restoring from Backup

```bash
./scripts/restore.sh ./backups/kb_backup_20260202_120000.tar.gz
```

**Warning:** This replaces ALL current data!

---

## Health Checks

### Service Health Endpoints

**Backend API:**
```bash
# Basic health
curl http://localhost:8004/api/v1/health
# {"status":"ok"}

# Detailed readiness
curl http://localhost:8004/api/v1/health/ready
# {"ready":true,"checks":{"database":true,"vector_store":true,...}}
```

**Frontend:**
```bash
curl http://localhost:5174/health
# healthy
```

### Container Health Status

```bash
# Check all containers
docker-compose -f docker-compose.production.yml ps

# Check specific container logs
docker logs kb-platform-backend-prod --tail 50
docker logs kb-platform-frontend-prod --tail 50
docker logs kb-platform-db-prod --tail 50
```

### Database Health

```bash
# Connect to database
docker exec -it kb-platform-db-prod psql -U kb_user -d knowledge_base

# Check tables
\dt

# Count records
SELECT COUNT(*) FROM knowledge_bases;
SELECT COUNT(*) FROM documents;
```

---

## Troubleshooting

### Common Issues

#### 1. Frontend shows "Network Error" or can't reach API

**Symptoms:**
- Console shows CORS errors
- API requests fail with 404 or connection refused

**Solution:**
```bash
# Check backend is running and healthy
docker logs kb-platform-backend-prod --tail 50

# Verify CORS_ORIGINS in .env.production
# Should include: http://your-ip:5174

# Restart backend
docker-compose -f docker-compose.production.yml restart backend
```

#### 2. "Invalid input value for enum" errors

**Symptoms:**
```
ERROR: invalid input value for enum documentstatus: "completed"
ERROR: invalid input value for enum filetype: "txt"
```

**Root Cause:** Enum case mismatch (uppercase in DB, lowercase in code)

**Solution:**
```bash
# This was a bug in migrations, fixed in commit 60da4ed
# If you encounter this:

# 1. Rebuild backend with latest code
git pull origin master
docker-compose -f docker-compose.production.yml --env-file .env.production build backend

# 2. Recreate database with correct migrations
docker exec kb-platform-db-prod psql -U kb_user -d postgres \
  --command "DROP DATABASE IF EXISTS knowledge_base"
docker exec kb-platform-db-prod psql -U kb_user -d postgres \
  --command "CREATE DATABASE knowledge_base OWNER kb_user"
docker exec kb-platform-backend-prod alembic upgrade head
./scripts/fix_enum_case.sh
```

#### 3. "Relation does not exist" errors

**Symptoms:**
```
ERROR: relation "knowledge_bases" does not exist
```

**Solution:**
```bash
# Run migrations
docker exec kb-platform-backend-prod alembic upgrade head
```

#### 4. Container restarts continuously

**Check logs:**
```bash
docker logs kb-platform-backend-prod --tail 100
```

**Common causes:**
- Missing environment variables
- Database connection failed
- Port already in use

**Solutions:**
```bash
# Check environment file
cat .env.production

# Check port conflicts
netstat -tlnp | grep -E "5174|8004"

# Restart with logs
docker-compose -f docker-compose.production.yml --env-file .env.production down
docker-compose -f docker-compose.production.yml --env-file .env.production up
```

#### 5. Out of disk space

**Check disk usage:**
```bash
df -h
docker system df
```

**Clean up:**
```bash
# Remove unused Docker resources
docker system prune -a

# Remove old backups (keep last 7)
cd backups
ls -t kb_backup_*.tar.gz | tail -n +8 | xargs rm

# Check volume sizes
docker volume ls | grep kb_ | while read _ vol; do
  echo "$vol: $(docker system df -v | grep $vol | awk '{print $3}')"
done
```

---

## Maintenance

### Updates

**Update application:**
```bash
# Pull latest code
git pull origin master

# Rebuild containers
docker-compose -f docker-compose.production.yml --env-file .env.production build

# Restart with new images
docker-compose -f docker-compose.production.yml --env-file .env.production up -d

# Run any new migrations
docker exec kb-platform-backend-prod alembic upgrade head
```

### Monitoring

**Check disk space:**
```bash
df -h
docker system df
```

**Check logs:**
```bash
# Backend logs
docker logs kb-platform-backend-prod --tail 100 -f

# Database logs
docker logs kb-platform-db-prod --tail 50

# All logs
docker-compose -f docker-compose.production.yml logs -f
```

**Monitor resource usage:**
```bash
docker stats
```

### Scaling

**Increase backend workers:**

Edit `docker-compose.production.yml`:
```yaml
services:
  backend:
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "8"]
    # Change --workers value based on CPU cores
```

**Increase memory limits:**
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 2G
```

---

## Security Checklist

- [ ] Changed default `SECRET_KEY`
- [ ] Changed default `POSTGRES_PASSWORD`
- [ ] Changed default `OPENSEARCH_PASSWORD`
- [ ] API keys stored in `.env.production` (not committed to git)
- [ ] `.env.production` has restricted permissions: `chmod 600 .env.production`
- [ ] Firewall configured (only 5174 and 8004 open)
- [ ] SSL/TLS configured (if public-facing)
- [ ] Regular backups scheduled
- [ ] Backup files stored securely off-server
- [ ] Log rotation configured
- [ ] Monitoring/alerting set up

---

## Production Checklist

Before going live:

- [ ] All services start successfully
- [ ] Health checks pass
- [ ] Can create knowledge base
- [ ] Can upload document
- [ ] Can search and chat
- [ ] Backup created and tested restore
- [ ] Scheduled backups configured
- [ ] Log monitoring set up
- [ ] Performance tested under load
- [ ] Documentation updated
- [ ] Team trained on operations

---

## Support

**Documentation:**
- [README.md](../README.md) - Project overview
- [RUNBOOK.md](../RUNBOOK.md) - Development guide
- [scripts/README.md](../scripts/README.md) - Utility scripts

**Scripts:**
- `./scripts/backup.sh` - Create backup
- `./scripts/restore.sh` - Restore from backup
- `./scripts/migrate_dev_to_prod.sh` - Migrate dev data
- `./scripts/fix_enum_case.sh` - Fix enum compatibility

**Logs:**
```bash
# Application logs
docker-compose -f docker-compose.production.yml logs -f backend

# Access logs
docker-compose -f docker-compose.production.yml logs -f frontend

# Database logs
docker-compose -f docker-compose.production.yml logs -f db
```

---

**Last Updated:** 2026-02-02
**Maintained By:** Development Team
**Review Frequency:** After each major release
