# Dockerfile för processing service - BASE IMAGE

FROM python:3.11-bullseye

WORKDIR /app

# Install system dependencies (non-GPU version)
RUN apt-get update && apt-get install -y \
    build-essential \
    tesseract-ocr \
    libtesseract-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    libglvnd0 \
    libglvnd-dev \
    curl \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY ./invoice.scanner.processing/requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt

# Copy application code
COPY ./invoice.scanner.processing .

# Create necessary directories
RUN mkdir -p /app/documents/raw && \
    mkdir -p /app/documents/processed && \
    mkdir -p /app/logs

# Health check - verify process is alive (works for both Celery and HTTP service)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ps aux | grep -q "[p]ython" || exit 1

# Default command - can be overridden
CMD ["python", "http_service.py"]
