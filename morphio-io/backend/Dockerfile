# Build stage
FROM python:3.13-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory for the build stage
WORKDIR /build

# Copy project metadata and lock for dependency installation
COPY backend/pyproject.toml /build/pyproject.toml
COPY backend/uv.lock /build/uv.lock

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1

# Install system dependencies required for Playwright and tooling
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      curl \
      # Playwright runtime deps (Chromium)
      libnss3 \
      libnspr4 \
      libatk1.0-0 \
      libatk-bridge2.0-0 \
      libcups2 \
      libdrm2 \
      libdbus-1-3 \
      libxkbcommon0 \
      libxcomposite1 \
      libxdamage1 \
      libxfixes3 \
      libxrandr2 \
      libgbm1 \
      libpango-1.0-0 \
      libcairo2 \
      libasound2; \
    rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y
ENV PATH="/root/.local/bin:${PATH}"

# Upgrade pip and create venv with locked deps
RUN python -m pip install --upgrade pip \
 && echo "Installing backend project dependencies with uv..." \
 && uv venv /opt/venv \
 && UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --no-dev --frozen \
 && playwright install chromium

# Final stage
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production
ENV APP_PORT=8005
ENV UVICORN_WORKERS=4

# Admin user environment variables (set these at runtime)
ENV ADMIN_EMAIL=""
ENV ADMIN_PASSWORD=""
ENV ADMIN_NAME=""

# Set work directory for the final stage
WORKDIR /app

# Copy project files
COPY backend .
COPY backend/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create database directory
RUN mkdir -p /app/db

# Install runtime dependencies including Playwright system dependencies
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      curl \
      ffmpeg \
      libnss3 \
      libnspr4 \
      libatk1.0-0 \
      libatk-bridge2.0-0 \
      libcups2 \
      libdrm2 \
      libdbus-1-3 \
      libxkbcommon0 \
      libxcomposite1 \
      libxdamage1 \
      libxfixes3 \
      libxrandr2 \
      libgbm1 \
      libpango-1.0-0 \
      libcairo2 \
      libasound2; \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user and switch to it
RUN adduser --disabled-password --gecos '' appuser

# Copy installed dependencies and Playwright browsers from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH=/opt/venv/bin:$PATH
COPY --from=builder /root/.cache/ms-playwright /home/appuser/.cache/ms-playwright

# Set correct permissions
RUN chown -R appuser:appuser /app /home/appuser/.cache
USER appuser

# Expose the port Flask is running on
EXPOSE 8005

# Simple healthcheck probing the FastAPI health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8005/health/ || exit 1

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
