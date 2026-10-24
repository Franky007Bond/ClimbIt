#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <dump-file> <target-database-name>" >&2
  exit 1
fi

DUMP_PATH="$1"
TARGET_DB="$2"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATABASE_URL="${DATABASE_URL:?DATABASE_URL is required}"

cd "${ROOT}/backend"
uv run python -m app.db_backup restore \
  --input "${DUMP_PATH}" \
  --target-database "${TARGET_DB}"
