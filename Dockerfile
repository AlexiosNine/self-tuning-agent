# Multi-stage build for self-tuning agent
FROM python:3.12-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN pip install --no-cache-dir --user build && \
    pip install --no-cache-dir --user -e .

# Runtime stage
FROM python:3.12-slim

# Create non-root user
RUN useradd -m -u 1000 agent && \
    mkdir -p /app && \
    chown -R agent:agent /app

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder --chown=agent:agent /root/.local /home/agent/.local

# Copy application code
COPY --chown=agent:agent src/ ./src/
COPY --chown=agent:agent config.yaml ./
COPY --chown=agent:agent CLAUDE.md ./

# Set PATH for user-installed packages
ENV PATH=/home/agent/.local/bin:$PATH
ENV PYTHONPATH=/app

# Switch to non-root user
USER agent

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "from src.common.config import load_config; print('OK')" || exit 1

# Default command
CMD ["python", "-c", "from src.agent.runtime import AgentRuntime; print('Self-tuning agent ready')"]
