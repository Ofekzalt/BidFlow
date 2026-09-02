FROM python:3.12-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.7.12 /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV PYTHONPATH=/app/src
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev
COPY src src
COPY alembic alembic
COPY alembic.ini ./
COPY docker-entrypoint.sh ./
RUN uv sync --frozen --no-dev && chmod +x docker-entrypoint.sh
EXPOSE 8002
ENTRYPOINT ["./docker-entrypoint.sh"]
