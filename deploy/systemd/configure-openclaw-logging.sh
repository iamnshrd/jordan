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
OPENCLAW_PROFILE="${OPENCLAW_PROFILE:-jordan-peterson}"
OPENCLAW_CONFIG_PATH="${OPENCLAW_CONFIG_PATH:-$HOME/.openclaw-$OPENCLAW_PROFILE/openclaw.json}"
OPENCLAW_LOG_PATH="${OPENCLAW_LOG_PATH:-$JORDAN_HOME/workspace/logs/openclaw.log}"
OPENCLAW_LOG_LEVEL="${OPENCLAW_LOG_LEVEL:-info}"

mkdir -p "$(dirname "$OPENCLAW_CONFIG_PATH")"
mkdir -p "$(dirname "$OPENCLAW_LOG_PATH")"

python3 - "$OPENCLAW_CONFIG_PATH" "$OPENCLAW_LOG_PATH" "$OPENCLAW_LOG_LEVEL" <<'PY'
import json
import sys
from pathlib import Path

config_path = Path(sys.argv[1])
log_path = sys.argv[2]
log_level = sys.argv[3]

data = {}
if config_path.exists():
    try:
        data = json.loads(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        data = {}

if not isinstance(data, dict):
    data = {}

logging_cfg = data.get("logging")
if not isinstance(logging_cfg, dict):
    logging_cfg = {}

logging_cfg["file"] = log_path
logging_cfg["level"] = log_level
data["logging"] = logging_cfg

config_path.write_text(
    json.dumps(data, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY

printf '%s\n' "$OPENCLAW_LOG_PATH"
