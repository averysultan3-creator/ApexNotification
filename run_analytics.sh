#!/usr/bin/env bash
# run_analytics.sh — start the analytics HTTP server on Linux/Mac
# Place this file in the ApexNotification directory and run:
#   chmod +x run_analytics.sh && ./run_analytics.sh

set -e
cd "$(dirname "$0")"

# Load .env if present
[ -f .env ] && export $(grep -v '^#' .env | xargs)

ANALYTICS_PORT=${ANALYTICS_PORT:-8080}
ANALYTICS_HOST=${ANALYTICS_HOST:-0.0.0.0}

echo "=== ApexNotification Analytics Server ==="
echo "Listening on ${ANALYTICS_HOST}:${ANALYTICS_PORT}"
echo "Database: ${DATABASE_URL:-leadform_hub.db}"
echo ""

exec python analytics_server.py --host "$ANALYTICS_HOST" --port "$ANALYTICS_PORT"
