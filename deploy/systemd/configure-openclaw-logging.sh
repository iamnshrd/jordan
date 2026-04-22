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
