#!/bin/bash

# ============================================================
# Development Server - Combined startup script
# Starts docker-compose + Cloud Functions Framework together
# ============================================================
#
# Local Development Stack:
#   - Frontend: Vite dev-server (hot-reload enabled)
#     * Uses Dockerfile.dev with npm run dev
#     * Changes reflect immediately without rebuild
#   - API: Flask on http://localhost:5001
#   - Database: PostgreSQL on localhost:5432
#   - Redis: Cache on localhost:6379
#   - Cloud Functions Framework: Processing backend on localhost:9000
#
# For GCP Deployment:
#   - Frontend: Use production Dockerfile (multi-stage build)
#   - Cloud Functions: Use deploy.sh script
# ============================================================

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Invoice Scanner - Local Development Server"
echo "============================================="
echo ""
echo "This script will start:"
echo "  1. Docker Compose (API, Frontend, Database, Redis)"
echo "     • Frontend: Vite dev-server with hot-reload"
echo "  2. Cloud Functions Framework (processing backend)"
echo ""
echo "Prerequisites:"
echo "  ✓ Docker & Docker Compose installed"
echo "  ✓ Python 3.11+ installed"
echo "  ✓ Cloud Functions dependencies (will auto-install)"
echo ""

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install Docker Desktop."
    exit 1
fi

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ python3 not found. Please install Python 3.11+"
    exit 1
fi

echo "✅ Prerequisites met"
echo ""

# Detect host machine's IP for Docker container networking
HOST_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
if [ -z "$HOST_IP" ]; then
    echo "⚠️  Warning: Could not auto-detect host IP. Using localhost."
    HOST_IP="localhost"
fi
echo "🔗 Host IP detected: $HOST_IP"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    docker-compose down 2>/dev/null || true
    echo "✓ All services stopped"
}

trap cleanup EXIT

# Start docker-compose
echo "1️⃣  Starting Docker Compose services..."
cd "$ROOT_DIR"
docker-compose down -v 2>/dev/null || true

# Pass host IP to docker-compose via environment variable
export PROCESSING_SERVICE_URL="http://${HOST_IP}:9000"
docker-compose up -d --build

echo "⏳ Waiting for services to be healthy..."
sleep 10

docker-compose ps

echo ""
echo "✅ Docker services started:"
echo "   API:                http://localhost:5001"
echo "   Frontend (Vite):    http://localhost:8080  (hot-reload enabled)"
echo "   Database:           localhost:5432"
echo "   Redis:              localhost:6379"
echo ""
echo "Frontend Development:"
echo "  • Changes to JSX/CSS files reflect instantly"
echo "  • No rebuild needed - Vite watches files automatically"
echo "  • View browser console for errors/warnings"
echo ""

# Start Cloud Functions Framework in a new terminal
echo "2️⃣  Starting Cloud Functions Framework in a new terminal..."
echo ""

if [ ! -f "invoice.scanner.cloud.functions/local_server.sh" ]; then
    echo "❌ invoice.scanner.cloud.functions/local_server.sh not found"
    exit 1
fi

chmod +x invoice.scanner.cloud.functions/local_server.sh

# Start Cloud Functions in a new Terminal window (macOS)
echo "📱 Opening new Terminal for Cloud Functions Framework..."

# Get the absolute path for the script
CF_SCRIPT="$ROOT_DIR/invoice.scanner.cloud.functions/local_server.sh"

# Open in new Terminal window and run the script
open -a Terminal "$CF_SCRIPT"

echo ""
echo "✅ All services started!"
echo ""
echo "📍 Services are running:"
echo "   API:                http://localhost:5001"
echo "   Frontend (Vite):    http://localhost:8080  (hot-reload enabled)"
echo "   Database:           localhost:5432"
echo "   Redis:              localhost:6379"
echo "   Cloud Functions:    http://localhost:9000  (new Terminal window)"
echo ""
echo "Frontend Development:"
echo "  • Changes to JSX/CSS files reflect instantly"
echo "  • No rebuild needed - Vite watches files automatically"
echo ""
echo "To view Cloud Functions logs:"
echo "  • Check the Terminal window that opened automatically"
echo "  • Or run: docker-compose logs -f api"
echo ""
echo "Press Ctrl+C in THIS terminal to stop Docker services"
echo "Press Ctrl+C in the CLOUD FUNCTIONS terminal to stop it"
echo ""

# Wait indefinitely so docker-compose stays running
wait
