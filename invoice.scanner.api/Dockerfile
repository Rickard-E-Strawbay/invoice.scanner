# Use Microsoft's official Python Dev Container base image
FROM mcr.microsoft.com/devcontainers/python:3.11

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install Python dependencies
COPY requirements.txt /tmp/pip-tmp/
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/pip-tmp/requirements.txt && \
    rm -rf /tmp/pip-tmp

# Install Playwright browsers
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN pip install playwright && playwright install --with-deps

# Set working directory
WORKDIR /app
COPY . /app

USER root
RUN mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix
USER vscode

# Expose port 5000
EXPOSE 5000

# Run the Flask app med debugpy och vänta på klient
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "main.py", "--host", "0.0.0.0", "--port", "8000"]
