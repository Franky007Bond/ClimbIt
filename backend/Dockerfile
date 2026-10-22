FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

RUN useradd --create-home --user-group app

WORKDIR /app

COPY --chown=app:app pyproject.toml uv.lock ./
COPY --chown=app:app app ./app

RUN chown app:app /app

USER app

RUN uv sync --frozen --no-dev --no-cache

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT []
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
