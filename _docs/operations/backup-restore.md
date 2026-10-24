# Database backup and restore (EU deployment)

ClimbIt stores application data in PostgreSQL with PostGIS on the EU VPS (see deployment in issue #63). Backups use PostgreSQL custom format (`pg_dump -Fc`) so restores can target a **fresh** database with `pg_restore`.

## Backup destination

| Layer | Location | Purpose |
| --- | --- | --- |
| On-host staging | `/var/backups/climbit/` on the VPS (mode `0700`, owned by the deploy user) | Recent dumps for fast restore on the same host |
| Offsite copy | `s3://climbit-eu-db-backups/` in **eu-central-1** (Frankfurt), e.g. Hetzner Object Storage or AWS S3 | Durability if the VPS is lost |

Environment variables:

- `DATABASE_URL` — source database (same as the API).
- `CLIMBIT_BACKUP_DIR` — on-host directory (default `/var/backups/climbit`).
- `CLIMBIT_BACKUP_S3_URI` — optional; when set, `scripts/db-backup.sh` uploads each dump with `aws s3 cp`.

Retention (operational default): keep 7 daily on-host dumps; lifecycle on the bucket expires objects after 35 days unless compliance requires longer.

## Backup procedure

From the repository root on the VPS (or any host with `DATABASE_URL`, `pg_dump`, and `uv`):

```bash
export DATABASE_URL='postgresql://climbit:***@127.0.0.1:5432/climbit'
export CLIMBIT_BACKUP_DIR=/var/backups/climbit
export CLIMBIT_BACKUP_S3_URI=s3://climbit-eu-db-backups/prod
./scripts/db-backup.sh
```

The script prints the path to the new `.dump` file.

Equivalent manual command:

```bash
cd backend
uv run python -m app.db_backup backup --output /var/backups/climbit/climbit-manual.dump
```

## Restore procedure (fresh environment)

Use a **new database name** on the same PostgreSQL instance (or a new instance after creating the `climbit` role and empty database cluster).

1. Stop the API so nothing writes during restore (`docker compose stop api`).
2. Restore into a disposable or replacement database:

```bash
export DATABASE_URL='postgresql://climbit:***@127.0.0.1:5432/climbit'
./scripts/db-restore.sh /var/backups/climbit/climbit-20261024T120000Z.dump climbit_restored
```

3. Point `DATABASE_URL` at `climbit_restored`, run `uv run alembic current` (should match head), smoke-test `/ready`.
4. Swap production to the restored database (rename databases or update Compose env), then start the API.

Python entry point:

```bash
cd backend
uv run python -m app.db_backup restore \
  --input /path/to/climbit.dump \
  --target-database climbit_restored
```

## Restore drill

Evidence from the latest drill: [`evidence/restore-drill-2026-10-24.md`](evidence/restore-drill-2026-10-24.md).

Automated restore-drill test (disposable databases, requires `DATABASE_URL` and client tools):

```bash
cd backend
DATABASE_URL=postgresql://climbit:climbit@127.0.0.1:5432/climbit uv run pytest tests/test_db_restore.py -v
```
