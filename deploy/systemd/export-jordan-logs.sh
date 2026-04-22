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
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EXPORT_ROOT="${JORDAN_HOME}/workspace/logs/exports"
EXPORT_DIR="${EXPORT_ROOT}/${TIMESTAMP}"

mkdir -p "$EXPORT_DIR"

copy_if_exists() {
  local src="$1"
  local dst_name="$2"
  if [ -f "$src" ]; then
    cp "$src" "${EXPORT_DIR}/${dst_name}"
  fi
}

copy_if_exists "${JORDAN_HOME}/workspace/logs/jordan.jsonl" "jordan.jsonl"
copy_if_exists "${JORDAN_HOME}/workspace/logs/conversation_audit.jsonl" "conversation_audit.jsonl"
copy_if_exists "${JORDAN_HOME}/workspace/logs/openclaw.log" "openclaw.log"

tar -C "$EXPORT_ROOT" -czf "${EXPORT_ROOT}/jordan-logs-${TIMESTAMP}.tar.gz" "$TIMESTAMP"

printf '%s\n' "${EXPORT_ROOT}/jordan-logs-${TIMESTAMP}.tar.gz"
