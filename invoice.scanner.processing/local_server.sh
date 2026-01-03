#!/bin/bash

# Local server for development
# Starts the Processing Worker Service locally with mock Pub/Sub

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Invoice Scanner - Processing Worker Service (Local Dev)       ║"
echo "╚════════════════════════════════════════════════════════════════╝"

# Check Python version
echo "📋 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.11"

if [[ "$PYTHON_VERSION" < "$REQUIRED_VERSION" ]]; then
    echo "❌ Python $REQUIRED_VERSION+ required (found $PYTHON_VERSION)"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION"

# Check system dependencies
echo "📋 Checking system dependencies..."
MISSING_DEPS=""

if ! command -v tesseract &> /dev/null; then
    MISSING_DEPS="$MISSING_DEPS tesseract-ocr"
fi

if ! command -v pdftoppm &> /dev/null; then
    MISSING_DEPS="$MISSING_DEPS poppler-utils"
fi

if [ -n "$MISSING_DEPS" ]; then
    echo "⚠️  Missing system dependencies:$MISSING_DEPS"
    echo "   Install with:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "   brew install$MISSING_DEPS"
    else
        echo "   sudo apt-get install$MISSING_DEPS"
    fi
    echo ""
    echo "   Continue anyway? (y/n)"
    read -r CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        exit 1
    fi
fi
echo "✅ System dependencies OK"

# Check Python dependencies
echo "📋 Checking Python dependencies..."
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

if ! pip freeze | grep -q "Flask==2.3.3"; then
    echo "📦 Installing Python dependencies..."
    pip install -q -r requirements.txt
fi
echo "✅ Python dependencies OK"

# Set environment variables for local development
echo "⚙️  Setting up environment..."
export PYTHONUNBUFFERED=1
export FLASK_ENV=development
export FLASK_DEBUG=1
export GCP_PROJECT_ID=${GCP_PROJECT_ID:-strawbayscannertest}
export DATABASE_HOST=${DATABASE_HOST:-localhost}
export DATABASE_PORT=${DATABASE_PORT:-5432}
export DATABASE_USER=${DATABASE_USER:-scanner}
export DATABASE_PASSWORD=${DATABASE_PASSWORD:-scanner}
export DATABASE_NAME=${DATABASE_NAME:-invoice_scanner}
export PROCESSING_LOG_LEVEL=INFO
export WORKER_MAX_PROCESSES=5
export PROCESSING_SLEEP_TIME=0.1

echo ""
echo "🚀 Starting Processing Worker Service..."
echo "   Host: 0.0.0.0:8000"
echo "   Database: $DATABASE_HOST:$DATABASE_PORT/$DATABASE_NAME"
echo "   GCP Project: $GCP_PROJECT_ID"
echo ""
echo "⚠️  Note: Pub/Sub subscriptions will fail in local mode (expected)"
echo "   Set GCP credentials to test with real Pub/Sub:"
echo "   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json"
echo ""

# Start the service
FLASK_APP=main:app python3 -m flask run --host=0.0.0.0 --port=8000
