ClimbIt is a web app for planning Klettersteig, alpine hiking, and selected outdoor climbing trips. It combines route discovery, route-type-specific difficulty information, weather and hazard inputs, public-transport journey planning with a last-return check, deterministic gear guidance, and an explainable planning recommendation.

Documents

- `_docs/process.md` - how work is organized

Commands

- `docker compose up -d db` - Postgres, needed before anything touches the
  database
- `uv sync` - install dependencies
- `uv run pytest` - the whole suite. The tests that read a built asset build it
  first, once per session, so a fresh checkout does not have to remember the npm
  commands below; a build that does not produce its file fails the run, naming
  the command to rerun
- `uv run pytest tests/test_home.py` - one test file
- `uv run ruff check . && uv run ruff format --check .` - lint and format check,
  run it before committing
- `npm install` - the build-time toolchain:  Vite

Rules

- Layout: a `backend/` app and a `frontend/` app.
- Backend: Python 3.14, uv, `fastapi[standard]`, import path `app.main:app`, tests with `uv run pytest` from `backend/`.
- Frontend: Node.js 22, npm, the Vite React TypeScript app, and `package-lock.json`.