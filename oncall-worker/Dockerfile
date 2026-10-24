FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /worker

COPY pyproject.toml ./
COPY oncall_worker ./oncall_worker

RUN uv sync --no-dev --no-cache

ENV PATH="/worker/.venv/bin:$PATH"

CMD ["python", "-m", "oncall_worker"]
