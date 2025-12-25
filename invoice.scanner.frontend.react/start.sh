#!/bin/sh
# Start script for nginx - reads PORT from environment variable
# Cloud Run sets PORT=8080, default to 8080 if not set

PORT=${PORT:-8080}

# Replace PORT placeholder in nginx config
sed -i "s/listen 3000;/listen ${PORT};/" /etc/nginx/conf.d/default.conf

echo "[nginx] Starting on port $PORT"

# Start nginx in foreground
exec nginx -g "daemon off;"
