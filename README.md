# ClimbIt

Neither application needs a database.

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
