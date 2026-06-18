#!/bin/bash
# Install or remove the macOS launchd schedule for QuantBot (9 PM weekdays).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.quantbot.daily"
PLIST_SRC="$ROOT/scripts/com.quantbot.daily.plist"
PLIST_DST="$HOME/Library/LaunchAgents/${LABEL}.plist"
WRAPPER="$ROOT/scripts/daily_pipeline.sh"

usage() {
  cat <<EOF
Usage: $(basename "$0") install|uninstall|status|test

  install   — register 9 PM weekday launchd job (local timezone)
  uninstall — unload and remove the launchd job
  status    — show whether the job is loaded
  test      — run the pipeline once now (logs under logs/)

Requires: .venv, .env with API keys, scripts/tickers_input.csv
EOF
}

ensure_prereqs() {
  local missing=0
  [[ -x "$ROOT/.venv/bin/python" ]] || { echo "Missing .venv — run: python3 -m venv .venv && .venv/bin/pip install -e ."; missing=1; }
  [[ -f "$ROOT/.env" ]] || { echo "Missing .env (copy from .env.example and add API keys)."; missing=1; }
  [[ -f "$ROOT/scripts/tickers_input.csv" ]] || { echo "Missing scripts/tickers_input.csv (one ticker per row)."; missing=1; }
  chmod +x "$WRAPPER"
  mkdir -p "$ROOT/logs"
  return "$missing"
}

install() {
  ensure_prereqs || exit 1
  sed "s|__PROJECT_ROOT__|$ROOT|g" "$PLIST_SRC" >"$PLIST_DST"
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"
  echo "Installed $LABEL → $PLIST_DST"
  echo "Runs Mon–Fri at 9:00 PM in your Mac's local timezone."
  echo "Logs: $ROOT/logs/daily_pipeline_*.log"
}

uninstall() {
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST_DST"
  echo "Removed $LABEL"
}

status() {
  if launchctl print "gui/$(id -u)/$LABEL" &>/dev/null; then
    echo "Loaded: $LABEL"
    launchctl print "gui/$(id -u)/$LABEL" | head -20
  else
    echo "Not loaded: $LABEL"
    [[ -f "$PLIST_DST" ]] && echo "(plist exists at $PLIST_DST but job is not loaded)"
  fi
}

test_run() {
  ensure_prereqs || exit 1
  exec "$WRAPPER"
}

cmd="${1:-}"
case "$cmd" in
  install) install ;;
  uninstall) uninstall ;;
  status) status ;;
  test) test_run ;;
  *) usage; exit 1 ;;
esac
