#!/bin/bash

# Recovery script: Extract DATABASE_URL from system_settings when API container won't start
# This happens when Setup Wizard changed the password but docker-compose has old password

echo "🔧 DATABASE_URL Recovery Script"
echo "================================"
echo ""

# Check if postgres container is running
if ! docker ps | grep -q "kb-platform-db"; then
    echo "❌ PostgreSQL container is not running"
    echo "   Start it with: docker-compose up -d db"
    exit 1
fi

echo "✓ PostgreSQL container is running"
echo ""

# Extract DATABASE_URL from system_settings table
echo "📊 Querying system_settings for database_url..."
echo ""

DATABASE_URL=$(docker exec kb-platform-db psql -U kb_user -d knowledge_base -t -c \
    "SELECT value FROM system_settings WHERE key = 'database_url';" 2>/dev/null | xargs)

if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  No database_url found in system_settings"
    echo "   This means the Setup Wizard hasn't changed the password yet."
    echo ""
    echo "   Try using the default credentials from docker-compose.yml:"
    echo "   DATABASE_URL=postgresql+asyncpg://kb_user:kb_pass_change_me@db:5432/knowledge_base"
    exit 1
fi

echo "✅ Found DATABASE_URL in system_settings:"
echo ""
echo "   $DATABASE_URL"
echo ""

# Extract password from DATABASE_URL (format: postgresql+asyncpg://user:pass@host:port/db)
PASSWORD=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')

if [ -z "$PASSWORD" ]; then
    echo "❌ Could not extract password from DATABASE_URL"
    exit 1
fi

echo "🔑 Extracted password: $PASSWORD"
echo ""

# Create/update .env file with correct DATABASE_URL
echo "📝 Updating .env file..."
echo ""

# Check if .env exists
if [ -f .env ]; then
    # Backup existing .env
    cp .env .env.backup
    echo "   ✓ Backed up existing .env to .env.backup"

    # Remove old DATABASE_URL if exists
    sed -i '/^DATABASE_URL=/d' .env

    # Add new DATABASE_URL
    echo "DATABASE_URL=$DATABASE_URL" >> .env
    echo "   ✓ Updated .env with correct DATABASE_URL"
else
    # Create new .env
    echo "DATABASE_URL=$DATABASE_URL" > .env
    echo "   ✓ Created .env with correct DATABASE_URL"
fi

echo ""
echo "✅ Recovery complete!"
echo ""
echo "Next steps:"
echo "  1. Restart containers: docker-compose down && docker-compose up -d"
echo "  2. Check API logs:     docker logs -f kb-platform-api"
echo ""
echo "Note: The .env file now contains the correct DATABASE_URL."
echo "      Docker Compose will use this instead of hardcoded values."
