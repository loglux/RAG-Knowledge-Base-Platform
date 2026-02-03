#!/bin/bash
set -e

echo "🚀 Starting Knowledge Base Platform API..."

# Ensure appuser can write to logs volume
if [ -d /app/logs ]; then
    chown -R appuser:appuser /app/logs
fi

# Wait for database to be ready
echo "⏳ Waiting for database..."
while ! pg_isready -h db -U kb_user -d knowledge_base > /dev/null 2>&1; do
    sleep 1
done
echo "✅ Database is ready"

# Check and fix DATABASE_URL if password was changed via Setup Wizard
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

# SECOND: Check if Setup Wizard saved DATABASE_URL in logs volume (legacy fallback)
PERSIST_PATH="/app/logs/.database_url"
if [ -z "$DATABASE_URL" ] && [ -f "$PERSIST_PATH" ]; then
    SAVED_DB_URL=$(cat "$PERSIST_PATH" 2>/dev/null | xargs)
    if [ -n "$SAVED_DB_URL" ]; then
        echo "✅ Found persisted DATABASE_URL (from Setup Wizard)"
        export DATABASE_URL="$SAVED_DB_URL"
        echo "🔗 Using credentials from Setup Wizard"
    fi
fi

if [ -z "$DATABASE_URL" ]; then
    echo "ℹ️  No persisted DATABASE_URL found"
    echo "   Attempting connection with DATABASE_URL from environment..."

    # Extract current password from DATABASE_URL
    CURRENT_PASSWORD=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')

    # Try to connect
    if ! PGPASSWORD="$CURRENT_PASSWORD" psql -h db -U kb_user -d knowledge_base -c "SELECT 1" > /dev/null 2>&1; then
        echo "❌ Authentication failed with DATABASE_URL from environment"
        echo "🔄 Trying default password as fallback..."

        # Try default password
        DEFAULT_PASSWORD="kb_pass_change_me"
        if PGPASSWORD="$DEFAULT_PASSWORD" psql -h db -U kb_user -d knowledge_base -c "SELECT 1" > /dev/null 2>&1; then
            echo "✅ Connected with default password"

            # Try to read DATABASE_URL from system_settings
            SAVED_DB_URL=$(PGPASSWORD="$DEFAULT_PASSWORD" psql -h db -U kb_user -d knowledge_base -t -c \
                "SELECT value FROM system_settings WHERE key = 'database_url';" 2>/dev/null | xargs || echo "")

            if [ -n "$SAVED_DB_URL" ]; then
                echo "✅ Found DATABASE_URL in system_settings, using it"
                export DATABASE_URL="$SAVED_DB_URL"

                # Save to logs volume for future restarts
                if [ -d /app/logs ]; then
                    echo "$SAVED_DB_URL" > "$PERSIST_PATH"
                    echo "📝 Saved to $PERSIST_PATH for persistence"
                fi
            else
                export DATABASE_URL="postgresql+asyncpg://kb_user:$DEFAULT_PASSWORD@db:5432/knowledge_base"
            fi
        else
            echo "💥 FATAL: Cannot connect to database with any known credentials"
            echo "   Tried: environment password, default password"
            echo "   Please check database configuration or re-run Setup Wizard"
            exit 1
        fi
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
