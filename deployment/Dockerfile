# MAGNET Ship Design Validation System
# Multi-stage Docker build
# BRAVO OWNS THIS FILE.

# =============================================================================
# Builder Stage
# =============================================================================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# =============================================================================
# Production Stage
# =============================================================================
FROM python:3.11-slim AS production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create storage directories
RUN mkdir -p /app/data/designs \
             /app/data/reports \
             /app/data/snapshots \
             /app/data/exports \
             /app/data/temp

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MAGNET_ENVIRONMENT=production \
    MAGNET_STORAGE_DIR=/app/data

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: run API server
CMD ["python", "-m", "magnet.bootstrap.entrypoints", "api"]

# =============================================================================
# Development Stage
# =============================================================================
FROM production AS development

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    flake8 \
    mypy

# Set development environment
ENV MAGNET_ENVIRONMENT=development \
    MAGNET_DEBUG=true

# =============================================================================
# Worker Stage
# =============================================================================
FROM production AS worker

# Override command to run worker
CMD ["python", "-m", "magnet.bootstrap.entrypoints", "worker"]

# =============================================================================
# CLI Stage
# =============================================================================
FROM production AS cli

# Set entrypoint for CLI
ENTRYPOINT ["python", "-m", "magnet.bootstrap.entrypoints", "cli"]
