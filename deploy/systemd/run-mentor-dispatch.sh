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

export JORDAN_HOME="${JORDAN_HOME:-$(resolve_jordan_home)}"
export JORDAN_LOG_PATH="${JORDAN_LOG_PATH:-$JORDAN_HOME/workspace/logs/jordan.jsonl}"

cd "$JORDAN_HOME"

if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  . .venv/bin/activate
fi

mkdir -p "$(dirname "$JORDAN_LOG_PATH")"

exec python3 library/mentor_dispatch.py >>"$JORDAN_LOG_PATH" 2>&1
