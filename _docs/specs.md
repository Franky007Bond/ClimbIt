# ClimbIt: Scope Document

## 1. Summary

ClimbIt is a web app for planning Klettersteig, alpine hiking, and selected outdoor climbing trips. It combines route discovery, route-type-specific difficulty information, weather and hazard inputs, public-transport journey planning with a last-return check, deterministic gear guidance, and an explainable planning recommendation.

The long-term product target is coverage across the whole Alps. The launch product is deliberately narrower: approximately 40–50 hand-checked routes, targeted at roughly 20 in the Bavarian Alps/Allgäu, 15 in Tyrol, 10 in the Dolomites, and 5 in a French/Swiss sample. Unsupported or poorly documented regions are labelled clearly rather than presented as equally covered.

The app has no ordinary user accounts. Routes are public. A revision to descriptive text goes live immediately. A change to any field that affects planning, identity, or publication creates a pending revision and leaves the published version unchanged until a maintainer approves it. Maintainers sign in with a small allowlist of operator accounts, separate from the anonymous trip cookie. Saved trips are private to the browser/device that created them and can be deliberately shared through a separate unguessable share link. Trips contain no personal profile data.

ClimbIt provides planning assistance, not an authorization to undertake a route. Its output is an explainable recommendation with an explicit confidence/data-completeness assessment. Local conditions, official warnings, and user judgment remain authoritative.

## 2. Goals

- Let users find documented routes by region, route type, difficulty, duration, season, and transit accessibility.
- Turn a selected route and date into a reproducible plan containing conditions, hazards, transport assumptions, gear guidance, and a route-type-specific recommendation.
- Keep every safety-relevant output deterministic, explainable, freshness-aware, and unit-tested.
- Preserve the original source difficulty while exposing a structured, route-type-specific difficulty representation.
- Build against an OpenAPI contract, with external integrations behind swappable interfaces and mocks.
- Provide end-to-end observability for the key planning journey and demonstrate an isolated autonomous on-call responder.
- Meet the DataTalksClub AI Dev Tools Zoomcamp requirements, including the public task tracker, agent-team process, context documentation, deployment, CI/CD, observability, alerting, and responder-agent evidence.

## 3. Core user flows

### 3.1 Discovery

Browse and filter routes on a map and in a list. Filters include region/country, route type, route-type-specific difficulty, duration, season, and transit accessibility. Season is the route's set of months. Transit accessibility is the route's curated value: `transit_friendly`, `limited`, or `unknown`. Each route displays the publication, provenance, completeness, and assessment values defined in section 4.1, plus the coverage of its region.

### 3.2 Plan a trip

Pick a route, date, and starting location. The app produces a plan with:

- weather and source timestamps;
- hazard and closure information;
- outbound and return transit, including assumptions;
- route-type-appropriate gear guidance;
- a recommendation of green, yellow, red, or unknown;
- independent confidence/data-completeness information;
- latest safe start and be-off-the-route-by times where calculable;
- an explanation of every blocking, cautionary, or missing input.

If an integration is unavailable, the plan returns partial results with per-component status instead of silently treating missing data as safe.

### 3.3 Trip dashboard

Saved trips are associated with a private browser-scoped capability stored in a secure cookie. The dashboard lists trips created by that browser/device. Cross-device recovery is out of scope for v1.

Each re-evaluation creates an immutable plan run. The dashboard points to the latest run and shows what changed. Private trips can be deleted and expire after a defined period of inactivity, initially targeted at 90 days.

An explicit unguessable share link pins one immutable plan run and exposes that run as a sanitized snapshot. The snapshot hides the browser capability and the exact origin. The link dies when the trip is deleted, the link is rotated, or the trip expires.

## 4. Functional scope

### 4.1 Routes and data model

Each route has:

