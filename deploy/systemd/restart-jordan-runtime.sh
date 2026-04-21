#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)"
JORDAN_HOME="${JORDAN_HOME:-$REPO_ROOT}"

log() {
  printf '[restart] %s\n' "$*"
}

restart_if_exists() {
  local unit="$1"
  if systemctl list-unit-files "$unit" --no-legend 2>/dev/null | grep -q "^$unit"; then
    log "restarting $unit"
    systemctl restart "$unit"
    return 0
  fi
  return 1
}

restart_active_match() {
  local pattern="$1"
  local restarted=0
  while IFS= read -r unit; do
    [ -n "$unit" ] || continue
    log "restarting $unit"
    systemctl restart "$unit"
    restarted=1
  done < <(systemctl list-units --type=service --all --no-legend | awk '{print $1}' | grep -E "$pattern" || true)
  return "$restarted"
}

restart_user_if_exists() {
  local unit="$1"
  if systemctl --user list-unit-files "$unit" --no-legend 2>/dev/null | grep -q "^$unit"; then
    log "restarting user unit $unit"
    systemctl --user restart "$unit"
    return 0
  fi
  return 1
}

restart_user_active_match() {
  local pattern="$1"
  local restarted=0
  while IFS= read -r unit; do
    [ -n "$unit" ] || continue
    log "restarting user unit $unit"
    systemctl --user restart "$unit"
    restarted=1
  done < <(systemctl --user list-units --type=service --all --no-legend | awk '{print $1}' | grep -E "$pattern" || true)
  return "$restarted"
}

main() {
  if [ -x "$JORDAN_HOME/deploy/systemd/configure-openclaw-logging.sh" ]; then
    log "configuring OpenClaw file logging"
    "$JORDAN_HOME/deploy/systemd/configure-openclaw-logging.sh" >/dev/null
  fi

  log "daemon-reload"
  systemctl daemon-reload

  log "restarting Jordan systemd units"
  restart_if_exists "jordan-mentor-dispatch.timer" || log "unit not found: jordan-mentor-dispatch.timer"
  restart_if_exists "jordan-mentor-dispatch.service" || log "unit not found: jordan-mentor-dispatch.service"

  log "restarting OpenClaw gateway/service units"
  if restart_if_exists "openclaw-gateway.service"; then
    :
  elif restart_active_match '^openclaw.*\.service$'; then
    :
  elif restart_user_if_exists "openclaw-gateway-jordan-peterson.service"; then
    :
  elif restart_user_active_match '^openclaw.*\.service$'; then
    :
  else
    log "no OpenClaw service units found"
  fi

  log "status snapshot"
  systemctl --no-pager --full status jordan-mentor-dispatch.service || true
  systemctl --no-pager --full status jordan-mentor-dispatch.timer || true
  systemctl --user --no-pager --full status openclaw-gateway-jordan-peterson.service || true
}

main "$@"
