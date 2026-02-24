#!/bin/bash
set -e

echo "🚀 Starting Knowledge Base Platform API..."

# Ensure appuser can write to logs and uploads volumes
# (bind mounts override Dockerfile ownership, so fix here as root)
if [ -d /app/logs ]; then
    chown -R appuser:appuser /app/logs
fi
if [ -d /app/uploads ]; then
    chown -R appuser:appuser /app/uploads
fi

# Wait for database to be ready
echo "⏳ Waiting for database..."
while ! pg_isready -h db -U kb_user -d knowledge_base > /dev/null 2>&1; do
    sleep 1
done
echo "✅ Database is ready"

# Check database credentials
echo "🔍 Checking database credentials..."

# FIRST: Check for Docker secret password
SECRET_PATH="/run/secrets/db_password"
if [ -f "$SECRET_PATH" ]; then
    DB_PASSWORD=$(cat "$SECRET_PATH" 2>/dev/null | xargs)
    if [ -n "$DB_PASSWORD" ]; then
        DB_HOST="${DB_HOST:-db}"
        DB_PORT="${DB_PORT:-5432}"
        DB_USER="${POSTGRES_USER:-kb_user}"
        DB_NAME="${POSTGRES_DB:-knowledge_base}"
        export DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
        echo "✅ Using DATABASE_URL from Docker secret"
    fi
fi

if [ -z "$DATABASE_URL" ]; then
    echo "ℹ️  No Docker secret found"
    echo "   Attempting connection with DATABASE_URL from environment..."

    # Extract current password from DATABASE_URL
    CURRENT_PASSWORD=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')

    # Try to connect
    if ! PGPASSWORD="$CURRENT_PASSWORD" psql -h db -U kb_user -d knowledge_base -c "SELECT 1" > /dev/null 2>&1; then
        echo "💥 FATAL: Cannot connect to database with provided credentials"
        echo "   Please check Docker secret or DATABASE_URL in environment"
        exit 1
    else
        echo "✅ Connection successful with DATABASE_URL from environment"
    fi
fi

# Run migrations with correct DATABASE_URL
echo "📦 Running database migrations..."
alembic upgrade head
echo "✅ Migrations completed"

# Start application as appuser
echo "🎯 Starting API server as appuser..."
exec gosu appuser uvicorn app.main:app --host 0.0.0.0 --port 8000
