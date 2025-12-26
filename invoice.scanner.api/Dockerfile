# Use Microsoft's official Python Dev Container base image
FROM python:3.11-slim

# Install system dependencies including Cloud SQL Proxy
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Download and install Cloud SQL Proxy
RUN curl -o /cloud-sql-proxy https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 && \
    chmod +x /cloud-sql-proxy

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

# Start Cloud SQL Proxy in background, then start Flask app
# Cloud SQL Proxy will listen on Unix socket and create it at /cloudsql/
# INSTANCE_CONNECTION_NAME env var must be set (e.g., "project:region:instance")
CMD ["/bin/sh", "-c", "/cloud-sql-proxy ${INSTANCE_CONNECTION_NAME} --unix-socket-path /cloudsql & python -u main.py"]

