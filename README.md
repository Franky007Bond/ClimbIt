# ClimbIt

Alpine trip planning: routes, weather, transit, gear, and explainable safety recommendations.

## Problem

Alpine outings (Klettersteig, high routes, and selected crags) need more than a map pin: season, difficulty, weather, hazards, public transport, gear, and daylight all affect whether a day is reasonable. ClimbIt is a full-stack web app that turns a chosen route and date into an **explainable** plan with per-component status (ok, degraded, or unknown), not a single opaque score. It assists planning; it does not replace official warnings or on-mountain judgment.

This repository is the [AI Dev Tools Zoomcamp](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp) capstone. The criteria are defined in the [course project README](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/project/README.md). The bullets below describe what the system does and where those requirements are met in this repo (no separate rubric table—see also [`_docs/course-evidence.md`](_docs/course-evidence.md) for evidence links).

## What ClimbIt does

- **Route discovery** — Browse and filter published routes on a map and list (region, type, difficulty, season, transit accessibility). Covers the end-to-end **Application** criterion: React frontend, FastAPI backend, and PostGIS persistence wired through a shared OpenAPI contract.
- **Route detail** — Trailhead map, elevation profile, difficulty and season metadata, official links, and a shortcut into trip planning for that route.
- **Trip planner and assessment** — For a route ID, plan date, and coarse origin, build a plan with weather, closure/hazard inputs, gear guidance, transit summary, daylight hints, recommendation (green / yellow / red / unknown), confidence, and a written explanation plus safety disclaimer. Partial integration failures surface as component status instead of silent “all clear.”
- **Instrumented planning journey** — Plan requests emit correlated structured logs, metrics, and traces (shared trace ID, redacted sensitive fields). Supports the **Observability** criterion; local stack and dashboards are documented in [`observability/README.md`](observability/README.md).
- **My Trips** — Save a plan run to a private list in this browser (capability cookie, no login), re-evaluate against fresh data, delete, or create a read-only share link for one pinned run. Same **Application** flow end to end.
- **Route wiki and maintainer review** — Community descriptive edits and protected fields that affect planning go through revision review; operator sign-in is separate from anonymous trip capabilities.
- **Product specification** — Scope, data model, and acceptance-oriented behavior are written in [`_docs/specs.md`](_docs/specs.md). Work is tracked in the public [GitHub Issues](https://github.com/Franky007Bond/ClimbIt/issues) backlog with groomed acceptance criteria (course **Product specification**).
- **Agent team and process** — How PM, engineer, QA, and orchestrator roles collaborate is defined in [`_docs/process.md`](_docs/process.md) and [`_docs/agent/team-roles.md`](_docs/agent/team-roles.md) (**Agent team specification**).
- **Context for coding agents** — [`AGENTS.MD`](AGENTS.MD) is the entry point and links modular docs (process, operations, security, integrations) (**Context management**).
- **Testing** — Backend unit and integration tests (`uv run pytest` from `backend/`), frontend tests (Vitest), and CI that runs them on pull requests (**Testing** and **CI/CD**).
- **Containerization** — API, frontend, and database run together with `docker compose up -d --build` from the repo root; migrations apply on start (**Containerization** and local **Application**).
- **Deployment and demo** — Dev/prod Compose deployment, rollback procedure, and recorded drills are in [`_docs/operations/deployment.md`](_docs/operations/deployment.md). A friend-ready walkthrough lives in [`_docs/demo-flow.md`](_docs/demo-flow.md) (**Deployment**).
- **CI/CD** — GitHub Actions run tests on PRs; dev deploys from `main`; production is a manual workflow with rollback evidence (**CI/CD**).
- **Alerting on user impact** — Grafana alert on elevated trip-plan failure rate (planning SLO, not CPU), with drill steps in [`_docs/operations/plan-failure-drill.md`](_docs/operations/plan-failure-drill.md) (**Alerting on user impact**).
- **On-call responder agent** — Isolated worker wakes on firing alerts, investigates with read-only repo tools, and records evidence without auto-merging or prod writes; see [`_docs/operations/oncall-responder.md`](_docs/operations/oncall-responder.md) (**On-call agent**).

Peer review of three other course projects is required to pass the course itself; deadlines are on the [course platform](https://courses.datatalks.club/ai-dev-tools-2026/), not in this repo.

## Screenshots

![Screenshot Explore Routes](./assets/Explore_Routes.png) 
*Figure 1: Explore Routes.*

![Screenshot Route Details](./assets/Route_Details.png)
*Figure 2: Route Details.*

![Screenshot Trip Planner](./assets/Trip_Planner.png)
*Figure 3: Trip Planner.*

![Screenshot Grafana Dashboard](./assets/Grafana_Dashboard.png)
*Figure 4: Grafana Dashboard*

## Quick start

From the repository root:

```powershell
docker compose up -d --build
```

- API: http://127.0.0.1:8000 (`GET /health`, `GET /ready`)
- Frontend: http://127.0.0.1:5173
- PostGIS: `127.0.0.1:5432`

**Live demo for friends:** step-by-step walkthrough in [`_docs/demo-flow.md`](_docs/demo-flow.md).

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