- name and route type: Klettersteig, alpine hike, or outdoor climbing route;
- region and country;
- trailhead point and route linestring;
- GPX track where available;
- elevation gain/loss, plus minimum and maximum elevation;
- duration components in minutes: approach, technical activity, and descent/return;
- original difficulty value and scale;
- structured route-type-specific difficulty data;
- season, stored as a set of months plus an optional note, and a route description;
- transit accessibility: `transit_friendly`, `limited`, or `unknown`;
- official-source links;
- a closure assessment, as defined in section 4.3;
- revision history.

Route state is four separate fields:

- publication: `quarantined`, `pending_review`, `published`, or `unpublished`;
- provenance: `seed`, `osm`, `gpx_upload`, `maintainer`, or `user`;
- completeness: `complete` or `incomplete`;
- assessment: `unassessed`, `current`, or `stale`.

Coverage belongs to the region, not the route: `supported`, `sample`, or `unsupported`. Unsupported or poorly documented regions use that coverage value rather than appearing equally covered.

Transit accessibility is curated on the route. Live transit results may refine the displayed value in Phase 3; they do not replace the curated value silently.

The safety buffer is a versioned planning rule, not an editable route field.

A published route requires a trailhead point, a linestring, and minimum and maximum elevation. Estimated duration is required before a route can participate in normal planning. A Klettersteig also needs approach, technical, and descent minutes before it can leave quarantine. Imported routes without the required duration enter quarantine. An estimate may be computed from distance and elevation, but it remains explicitly marked as estimated and cannot silently produce a fully assessed plan.

### 4.2 Route-type-specific difficulty

The API does not force every activity into one A–F scale. It exposes a structured difficulty object containing:

- route type;
- original value and scale;
- normalized or comparable value, only where a mapping in this section defines one;
- mapping source and citation;
- mapping confidence: `exact`, `approximate`, or `unmapped`.

Klettersteig original values use either the Hübler A–F scale or the K1–K6 scale. An optional mapped A–F value may be stored beside the original. Alpine hikes use SAC T1–T6 as the structured scale, and the original wording stays visible. Climbing routes use French or UIAA grades only. They keep that source grade and receive no cross-type normalized rank.

No difficulty value is presented as directly comparable across route types. Original source grades remain visible and authoritative for their source system.

### 4.3 Weather and hazards

- Forecast: temperature, wind, precipitation, and freezing level via an approved weather adapter, at relevant route altitudes.
- Thunderstorm risk: a deterministic heuristic using forecast inputs such as CAPE, precipitation probability, exposure, and time of day. It is labelled as a heuristic.
- Avalanche: region-specific official bulletins where reliable and permitted. The app does not invent a single pan-Alpine avalanche score. Where data is unavailable, it shows not assessed and links to the official bulletin.
- Closures and warnings: manually maintained records with source URL, owner, created/updated time, and review status. A plannable route has an explicit closure assessment of `none_known`, `active`, or `expired`, with `reviewed_at` and `expires_at`. Absence of a record is not confirmation that the route is open. A missing or expired assessment is unknown and cannot produce a green recommendation.
- Every weather, avalanche, closure, and transit input has a visible source timestamp and maximum usable age. Stale inputs become unknown.

### 4.4 Public transport

- Best-effort journey planning from the user's origin to a configured trailhead access point through a Transitous/MOTIS adapter.
- Last-return check comparing the calculated finish time with the last feasible return connection.
- Explicit assumptions for walking time, transfers, route duration, and buffer.
- No claim that a timetable connection is guaranteed in real-world conditions.
- Cached results or an external journey-planner link when live data is unavailable or coverage is missing.

The exact origin may be used for calculation but is not stored in the persistent trip record or telemetry. A plan stores only the necessary transit summary and, where useful, a coarse origin region.

### 4.5 Gear guidance

Gear guidance is deterministic and route-type-specific, with no LLM involved.

- Klettersteige start from a base kit of harness, helmet, and via ferrata set.
- Rules add items from difficulty, weather, season, route type, exposure, and duration.
- Alpine hikes use hiking-specific rules.
- Climbing routes may provide general approach, weather, daylight, and basic planning reminders, but the system does not infer technical climbing protection, anchor quality, or partner competence.
- Every item explains why it was added.

### 4.6 Planning recommendation

