#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SHA="${1:?usage: rollback-compose.sh <git-sha>}"
export CLIMBIT_IMAGE_TAG="$SHA"

echo "Rolling back to CLIMBIT_IMAGE_TAG=$SHA"
git fetch --depth=1 origin "$SHA" 2>/dev/null || true
git checkout "$SHA" -- docker-compose.yml backend/Dockerfile frontend/Dockerfile 2>/dev/null || true

docker compose -f docker-compose.yml up -d --build
echo "Rollback complete."
