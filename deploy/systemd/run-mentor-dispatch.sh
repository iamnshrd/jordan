#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)"

export JORDAN_HOME="${JORDAN_HOME:-$REPO_ROOT}"
export JORDAN_LOG_PATH="${JORDAN_LOG_PATH:-$JORDAN_HOME/workspace/logs/jordan.jsonl}"

cd "$JORDAN_HOME"

if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  . .venv/bin/activate
fi

mkdir -p "$(dirname "$JORDAN_LOG_PATH")"

exec python3 library/mentor_dispatch.py >>"$JORDAN_LOG_PATH" 2>&1
