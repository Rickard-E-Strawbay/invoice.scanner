# Use Microsoft's official Python Dev Container base image
FROM python:3.11-slim

# Install system dependencies (including SSL for cloud-sql-python-connector)
RUN apt-get update && apt-get install -y \
    curl \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install shared package first (before WORKDIR to avoid relative path issues)
COPY invoice.scanner.shared /tmp/invoice.scanner.shared
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e /tmp/invoice.scanner.shared && \
    rm -rf /tmp/invoice.scanner.shared

# Set working directory
WORKDIR /app

# Set PYTHONPATH so Python can find modules in /app
ENV PYTHONPATH=/app

# Copy requirements and install remaining dependencies
COPY invoice.scanner.api/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt && \
    rm -rf /tmp/requirements.txt

# Copy application code
COPY invoice.scanner.api /app/

# Expose port 8080 (Cloud Run expects this by default)
EXPOSE 8080

# Start Flask app - use gunicorn for production, Flask dev server for local
# Cloud SQL Connector will handle database connection based on environment
# In Cloud Run: INSTANCE_CONNECTION_NAME env var triggers Connector mode
# Locally: DATABASE_* env vars trigger psycopg2 mode
# NOTE: Cloud Run's gunicorn wrapper only accepts --host and --port, no other flags
CMD exec sh -c 'if [ "$FLASK_ENV" = "production" ]; then exec gunicorn --host 0.0.0.0 --port ${PORT:-8080} main:app; else exec python -u main.py --port ${PORT:-8080}; fi'
