# Dockerfile.ml - GPU-OPTIMIZED OCR WORKER

# CUDA base image för GPU support
# Obs: Denna är större (ca 3GB) men 10x snabbare för OCR
FROM nvidia/cuda:12.1.1-devel-ubuntu22.04

WORKDIR /app

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    python3-dev \
    build-essential \
    tesseract-ocr \
    libtesseract-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create Python symlinks
RUN ln -s /usr/bin/python3.11 /usr/bin/python && \
    ln -s /usr/bin/python3.11 /usr/bin/python3

# Upgrade pip
RUN python -m pip install --upgrade pip setuptools wheel

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
# PyTorch with CUDA support
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install project requirements
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/documents/raw && \
    mkdir -p /app/documents/processed && \
    mkdir -p /app/logs

# Set environment variables for GPU
ENV PADDLE_DEVICE=gpu
ENV CUDA_VISIBLE_DEVICES=0

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:6379/ping || exit 1

# Start OCR worker with GPU support
CMD ["celery", "-A", "tasks.celery_app", "worker", "-Q", "ocr", "-l", "info", "-c", "2", "--hostname=ocr-gpu@%h"]
