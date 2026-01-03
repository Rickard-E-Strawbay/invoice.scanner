# Processing Worker Service - Cloud Run Image
# Handles Pub/Sub-triggered document processing with parallel workers

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy shared module and application files
COPY invoice.scanner.shared ./shared
COPY invoice.scanner.processing/requirements.txt .
COPY invoice.scanner.processing/main.py .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for security
RUN useradd -m -u 1000 scanner && chown -R scanner:scanner /app
USER scanner

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:${PORT:-8080}/health')" || exit 1

# Start application
# Cloud Run expects container to listen on port 8080 (set via PORT env var)
EXPOSE 8080
CMD sh -c 'gunicorn --bind 0.0.0.0:8080 --workers 1 --threads 4 --worker-class gthread --timeout 0 --access-logfile - --error-logfile - main:app'
