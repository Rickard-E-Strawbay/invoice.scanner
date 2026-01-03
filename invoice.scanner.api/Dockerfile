# Use Microsoft's official Python Dev Container base image
FROM python:3.11-slim

# Install system dependencies (including SSL for cloud-sql-python-connector)
RUN apt-get update && apt-get install -y \
    curl \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY invoice.scanner.api/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt && \
    rm -rf /tmp/requirements.txt

# Copy shared module and application code
COPY invoice.scanner.shared /app/shared
COPY invoice.scanner.api /app

# Expose port 8080 (Cloud Run expects this by default)
EXPOSE 8080

# Start Flask app via gunicorn for production, or directly for local dev
# Cloud SQL Connector will handle database connection based on environment
# In Cloud Run: INSTANCE_CONNECTION_NAME env var triggers Connector mode
# Locally: DATABASE_* env vars trigger psycopg2 mode
CMD sh -c 'if [ "$FLASK_ENV" = "production" ]; then gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 4 --threads 2 --worker-class gthread --timeout 120 --access-logfile - --error-logfile - main:app; else python -u main.py --port ${PORT:-8080}; fi'