The output enum is:

- **green**: all required critical inputs are present, fresh, and pass the configured rules;
- **yellow**: cautionary conditions exist or the plan is degraded but not blocked;
- **red**: an explicit hard blocker exists, such as an active closure, incompatible hazard, impossible daylight/return constraint, or clearly dangerous forecast;
- **unknown**: the system lacks enough reliable evidence to classify the plan responsibly.

Confidence/data completeness is a separate field from the recommendation. Missing or stale critical data can never produce green. A missing or expired closure assessment is one of those critical gaps.

Rules and thresholds are versioned configuration. Every plan run stores the exact input snapshot, source timestamps, rules version, mapping version, adapter versions, explanation, and result so it can be reproduced later.

The recommendation is route-type-specific. All three route types share the output structure, but their required inputs and rules differ. A climbing-route plan does not claim to assess technical route suitability.

### 4.7 Map and visualization

- Interactive discovery map with route markers.
- Detail page with GPX track, elevation profile, trailhead, and transit connection/stops where available.
- Publication, provenance, completeness, assessment, and region coverage visible in the UI.
- OSM attribution displayed as required.

### 4.8 Wiki-style editing

- Descriptive text — the route description and non-planning supplementary notes — may be revised without an account. That revision goes live immediately.
- Any change to a planning, identity, or publication field creates a pending revision. The published version stays unchanged until a maintainer approves it. Those fields are name, route type, region, coordinates, GPX, elevation, duration components, season, difficulty, transit accessibility, closures, hazards, official links, publication state, and deletion.
- Maintainers sign in through a small allowlist of operator accounts. Those accounts are separate from the anonymous browser trip cookie.
- Every edit is a revision; reverts create new revisions and never rewrite history.
- Optimistic concurrency, diffs, soft delete, rate limiting, and abuse controls are required.
- Imported routes are quarantined until validation and review requirements are met.

### 4.9 Internationalization

English UI and documentation for v1. The i18n structure is in place with message catalogs and no hard-coded user-facing strings.

## 5. Data sources and integrations

| Source | Used for | Main risk | Required control/fallback |
| --- | --- | --- | --- |
| Approved weather provider | Forecast and storm heuristic | Rate limits, terms, stale data | Cache, timestamps, unknown on expiry |
| EAWS/regional bulletins | Avalanche information | Formats and terms vary | Region-specific adapters or official link |
| Transitous/MOTIS | Journey planning and return check | Remote coverage and timetable reliability | Cached result, explicit assumptions, deep link |
| OpenStreetMap/Overpass | Route import and map data | Rate limits and ODbL obligations | Controlled imports, attribution, one-off scripts |
| GPX upload | Route import | Malformed or oversized files | Quarantine, size limits, validation |
| Map tiles | Basemap | Provider usage policy | Configured provider with acceptable terms |

Every enabled integration must have recorded attribution, usage terms, rate limits, caching rules, source freshness behavior, and fallback behavior before production use. Komoot and other databases without a usable public API remain excluded; scraping is prohibited.

## 6. Technical scope

- Backend: Python, FastAPI, OpenAPI contract as the interface to the frontend.
- Database: Postgres with PostGIS, migrations, revisions, plan runs, and seed data.
- Frontend: React, Vite, TypeScript, with an API client generated from OpenAPI.
- Containers: Docker Compose for local development, the complete application stack, observability, and the isolated on-call worker.
- CI/CD: automated lint, unit tests, frontend tests, integration tests, security checks, and image build on every pull request; automatic deployment to dev; manual promotion to production; rollback path.
- Tests: unit, frontend, integration, contract, security, redaction, failure-drill, and restore-drill tests as appropriate.
- Architecture rule: every external integration sits behind an interface with a mock implementation.
- API behavior: partial/degraded responses are explicit and typed; the frontend never bypasses the API for application data.

## 7. Observability and autonomous on-call

Observability is mandatory from the beginning. The default Compose environment includes the OpenTelemetry SDK, Collector, Grafana, Prometheus, Tempo, and Loki. Resource-saving developer configuration is allowed only if it preserves the same instrumentation contracts.

