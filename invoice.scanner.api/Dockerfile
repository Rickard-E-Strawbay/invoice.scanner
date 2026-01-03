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

# Start Flask app directly
# Cloud SQL Connector will handle database connection based on environment
# In Cloud Run: INSTANCE_CONNECTION_NAME env var triggers Connector mode
# Locally: DATABASE_* env vars trigger psycopg2 mode
CMD ["python", "-u", "main.py"]

