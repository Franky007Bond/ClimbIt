# Agent permissions

## May read

- All product and process docs under `_docs/`, root `AGENTS.md`, OpenAPI spec, and non-secret configuration in `.env.example`.
- Application source in `backend/` and `frontend/`.
- Telemetry dashboards and traces in local Grafana (observability profile)—no customer coordinates or secrets in exports.

## May run (local / CI)

- `docker compose up`, `uv run pytest`, frontend `npm run test`, linters, migrations against disposable databases.
- Documented drills (`scripts/plan-failure-drill.sh`, backup/restore scripts) in non-production only.
- Read-only MCP tools (see below)—**write tools disabled**.

## Must not

- Merge or deploy without human approval (except orchestrator closing groomed issues after QA PASS).
- Change difficulty mappings or recommendation rules without paired test updates (enforced by `scripts/check-safety-logic-coupling.py`).
- Store secrets in the repository, logs, traces, or evidence files.
- Fetch user-supplied URLs or disable redaction in the OpenTelemetry Collector.

## Read-only MCP

Start from `backend/`:

```bash
uv run python -m app.agent_mcp
```

Tools: search routes, get route, get plan snapshot fields, list gear rules version, describe transit adapter mode. **No write tools** unless `CLIMBIT_MCP_WRITE_ENABLED=1` (default off).
