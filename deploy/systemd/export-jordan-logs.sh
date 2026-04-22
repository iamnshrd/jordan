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
RUNTIME_LOG="${JORDAN_HOME}/workspace/logs/jordan.jsonl"
CONVERSATION_AUDIT_LOG="${JORDAN_HOME}/workspace/logs/conversation_audit.jsonl"
OPENCLAW_LOG="${JORDAN_HOME}/workspace/logs/openclaw.log"

mkdir -p "$EXPORT_DIR"

copy_if_exists() {
  local src="$1"
  local dst_name="$2"
  if [ -f "$src" ]; then
    cp "$src" "${EXPORT_DIR}/${dst_name}"
  fi
}

build_export_audit() {
  local dst="$1"
  local source_kind="missing"

  if [ -s "$CONVERSATION_AUDIT_LOG" ]; then
    cp "$CONVERSATION_AUDIT_LOG" "$dst"
    source_kind="canonical_audit"
  elif [ -f "$CONVERSATION_AUDIT_LOG" ]; then
    : > "$dst"
  fi

  if [ "${source_kind}" = "missing" ] && [ -s "$RUNTIME_LOG" ]; then
    python3 - "$RUNTIME_LOG" "$dst" <<'PY'
import json
import sys
from pathlib import Path

runtime_path = Path(sys.argv[1])
export_path = Path(sys.argv[2])

def keep_event(row: dict) -> bool:
    event = str(row.get("event") or "")
    msg = str(row.get("msg") or "")
    return (
        event.startswith("conversation.")
        or event.startswith("telegram.jordan_adapter_")
        or event in {"telegram.delivery_succeeded", "telegram.inbound", "telegram.context_built", "telegram.dispatch_started"}
        or msg.startswith("conversation.")
    )

export_path.parent.mkdir(parents=True, exist_ok=True)
with runtime_path.open("r", encoding="utf-8", errors="replace") as src, export_path.open("w", encoding="utf-8") as dst:
    for line in src:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if keep_event(row):
            dst.write(json.dumps(row, ensure_ascii=False) + "\n")
PY
    source_kind="derived_from_runtime"
  fi

  if [ "${source_kind}" = "missing" ]; then
    : > "$dst"
  fi

  printf '%s\n' "$source_kind"
}

write_export_manifest() {
  local audit_source="$1"
  local manifest="${EXPORT_DIR}/manifest.json"
  python3 - "$manifest" "$RUNTIME_LOG" "$CONVERSATION_AUDIT_LOG" "$OPENCLAW_LOG" "$EXPORT_DIR/conversation_audit.jsonl" "$audit_source" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

manifest_path = Path(sys.argv[1])
runtime_path = Path(sys.argv[2])
audit_path = Path(sys.argv[3])
openclaw_path = Path(sys.argv[4])
export_audit_path = Path(sys.argv[5])
audit_source = sys.argv[6]

def stat_payload(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "size_bytes": 0, "mtime": ""}
    st = path.stat()
    return {
        "exists": True,
        "size_bytes": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
    }

payload = {
    "exported_at": datetime.now(timezone.utc).isoformat(),
    "runtime_log": stat_payload(runtime_path),
    "canonical_conversation_audit_log": stat_payload(audit_path),
    "openclaw_log": stat_payload(openclaw_path),
    "exported_conversation_audit_log": stat_payload(export_audit_path),
    "conversation_audit_source": audit_source,
}

manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

copy_if_exists "$RUNTIME_LOG" "jordan.jsonl"
AUDIT_SOURCE="$(build_export_audit "${EXPORT_DIR}/conversation_audit.jsonl")"
copy_if_exists "$OPENCLAW_LOG" "openclaw.log"
write_export_manifest "$AUDIT_SOURCE"

tar -C "$EXPORT_ROOT" -czf "${EXPORT_ROOT}/jordan-logs-${TIMESTAMP}.tar.gz" "$TIMESTAMP"

printf '%s\n' "${EXPORT_ROOT}/jordan-logs-${TIMESTAMP}.tar.gz"
