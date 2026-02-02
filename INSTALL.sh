#!/bin/bash
# Quick install script for Knowledge Base Platform

set -e

echo "🚀 Knowledge Base Platform - Quick Install"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.production.example .env
    echo "✓ .env created"
    echo ""
    echo "⚠️  IMPORTANT: Default PostgreSQL password is 'kb_pass_change_me'"
    echo "   You can change it now in .env or later via Setup Wizard"
    echo ""
else
    echo "✓ .env already exists"
fi

# Stop any running containers
if [ "$(docker ps -q)" ]; then
    echo "🛑 Stopping running containers..."
    docker-compose down
fi

# Start services
echo "🐳 Starting Docker services..."
docker-compose up -d --build

echo ""
echo "⏳ Waiting for services to be ready (30 seconds)..."
sleep 30

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "✅ Installation complete!"
    echo ""
    echo "📍 Next steps:"
    echo "   1. Start frontend: cd frontend && npm install && npm run dev"
    echo "   2. Open browser: http://localhost:5174/setup"
    echo "   3. Complete Setup Wizard"
    echo ""
    echo "📚 Useful commands:"
    echo "   - View logs: docker-compose logs -f"
    echo "   - Check status: docker-compose ps"
    echo "   - API docs: http://localhost:8004/docs"
    echo ""
else
    echo ""
    echo "❌ Some services failed to start"
    echo "Run 'docker-compose logs' to see errors"
    exit 1
fi
