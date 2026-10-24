# Plan-request failure drill

Use this drill in **non-production** environments (`CLIMBIT_ENVIRONMENT` not `production`) to verify the **user-impact alert**, **traces**, and **planning dashboard** line up when trip-plan POST requests fail.

## Injection hook

Set on the API container:

```bash
CLIMBIT_PLAN_FAILURE_DRILL=1
CLIMBIT_ENVIRONMENT=local   # or dev, staging — never production
```

While enabled, `POST /routes/{route_id}/plans` returns **503** before planning runs. Responses include **`X-Trace-Id`**, and logs emit `plan_drill_injected_failure` with the same trace id. Plan outcome metrics record `result=failure` (`climbit_plan_requests_total` in Prometheus).

**Always unset the drill when finished:**

```bash
CLIMBIT_PLAN_FAILURE_DRILL=
```

Restart or redeploy the API so the variable is cleared.

## Prerequisites

Observability profile running (see [`observability/README.md`](../../observability/README.md)):

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability up -d --build
```

API export:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
```

## Drill steps

1. **Enable injection** — set `CLIMBIT_PLAN_FAILURE_DRILL=1` on the API and restart.
2. **Generate failing plan traffic** — run `./scripts/plan-failure-drill.sh` or POST several plan requests manually.
3. **Dashboard** — open Grafana → **ClimbIt planning system** (`http://127.0.0.1:3000/d/climbit-planning/climbit-planning-system`). Confirm rising plan failure rate / failed requests.
4. **Trace** — copy `X-Trace-Id` from a 503 response; in Grafana **Explore → Tempo**, search by trace id and confirm `plan.build` (or the plan HTTP span) is present.
5. **Alert** — Grafana → **Alerting** → rule **Trip plan failure rate above 5%** (`climbit-plan-failure-rate`). After sustained failures (>5% for 5 minutes), state should move to **Firing** with annotations: `service`, `environment`, `version`, `owner`, `dashboard_url`.
6. **Teardown** — unset `CLIMBIT_PLAN_FAILURE_DRILL`, restart the API, confirm plans return **200** again.

Prometheus check (optional):

```promql
sum(rate(climbit_plan_requests_total{result="failure"}[5m]))
/
clamp_min(sum(rate(climbit_plan_requests_total[5m])), 1e-9)
```

## Evidence

Latest recorded drill: [`evidence/plan-failure-drill-2026-10-24.md`](evidence/plan-failure-drill-2026-10-24.md).

Automated checks (no injection unless env is set in the test):

```bash
cd backend
DATABASE_URL=postgresql://climbit:climbit@127.0.0.1:5432/climbit uv run pytest tests/test_plan_failure_drill.py -v
```
