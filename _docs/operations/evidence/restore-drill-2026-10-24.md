# Restore drill evidence — 2026-10-24

**Goal:** Confirm a PostgreSQL backup of the ClimbIt database can be restored into a fresh database with matching route data.

**Environment:** Local Compose PostGIS (`climbit-db-1`), database `climbit`, same major version as production target (PostgreSQL 17 + PostGIS 3.5).

## Automated restore-drill test

- **Test:** `backend/tests/test_db_restore.py::test_restore_drill_round_trip`
- **Mechanism:** Migrate + seed disposable source DB → `pg_dump -Fc` → `pg_restore` into a second disposable DB → assert row counts and a known seeded route id.
- **CI:** Runs in job `backend-integration` when `postgresql-client` is installed (requires `DATABASE_URL`).

## Manual drill (Compose)

Commands run against the running `db` service:

```text
$ docker exec climbit-db-1 psql -U climbit -d climbit -c "SELECT count(*) FROM routes"
 count
-------
    25

$ docker exec climbit-db-1 pg_dump -U climbit -d climbit -Fc -f /tmp/restore-drill.dump
$ docker exec climbit-db-1 psql -U climbit -d climbit -c "CREATE DATABASE climbit_restore_drill"
$ docker exec climbit-db-1 pg_restore -U climbit -d climbit_restore_drill --no-owner --no-acl /tmp/restore-drill.dump
$ docker exec climbit-db-1 psql -U climbit -d climbit_restore_drill -c "SELECT count(*) FROM routes"
 count
-------
    25
```

Cleanup: `DROP DATABASE climbit_restore_drill WITH (FORCE)`.

## Result

**PASS** — Route count matched (25 → 25) after restore into `climbit_restore_drill`. Documented backup destination and scripts: [`../backup-restore.md`](../backup-restore.md).
