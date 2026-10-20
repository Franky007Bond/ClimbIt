# ClimbIt task backlog

Implement these tasks in order. Each one is sized for a single session. The description states the outcome and the rules that matter, so a task can be handed to someone who has not read the other tasks. Use `_docs/specs.md` for the product rules. Ordinary user accounts, cross-device recovery, photos, ratings, reviews, and scraping stay out of scope.

The main flows can be tested at these points:

- After task 16, a visitor can filter routes and open one.
- After task 24, a visitor can submit an edit and a maintainer can review it.
- After task 33, a visitor can plan a trip against mocked weather and transit.
- After task 39, a visitor can save, reopen, share, and delete that plan.

## 1. Create an empty project with a passing test
Goal: A FastAPI backend and a React, Vite, and TypeScript frontend exist, and one automated test passes.
Description: Create the two applications from spec section 6 without routes, screens, or external integrations. Add one backend test that passes locally and proves the test runner is wired up. Both applications start without a database.

## 2. Run the test on every pull request
Goal: The existing automated test runs in GitHub Actions whenever a pull request is opened or updated.
Description: Add a workflow that checks out the repository and runs the backend test. The workflow fails when that test fails. Do not add deployment yet.

## 3. Run the API and PostGIS locally with Compose
Goal: Docker Compose starts the FastAPI application and Postgres with PostGIS.
Description: Add a Compose file for local development that builds the backend and starts a PostGIS database. The backend receives the database connection only through environment variables. A documented command brings both services up.

## 4. Add database migrations
Goal: Schema changes are applied through versioned migrations.
Description: Add a migration tool to the backend and an initial migration that can run against the Compose database. Starting the stack applies pending migrations. Add a test that a fresh database ends on the latest migration.

## 5. Expose health and write structured logs
Goal: Operators can see whether the process and the database are ready, and logs are structured JSON.
Description: Add `/health` for process liveness and `/ready` for database and migration readiness, as specified in section 7. Write logs as JSON and leave out credentials, authorization headers, request bodies, and exact origins. Add a test that readiness fails when the database is unavailable.

## 6. Model a route and its state
Goal: Route data and its four state fields can be validated without a database.
Description: Implement the route fields and the publication, provenance, completeness, and assessment values from spec section 4.1. Put region coverage on the region as `supported`, `sample`, or `unsupported`. Add tests that a published route requires a trailhead, a linestring, minimum and maximum elevation, and a duration, and that a Klettersteig also needs approach, technical, and descent minutes before it can leave quarantine.

## 7. Model route-type-specific difficulty
Goal: Difficulty is stored per route type without a cross-type ranking.
Description: Implement the difficulty object from spec section 4.2: Hübler A–F or K1–K6 for Klettersteig, with an optional mapped A–F value; SAC T1–T6 for alpine hikes; French or UIAA only for climbing. Mapping confidence is `exact`, `approximate`, or `unmapped`. Add tests that no value is treated as comparable across route types.

## 8. Model closure assessment
Goal: A route can record whether its closure status was actually checked.
Description: Implement the closure assessment from spec section 4.3: `none_known`, `active`, or `expired`, with source, owner, review status, `reviewed_at`, and `expires_at`. Absence of a record stays distinct from `none_known`. Add tests that a missing or expired assessment is unknown.

## 9. Persist routes in PostGIS
Goal: A route, its difficulty, its geometry, and its closure assessment can be saved and read back.
Description: Add the PostGIS schema and repository for the route model, including the linestring, trailhead, elevation, duration components, season months, curated transit accessibility, and official links. The safety buffer is not a route column. Add an integration test that round-trips one route of each route type.

## 10. Load a representative seed set
Goal: Local development has a few hand-checked routes that exercise the state model.
Description: Add a repeatable seed command that loads published and quarantined examples across Klettersteig, alpine hike, and climbing, plus at least one region marked `sample` or `unsupported`. Every seeded duration that was computed from distance and elevation is marked estimated. Add a test that the seed is idempotent.

## 11. Serve route search
Goal: Clients can list and filter published routes.
Description: Add an OpenAPI endpoint that filters by region, country, route type, route-type-specific difficulty, duration, season month, and curated transit accessibility. Results include publication, provenance, completeness, assessment, and region coverage. Add tests that quarantined routes stay out of the default list and that difficulty filters cannot mix scales across route types.

## 12. Serve one route
Goal: Clients can read a single route with its geometry and closure assessment.
Description: Add an OpenAPI endpoint that returns one route, including the trailhead, linestring, GPX when present, difficulty object, and closure assessment. A missing route returns a not-found response. Add a test that an estimated duration is labeled as estimated.

