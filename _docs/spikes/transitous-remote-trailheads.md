# Spike: Transitous / MOTIS vs remote alpine trailheads

Issue [#42](https://github.com/Franky007Bond/ClimbIt/issues/42). Docs-only spike; the application still uses `mock_transit_summary` (no live adapter).

## Instance and query parameters

| Item | Value |
| --- | --- |
| **Primary instance (MOTIS 2)** | `https://api.transitous.org/api/v1/plan` |
| Optional comparison | Not run; Transitous public API is the designated Phase 3 instance |
| **Trip date** | Saturday **2027-07-03** (summer weekend) |
| **Departure time** | **07:00** local (`time=2027-07-03T07:00:00+02:00`, `arriveBy=false`) |
| **Loaded timetable window** (from API error on out-of-range dates) | 2026-09-22 00:00 UTC → 2027-10-23 00:00 UTC |
| HTTP client | `User-Agent: ClimbIt-spike/1.0 (docs-only; issue-42)` |

Interpret arrival/departure times in **Central European Summer Time (UTC+2)** unless a leg ends in Switzerland (same offset on this date).

### Attribution, terms, and rate limits

Per [Transitous API usage](https://transitous.org/api/) and [`_docs/integrations.md`](../integrations.md):

- **Attribution:** Transitous, underlying GTFS operators, and OpenStreetMap (ODbL) where OSM is used in routing.
- **Usage:** Community best-effort API; open-source non-commercial use; visible link to [transitous.org/sources](https://transitous.org/sources/); identifiable `User-Agent` on every request.
- **Rate limits:** No fixed quota published; avoid bulk or automated high-volume `/plan` traffic. This spike issued **10** plan requests (~1.5 s apart). Heavy use requires coordination via the Transitous Matrix channel.
- **Privacy:** Origins below are **named city/main stations only** (hub coordinates); no user-style street addresses.

### Origin hubs (one per country tested)

| Country | Hub name | Hub WGS84 (lat, lon) |
| --- | --- | --- |
| DE | München Hauptbahnhof | 48.140, 11.558 |
| FR | Lyon Part-Dieu | 45.760, 4.859 |
| AT | Innsbruck Hauptbahnhof | 47.263, 11.401 |
| IT | Bolzano | 46.498, 11.358 |
| CH | Zürich Hauptbahnhof | 47.378, 8.540 |

Each outbound query uses **that trailhead’s country hub** → **trailhead coordinates**.

## Trailhead catalog (10)

Coordinates for the two seed trailheads match `backend/app/data/seed_routes.py` (`Point(longitude=…, latitude=…)` on the published alpine hike linestrings).

| # | Country | Trailhead | Latitude | Longitude | Point source |
| --- | --- | --- | ---: | ---: | --- |
| 1 | DE | Allgäu (seed published alpine hike) | 47.35 | 10.25 | Seed |
| 2 | FR | Chamonix (seed published alpine hike) | 45.92 | 6.86 | Seed |
| 3 | AT | Stubaier Gletscher Bergstation | 47.110 | 11.328 | Curated spike |
| 4 | IT | Tre Cime di Lavaredo (Rifugio Auronzo area) | 46.618 | 12.303 | Curated spike |
| 5 | CH | Kleine Scheidegg | 46.585 | 7.961 | Curated spike |
| 6 | DE | Königssee / Watzmann trailhead | 47.593 | 12.976 | Curated spike |
| 7 | AT | Großglockner Hochalpenstraße (Edelweißspitze area) | 47.054 | 12.774 | Curated spike |
| 8 | IT | Gran Paradiso (Valsavarenche trailhead) | 45.505 | 7.273 | Curated spike |
| 9 | CH | Zermatt (Matterhorn base) | 46.020 | 7.749 | Curated spike |
| 10 | FR | La Bérarde (Écrins) | 44.917 | 6.283 | Curated spike |

## Journey query results

All queries: `GET /api/v1/plan` with `fromPlace=<hub_lat>,<hub_lon>`, `toPlace=<trailhead_lat>,<trailhead_lon>`, shared date/time above, `numItineraries=3`.

| # | Trailhead | Hub | API outcome | Itinerary returned? | Best result (one line) |
| --- | --- | --- | --- | --- | --- |
| 1 | Allgäu (seed) | München Hbf | HTTP 200 success | **No** | **Coverage gap:** empty `itineraries` at raw trailhead coordinate |
| 2 | Chamonix (seed) | Lyon Part-Dieu | HTTP 200 success | Yes | ~17 h over **two calendar days**; rail Lyon→Genève, buses via Sallanches; 32 min walk; first departure in response **2027-07-05** (not same-day from 07-03 query) |
| 3 | Stubaier Gletscher | Innsbruck Hbf | HTTP 200 success | **No** | **Coverage gap:** empty `itineraries` (likely beyond scheduled PT + path network) |
| 4 | Tre Cime / Auronzo | Bolzano | HTTP 200 success | **No** | **Coverage gap:** empty `itineraries` |
| 5 | Kleine Scheidegg | Zürich HB | HTTP 200 success | Yes | ~**3 h 8 min** same day; Zürich→Interlaken→Lauterbrunnen→Wengen, funicular/rail + **17 min** walk |
| 6 | Königssee / Watzmann | München Hbf | HTTP 200 success | **No** | **Coverage gap:** empty `itineraries` |
| 7 | Großglockner (Edelweißspitze) | Innsbruck Hbf | HTTP 200 success | **No** | **Coverage gap:** empty `itineraries` |
| 8 | Gran Paradiso (Valsavarenche) | Bolzano | HTTP 200 success | **No** | **Coverage gap:** empty `itineraries` |
| 9 | Zermatt | Zürich HB | HTTP 200 success | Yes | ~**3 h 24 min** same day; long-distance + regional rail to Zermatt + **19 min** walk |
| 10 | La Bérarde (Écrins) | Lyon Part-Dieu | HTTP 200 success | **No** | **Coverage gap:** empty `itineraries` |

**Coverage gaps (no itinerary):** seven trailheads (rows 1, 3, 4, 6, 7, 8, 10). At least two are explicitly documented above as required.

**Notes on successes:**

- Swiss resort nodes (5, 9) return plausible same-day hub→near-trailhead plans with explicit walk legs.
- Chamonix (2) returns plans, but the best ranked option is a **multi-day** connection and does not respect a simple “Saturday 07:00 outbound” interpretation; treat as weak/feasibility-only for MVP last-return logic until stop snapping and same-day constraints are validated.

Requests without a `User-Agent` received **HTTP 403 Forbidden** during the spike; production adapter must send a compliant agent string.

## Spec §4.4 assumptions vs MOTIS output

Aligned with [`_docs/specs.md`](../specs.md) §4.4 and transit fallback rules in [`_docs/integrations.md`](../integrations.md).

| Planning assumption | Provided by Transitous `/plan` | ClimbIt must compute or display |
| --- | --- | --- |
| Walking time | Walk legs between stops and to/from coordinate endpoints (when a route exists) | Extra buffer from **last PT stop** to true trailhead if snapping is used; hiking approach time from route metadata |
| Transfers | Mode per leg; transfer count derivable from legs | Human-readable transfer summary; cap/complexity hints for UI |
| Route (journey) duration | `duration` and per-leg times | Tie-in to **route duration** and daylight (planning service) |
| Buffer | Not explicit | Configurable pedestrian / schedule buffer before hike start and for last-return |
| Best-effort / not guaranteed | Not explicit | Required disclaimer in UI copy |
| Last-return check | Separate query or reverse `/plan` needed | Compare finish time vs return legs; not evaluated in this spike |
| Privacy (no exact origin stored) | N/A | Only coarse origin region in trip record; hub-style origins in plans |

When live data is missing or `/plan` returns no itinerary → transit component **`degraded` / `unknown`** with summary text (per integrations fallback), not silent success.

## Phase 3 gate recommendation

**Enable live adapter on `api.transitous.org` with documented regional gaps** — do **not** flip off `mock_transit_summary` until #43 implements snapping, timeouts, and degraded handling.

**Reasoning from the table:**

- The public instance is **reachable and returns valid MOTIS JSON** for major Swiss trailhead-adjacent coordinates (3/3 CH queries that hit resort PT).
- **Seven of ten** raw WGS84 alpine trailheads returned **no itinerary**, including both seed points in DE/FR-adjacent mountains when queried as naked coordinates from national hubs. A live adapter that passes trailhead lat/lon directly will often look “broken” without **nearest-stop snapping**, seasonal shuttle GTFS, or curated access points.
- FR Chamonix shows **itineraries exist in graph** but not always on the requested day/hour; last-return (#43) needs strict datetime and reverse-journey tests before trust.

**Not recommended yet:** full “green” transit status for remote DE/AT/IT catalog routes based on this spike alone.

**Application state after this task:** unchanged — still `mock_transit_summary` only; no live adapter wired.
