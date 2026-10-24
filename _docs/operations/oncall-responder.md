# Isolated on-call responder

Spec section 7: the **oncall-worker** polls Grafana for firing alerts, deduplicates by **fingerprint**, and runs at most **one session per cooldown** (default **900 s**).

## Compose

With the observability profile:

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability up -d
```

The `oncall-worker` service mounts the repository read/write at `/repo` so it can write evidence under `_docs/operations/evidence/`.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `ONCALL_GRAFANA_URL` | `http://grafana:3000` | Grafana base URL |
| `ONCALL_GRAFANA_TOKEN` | (empty) | Optional service account token |
| `ONCALL_REPO_PATH` | `/repo` | Repository root for tests and evidence |
| `ONCALL_POLL_INTERVAL_SECONDS` | `60` | Poll interval |
| `ONCALL_COOLDOWN_SECONDS` | `900` | Fingerprint cooldown |
| `ONCALL_SESSION_TIMEOUT_SECONDS` | `900` | Session wall clock budget |
| `ONCALL_EVIDENCE_DIR` | `_docs/operations/evidence` | Evidence output |
| `ONCALL_DRY_RUN` | `0` | Skip subprocess tests (unit demos) |

Secrets stay in environment variables only.

## Allowed responder actions

1. Investigate using dashboard URLs and traces (read-only).
2. Run approved tests: `uv run pytest tests/test_plan_failure_drill.py` from `backend/`.
3. Commit **only** on branch `oncall/<alert-id>` where `<alert-id>` is `{rule_uid}-{first_8_alnum_of_fingerprint}`.
4. Write an evidence record (markdown + JSON).

## Forbidden

Merge, deploy, edit alert rules, use production credentials, mutate production data, or change grade mappings / recommendation rules without paired test updates and human review.

## Human-review handoff

1. Inspect branch `oncall/<alert-id>` and the matching `oncall-<alert-id>.md` evidence file.
2. Open a pull request from that branch **manually**; the worker never merges.
3. For drill-induced failures ([#60](../operations/plan-failure-drill.md)), expect **no code fix**—teardown the drill flag and confirm plans succeed.

## End-to-end demo (plan failure alert)

1. Start stack with observability profile and seed data.
2. Set `CLIMBIT_PLAN_FAILURE_DRILL=1` on the API (non-production only).
3. Run `./scripts/plan-failure-drill.sh` until the **Trip plan failure rate above 5%** alert fires.
4. Confirm trace in Tempo via `X-Trace-Id` on 503 responses.
5. Worker runs one session → evidence file → optional commit on `oncall/climbit-plan-failure-rate-*`.
6. Teardown: unset drill flag, restart API, clear alert.

Recorded run: [`evidence/oncall-climbit-plan-failure-rate-2026-10-24.md`](evidence/oncall-climbit-plan-failure-rate-2026-10-24.md).

## Local one-shot

```bash
cd oncall-worker
uv sync
ONCALL_DRY_RUN=1 ONCALL_REPO_PATH=.. uv run python -c "from oncall_worker.config import OncallConfig; from oncall_worker.worker import OncallWorker; from oncall_worker.alerts import StaticAlertSource, FiringAlert; c=OncallConfig.from_environ(); c=OncallConfig(**{**c.__dict__, 'dry_run': True, 'repo_path': '..'}); w=OncallWorker(c, alert_source=StaticAlertSource([FiringAlert('climbit-plan-failure-rate','Trip plan failure rate above 5%','demo0001','2026-10-24T20:00:00Z',{'dashboard_url':'http://127.0.0.1:3000/d/climbit-planning/climbit-planning-system'},{})])); print(w.process_once())"
```
