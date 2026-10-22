# ClimbIt

From the repository root, `docker compose up -d --build` starts the API and PostGIS. Compose applies pending migrations before the API serves traffic.

`uv run pytest` and `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000` from `backend/` still do not need a database. Host uvicorn still starts with `DATABASE_URL` unset. Host pytest without `DATABASE_URL` skips the migration test.

## Backend

From `backend/`:

```powershell
uv run pytest
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Frontend

From `frontend/`:

```powershell
npm run dev
```
