#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/backend"
# shellcheck disable=SC1091
source .venv/bin/activate
set -a
# shellcheck disable=SC1091
source "$ROOT/.env"
set +a
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
