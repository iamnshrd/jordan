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

OPS_JORDAN_HOME="${JORDAN_HOME:-$(resolve_jordan_home)}"
RUNTIME_ROOT="${JORDAN_RUNTIME_ROOT:-$OPS_JORDAN_HOME/runtime}"
RELEASES_DIR="${RUNTIME_ROOT}/releases"
CURRENT_LINK="${RUNTIME_ROOT}/current"
SHARED_WORKSPACE="${OPS_JORDAN_HOME}/workspace"
SHARED_VENV="${OPS_JORDAN_HOME}/.venv"

log() {
  jordan_log activate-release "$*"
}

usage() {
  cat <<'EOF'
Usage: activate-jordan-release.sh <bundle.tar.gz>
EOF
}

require_bundle() {
  if [ $# -lt 1 ]; then
    usage >&2
    exit 1
  fi
  if [ ! -f "$1" ]; then
    log "bundle not found: $1"
    exit 1
  fi
}

main() {
  require_bundle "$@"
  local bundle_path="$1"
  local top_level
  local release_manifest
  local release_id
  local release_dir
  local tmp_dir

  top_level="$(tar -tzf "$bundle_path" | head -n 1 | cut -d/ -f1)"
  if [ -z "$top_level" ]; then
    log "failed to read bundle layout"
    exit 1
  fi

  release_manifest="$(
    tar -xOzf "$bundle_path" "${top_level}/release-manifest.json" 2>/dev/null || true
  )"
  if [ -z "$release_manifest" ]; then
    log "bundle is missing release-manifest.json"
    exit 1
  fi

  release_id="$(
    RELEASE_MANIFEST_JSON="$release_manifest" python3 - "$top_level" <<'PY'
import json
import os
import sys

payload = json.loads(os.environ.get("RELEASE_MANIFEST_JSON") or "{}")
release_id = str(payload.get("release_id") or "").strip()
if not release_id:
    release_id = sys.argv[1]
print(release_id)
PY
  )"

  mkdir -p "$RUNTIME_ROOT" "$RELEASES_DIR" "$SHARED_WORKSPACE/logs"
  release_dir="${RELEASES_DIR}/${release_id}"
  if [ -e "$release_dir" ]; then
    log "release already exists: $release_dir"
    exit 1
  fi

  tmp_dir="$(mktemp -d "${RUNTIME_ROOT}/.activate.XXXXXX")"
  trap 'rm -rf "$tmp_dir"' EXIT
  tar -xzf "$bundle_path" -C "$tmp_dir"
  mv "$tmp_dir/$top_level" "$release_dir"

  rm -rf "$release_dir/workspace"
  ln -s "$SHARED_WORKSPACE" "$release_dir/workspace"

  if [ -e "$SHARED_VENV" ] && [ ! -e "$release_dir/.venv" ]; then
    ln -s "$SHARED_VENV" "$release_dir/.venv"
  fi

  ln -sfn "$release_dir" "${CURRENT_LINK}.next"
  mv -Tf "${CURRENT_LINK}.next" "$CURRENT_LINK"

  log "activated release ${release_id}"
  log "current runtime: $CURRENT_LINK"

  if [ "${JORDAN_SKIP_RESTART:-0}" = "1" ]; then
    log "restart skipped by JORDAN_SKIP_RESTART=1"
    exit 0
  fi

  if [ -x /usr/local/bin/restart-jordan-runtime ]; then
    /usr/local/bin/restart-jordan-runtime
    exit 0
  fi

  if [ -x "$CURRENT_LINK/deploy/systemd/restart-jordan-runtime.sh" ]; then
    "$CURRENT_LINK/deploy/systemd/restart-jordan-runtime.sh"
    exit 0
  fi

  log "restart helper not found; release activated without restart"
}

main "$@"
