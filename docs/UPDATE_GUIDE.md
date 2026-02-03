# Update Guide

Guide for updating the Knowledge Base Platform without breaking database connections.

## Problem: Password Authentication Failure After Update

### Symptoms

After running `git pull` and `docker-compose up -d --build`, you see:

```
ERROR: password authentication failed for user "kb_user"
```

API container keeps restarting, frontend never starts.

### Root Cause

1. **Initial Setup**: You run the Setup Wizard, which changes the PostgreSQL password for security
2. **Password Saved**: New password is saved to `system_settings` table in database
3. **Update Code**: You `git pull` new code and rebuild containers
4. **Mismatch**: New API container tries to use default password from `docker-compose.yml`, but database has changed password
5. **Authentication Fails**: Connection refused, container crashes

### Solution

#### Option 1: Automatic Recovery Script (Recommended)

Run the recovery script to extract the correct password and update `.env`:

```bash
cd /path/to/knowledge-base-platform
./scripts/recover_database_url.sh
```

The script will:
1. Extract `DATABASE_URL` from `system_settings` table
2. Create/update `.env` file with correct credentials
3. Docker Compose will use `.env` on next restart

Then restart containers:

```bash
docker-compose down
docker-compose up -d
```

#### Option 2: Manual Recovery

If the script doesn't work, manually query the database:

```bash
# Connect to postgres container
docker exec -it kb-platform-db psql -U kb_user -d knowledge_base

# Query for saved DATABASE_URL
SELECT value FROM system_settings WHERE key = 'database_url';
```

Copy the DATABASE_URL and create `.env` file:

```bash
# Create .env in project root
cat > .env << 'EOF'
DATABASE_URL=postgresql+asyncpg://kb_user:YOUR_PASSWORD_HERE@db:5432/knowledge_base
EOF

# Restart
docker-compose down && docker-compose up -d
```

#### Option 3: Reset Password (Data Loss Risk)

⚠️ **WARNING**: This will reset the database, losing all Knowledge Bases and documents.

```bash
# Stop and remove everything
docker-compose down -v

# Start fresh with default credentials
docker-compose up -d

# Run Setup Wizard again
```

## How It Works (Fixed in Latest Version)

### Before Fix

- `docker-compose.yml` hardcoded `DATABASE_URL` with default password
- Setup Wizard changed password and saved to `system_settings`
- On restart, API used hardcoded default → authentication failed

### After Fix

1. **Docker Compose**: Uses `.env` file if exists, falls back to default:
   ```yaml
   environment:
     - DATABASE_URL=${DATABASE_URL:-postgresql+asyncpg://kb_user:kb_pass_change_me@db:5432/knowledge_base}
   ```

2. **Application Startup**: Checks for password mismatch and auto-fixes:
   ```python
   # app/main.py lifespan()
   saved_db_url = await SystemSettingsManager.get_setting(db, "database_url")
   if saved_db_url and saved_db_url != settings.DATABASE_URL:
       await recreate_engine(saved_db_url)  # Reconnect with correct password
   ```

3. **Result**: After initial Setup Wizard:
   - Password saved to `system_settings`
   - Recovery script creates `.env` with correct credentials
   - Future updates read from `.env` → no more authentication failures

## Update Process (Best Practice)

### First Update After Setup Wizard

1. **Pull Changes**:
   ```bash
   git pull origin master
   ```

2. **Run Recovery Script** (extracts saved password):
   ```bash
   ./scripts/recover_database_url.sh
   ```

3. **Rebuild and Restart**:
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

4. **Verify**:
   ```bash
   docker logs -f kb-platform-api
   # Should see: "✓ Database credentials match"
   ```

### Subsequent Updates

Once `.env` file exists with correct `DATABASE_URL`:

```bash
git pull origin master
docker-compose up -d --build
```

No recovery needed - Docker Compose reads from `.env` automatically.

## Troubleshooting

### Error: "No database_url found in system_settings"

This means Setup Wizard hasn't changed the password yet. Use default:

```bash
# Create .env with default
echo "DATABASE_URL=postgresql+asyncpg://kb_user:kb_pass_change_me@db:5432/knowledge_base" > .env

# Restart
docker-compose up -d
```

### Error: "PostgreSQL container is not running"

Start database first:

```bash
docker-compose up -d db
# Wait 5 seconds for postgres to start
sleep 5
# Then run recovery
./scripts/recover_database_url.sh
```

### Error: "Could not extract password from DATABASE_URL"

The `database_url` in `system_settings` might be malformed. Check manually:

```bash
docker exec kb-platform-db psql -U kb_user -d knowledge_base -c \
  "SELECT key, value FROM system_settings WHERE key = 'database_url';"
```

If empty or wrong format, you may need to reset and run Setup Wizard again.

### API Logs Show "Could not check database credentials"

This warning is OK on first startup. It means:
- Database tables don't exist yet (before migrations)
- Or Setup Wizard hasn't been completed

Run Setup Wizard at `http://your-domain.com/setup` (frontend will auto-redirect).

## Files Involved

- **docker-compose.yml**: Reads `DATABASE_URL` from `.env` with default fallback
- **app/main.py**: Auto-detects password mismatch on startup and reconnects
- **app/services/setup_manager.py**: Changes password and saves to `system_settings`
- **scripts/recover_database_url.sh**: Extracts saved password and creates `.env`
- **.env**: User-specific settings (gitignored, not committed)

## Security Note

The `.env` file contains sensitive credentials. Ensure:

```bash
# Check .gitignore includes .env
grep -q "^\.env$" .gitignore || echo ".env" >> .gitignore

# Restrict permissions
chmod 600 .env
```

Never commit `.env` to version control.

## Prevention (For Developers)

When developing features that change database credentials:

1. **Save to system_settings**: ✅ Already done in `setup_manager.py`
2. **Load on startup**: ✅ Already done in `main.py` lifespan
3. **Document**: ✅ This guide
4. **Test**: Run `./scripts/recover_database_url.sh` after Setup Wizard

## Summary

**Problem**: Setup Wizard changes password → updates break authentication
**Solution**: Recovery script extracts password → creates `.env` → Docker Compose uses it
**Prevention**: Application auto-detects and reconnects with correct password on startup

---

**Last Updated**: 2026-02-03
**Applies to**: Version 0.1.0+
