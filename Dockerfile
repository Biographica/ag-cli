FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src/ src/

# Install with configurable extras (default: biology)
ARG EXTRAS="biology"
RUN uv sync --extra $EXTRAS

# Create data directory for persistent downloads
RUN mkdir -p /root/.ct/data

VOLUME /root/.ct/data

ENTRYPOINT ["uv", "run", "ct"]
