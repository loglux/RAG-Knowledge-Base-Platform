#!/bin/bash
set -e

echo "🚀 Starting Knowledge Base Platform API..."

# Wait for database to be ready
echo "⏳ Waiting for database..."
while ! pg_isready -h db -U kb_user -d knowledge_base > /dev/null 2>&1; do
    sleep 1
done
echo "✅ Database is ready"

# Run migrations
echo "📦 Running database migrations..."
alembic upgrade head
echo "✅ Migrations completed"

# Start application
echo "🎯 Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
