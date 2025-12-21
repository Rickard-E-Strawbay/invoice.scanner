#!/bin/bash

# Live monitoring script for processing tasks
# Usage: ./dev-monitor.sh
# or:    ./dev-monitor.sh debug

LOG_LEVEL=${1:-info}

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          INVOICE SCANNER - Live Task Monitor                   ║"
echo "║                                                                ║"
echo "║  Log Level: $LOG_LEVEL"
echo "║  Monitoring: Preprocessing Worker + HTTP Service + API         ║"
echo "║                                                                ║"
echo "║  To stop: Press Ctrl+C                                         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")" || exit 1

# Show which log level is set
echo "Current environment:"
echo "  CELERY_LOG_LEVEL: ${CELERY_LOG_LEVEL:-not set, will use default}"
echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo ""

# Function to color output
format_logs() {
    while IFS= read -r line; do
        if [[ "$line" == *"ERROR"* ]] || [[ "$line" == *"error"* ]]; then
            echo "🔴 $line"
        elif [[ "$line" == *"[Received task"* ]]; then
            echo "📨 $line"
        elif [[ "$line" == *"SUCCESS"* ]] || [[ "$line" == *"success"* ]] || [[ "$line" == *"successfully"* ]]; then
            echo "✅ $line"
        elif [[ "$line" == *"PROCESSING"* ]] || [[ "$line" == *"processing"* ]]; then
            echo "⚙️  $line"
        elif [[ "$line" == *"RETRY"* ]] || [[ "$line" == *"retrying"* ]]; then
            echo "🔄 $line"
        else
            echo "   $line"
        fi
    done
}

# Run logs with filtering
docker-compose logs -f \
  --tail=50 \
  worker_preprocessing_1 \
  processing_http \
  api \
  2>&1 | grep -v "pidbox\|security\|WARNING\|disable this\|^--" | format_logs
