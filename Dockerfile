# Wormhole Tools Docker Image
# Multi-stage build for smaller final image

# Build stage
FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/

# Install the package
RUN pip install --no-cache-dir build && \
    python -m build --wheel && \
    pip install --no-cache-dir dist/*.whl

# Runtime stage
FROM python:3.12-slim

LABEL maintainer="Wormhole Tools <wormhole-tools@example.com>"
LABEL description="Wormhole network tools - NAT-traversing networking utilities"
LABEL version="0.5.0"

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/wh /usr/local/bin/wh

# Create non-root user
RUN useradd -m -s /bin/bash wormhole && \
    mkdir -p /home/wormhole/.wh && \
    chown -R wormhole:wormhole /home/wormhole

USER wormhole
WORKDIR /home/wormhole

# Default environment variables
ENV WH_RELAY="wss://relay.magic-wormhole.io/v1"
ENV WH_TRANSIT="tcp:transit.magic-wormhole.io:4001"

# Expose daemon port
EXPOSE 9475

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wh daemon status || exit 1

# Default command
ENTRYPOINT ["wh"]
CMD ["--help"]
