# External integrations and service targets

This document records attribution, usage terms, rate limits, caching, freshness,
and fallback behavior for each enabled external source, as required by spec
sections 5 and 13. Komoot and other sources without a usable public API remain
excluded; scraping is prohibited.

## Selected map tile provider

**Provider:** OpenStreetMap standard raster tiles (`tile.openstreetmap.org`)

| Topic | Record |
| --- | --- |
| Attribution | © OpenStreetMap contributors (shown in the map control and documented here) |
| Usage terms | [OSM Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/) — no bulk scraping; suitable for interactive browsing at MVP traffic |
| Rate limits | Fair-use; heavy traffic requires a dedicated tile cache or third-party CDN |
| Caching | Browser tile cache only in v1; no server-side tile proxy |
| Freshness | Tiles update as OSM editors publish changes; no realtime guarantee |
| Fallback | If tiles fail to load, maps show an empty basemap; route geometry overlays still render |

Frontend configuration: `VITE_MAP_TILE_URL` and `VITE_MAP_TILE_ATTRIBUTION` in `frontend/.env.example`.

## Open-Meteo (weather forecast)

| Topic | Record |
| --- | --- |
| Used for | Trailhead-area forecast inputs and thunderstorm heuristic |
| Attribution | [Open-Meteo](https://open-meteo.com/) |
| Usage terms | Free non-commercial API; see site terms for production scaling |
| Rate limits | Documented per-endpoint limits on open-meteo.com |
| Caching | Backend weather adapter may cache by route/date/elevation band with TTL |
| Freshness | `source_time` on forecast; stale/expired → component status degraded/unknown |
| Fallback | Missing or stale forecast → weather component `unknown`; verdict never treats missing data as safe |

Implementation: `MockWeatherAdapter` in tests; production adapter behind `WeatherPort` interface.

## EAWS / regional avalanche bulletins

| Topic | Record |
| --- | --- |
| Used for | Avalanche hazard context (MVP: official links + conservative unknown when absent) |
| Attribution | European Avalanche Warning Services and linked regional providers |
| Usage terms | Follow each bulletin’s terms; no republishing full bulletins without permission |
| Rate limits | Adapter-specific; prefer official JSON/RSS where licensed |
| Caching | Short TTL; store source timestamp only |
| Freshness | Expired bulletin → hazard component unknown |
| Fallback | No adapter data → link to official source; planning shows unknown, not green |

## Transitous / MOTIS (public transport)

| Topic | Record |
| --- | --- |
| Used for | Journey summary and last-return feasibility check |
| Attribution | Transitous project and underlying GTFS/OSM contributors where required |
| Usage terms | Self-hosted or public instance terms; no storing exact user origin in trips |
| Rate limits | Instance-dependent; mock in CI |
| Caching | Ephemeral per plan request in v1 |
| Freshness | Timetable age surfaced in transit component status |
| Fallback | Unavailable origin or remote failure → transit `degraded`/`unknown` with summary text |

Implementation: `mock_transit_summary` in MVP path; real adapter behind transit interface later.

Spike (remote trailhead coverage on the public instance): [`_docs/spikes/transitous-remote-trailheads.md`](spikes/transitous-remote-trailheads.md) (issue #42).

## OpenStreetMap / Overpass (route import)

| Topic | Record |
| --- | --- |
| Used for | Route geometry import scripts (quarantined routes) |
| Attribution | © OpenStreetMap contributors — ODbL |
| Usage terms | [ODbL](https://www.openstreetmap.org/copyright); share-alike obligations on produced data |
| Rate limits | Overpass API fair-use; scripted imports throttled |
| Caching | One-off import jobs; no live Overpass on user requests |
| Freshness | Import timestamp stored in route provenance |
| Fallback | Import failure leaves route quarantined |
| Env | `OVERPASS_API_URL` (default `https://overpass-api.de/api/interpreter`); `OVERPASS_MIN_INTERVAL_SECONDS` (default `2`) |
| Maintainer CLI | From `backend/` with `DATABASE_URL` set: `uv run python -m app.import_osm --manifest <path>` — JSON manifest with an `entries` array (see `backend/tests/fixtures/osm/manifest.json`) |

## GPX upload (route import)

| Topic | Record |
| --- | --- |
| Used for | User/maintainer route track upload |
| Risk | Malformed, empty, or oversized files |
| Limits | Size cap enforced at upload; invalid files rejected |
| Fallback | Quarantine until validated |

## Initial service targets (spec section 13)

These are verification targets for MVP operations, not SLO commitments:

| Target | Initial value | Notes |
| --- | --- | --- |
| Plan latency (p95) | ≤ 3 s | End-to-end `POST /routes/{id}/plans` with mocked externals in CI; measure in staging with real adapters |
| Integration timeout | 5 s per outbound call | Weather, transit, avalanche adapters abort and mark component unknown/degraded |
| API availability | 99.5% monthly | Excludes planned maintenance |
| Max GPX upload size | 10 MiB | Configurable env when upload endpoint ships |
| On-call agent runtime | ≤ 15 min | Isolated responder session budget per alert |

Review this document when enabling a new provider or changing caching/TTL defaults.
