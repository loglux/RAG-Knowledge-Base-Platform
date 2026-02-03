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

# FIRST: Check if Setup Wizard saved DATABASE_URL in shared volume
if [ -f /shared/database_url ]; then
    SAVED_DB_URL=$(cat /shared/database_url 2>/dev/null | xargs)
    if [ -n "$SAVED_DB_URL" ]; then
        echo "✅ Found DATABASE_URL in shared volume (from Setup Wizard)"
        export DATABASE_URL="$SAVED_DB_URL"
        echo "🔗 Using credentials from Setup Wizard"
    fi
else
    echo "ℹ️  No saved DATABASE_URL in shared volume"
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
            export DATABASE_URL="postgresql+asyncpg://kb_user:$DEFAULT_PASSWORD@db:5432/knowledge_base"
        else
            echo "💥 FATAL: Cannot connect to database"
            echo "   If Setup Wizard changed password, please re-run Setup Wizard"
            echo "   to save credentials to shared volume."
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

# Start application
echo "🎯 Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
