# ClimbIt

From the repository root, `docker compose up -d --build` starts the API and PostGIS.

`uv run pytest` and `uv run uvicorn app.main:app --host 127.0.0.1 --port 8000` from `backend/` still do not need a database.

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
