FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

RUN useradd --create-home --user-group app

WORKDIR /app

COPY --chown=app:app pyproject.toml uv.lock ./
COPY --chown=app:app app ./app
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app entrypoint.py ./entrypoint.py

RUN chown app:app /app

USER app

RUN uv sync --frozen --no-dev --no-cache

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["python", "/app/entrypoint.py"]
