#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
COMMON_SH="$SCRIPT_DIR/common.sh"
if [ ! -r "$COMMON_SH" ] && [ -r /etc/default/jordan ]; then
  COMMON_JORDAN_HOME="$(
    bash -lc 'set -a; . /etc/default/jordan >/dev/null 2>&1; printf %s "${JORDAN_HOME:-}"'
  )"
  if [ -n "$COMMON_JORDAN_HOME" ] && [ -r "$COMMON_JORDAN_HOME/deploy/systemd/common.sh" ]; then
    COMMON_SH="$COMMON_JORDAN_HOME/deploy/systemd/common.sh"
  fi
fi
if [ ! -r "$COMMON_SH" ] && [ -r "$PWD/deploy/systemd/common.sh" ]; then
  COMMON_SH="$PWD/deploy/systemd/common.sh"
fi
. "$COMMON_SH"

JORDAN_HOME="$(resolve_jordan_home)"

log() {
  jordan_log update "$*"
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