## 13. Generate the TypeScript API client
Goal: The frontend calls the backend through a client generated from OpenAPI.
Description: Publish the backend OpenAPI document and generate a TypeScript client from it. Add a contract test that the search and route-detail operations in the document match the running API. The frontend does not keep a hand-written copy of those response types.

## 14. Add the frontend shell and English catalog
Goal: The web app has a navigable shell and no hard-coded user-facing strings.
Description: Create the React application shell with English message catalogs, following spec section 4.9. Include navigation for discovery, route detail, trip planning, saved trips, and route review. Add a frontend test that the shell renders its labels from the catalog.

## 15. Build the discovery screen
Goal: A visitor can browse and filter routes on a map and in a list.
Description: Build the discovery screen for spec section 3.1, using `_docs/design/screens/01 - Explore Routes - desktop.png` for layout. Show route markers, the section 4.1 state fields, and region coverage, and load data only through the generated client. Add a frontend test that applying a route-type and season filter changes the list.

## 16. Build the route detail screen
Goal: A visitor can open a route and read its identity, difficulty, and line.
Description: Build the route detail screen for spec section 4.7, using `_docs/design/screens/02 - Route Detail - desktop.png` for layout. Show the trailhead, linestring, original difficulty, state fields, and a plan action. Leave the elevation profile and live transit stops for a later task, and add a frontend test that the original grade remains visible.

Discovery can be tested after task 16.

## 17. Record append-only route revisions
Goal: Every route change is stored as a new revision and history is never rewritten.
Description: Add revision storage for a route, including author context, timestamp, and the before-and-after values. Replacing a route updates the current version by adding a revision. Add a test that an existing revision row cannot be updated or deleted through the application.

## 18. Publish descriptive edits immediately
Goal: An anonymous visitor can correct descriptive text and see it live.
Description: Add an unauthenticated edit endpoint for the route description and non-planning supplementary notes, as specified in section 4.8. The change becomes a new revision and updates the published route. Add a test that this path does not require a maintainer account.

## 19. Hold protected edits for review
Goal: Changes that affect planning, identity, or publication do not change the published route until approval.
Description: Add an endpoint that accepts edits to name, route type, region, coordinates, GPX, elevation, duration components, season, difficulty, transit accessibility, closures, hazards, official links, publication state, and deletion. Each submission creates a pending revision and leaves the published version unchanged. Add a test that the public route detail still returns the previous values.

## 20. Authenticate maintainers
Goal: Maintainer actions require an allowlisted operator account.
Description: Add login for a small allowlist of operator accounts supplied through environment configuration. The session is separate from any anonymous trip cookie. Add tests that an unknown account is rejected and that maintainer credentials are not written to logs.

## 21. Approve or reject a pending revision
Goal: A maintainer can inspect a diff and publish or discard one pending revision.
Description: Add maintainer endpoints that list pending revisions, show a field diff, and approve or reject one revision. Approval updates the published route by appending a revision. Add tests that rejection leaves the published route unchanged and that an anonymous caller cannot approve.

## 22. Reject conflicting edits
Goal: Two overlapping edits cannot silently overwrite each other.
Description: Require a revision token on descriptive and protected edits, and reject the request when the token does not match the current revision. Return enough information for the caller to reload the latest revision. Add a test where the second of two concurrent edits fails.

## 23. Soft-delete, revert, and limit abuse
Goal: Routes can be withdrawn or restored without rewriting history, and anonymous edits can be throttled.
Description: Add soft delete and revert as new revisions, with deletion waiting for maintainer approval under section 4.8. Add rate limiting and basic abuse controls for anonymous edit submissions. Add tests that a reverted route gains a new revision and that an over-limit client is rejected.

## 24. Build the route review screen
Goal: A maintainer can review pending route edits in the browser.
Description: Build the review screen for spec section 4.8, using `_docs/design/screens/05 - Route Wiki - desktop.png` for layout. Show the queue, the diff, and approve or reject actions, and put visible copy in the English catalog. Add a frontend test that a pending difficulty change is shown apart from the published value.

Reviewed editing can be tested after task 24.

## 25. Store an immutable plan run
Goal: A planning result can be saved and reproduced from the inputs and versions that created it.
Description: Add storage for a plan run that keeps the input snapshot, source timestamps, rules version, mapping version, adapter versions, explanation, and result from spec section 4.6. A stored run is never updated in place. Add a test that reading the run returns the same result as the snapshot that was stored.

