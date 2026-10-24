# ClimbIt

Alpine trip planning: routes, weather, transit, gear, and explainable safety recommendations.

## Quick start

From the repository root:

```powershell
docker compose up -d --build
```

- API: http://127.0.0.1:8000 (`GET /health`, `GET /ready`)
- Frontend: http://127.0.0.1:5173
- PostGIS: `127.0.0.1:5432`

Load seed routes (optional):

```powershell
cd backend
$env:DATABASE_URL="postgresql://climbit:climbit@127.0.0.1:5432/climbit"
uv run python -m app.seed
```

Observability profile (Grafana, alerts, on-call worker):

```powershell
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability up -d
```

## Documentation

| Topic | Link |
| --- | --- |
| Product specification | [`_docs/specs.md`](_docs/specs.md) |
| Public task tracker | [GitHub Issues](https://github.com/Franky007Bond/ClimbIt/issues) |
| Agent entry point | [`AGENTS.MD`](AGENTS.MD) |
| Course / peer review | [`_docs/course-evidence.md`](_docs/course-evidence.md) |
| Agent evidence index | [`_docs/evidence/README.md`](_docs/evidence/README.md) |
| Deployment & rollback | [`_docs/operations/deployment.md`](_docs/operations/deployment.md) |
| Deploy rollback evidence | [`_docs/operations/evidence/deploy-rollback-2026-10-24.md`](_docs/operations/evidence/deploy-rollback-2026-10-24.md) |
| CI | [`_docs/ci.md`](_docs/ci.md) |

## Backend

From `backend/`:

```powershell
uv run pytest
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Frontend

From `frontend/`:

```powershell
npm run dev
```
