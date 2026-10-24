#!/usr/bin/env bash
set -euo pipefail

API_BASE="${CLIMBIT_API_BASE:-http://127.0.0.1:8000}"
ROUTE_ID="${CLIMBIT_DRILL_ROUTE_ID:-50620691-2211-5a6e-8dfd-1c5bf7af289b}"
REQUESTS="${CLIMBIT_DRILL_REQUESTS:-20}"

if [[ "${CLIMBIT_PLAN_FAILURE_DRILL:-}" != "1" ]]; then
  echo "Set CLIMBIT_PLAN_FAILURE_DRILL=1 on the API before running this script." >&2
  exit 1
fi

echo "Sending ${REQUESTS} plan POSTs to ${API_BASE} (expect 503 while drill is enabled)"
trace_id=""
for _ in $(seq 1 "${REQUESTS}"); do
  headers="$(mktemp)"
  status="$(
    curl -sS -o /dev/null -w "%{http_code}" -D "${headers}" \
      -X POST "${API_BASE}/routes/${ROUTE_ID}/plans" \
      -H "Content-Type: application/json" \
      -d '{"plan_date":"2026-07-15","origin":"Drill origin"}'
  )"
  if [[ "${status}" != "503" ]]; then
    echo "Unexpected status ${status} (expected 503 with drill enabled)" >&2
    exit 1
  fi
  if [[ -z "${trace_id}" ]]; then
    trace_id="$(grep -i '^x-trace-id:' "${headers}" | cut -d' ' -f2 | tr -d '\r')"
  fi
  rm -f "${headers}"
done

echo "All requests returned 503."
if [[ -n "${trace_id}" ]]; then
  echo "Sample trace id: ${trace_id}"
  echo "Tempo: Grafana Explore → Tempo → TraceQL trace_id=\"${trace_id}\""
fi
echo "Dashboard: http://127.0.0.1:3000/d/climbit-planning/climbit-planning-system"
echo "Alert rule: climbit-plan-failure-rate (Trip plan failure rate above 5%)"
echo "When finished: unset CLIMBIT_PLAN_FAILURE_DRILL and restart the API."
