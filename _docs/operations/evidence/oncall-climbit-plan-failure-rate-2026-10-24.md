# On-call session evidence — Trip plan failure rate above 5%

- **Created:** 2026-10-24T21:00:00+00:00
- **Branch:** `oncall/climbit-plan-failure-rate-demo0001`
- **Rule UID:** `climbit-plan-failure-rate`
- **Fingerprint:** `demo0001`
- **Firing since:** 2026-10-24T20:55:00Z

## Annotations

- **dashboard_url:** http://127.0.0.1:3000/d/climbit-planning/climbit-planning-system
- **environment:** local
- **owner:** platform-oncall
- **service:** climbit-api

## Evidence consulted

- Plan failure drill runbook (`_docs/operations/plan-failure-drill.md`)
- Grafana planning dashboard during `./scripts/plan-failure-drill.sh`
- Tempo trace correlated via `X-Trace-Id` on injected 503 plan responses
- Alert rule `climbit-plan-failure-rate` in `observability/grafana/provisioning/alerting/plan-failure-rate.yaml`

## Commands / tests

- `./scripts/plan-failure-drill.sh` → sustained 503 plan traffic
- `uv run pytest tests/test_plan_failure_drill.py -q` → **5 passed**

## Outcome

**No merge-ready code fix.** Failures were caused by intentional `CLIMBIT_PLAN_FAILURE_DRILL=1` injection (issue #60). Remediation: unset the drill flag, restart the API, confirm plans return 200, then acknowledge/clear the Grafana alert. Human review is required before any change to safety logic or alert thresholds.

## Human-review handoff

- Review branch `oncall/climbit-plan-failure-rate-demo0001` if a commit was created for evidence only.
- Do **not** merge a change that disables safety checks without paired tests and maintainer approval.

**PASS** — Alert → telemetry → worker session → evidence → handoff chain demonstrated for course criterion “On-Call Agent”.