## 26. Add a weather port and staleness rule
Goal: Planning can request a forecast without depending on a live provider.
Description: Add a weather interface that returns temperature, wind, precipitation, and freezing level at the route's relevant altitudes, plus source time and maximum usable age. Include a mock implementation and a cache boundary. Add tests that a stale forecast becomes unknown and that the mock can be substituted for the interface.

## 27. Add the thunderstorm heuristic
Goal: Thunderstorm risk is a labeled, deterministic result.
Description: Add a versioned heuristic that uses CAPE, precipitation probability, exposure, and time of day, as specified in section 4.3. The result says that it is a heuristic. Add tests for a low-risk case, a high-risk case, and a case with a required input missing.

## 28. Apply closure status to a plan
Goal: Planning treats closure evidence as a critical input.
Description: When a plan is built, copy the route's closure assessment and its source timestamp into the plan inputs. A missing or expired assessment is unknown. Add tests that an active closure is retained as a hard condition and that an empty closure table does not become `none_known`.

## 29. Add deterministic gear rules
Goal: Gear guidance is explainable and route-type-specific.
Description: Add versioned rules from spec section 4.5: Klettersteig starts from harness, helmet, and a via ferrata set; alpine hikes use hiking rules; climbing receives only general approach, weather, daylight, and planning reminders. Every added item includes its reason. Add tests that climbing output does not recommend technical protection.

## 30. Judge the recommendation and its confidence
Goal: A plan receives green, yellow, red, or unknown, plus a separate confidence result.
Description: Implement the versioned recommendation rules from spec section 4.6, with different required inputs per route type. Green requires every critical input to be present and fresh. Add tests that missing data, a stale forecast, and a missing closure assessment cannot be green, and that a climbing plan does not claim technical suitability.

## 31. Calculate the daylight window
Goal: A plan reports the latest safe start and the time to be off the route when it can.
Description: From the route duration, the versioned safety buffer, and the trailhead timezone, calculate the latest safe start and the be-off-by time. Leave both unset when the duration or daylight inputs are insufficient, and explain why. Add tests for a calculable summer day and a route whose duration is only an unmarked estimate.

## 32. Expose the plan endpoint
Goal: A client can request a plan and receive an explicit result for every component.
Description: Add an OpenAPI operation that accepts a route, a calendar date in the trailhead timezone, an optional start time, and an origin. Return weather, closure, mocked transit, gear, recommendation, confidence, daylight times, explanations, and the safety disclaimer. Persist the transit summary and a coarse origin region only, and add tests that an unavailable component is typed as degraded and that the exact origin is absent from the stored run.

## 33. Build the trip planner screen
Goal: A visitor can turn a route and a date into a readable plan.
Description: Build the planner screen for spec section 3.2, using `_docs/design/screens/04 - Trip Planner - desktop.png` for layout. Show the recommendation, confidence, component statuses, explanations, and disclaimer, with copy in the English catalog. Add a frontend test that a missing critical input is shown as unknown rather than green.

Planning a trip can be tested after task 33.

## 34. Issue a browser trip capability
Goal: A browser can hold a private capability for its own trips.
Description: Set a secure, HTTP-only cookie that identifies the browser's trip capability, as specified in section 3.3. The capability is unguessable, can be invalidated, and is distinct from a maintainer session. Add tests that the value is absent from URLs and logs.

## 35. Save and list trips for one browser
Goal: The browser that created a trip can see it on a private list.
Description: Add endpoints to save a plan run as a trip for the current capability and to list only that capability's trips. The list points at the latest run. Add tests that another capability cannot read the trip and that the stored trip has no personal profile fields.

## 36. Re-evaluate a trip and show what changed
Goal: Running a trip again keeps the old plan and surfaces the difference.
Description: Add an endpoint that creates a new immutable plan run for an existing trip and records what changed from the previous run. The dashboard data points at the latest run. Add a test that the earlier run remains readable and unchanged.

## 37. Delete a trip and expire inactive ones
Goal: A private trip can be removed, and unused trips do not live forever.
Description: Add deletion for a trip owned by the current capability. Expire trips after 90 days without activity and define activity as viewing, re-evaluating, or sharing the trip. Add tests that a deleted trip disappears from the owner's list and that an inactive trip expires.

## 38. Share one immutable plan run
Goal: A holder of the share link can see a sanitized snapshot of one run.
Description: Add an unguessable share link that pins one plan run, as specified in sections 3.3 and 10. The snapshot omits the browser capability and the exact origin. Add tests that deleting the trip, rotating the link, or expiring the trip makes the old link fail.

