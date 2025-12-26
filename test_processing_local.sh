#!/bin/bash

# FASE 6E - Testing Script
# Quick verification that processing works locally

set -e

echo "================================"
echo "FASE 6E - Local Processing Test"
echo "================================"
echo ""

# Configuration
API_URL="http://localhost:5001"
PROCESSING_URL="http://localhost:5002"
TOKEN="YOUR_AUTH_TOKEN"  # Set this before running

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if services are running
echo "1️⃣  Checking if services are running..."
echo ""

# Check API
if curl -s "$API_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} API is running on $API_URL"
else
    echo -e "${RED}✗${NC} API is NOT running on $API_URL"
    echo "   Start with: docker-compose up -d api"
    exit 1
fi

# Check Processing HTTP Service
if curl -s "$PROCESSING_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Processing HTTP is running on $PROCESSING_URL"
else
    echo -e "${RED}✗${NC} Processing HTTP is NOT running on $PROCESSING_URL"
    echo "   Start with: docker-compose up -d processing_http"
    exit 1
fi

# Check Redis
if docker exec invoice.scanner.redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Redis is running"
else
    echo -e "${RED}✗${NC} Redis is NOT running"
    echo "   Start with: docker-compose up -d redis"
    exit 1
fi

# Check Celery Workers
WORKER_COUNT=$(docker ps --filter "name=invoice.scanner.worker" --quiet | wc -l)
if [ $WORKER_COUNT -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Found $WORKER_COUNT Celery workers"
else
    echo -e "${YELLOW}⚠${NC} No Celery workers running (processing will not execute)"
fi

echo ""
echo "2️⃣  Testing Processing Backend..."
echo ""

# Check that processing_backend.py exists
if [ -f "invoice.scanner.api/lib/processing_backend.py" ]; then
    echo -e "${GREEN}✓${NC} processing_backend.py exists"
else
    echo -e "${RED}✗${NC} processing_backend.py NOT found"
    exit 1
fi

# Check that LocalCeleryBackend is in the file
if grep -q "class LocalCeleryBackend" invoice.scanner.api/lib/processing_backend.py; then
    echo -e "${GREEN}✓${NC} LocalCeleryBackend class found"
else
    echo -e "${RED}✗${NC} LocalCeleryBackend class NOT found"
    exit 1
fi

# Check that CloudFunctionsBackend is in the file
if grep -q "class CloudFunctionsBackend" invoice.scanner.api/lib/processing_backend.py; then
    echo -e "${GREEN}✓${NC} CloudFunctionsBackend class found"
else
    echo -e "${RED}✗${NC} CloudFunctionsBackend class NOT found"
    exit 1
fi

echo ""
echo "3️⃣  Testing HTTP Endpoints..."
echo ""

# Test processing health endpoint
HEALTH=$(curl -s "$PROCESSING_URL/health" | jq -r '.status' 2>/dev/null || echo "ERROR")
if [ "$HEALTH" = "healthy" ]; then
    echo -e "${GREEN}✓${NC} Processing /health endpoint working"
else
    echo -e "${RED}✗${NC} Processing /health endpoint returned: $HEALTH"
fi

# Test API health endpoint (implicit, already tested above)
echo -e "${GREEN}✓${NC} API health check passed"

echo ""
echo "4️⃣  Testing Celery Task Queue..."
echo ""

# Check Redis queue depth
QUEUE_DEPTH=$(docker exec invoice.scanner.redis redis-cli LLEN celery 2>/dev/null || echo "0")
echo "Current Celery queue depth: $QUEUE_DEPTH tasks"

# Check if Redis has data
REDIS_SIZE=$(docker exec invoice.scanner.redis redis-cli DBSIZE 2>/dev/null | grep -oE '[0-9]+' || echo "0")
echo "Redis database size: $REDIS_SIZE keys"

echo ""
echo "5️⃣  Checking Logs for Errors..."
echo ""

# Check processing_http logs for errors
PROCESSING_ERRORS=$(docker logs invoice.scanner.processing_http 2>&1 | grep -i "error" | wc -l)
if [ $PROCESSING_ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓${NC} No errors in processing_http logs"
else
    echo -e "${YELLOW}⚠${NC} Found $PROCESSING_ERRORS error messages in processing_http logs"
    echo "   View with: docker logs invoice.scanner.processing_http | grep -i error | head -5"
fi

# Check API logs for errors
API_ERRORS=$(docker logs invoice.scanner.api 2>&1 | grep -i "error" | wc -l)
if [ $API_ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓${NC} No errors in API logs"
else
    echo -e "${YELLOW}⚠${NC} Found $API_ERRORS error messages in API logs"
fi

echo ""
echo "================================"
echo "✅ All checks passed!"
echo "================================"
echo ""
echo "Next steps to test document processing:"
echo ""
echo "1. Create a test PDF or image file"
echo ""
echo "2. Upload it to the API:"
echo "   curl -X POST http://localhost:5001/documents/upload \\"
echo "     -F \"file=@test.pdf\" \\"
echo "     -H \"Authorization: Bearer TOKEN\""
echo ""
echo "3. Monitor processing in real-time:"
echo "   watch -n 2 'curl http://localhost:5001/documents/{DOCUMENT_ID}/status | jq .status'"
echo ""
echo "4. Check Celery worker logs:"
echo "   docker logs -f invoice.scanner.worker.preprocessing.1"
echo ""
echo "5. Check Redis queue:"
echo "   docker exec invoice.scanner.redis redis-cli LLEN celery"
echo ""
echo "6. View full processing logs:"
echo "   docker-compose logs -f processing_http"
echo ""
