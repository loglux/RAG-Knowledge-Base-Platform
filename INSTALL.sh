#!/bin/bash
# Quick install script for Knowledge Base Platform

set -e

echo "🚀 Knowledge Base Platform - Quick Install"
echo "=========================================="
echo ""
echo "✨ No .env file needed! All defaults are in docker-compose.yml"
echo "   Change database password later via Setup Wizard"
echo ""

# Stop only this project stack if it is running
if docker compose ps --status running 2>/dev/null | grep -q .; then
    echo "🛑 Stopping current project containers..."
    docker compose down
fi

# Start services
echo "🐳 Starting Docker services..."
docker compose up -d --build

echo ""
echo "⏳ Waiting for services to be ready (30 seconds)..."
sleep 30

# Check if services are running
if docker compose ps --status running | grep -q .; then
    echo ""
    echo "✅ Installation complete!"
    echo ""
    echo "🎉 All services are running:"
    echo "   - Frontend: http://localhost:5174"
    echo "   - Backend API: http://localhost:8004"
    echo "   - API Docs: http://localhost:8004/docs"
    echo ""
    echo "📍 Next step:"
    echo "   Open browser: http://localhost:5174/setup"
    echo "   Complete Setup Wizard to configure API keys and settings"
    echo ""
    echo "📚 Useful commands:"
    echo "   - View logs: docker compose logs -f"
    echo "   - Check status: docker compose ps"
    echo "   - Restart: docker compose restart"
    echo ""
else
    echo ""
    echo "❌ Some services failed to start"
    echo "Run 'docker compose logs' to see errors"
    exit 1
fi
