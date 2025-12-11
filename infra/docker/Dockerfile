# Build stage
FROM python:3.14-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package installation
RUN pip install --no-cache-dir uv

# Copy project files needed for installation
COPY pyproject.toml ./
COPY src/ ./src/

# Create virtual environment and install the package
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
RUN uv pip install .

# Production stage
FROM python:3.14-slim AS production

WORKDIR /app

# Install curl for healthcheck and create non-root user
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r mcp && useradd -r -g mcp mcp

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY src/ ./src/
COPY pyproject.toml ./

# Create data directory for state persistence
RUN mkdir -p /data/mattermost-mcp && chown -R mcp:mcp /data /app

# Switch to non-root user
USER mcp

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HTTP_PORT=8000
ENV LOG_FORMAT=json
ENV LOG_LEVEL=INFO
ENV MONITORING_STATE_PATH=/data/mattermost-mcp/monitor-state.json

# Expose HTTP port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start server
CMD ["python", "-m", "mattermost_mcp.main"]
