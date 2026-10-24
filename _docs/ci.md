# Continuous integration

Pull requests run [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). The workflow validates the change set and builds container images; it does **not** deploy.

## Jobs

| Job | Purpose |
| --- | --- |
| `backend-lint` | `ruff check` and `ruff format --check` in `backend/` |
| `backend-unit` | Pytest tests that do not need PostgreSQL |
| `backend-integration` | Pytest integration tests against PostGIS |
| `backend-contract` | Committed OpenAPI export, Redocly lint, pytest contract tests |
| `frontend` | oxlint, Vitest, production build |
| `image-build` | `docker build` for the API and `docker compose build api` |
| `security-scan` | `pip-audit` on locked dependencies and Trivy on the API image |

Integration and contract jobs set `DATABASE_URL=postgresql://climbit:climbit@127.0.0.1:5432/climbit` and wait for the PostGIS service container.

Pytest marks `integration` and `contract` are applied in `backend/tests/conftest.py` (module-level `DATABASE_URL` skip fixtures and `test_openapi_contract.py`).

## Run checks locally

From the repository root:

```bash
cd backend && uv run ruff check . && uv run ruff format --check .
cd backend && uv run pytest -m "not integration and not contract"
cd backend && DATABASE_URL=postgresql://climbit:climbit@127.0.0.1:5432/climbit uv run pytest -m integration
cd backend && uv run python -m app.export_openapi && git diff --exit-code ../contracts/openapi.json
cd frontend && npm ci && npm run lint && npm run test && npm run build
docker build -t climbit-api:ci -f backend/Dockerfile backend
docker compose build api
```

Start PostGIS locally with `docker compose up -d db` when running integration or contract tests.

## Reading a failing check (example)

When a job fails, open the pull request **Checks** tab and expand the red job. The log shows which step failed and the command output.

**Example — `backend-lint` after an unformatted file**

A contributor edits Python but does not run the formatter. CI runs:

```text
uv run --frozen ruff format --check .
```

GitHub Actions log (excerpt):

```text
Run uv run --frozen ruff format --check .
Would reformat: app/planning/service.py
1 file would be reformatted, 42 files already formatted
Error: Process completed with exit code 1.
```

What to do:

1. Note the job name (`backend-lint`) and the failing step (`Ruff check and format`).
2. Reproduce locally: `cd backend && uv run ruff format app/planning/service.py` (or format the whole tree), then `uv run ruff check .`.
3. Push the fix; all jobs re-run on the new commit.

Other jobs fail the same way: the step name maps to a script block in `ci.yml`, and the log ends with a non-zero exit code. Security scans (`security-scan`) fail when `pip-audit` or Trivy reports CRITICAL/HIGH library vulnerabilities on the API image.
