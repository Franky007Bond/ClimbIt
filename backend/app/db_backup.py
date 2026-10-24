"""PostgreSQL backup and restore helpers (pg_dump / pg_restore)."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from sqlalchemy.engine.url import URL, make_url


def _require_pg_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"{name} is not on PATH")
    return path


def _normalize_url(database_url: str) -> URL:
    url = make_url(database_url)
    driver = url.drivername.split("+", 1)[0]
    if driver not in {"postgres", "postgresql"}:
        raise ValueError(f"unsupported database URL driver: {url.drivername}")
    return url.set(drivername="postgresql")


def _pg_env(url: URL) -> dict[str, str]:
    env = os.environ.copy()
    if url.password is not None:
        env["PGPASSWORD"] = url.password
    return env


def _pg_base_args(url: URL) -> list[str]:
    args: list[str] = []
    if url.host:
        args.extend(["-h", url.host])
    if url.port:
        args.extend(["-p", str(url.port)])
    if url.username:
        args.extend(["-U", url.username])
    return args


def backup_database(database_url: str, output_path: Path) -> Path:
    """Write a custom-format pg_dump of the database to output_path."""
    _require_pg_tool("pg_dump")
    url = _normalize_url(database_url)
    if not url.database:
        raise ValueError("DATABASE_URL must include a database name")

    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "pg_dump",
        *_pg_base_args(url),
        "-d",
        url.database,
        "-Fc",
        "-f",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, env=_pg_env(url))
    return output_path


def restore_database(
    admin_database_url: str,
    target_database: str,
    dump_path: Path,
    *,
    drop_existing: bool = True,
) -> None:
    """Restore a custom-format dump into a fresh database on the same server."""
    _require_pg_tool("pg_restore")
    _require_pg_tool("psql")
    admin = _normalize_url(admin_database_url)
    if not admin.database:
        raise ValueError("admin DATABASE_URL must include a database name")

    dump_path = dump_path.resolve()
    if not dump_path.is_file():
        raise FileNotFoundError(dump_path)

    maintenance_db = admin.database
    create_sql = f'CREATE DATABASE "{target_database}"'
    drop_sql = f'DROP DATABASE IF EXISTS "{target_database}" WITH (FORCE)'

    psql_base = [
        "psql",
        *_pg_base_args(admin),
        "-d",
        maintenance_db,
        "-v",
        "ON_ERROR_STOP=1",
    ]
    env = _pg_env(admin)

    if drop_existing:
        subprocess.run([*psql_base, "-c", drop_sql], check=True, env=env)
    subprocess.run([*psql_base, "-c", create_sql], check=True, env=env)

    target_url = admin.set(database=target_database)
    restore_cmd = [
        "pg_restore",
        *_pg_base_args(target_url),
        "-d",
        target_database,
        "--no-owner",
        "--no-acl",
        str(dump_path),
    ]
    completed = subprocess.run(restore_cmd, env=_pg_env(target_url))
    if completed.returncode not in {0, 1}:
        # pg_restore exits 1 when non-fatal warnings occur (e.g. existing extensions).
        raise subprocess.CalledProcessError(completed.returncode, restore_cmd)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ClimbIt PostgreSQL backup and restore"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    backup = sub.add_parser("backup", help="pg_dump the application database")
    backup.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="source database (default: DATABASE_URL)",
    )
    backup.add_argument(
        "--output",
        required=True,
        type=Path,
        help="output path for the custom-format dump file",
    )

    restore = sub.add_parser("restore", help="pg_restore into a new database")
    restore.add_argument(
        "--admin-database-url",
        default=os.environ.get("DATABASE_URL"),
        help="URL with rights to CREATE DATABASE (default: DATABASE_URL)",
    )
    restore.add_argument(
        "--target-database",
        required=True,
        help="name of the database to create and restore into",
    )
    restore.add_argument(
        "--input",
        required=True,
        type=Path,
        help="custom-format dump file from backup",
    )
    restore.add_argument(
        "--keep-existing",
        action="store_true",
        help="do not drop an existing target database first",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.command == "backup":
        if not args.database_url:
            raise SystemExit("DATABASE_URL or --database-url is required")
        path = backup_database(args.database_url, args.output)
        print(path)
    elif args.command == "restore":
        if not args.admin_database_url:
            raise SystemExit("DATABASE_URL or --admin-database-url is required")
        restore_database(
            args.admin_database_url,
            args.target_database,
            args.input,
            drop_existing=not args.keep_existing,
        )
    else:
        raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    main(sys.argv[1:])
