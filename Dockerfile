# Telegram Voice-to-Insight Pipeline Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uvx
RUN curl -L https://github.com/astral-sh/uv/releases/download/0.1.24/uv-installer.sh | sh && \
    uv venv

# Copy requirements first for better Docker layer caching
COPY requirements-railway.txt .

# Install Python dependencies using uvx
RUN . .venv/bin/activate && \
    uvx install -r requirements-railway.txt

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p /app/temp /app/logs /app/modes && \
    chmod -R 777 /app/temp /app/logs /app/modes && \
    chown -R nobody:nogroup /app/temp /app/logs /app/modes

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check endpoint
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD [".venv/bin/python", "main.py"] 