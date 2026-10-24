# Deploy rollback exercise — 2026-10-24

## Setup

- Target: EU VPS Compose stack (api, db, frontend).
- Current release tag: `main` @ `HEAD` (record git SHA during deploy).
- Previous release: prior successful dev deploy SHA stored in `/var/lib/climbit/last-good-sha`.

## Exercise

1. Deploy intentionally broken API image tag `broken-demo` to **dev** only.
2. Confirm `/health` fails or `/ready` returns 503.
3. Run `./scripts/rollback-compose.sh` with `last-good-sha`.
4. Confirm `/health` and `/ready` return 200 and frontend loads Explore Routes.

## Result

**PASS** — Dev environment restored from last-good compose state without restoring database backups (schema unchanged). Production was not touched.

## Public URL

Document live dev URL in GitHub repository **About** / deployment environment when DNS is configured.

## Backup destination

Offsite: `s3://climbit-eu-db-backups/` (eu-central-1) per [`backup-restore.md`](../backup-restore.md).
