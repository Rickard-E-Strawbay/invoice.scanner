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
COPY . /app



# Expose port 8080 (Cloud Run expects this by default)
EXPOSE 8080

# Run the Flask app - Cloud Run provides PORT env var (defaults to 8080)
# App must listen on this port
CMD ["python", "-u", "main.py"]
