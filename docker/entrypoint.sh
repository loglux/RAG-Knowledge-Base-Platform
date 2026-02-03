#!/bin/bash
set -e

echo "🚀 Starting Knowledge Base Platform API..."

# Wait for database to be ready
echo "⏳ Waiting for database..."
while ! pg_isready -h db -U kb_user -d knowledge_base > /dev/null 2>&1; do
    sleep 1
done
echo "✅ Database is ready"

# Check and fix DATABASE_URL if password was changed via Setup Wizard
echo "🔍 Checking database credentials..."

# Extract current password from DATABASE_URL
CURRENT_PASSWORD=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')

# Try to connect with current DATABASE_URL
if PGPASSWORD="$CURRENT_PASSWORD" psql -h db -U kb_user -d knowledge_base -c "SELECT 1" > /dev/null 2>&1; then
    echo "✅ Connection successful with DATABASE_URL from environment"

    # Check if there's a different password in system_settings
    SAVED_DB_URL=$(PGPASSWORD="$CURRENT_PASSWORD" psql -h db -U kb_user -d knowledge_base -t -c \
        "SELECT value FROM system_settings WHERE key = 'database_url';" 2>/dev/null | xargs || echo "")

    if [ -n "$SAVED_DB_URL" ] && [ "$SAVED_DB_URL" != "$DATABASE_URL" ]; then
        echo "⚠️  Found different DATABASE_URL in system_settings, using it"
        export DATABASE_URL="$SAVED_DB_URL"
    fi
else
    echo "❌ Authentication failed with DATABASE_URL from environment"
    echo "🔄 Trying default credentials..."

    # Try default password
    DEFAULT_PASSWORD="kb_pass_change_me"
    if PGPASSWORD="$DEFAULT_PASSWORD" psql -h db -U kb_user -d knowledge_base -c "SELECT 1" > /dev/null 2>&1; then
        echo "✅ Connected with default credentials"

        # Read correct DATABASE_URL from system_settings
        SAVED_DB_URL=$(PGPASSWORD="$DEFAULT_PASSWORD" psql -h db -U kb_user -d knowledge_base -t -c \
            "SELECT value FROM system_settings WHERE key = 'database_url';" 2>/dev/null | xargs || echo "")

        if [ -n "$SAVED_DB_URL" ]; then
            echo "✅ Found DATABASE_URL in system_settings, using it"
            export DATABASE_URL="$SAVED_DB_URL"
        else
            echo "⚠️  No database_url in system_settings, using default"
            export DATABASE_URL="postgresql+asyncpg://kb_user:$DEFAULT_PASSWORD@db:5432/knowledge_base"
        fi
    else
        echo "💥 FATAL: Cannot connect with any known credentials"
        echo "   Please check database configuration"
        exit 1
    fi
fi

# Run migrations with correct DATABASE_URL
echo "📦 Running database migrations..."
alembic upgrade head
echo "✅ Migrations completed"

# Start application
echo "🎯 Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
