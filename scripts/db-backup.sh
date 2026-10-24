#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${CLIMBIT_BACKUP_DIR:-/var/backups/climbit}"
DATABASE_URL="${DATABASE_URL:?DATABASE_URL is required}"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="${BACKUP_DIR}/climbit-${timestamp}.dump"

mkdir -p "${BACKUP_DIR}"
cd "${ROOT}/backend"
uv run python -m app.db_backup backup --output "${output}"

if [[ -n "${CLIMBIT_BACKUP_S3_URI:-}" ]]; then
  aws s3 cp "${output}" "${CLIMBIT_BACKUP_S3_URI%/}/$(basename "${output}")"
fi

echo "${output}"
