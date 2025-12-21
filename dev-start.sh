#!/bin/bash

# Development startup script for invoice.scanner
# Usage: ./dev-start.sh
# or:    CELERY_LOG_LEVEL=debug ./dev-start.sh

# Default log level
CELERY_LOG_LEVEL=${CELERY_LOG_LEVEL:-info}
export CELERY_LOG_LEVEL

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          INVOICE SCANNER - Development Start                   ║"
echo "║                                                                ║"
echo "║  Celery Log Level: $CELERY_LOG_LEVEL"
echo "║  API:              http://localhost:5001"
echo "║  Frontend:         http://localhost:3000"
echo "║  Processing HTTP:  http://localhost:5002"
echo "║                                                                ║"
echo "║  Tips:                                                          ║"
echo "║    In another terminal:                                         ║"
echo "║      docker-compose logs -f worker_preprocessing_1             ║"
echo "║      docker-compose logs -f processing_http                    ║"
echo "║                                                                ║"
echo "║  To stop: Press Ctrl+C                                         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

docker-compose down -v
docker system prune -af  # Städar alla unused images/containers/networks

# Start containers
echo "[1/2] Starting containers..."


docker-compose up -d db redis api processing processing_http worker_preprocessing_1 worker_preprocessing_2 worker_ocr_1 worker_llm_1 worker_extraction_1 frontend

echo ""
echo "[2/2] Containers started. Services will be ready in 10-30 seconds..."
echo ""
echo "    🟢 DB:             http://localhost:5432"
echo "    🟢 Redis:          http://localhost:6379"
echo "    🟢 API:            http://localhost:5001"
echo "    🟢 Frontend:       http://localhost:3000"
echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo "To monitor processing in real-time, in another terminal run:"
echo ""
echo "   docker-compose logs -f worker_preprocessing_1"
echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo ""
echo "Development environment is ready! 🚀"
echo ""
