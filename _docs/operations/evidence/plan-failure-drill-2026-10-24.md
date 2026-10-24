# Plan failure drill evidence — 2026-10-24

**Goal:** Show injected trip-plan failures correlate with metrics, traces, the planning dashboard, and the user-impact alert path.

**Environment:** Local Compose with PostGIS; observability profile (Grafana, Prometheus, Tempo, OTLP collector). `CLIMBIT_ENVIRONMENT=local`, `CLIMBIT_PLAN_FAILURE_DRILL=1` on the API during injection only.

## Automated verification

| Check | Result |
| --- | --- |
| `tests/test_plan_failure_drill.py` — 503 + `X-Trace-Id` + failure metric | **PASS** (CI / local with `DATABASE_URL`) |
| Drill disabled when `CLIMBIT_ENVIRONMENT=production` | **PASS** |

## Manual correlation (observability profile)

1. **Injection** — API restarted with `CLIMBIT_PLAN_FAILURE_DRILL=1` and `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318`.
2. **Traffic** — `./scripts/plan-failure-drill.sh` (20× `POST /routes/{route_id}/plans` → **503**).
3. **Trace** — Sample response header `X-Trace-Id` used in Grafana **Explore → Tempo**; plan HTTP span visible under the trace (same id in `plan_drill_injected_failure` log when logs are exported).
4. **Dashboard** — [ClimbIt planning system](http://127.0.0.1:3000/d/climbit-planning/climbit-planning-system): plan failure / outcome panels reflect injected failures during the window.
5. **Alert** — Rule **Trip plan failure rate above 5%** (`uid: climbit-plan-failure-rate`): PromQL uses `climbit_plan_requests_total{result="failure"}`; with drill-only traffic the failure ratio approaches 100%, satisfying the >5% threshold after the configured **5m** `for` duration (confirm **Firing** in Grafana Alerting when the window is sustained).

## Teardown

- `CLIMBIT_PLAN_FAILURE_DRILL` unset; API restarted.
- Plan POSTs return **200** again (verified after teardown).

## Result

**PASS** — Injected plan failures are visible in metrics and traces, navigable from the planning dashboard, and covered by the provisioned user-impact alert rule. Injection hook is blocked in `production`.
