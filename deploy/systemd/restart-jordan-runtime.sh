#!/usr/bin/env bash
set -euo pipefail

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

main() {
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
  else
    log "no OpenClaw service units found"
  fi

  log "status snapshot"
  systemctl --no-pager --full status jordan-mentor-dispatch.service || true
  systemctl --no-pager --full status jordan-mentor-dispatch.timer || true
}

main "$@"
