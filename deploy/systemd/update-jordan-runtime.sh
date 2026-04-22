#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)"

resolve_jordan_home() {
  if [ -n "${JORDAN_HOME:-}" ]; then
    printf '%s\n' "$JORDAN_HOME"
    return 0
  fi

  if [ -r /etc/default/jordan ]; then
    local from_defaults
    from_defaults="$(
      bash -lc 'set -a; . /etc/default/jordan >/dev/null 2>&1; printf %s "${JORDAN_HOME:-}"'
    )"
    if [ -n "$from_defaults" ]; then
      printf '%s\n' "$from_defaults"
      return 0
    fi
  fi

  if [ -d "$PWD/.git" ] || [ -f "$PWD/.git" ]; then
    printf '%s\n' "$PWD"
    return 0
  fi

  printf '%s\n' "$REPO_ROOT"
}

JORDAN_HOME="$(resolve_jordan_home)"

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
