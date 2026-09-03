FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev


FROM python:3.12-slim

RUN useradd --create-home --uid 1000 overleaf-mcp
WORKDIR /app

COPY --from=builder --chown=overleaf-mcp:overleaf-mcp /app/.venv /app/.venv
COPY --from=builder --chown=overleaf-mcp:overleaf-mcp /app/src /app/src
COPY README.md /app/README.md
COPY LICENSE /app/LICENSE

ENV PATH="/app/.venv/bin:$PATH"

USER overleaf-mcp

# Only used for --http; ignored for the default stdio transport.
EXPOSE 8000

ENTRYPOINT ["overleaf-mcp"]
