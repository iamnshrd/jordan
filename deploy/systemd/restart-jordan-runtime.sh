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
  printf '[restart] %s\n' "$*"
}

run_jordan_warmup() {
  local python_bin module
  python_bin="${OPENCLAW_JORDAN_BRIDGE_PYTHON:-}"
  module="${OPENCLAW_JORDAN_BRIDGE_MODULE:-library}"
  if [ -z "$python_bin" ] && [ -x "$JORDAN_HOME/.venv/bin/python3" ]; then
    python_bin="$JORDAN_HOME/.venv/bin/python3"
  fi
  if [ -z "$python_bin" ]; then
    python_bin="python3"
  fi

  log "warming Jordan runtime"
  if (cd "$JORDAN_HOME" && "$python_bin" -m "$module" warmup --timeout-seconds 60 --retry-interval 2); then
    log "Jordan warmup complete"
  else
    log "Jordan warmup failed; continuing"
  fi
}

_user_uid() {
  id -u
}

_user_systemctl() {
  local uid runtime_dir bus
  uid="$(_user_uid)"
  runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$uid}"
  bus="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$runtime_dir/bus}"
  XDG_RUNTIME_DIR="$runtime_dir" DBUS_SESSION_BUS_ADDRESS="$bus" systemctl --user "$@"
}

user_bus_available() {
  local uid runtime_dir
  uid="$(_user_uid)"
  runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$uid}"
  [ -S "$runtime_dir/bus" ]
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
  if ! user_bus_available; then
    return 1
  fi
  if _user_systemctl list-unit-files "$unit" --no-legend 2>/dev/null | grep -q "^$unit"; then
    log "restarting user unit $unit"
    _user_systemctl restart "$unit"
    return 0
  fi
  return 1
}

restart_user_active_match() {
  local pattern="$1"
  local restarted=0
  if ! user_bus_available; then
    return 1
  fi
  while IFS= read -r unit; do
    [ -n "$unit" ] || continue
    log "restarting user unit $unit"
    _user_systemctl restart "$unit"
    restarted=1
  done < <(_user_systemctl list-units --type=service --all --no-legend | awk '{print $1}' | grep -E "$pattern" || true)
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
  elif ! user_bus_available; then
    log "OpenClaw user bus unavailable; run this helper without sudo or ensure /run/user/$(_user_uid)/bus is present"
  else
    log "no OpenClaw service units found"
  fi

  log "status snapshot"
  systemctl --no-pager --full status jordan-mentor-dispatch.service || true
  systemctl --no-pager --full status jordan-mentor-dispatch.timer || true
  if user_bus_available; then
    _user_systemctl --no-pager --full status openclaw-gateway-jordan-peterson.service || true
  fi
  run_jordan_warmup
}

main "$@"
