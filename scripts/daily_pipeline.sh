#!/bin/bash
# Wrapper for launchd/cron: load .env, log output, run daily_pipeline.py.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"
STAMP="$(date +%Y-%m-%d_%H%M%S)"
LOG="$LOG_DIR/daily_pipeline_${STAMP}.log"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

{
  echo "=== daily_pipeline start $(date) ==="
  "$ROOT/.venv/bin/python" "$ROOT/scripts/daily_pipeline.py" "$@"
  status=$?
  echo "=== daily_pipeline end $(date) exit=$status ==="
  exit "$status"
} >>"$LOG" 2>&1