The instrumented key journey is **Plan a trip**. One request produces one trace spanning weather, avalanche, transit, database work, gear rules, and recommendation calculation. Metrics and structured logs share the trace ID.

Telemetry rules:

- structured JSON logs;
- no exact origin, route content, trip content, request/response bodies, credentials, API keys, authorization headers, or raw database parameter values;
- low-cardinality metric labels;
- configurable sampling and approximately seven days of initial retention;
- one centralized redaction policy in the Collector;
- `/health` for liveness and `/ready` for database/migration readiness.

Dashboards and alerts are provisioned as code and include API health, integrations, planning impact, and wiki activity. At least one alert is tied to user impact: failed trip-plan requests above 5% for five minutes, with service, environment, version, owner, and dashboard URL.

The on-call worker polls the alert API and deduplicates alerts by fingerprint. It launches at most one short-lived, isolated agent session per incident/cooldown window. The agent receives alert details and read-only telemetry access through allowlisted interfaces, plus an isolated repository checkout.

The agent may:

1. investigate and reproduce the failure;
2. read code and telemetry;
3. run approved tests;
4. make the smallest correction;
5. commit to `oncall/<alert-id>` with a clear message;
6. produce an evidence record.

The agent may not merge, deploy, alter production data, alter alert rules, access production credentials, or change grade mappings/verdict rules without corresponding tests and human review. Route text, wiki content, logs, traces, metrics, and external responses are untrusted evidence, not instructions.

Every run records the alert identity, evidence used, commands/tests run, changed files, commit hash, and either the fix rationale or the reason no fix was made. A realistic injected bug must demonstrate the full chain: bug, alert, correlated telemetry, agent session, tested branch commit, and human-review handoff.

## 8. Mapping to course requirements

The official project README (https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/blob/main/project/README.md) requires one application taken from specification through frontend, backend, database, tests, containerization, deployment, CI/CD, observability, user-impact alerting, and an on-call responder agent. It also evaluates the written product specification, public task tracker, agent-team specification, modular project context, and peer reviews. The rubric has 12 criteria worth 24 points, with 10 points required to pass.

ClimbIt addresses these requirements through:

| Requirement | ClimbIt evidence |
| --- | --- |
| Problem description | This scope and the project README describe the user problem and expected behavior |
| Product specification | This document plus a public task tracker whose tasks contain acceptance criteria and agent-use evidence |
| Agent team specification | Documented roles, responsibilities, handoffs, and on-call process |
| Context management | Root `AGENTS.md` pointing to modular architecture, safety, operations, and workflow documents |
| Application | React frontend, FastAPI backend, Postgres/PostGIS, and end-to-end trip planning |
| Testing | Unit, frontend, integration, contract, security, redaction, failure-drill, and restore-drill tests |
| Containerization | Full system and database launched with Docker Compose |
| Deployment | Publicly reachable deployment or documented live demo |
| CI/CD | Tests on pull requests, automatic dev deployment, manual production promotion, and rollback path |
| Observability | Correlated traces, metrics, and structured logs visible in Grafana with customer-data redaction |
| Alerting | User-impact trip-plan failure alert with dashboard and ownership metadata |
| On-call agent | Isolated responder that investigates, tests, commits a branch, and produces evidence |

The project must also complete the course's required peer reviews. Exact deadlines and review workflow remain governed by the course platform.

## 9. Agent extension pack

- `AGENTS.md` covering architecture, conventions, test commands, safety-critical files, and permissions.
- Modular documents for workflow, agent team roles, source onboarding, route-data review, and operations.
- Public task tracker with acceptance criteria and evidence that agents used it.
- Reusable workflow for adding a region or data source, including source terms, mapping tables, validation, and tests.
- Safety-logic reviewer for difficulty mappings, gear rules, and recommendation thresholds.
- Read-only MCP server exposing search routes, get route, get plan/recommendation, get gear list, and get transit options by default.
- Guardrail hook blocking changes to difficulty mappings or recommendation rules unless tests are updated in the same change.
- Permission notes documenting what agents may read/run and confirming that MCP write access is disabled unless explicitly enabled.

