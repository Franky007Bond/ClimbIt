#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SHA="${1:-$(git rev-parse HEAD)}"
export CLIMBIT_IMAGE_TAG="$SHA"

echo "Deploying ClimbIt compose stack with CLIMBIT_IMAGE_TAG=$CLIMBIT_IMAGE_TAG"
docker compose -f docker-compose.yml pull || true
docker compose -f docker-compose.yml up -d --build

mkdir -p /var/lib/climbit 2>/dev/null || true
echo "$SHA" > "${CLIMBIT_LAST_GOOD_SHA_FILE:-/var/lib/climbit/last-good-sha}" 2>/dev/null || \
  echo "$SHA" > "$ROOT/.last-good-sha"

echo "Deploy complete."