## 39. Build the trips screen and the share page
Goal: A visitor can manage saved trips and open a shared plan.
Description: Build the trips screen for spec section 3.3, using `_docs/design/screens/03 - My Trips - desktop.png` for layout, plus a page for a share link. Show the latest run, what changed, re-evaluate, delete, and share controls, without backup-token or account controls. Add a frontend test that the share page renders a plan without an origin or a capability.

The trip dashboard can be tested after task 39.

## 40. Record integration limits and choose the basemap
Goal: Each enabled external source has written terms, and the map provider is selected.
Description: Record attribution, usage terms, rate limits, caching, freshness, and fallback for the chosen weather, avalanche, transit, map, and OpenStreetMap sources, as required by spec sections 5 and 13. Select and document the map-tile provider. Also record the initial plan-latency, integration-timeout, availability, GPX-size, and agent-runtime targets.

## 41. Show the basemap with required attribution
Goal: Discovery and route detail use the selected tiles and display the required credit.
Description: Configure the chosen tile provider in the existing maps and show its attribution, including OpenStreetMap attribution wherever OSM data is drawn. Keep the provider settings in configuration. Add a frontend test that the attribution text is visible.

## 42. Spike Transitous against remote trailheads
Goal: The team knows whether Transitous can plan the launch trailheads before the live adapter is trusted.
Description: Query Transitous or MOTIS for about ten remote trailheads across Austria, Germany, Italy, Switzerland, and France. Record coverage, failures, and the assumptions that would have to be shown to a user. Do not enable the live adapter in the application as part of this task.

## 43. Add live transit and the last-return check
Goal: A plan can compare the route finish with the last feasible return connection.
Description: Add a Transitous adapter behind the transit interface, using the walking, transfer, duration, and buffer assumptions from spec section 4.4. Compare the calculated finish with the last feasible return and label the result as best effort. Add tests that a missed return is explained and that the exact origin is not stored.

## 44. Degrade transit when live data is unavailable
Goal: A transit failure stays visible and still leaves the user a next step.
Description: When live transit times out, is stale, or has no coverage, return a cached summary or an external journey-planner link together with the assumptions. The component status says the live result is unavailable. Add a test that this response cannot make the whole plan green.

## 45. Accept a GPX upload into quarantine
Goal: A visitor can submit a GPX track without publishing a route.
Description: Add an upload endpoint that enforces the GPX size limit, validates the file, and stores a sanitized route with provenance `gpx_upload` and publication `quarantined`. User-supplied URLs inside the file are not fetched. Add tests that an oversized or malformed file is rejected and that the route is absent from public search.

## 46. Import OpenStreetMap routes into quarantine
Goal: A maintainer can run a controlled import without publishing directly.
Description: Add a one-off import script for OpenStreetMap or Overpass that respects the recorded rate limits and ODbL attribution. Imported routes start quarantined, keep provenance `osm`, and carry an estimated duration only when it is labeled as estimated. Add a test that the import cannot set publication to `published`.

## 47. Seed the Bavarian Alps and Allgäu
Goal: The launch catalog contains the hand-checked Bavarian Alps and Allgäu routes.
Description: Add about twenty hand-checked routes for this region through the existing seed format. Each published route satisfies the section 4.1 requirements, and any computed duration is marked estimated. Add a test that the loaded count and region coverage match the launch target.

## 48. Seed Tyrol
Goal: The launch catalog contains the hand-checked Tyrol routes.
Description: Add about fifteen hand-checked Tyrol routes through the existing seed format. Preserve each route's original difficulty scale and closure assessment. Add a test that these routes are searchable by region and route type.

## 49. Seed the Dolomites
Goal: The launch catalog contains the hand-checked Dolomites routes.
Description: Add about ten hand-checked Dolomites routes through the existing seed format. Keep their source grades and region coverage explicit. Add a test that a Dolomites hiking grade and a Klettersteig grade remain on separate scales.

## 50. Seed the French and Swiss sample
Goal: The small French and Swiss sample is present, and unsupported regions are labeled.
Description: Add about five hand-checked routes for the French and Swiss sample and mark that region coverage as `sample`. Mark regions outside the launch set as `unsupported` so they are not presented as equally covered. Add a test that an unsupported region is labeled in search results.

