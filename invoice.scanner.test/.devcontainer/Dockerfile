# Test Container - Cloud Functions Testing Environment
# Python 3.11 with combined dependencies from cloud.functions and api

FROM python:3.11-slim

# ============================================================
# Install system dependencies
# ============================================================
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# Set environment variables
# ============================================================
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

# ============================================================
# Create working directory
# ============================================================
WORKDIR /workspace

# ============================================================
# Copy requirements
# ============================================================
COPY requirements.txt /workspace/requirements.txt

# ============================================================
# Install Python dependencies
# ============================================================
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# ============================================================
# Install debugpy for VSCode debugging
# ============================================================
RUN pip install debugpy

# ============================================================
# Create non-root user for VSCode
# ============================================================
RUN useradd -m -s /bin/bash vscode && \
    mkdir -p /home/vscode && \
    chown -R vscode:vscode /workspace

# ============================================================
# Set up git (for development)
# ============================================================
RUN git config --global --add safe.directory /workspace

# ============================================================
# Default command
# ============================================================
CMD ["/bin/bash"]
