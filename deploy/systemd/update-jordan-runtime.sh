#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)"
JORDAN_HOME="${JORDAN_HOME:-$REPO_ROOT}"

log() {
  printf '[update] %s\n' "$*"
}

clear_if_exists() {
  local path="$1"
  if [ -e "$path" ]; then
    : > "$path"
    log "cleared $path"
  fi
}

main() {
  log "updating repo in $JORDAN_HOME"
  cd "$JORDAN_HOME"
  git pull --ff-only

  mkdir -p "$JORDAN_HOME/workspace/logs"

  # Keep both paths in sync while older deployments may still emit the audit
  # file at the repo root.
  clear_if_exists "$JORDAN_HOME/conversation_audit.jsonl"
  clear_if_exists "$JORDAN_HOME/workspace/logs/conversation_audit.jsonl"
  clear_if_exists "$JORDAN_HOME/workspace/logs/openclaw.log"

  if [ -x /usr/local/bin/restart-jordan-runtime ]; then
    log "running restart-jordan-runtime"
    /usr/local/bin/restart-jordan-runtime
    exit 0
  fi

  log "restart helper not installed, falling back to direct service restart"
  systemctl --user restart openclaw-gateway-jordan-peterson.service
  systemctl --user status openclaw-gateway-jordan-peterson.service --no-pager --full
}

main "$@"
