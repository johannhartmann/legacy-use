# MCP Server for Legacy-Use - Optimized build
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy dependency files
COPY mcp-server/pyproject.toml mcp-server/README.md ./

# Create virtual environment and install dependencies  
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --compile-bytecode

# Copy source code and install project
COPY mcp-server/src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --compile-bytecode

# Final stage - minimal runtime
FROM python:3.12-slim-bookworm

# Install only runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 mcpuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=mcpuser:mcpuser /app/.venv /app/.venv
COPY --from=builder --chown=mcpuser:mcpuser /app/src /app/src

USER mcpuser

# Set Python path
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Environment variables
ENV DATABASE_URL=""
ENV LEGACY_USE_URL="http://legacy-use-backend:8080"
ENV LEGACY_USE_API_KEY=""
ENV LOG_LEVEL="INFO"
ENV SYNC_INTERVAL="30"
ENV MCP_SERVER_HOST="0.0.0.0"
ENV MCP_SERVER_PORT="3000"
ENV MCP_SERVER_PATH="/mcp"

# Expose MCP server port
EXPOSE 3000

CMD ["python", "-m", "src"]