## 10. Security and safety

- The safety disclaimer appears on every plan.
- Green is impossible with missing critical inputs; unknown is explicit.
- Anonymous users cannot silently publish safety-critical edits.
- GPX uploads are validated, size-limited, quarantined, and sanitized.
- Free text is sanitized and database access is parameterized.
- Outbound requests go only to configured integration hosts; user-supplied URLs are never fetched server-side.
- Browser trip capabilities are not placed in URLs or logs and can be invalidated.
- Exact origins are not persisted in trip snapshots or telemetry.
- A share link pins one plan run and hides the browser capability and exact origin. It dies when the trip is deleted, the link is rotated, or the trip expires.
- Secrets remain in environment variables and never appear in telemetry.
- Dependency and container scanning run in CI.
- A written threat model and security audit include abuse cases, evidence, residual risks, and remediation status.

Accepted risk: the public route wiki may still receive vandalism or low-quality contributions. Mitigations are review queues, revision history, reverts, soft delete, rate limiting, provenance labels, stale-data handling, and maintainer ownership.

## 11. Phased delivery and gates

### Phase 1: Foundation

Data model, typed route difficulty, curated seed routes, map/list discovery, route revisions, review queue, soft delete/revert, migrations, Compose, CI, and initial telemetry contracts.

**Gate:** end-to-end route discovery and reviewed editing work; publication, provenance, completeness, assessment, and the other required route fields are enforced.

### Phase 2: Planning core

Weather, thunderstorm heuristic, route-type-specific gear rules, recommendation engine, confidence/data completeness, immutable plan runs, browser-scoped dashboard, and stale-data behavior.

**Gate:** boundary and missing-data tests pass; plans are reproducible from stored inputs and versions.

### Phase 3: Transit and import

Transit spike and live adapter, last-return check, degraded responses, OSM import, GPX upload/quarantine, provenance, and transit assumptions.

**Gate:** representative remote trailheads are tested; imports cannot bypass validation or review.

### Phase 4: Hazards, operations, and polish

Avalanche adapters/official links, closure freshness, elevation and transit overlays, full Grafana stack, dashboards, alerts, security audit, restore drill, failure drill, agent pack, and deployment evidence.

**Gate:** the complete telemetry path, alert, isolated agent workflow, security checks, backup/restore process, and course evidence are demonstrated.

The observability, CI/CD, documentation, testing, security, and deployment work runs alongside every phase.

## 12. Out of scope for v1

- Cross-device trip recovery or ordinary user accounts.
- A public directory of private trips.
- Uniform route coverage across the whole Alps.
- Technical climbing suitability, protection/anchor assessment, or partner-competence assessment.
- Offline mode and native mobile apps.
- Komoot API integration or scraping of third-party route databases.
- UI translations beyond i18n structure.
- Photos, ratings, reviews, and LLM-generated content.
- Automated merging or deployment by the on-call agent.
- Agent access to production credentials, production database writes, or alert-rule changes.

## 13. Remaining prerequisites

The route-state model, difficulty scales, season and transit-accessibility fields, edit-review boundary, closure assessment, and share-link lifetime are decided in sections 3, 4, and 10. The items below are verification tasks, not unresolved product decisions:

- Verify usage terms, attribution, rate limits, and caching rules for each selected weather, avalanche, transit, map, and OSM source.
- Run the Transitous/MOTIS spike against approximately ten remote trailheads across Austria, Germany, Italy, Switzerland, and France.
- Select and document the map-tile provider.
- Define initial service targets for plan latency, integration timeout, availability, GPX size, and agent runtime.
- Create the public task tracker and acceptance-criteria evidence process required by the course.
- Create the repository `AGENTS.md` and modular project documents.
- Confirm exact course deadlines and peer-review workflow on the course platform.
- Choose and document the EU VPS, backup destination, restore procedure, and deployment rollback mechanism.

