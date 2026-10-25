# Demo flow (friends & live walkthrough)

~15 minutes: start stack → seed routes → walk the main screens → plan one trip.

## Before you start

- **Docker Desktop** running.
- **uv** installed (one-time seed only): [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)
- Clone this repo and open a terminal at the **repository root**.

## 1. Start the app (2–5 min)

```powershell
docker compose up -d --build
```

Wait until the API is ready:

```powershell
curl http://127.0.0.1:8000/ready
```

Expect JSON with `"status":"ready"`. If you get 503, wait 30–60 seconds and retry (PostGIS + migrations on first boot).

Open in the browser:

| What | URL |
| --- | --- |
| **App (use this for the demo)** | http://127.0.0.1:5173 |
| API docs (optional) | http://127.0.0.1:8000/docs |

## 2. Load demo routes (once per fresh database)

Compose starts an **empty** database. Without seeding, Explore will look empty.

```powershell
cd backend
uv sync
$env:DATABASE_URL="postgresql://climbit:climbit@127.0.0.1:5432/climbit"
uv run python -m app.seed
cd ..
```

Refresh http://127.0.0.1:5173 — you should see published routes (e.g. **Hindelanger Klettersteig**, **Grand Balcon Sud**, **Hinterstein Blaustein**).

## 3. Story to tell (screen order)

### A. Explore Routes (home)

**URL:** http://127.0.0.1:5173/

- Map + list of alpine routes (Klettersteig, hikes, climbing).
- Try a **filter** (region, route type, or difficulty) and point out the list and map updating together.
- Click a route row to open detail.

**One-liner:** “Discovery first — same data powers the map and the list.”

### B. Route detail

**URL:** http://127.0.0.1:5173/routes/50620691-2211-5a6e-8dfd-1c5bf7af289b  
(or use nav **Route detail** — seeded **Grand Balcon Sud**)

- Name, region, route type, normalized difficulty (with original grade).
- Map, elevation profile, duration, season, transit accessibility.
- Official links where present.

**One-liner:** “Everything here is reviewed route data, not a generic map pin.”

### C. Trip planner (core demo)

**URL:** http://127.0.0.1:5173/plan

Use these values (works with default mock integrations):

| Field | Value |
| --- | --- |
| Route ID | `50620691-2211-5a6e-8dfd-1c5bf7af289b` (Grand Balcon Sud) |
| Plan date | `2026-07-15` (mid-summer, in season) |
| Origin | `Munich` (coarse label — not stored as exact coordinates in telemetry) |

Submit **Plan trip**.

Show on the result:

- **Recommendation** (green / yellow / red / unknown) and short **explanation**.
- **Weather** and **component statuses** (ok / degraded / unknown).
- **Gear** list (route-type rules).
- **Transit** summary and last-return style messaging when shown.
- **Safety disclaimer** on every plan.

**One-liner:** “One button pulls weather, hazards, gear, transit, and a deterministic verdict — with reasons, not a black box.”

Optional second plan: same route ID, date **`2026-01-15`** — often worse season / daylight story; good contrast if you have time.

### D. My trips

**URL:** http://127.0.0.1:5173/trips

- Plans are tied to **this browser** (capability cookie), not a login.
- Open a saved trip if one appears after planning.

**One-liner:** “No account for the demo — trips stay on your device until they expire.”

### E. Route wiki (short)

**URL:** http://127.0.0.1:5173/review

- Mention community / maintainer workflow for route text (descriptive vs protected fields).

Skip deep maintainer login unless your audience cares about ops.

## 4. Shut down after the demo

```powershell
docker compose down
```

Data survives in the Docker volume unless you remove volumes (`docker compose down -v` wipes the DB).

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Explore empty | Run **seed** (step 2). |
| `/ready` 503 | Wait for DB; `docker compose logs api --tail 50`. |
| Plan fails / error banner | Confirm route ID and date; check API: `curl http://127.0.0.1:8000/health`. |
| Port 5173 in use | Stop other dev servers or change the Compose frontend port mapping. |

## Optional: “how we run it in prod” (technical friends)

Do **not** enable this for a casual demo unless you want to show Grafana.

```powershell
docker compose -f docker-compose.yml -f docker-compose.observability.yml --profile observability up -d
```

Grafana: http://127.0.0.1:3000 — planning dashboards and alerts (local profile only).

## Sharing on another laptop on your Wi‑Fi

By default the app binds to **127.0.0.1** only. For another device on the same network you would temporarily publish ports on `0.0.0.0` and set `CORS_ALLOWED_ORIGINS` to your laptop’s LAN URL — only do that on a trusted network.