## 51. Add regional avalanche evidence
Goal: A plan shows official avalanche information only where a permitted regional source exists.
Description: Add a region-specific avalanche adapter or an official bulletin link, as specified in section 4.3. Where no permitted feed exists, show not assessed and link to the official bulletin. Add tests that the application does not invent a single pan-Alpine score and that a stale bulletin becomes unknown.

## 52. Expire closure assessments
Goal: An old closure check stops being treated as current.
Description: When `expires_at` has passed, present the assessment as expired and unknown to planning. Keep the historical record. Add a test that a previously green plan input becomes a critical gap after expiry.

## 53. Add the elevation profile and transit overlay
Goal: Route detail shows the height profile and the transit connection used for the route.
Description: On the route detail screen, draw the elevation profile from the stored track and show the trailhead transit stop or connection when the API provides one. Keep both views on data from the API. Add a frontend test that a route without a transit connection still renders the profile.

## 54. Trace one plan request
Goal: One plan request produces one trace across every planning step.
Description: Instrument the plan operation so weather, avalanche, transit, database work, gear rules, and recommendation calculation appear in one trace, as specified in section 7. Metrics and structured logs share that trace ID, and labels stay low-cardinality. Add a test that a plan response carries the trace identifier used in the logs.

## 55. Redact telemetry in the collector
Goal: Sensitive values are removed once, in the OpenTelemetry Collector.
Description: Add the Compose observability stack from spec section 7, or a resource-saving configuration that keeps the same contracts. Configure one Collector redaction policy, sampling, and about seven days of retention. Add a redaction test that an exact origin, authorization header, and request body do not remain in exported logs.

## 56. Provision dashboards and the user-impact alert
Goal: Grafana shows the planning system, and a plan outage raises an owned alert.
Description: Provision dashboards as code for API health, integrations, planning impact, and wiki activity. Add an alert when failed trip-plan requests stay above 5% for five minutes, with service, environment, version, owner, and dashboard URL. Add a test or fixture that the alert rule contains those fields.

## 57. Add the security checks and threat model
Goal: The safety and abuse controls in spec section 10 are tested and documented.
Description: Add tests for sanitized free text, parameterized database access, refusal to fetch user-supplied URLs, and secrets remaining in environment variables. Run dependency and container scanning in the pull-request workflow. Write the threat model with abuse cases, evidence, residual risks, and remediation status, including the accepted wiki-vandalism risk.

## 58. Extend continuous integration
Goal: A pull request runs the full automated check and builds images.
Description: Extend the workflow so lint, unit tests, frontend tests, integration tests, contract tests, security checks, and image build all run on a pull request. The workflow does not deploy. Add a failing-check example to the workflow documentation.

## 59. Drill backup and restore
Goal: A database backup can be restored into a fresh environment.
Description: Document and script the backup destination and restore procedure for the EU deployment database. Run one restore drill and record the result. Add an automated test for the restore step that can run against a disposable database.

## 60. Drill a plan-request failure
Goal: The user-impact alert can be raised and correlated with telemetry.
Description: Inject a realistic plan-request failure in a non-production environment and show the alert, the trace, and the dashboard together. Record the evidence. Remove the injected failure at the end of the drill.

## 61. Add the isolated on-call responder
Goal: An alert can produce one reviewed branch and an evidence record.
Description: Add the on-call worker from spec section 7. It deduplicates alerts by fingerprint, starts at most one isolated session per cooldown, and may only investigate, test, and commit to `oncall/<alert-id>`. Demonstrate the chain with the injected bug, and record the alert, evidence, commands, changed files, commit hash, and why a fix was or was not made.

## 62. Add the agent context pack
Goal: Agents working in the repository have the boundaries and entry points in writing.
Description: Add root `AGENTS.md` and the modular workflow, team-role, source-onboarding, route-review, and operations documents from spec section 9. Add the read-only route and plan lookup interface with write access disabled, and a guardrail that blocks difficulty-mapping or recommendation-rule changes unless tests change in the same change. Document what agents may read and run.

## 63. Deploy with a rollback path
Goal: The application is publicly reachable, and a bad release can be rolled back.
Description: Deploy the Compose stack to the chosen EU VPS, with automatic deployment to dev and manual promotion to production. Document the rollback mechanism and perform one rollback exercise. Record the public URL and the backup destination.

## 64. Record the course evidence
Goal: The course deliverables point at the specification, tracker, and review process.
Description: Publish this backlog as the public task tracker and add a place to record acceptance evidence when an agent completes a task. Confirm the current course deadlines and peer-review workflow and write them into the project documentation. Link the tracker, `AGENTS.md`, and deployment evidence from the project README.
