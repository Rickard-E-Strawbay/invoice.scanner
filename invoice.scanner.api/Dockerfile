# Use Microsoft's official Python Dev Container base image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python dependencies
COPY requirements.txt /tmp/pip-tmp/
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/pip-tmp/requirements.txt && \
    rm -rf /tmp/pip-tmp

# Set working directory
WORKDIR /app

# Copy application code
COPY . /app

# Expose port 8080 (Cloud Run expects this by default)
EXPOSE 8080

# Start Flask app directly
# Cloud SQL Connector will handle database connection based on environment
# In Cloud Run: INSTANCE_CONNECTION_NAME env var triggers Connector mode
# Locally: DATABASE_* env vars trigger psycopg2 mode
CMD ["python", "-u", "main.py"]

