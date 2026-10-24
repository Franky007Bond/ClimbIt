# Deployment and rollback (EU VPS)

ClimbIt deploys with **Docker Compose** on an EU VPS (Hetzner, Frankfurt region). **Dev** receives automatic deploys from `main`; **production** is promoted manually.

## Environments

| Environment | URL | Deploy |
| --- | --- | --- |
| Dev | `https://dev.climbit.example` (replace with your VPS DNS) | Automatic on push to `main` via `.github/workflows/deploy-dev.yml` |
| Production | `https://climbit.example` | Manual `workflow_dispatch` via `.github/workflows/deploy-prod.yml` |

Database backups: see [`backup-restore.md`](backup-restore.md) (`s3://climbit-eu-db-backups/` in **eu-central-1**).

## Rollback

Images are tagged by git SHA. To roll back:

```bash
./scripts/rollback-compose.sh <previous-sha>
```

This checks out the recorded compose files for that SHA, pulls images, and recreates containers without running migrations backward.

## Secrets

Configure on the VPS (never commit):

- `DATABASE_URL`, Postgres passwords
- `MAINTAINER_SESSION_SECRET`, `TRIP_CAPABILITY_SECRET`
- Deploy SSH key in GitHub Actions secrets (`DEPLOY_SSH_KEY`, `DEPLOY_HOST`)

## Evidence

Rollback exercise: [`evidence/deploy-rollback-2026-10-24.md`](evidence/deploy-rollback-2026-10-24.md).
