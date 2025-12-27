#!/bin/bash

# ============================================================
# Local Cloud Functions Server
# Runs Cloud Functions Framework locally on port 9000
# Simulates GCP Cloud Functions environment
# ============================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "🚀 Cloud Functions Framework - Local Server"
echo "=========================================="
echo ""

# Check for Python 3.11+
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11+ not found"
    echo "Please install Python 3.11 or later via Homebrew:"
    echo "  brew install python@3.11"
    exit 1
fi

# Check if dependencies are installed
if ! python3.11 -c "import functions_framework" 2>/dev/null; then
    echo "📦 Installing dependencies for Python 3.11..."
    python3.11 -m pip install -q -r "$SCRIPT_DIR/requirements.txt"
    echo "✓ Dependencies installed"
fi

echo ""
echo "Starting functions-framework on port 9000..."
echo "Target: cf_preprocess_document (main entry point)"
echo ""
echo "📍 Local URL: http://localhost:9000"
echo "📍 From Docker: http://host.docker.internal:9000"
echo ""
echo "Available functions via gcloud emulator:"
echo "  - cf_preprocess_document"
echo "  - cf_extract_ocr_text"
echo "  - cf_predict_invoice_data"
echo "  - cf_extract_structured_data"
echo "  - cf_run_automated_evaluation"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Set environment variables
export PYTHONUNBUFFERED=1
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
export DATABASE_HOST="${DATABASE_HOST:-127.0.0.1}"
export DATABASE_PORT="${DATABASE_PORT:-5432}"
export DATABASE_NAME="${DATABASE_NAME:-invoice_scanner}"
export DATABASE_USER="${DATABASE_USER:-scanner}"
export DATABASE_PASSWORD="${DATABASE_PASSWORD:-scanner}"

# Start functions-framework
cd "$SCRIPT_DIR"
python3.11 -m functions_framework \
    --target=cf_preprocess_document \
    --debug \
    --port=9000 \
    --source=main.py

