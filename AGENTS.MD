ClimbIt is a web app for planning Klettersteig, alpine hiking, and selected outdoor climbing trips. It combines route discovery, route-type-specific difficulty information, weather and hazard inputs, public-transport journey planning with a last-return check, deterministic gear guidance, and an explainable planning recommendation.

Documents

- `_docs/process.md` - how work is organized
- `_docs/ci.md` - pull-request CI jobs and reading failed checks

Commands

- `docker compose up -d --build` - start the API and PostGIS from the
  repository root. The database service is named `db`. Compose applies
  pending migrations on start
- `uv sync` - install dependencies
- `uv run pytest` - the whole suite. The tests that read a built asset build it
  first, once per session, so a fresh checkout does not have to remember the npm
  commands below; a build that does not produce its file fails the run, naming
  the command to rerun
- `uv run pytest tests/test_home.py` - one test file
- `uv run ruff check . && uv run ruff format --check .` - lint and format check,
  run it before committing
- `uv run alembic upgrade head` - apply pending migrations from `backend/`
- `uv run alembic check` - confirm the database schema matches SQLAlchemy
  metadata, from `backend/`
- `uv run alembic heads` - print the migration head(s) from `backend/`
- `uv run python -m app.seed` - load the six fixture routes from `backend/`. Requires `DATABASE_URL`. Compose does not load seed data automatically. Example host URL for the published Compose port: `postgresql://climbit:climbit@127.0.0.1:5432/climbit`
- `uv run python -m app.import_osm --manifest <path>` - import OpenStreetMap routes into quarantine from a JSON manifest (`backend/tests/fixtures/osm/manifest.json` is an example). Requires `DATABASE_URL`; optional `OVERPASS_API_URL` and `OVERPASS_MIN_INTERVAL_SECONDS`
- `uv run python -m app.export_openapi` - from `backend/`, write `contracts/openapi.json` from the FastAPI schema
- `npm run generate:api` - from `frontend/`, regenerate `src/api/generated/` from `contracts/openapi.json` (run export first when the API changes)
- `npm install` - the build-time toolchain:  Vite

Rules

- Layout: a `backend/` app and a `frontend/` app.
- Backend: Python 3.14, uv, `fastapi[standard]`, import path `app.main:app`, tests with `uv run pytest` from `backend/`.
- Frontend: Node.js 22, npm, the Vite React TypeScript app, and `package-lock.json`.