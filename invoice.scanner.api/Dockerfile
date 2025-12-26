# Use Microsoft's official Python Dev Container base image
FROM python:3.11-slim

# Install system dependencies including Cloud SQL Auth Proxy v2
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download and install Cloud SQL Auth Proxy v2 (latest stable)
RUN curl -fsSL https://dl.google.com/cloudsql/cloud-sql-proxy.linux.amd64 -o /cloud-sql-proxy && \
    chmod +x /cloud-sql-proxy && \
    /cloud-sql-proxy --version 2>&1 | head -1

# Upgrade pip and install Python dependencies
COPY requirements.txt /tmp/pip-tmp/
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/pip-tmp/requirements.txt && \
    rm -rf /tmp/pip-tmp

# Set working directory
WORKDIR /app
COPY . /app

# Create socket directory for Cloud SQL Proxy
RUN mkdir -p /cloudsql

# Expose port 8080 (Cloud Run expects this by default)
EXPOSE 8080

# Start Cloud SQL Auth Proxy v2 in background, then start Flask app
# Cloud SQL Auth Proxy v2 uses IAM authentication (no password needed)
# Listens on Unix socket at /cloudsql/
# INSTANCE_CONNECTION_NAME env var must be set (e.g., "project:region:instance")
CMD ["/bin/sh", "-c", "(/cloud-sql-proxy ${INSTANCE_CONNECTION_NAME} --unix-socket-dir=/cloudsql &) && sleep 3 && python -u main.py"]

