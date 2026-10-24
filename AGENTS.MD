ClimbIt is a web app for planning Klettersteig, alpine hiking, and selected outdoor climbing trips. It combines route discovery, route-type-specific difficulty information, weather and hazard inputs, public-transport journey planning with a last-return check, deterministic gear guidance, and an explainable planning recommendation.

Documents

- `_docs/specs.md` - product scope and architecture
- `_docs/process.md` - how work is organized
- `_docs/ci.md` - pull-request CI jobs and reading failed checks
- `_docs/course-evidence.md` - course tracker, peer review, rubric links
- `_docs/agent/workflow.md` - agent lifecycle
- `_docs/agent/team-roles.md` - PM, engineer, QA, orchestrator
- `_docs/agent/source-onboarding.md` - new regions and integrations
- `_docs/agent/route-data-review.md` - quarantine and maintainer review
- `_docs/agent/operations.md` - drills, deploy, security index
- `_docs/agent/permissions.md` - what agents may read and run
- `_docs/operations/backup-restore.md` - EU database backup destination and restore procedure
- `_docs/operations/plan-failure-drill.md` - inject plan failures and correlate alert, trace, dashboard
- `_docs/operations/oncall-responder.md` - isolated on-call worker, cooldown, evidence handoff
- `_docs/operations/deployment.md` - dev auto-deploy, manual prod, rollback
- `_docs/security/threat-model.md` - abuse cases and mitigations

Safety-critical files (require tests in the same change)

- `backend/app/data/difficulty_mappings.json`
- `backend/app/planning/recommendation.py`, `thunderstorm.py`, `gear.py`
- `backend/app/domain/difficulty.py`

Run `python scripts/check-safety-logic-coupling.py origin/main` before opening a PR that touches those paths.

Read-only agent MCP (write disabled by default)

```powershell
cd backend
uv run python -m app.agent_mcp
```

Set `CLIMBIT_MCP_WRITE_ENABLED=1` only in isolated experiments; default is read-only.

Commands

- `docker compose up -d --build` - start PostGIS, API, and frontend from the repository root. The database service is named `db`. Compose applies pending migrations on start. Frontend: http://127.0.0.1:5173
- `docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability up -d` - add Grafana, Prometheus, Tempo, Loki, and the on-call worker
- `uv sync` - install dependencies
- `uv run pytest` - the whole suite. The tests that read a built asset build it first, once per session, so a fresh checkout does not have to remember the npm commands below; a build that does not produce its file fails the run, naming the command to rerun
- `uv run pytest tests/test_home.py` - one test file
- `uv run ruff check . && uv run ruff format --check .` - lint and format check, run it before committing
- `uv run alembic upgrade head` - apply pending migrations from `backend/`
- `uv run alembic check` - confirm the database schema matches SQLAlchemy metadata, from `backend/`
- `uv run alembic heads` - print the migration head(s) from `backend/`
- `uv run python -m app.seed` - load the six fixture routes from `backend/`. Requires `DATABASE_URL`. Compose does not load seed data automatically. Example host URL for the published Compose port: `postgresql://climbit:climbit@127.0.0.1:5432/climbit`
- `uv run python -m app.import_osm --manifest <path>` - import OpenStreetMap routes into quarantine from a JSON manifest (`backend/tests/fixtures/osm/manifest.json` is an example). Requires `DATABASE_URL`; optional `OVERPASS_API_URL` and `OVERPASS_MIN_INTERVAL_SECONDS`
- `uv run python -m app.export_openapi` - from `backend/`, write `contracts/openapi.json` from the FastAPI schema
- `npm run generate:api` - from `frontend/`, regenerate `src/api/generated/` from `contracts/openapi.json` (run export first when the API changes)
- `npm install` - the build-time toolchain: Vite

Rules

- Layout: a `backend/` app and a `frontend/` app.
- Backend: Python 3.14, uv, `fastapi[standard]`, import path `app.main:app`, tests with `uv run pytest` from `backend/`.
- Frontend: Node.js 22, npm, the Vite React TypeScript app, and `package-lock.json`.
