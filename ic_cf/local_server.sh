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

# Determine which Python version to use (3.11+ preferred, but 3.9+ works)
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "❌ Python 3.9+ not found"
    exit 1
fi

echo "Using Python: $($PYTHON_CMD --version)"
echo ""

# Install dependencies if needed
echo "📦 Installing dependencies..."
$PYTHON_CMD -m pip install -q -r "$SCRIPT_DIR/requirements.txt" 2>/dev/null || true
echo "✓ Dependencies ready"

# Set environment variables (match docker-compose.yml for local dev)
export PYTHONUNBUFFERED=1
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
export PYTHONPATH="$(cd "$SCRIPT_DIR/../" && pwd):$PYTHONPATH"
export ENVIRONMENT=local
export DATABASE_HOST="${DATABASE_HOST:-127.0.0.1}"
export DATABASE_PORT="${DATABASE_PORT:-5432}"
export DATABASE_NAME="${DATABASE_NAME:-invoice_scanner}"
export DATABASE_USER="${DATABASE_USER:-scanner_local}"
export DATABASE_PASSWORD="${DATABASE_PASSWORD:-scanner_local}"

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

# Start functions-framework
cd "$SCRIPT_DIR"
$PYTHON_CMD -m functions_framework \
    --target=cf_preprocess_document \
    --debug \
    --port=9000 \
    --source=main.py

