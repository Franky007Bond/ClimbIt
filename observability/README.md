# Observability (Compose profile)

Start the app with the observability stack:

```bash
docker compose --profile observability up -d --build
```

Set on the API (included when using the profile via `.env` or compose override):

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
```

Endpoints (localhost):

- Grafana: http://127.0.0.1:3000
- Prometheus: http://127.0.0.1:9090
- Tempo: http://127.0.0.1:3200
- Loki: http://127.0.0.1:3100
- OTLP HTTP: http://127.0.0.1:4318

Retention is **168 hours** (~7 days) in Loki and Tempo. Trace sampling is configured on the collector (`probabilistic_sampler`, default 100% for local dev).

Sensitive fields are redacted **once** in the OpenTelemetry Collector (`transform/redaction` in `otel-collector-config.yaml`), including authorization headers, request bodies, and exact trip origins.

Grafana loads **dashboards and alerts from git** under `observability/grafana/` (API health, integrations, planning impact, wiki activity). The **trip plan failure rate** alert fires when failures stay above 5% for five minutes and carries service, environment, version, owner, and dashboard URL metadata.

Run the **plan failure drill** (inject 503s, correlate trace + dashboard + alert): [`_docs/operations/plan-failure-drill.md`](../_docs/operations/plan-failure-drill.md).

Validate collector config:

```bash
docker run --rm -v "%cd%/observability:/cfg" otel/opentelemetry-collector-contrib:0.114.0 validate --config=/cfg/otel-collector-config.yaml
```
