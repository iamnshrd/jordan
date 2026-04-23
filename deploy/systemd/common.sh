#!/usr/bin/env bash

resolve_jordan_home() {
  local script_dir repo_root
  script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  repo_root="$(CDPATH= cd -- "$script_dir/../.." && pwd)"

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

  printf '%s\n' "$repo_root"
}

resolve_jordan_runtime_home() {
  local base_home="${1:-}"
  if [ -z "$base_home" ]; then
    base_home="$(resolve_jordan_home)"
  fi

  if [ -L "$base_home/runtime/current" ] || [ -d "$base_home/runtime/current" ]; then
    printf '%s\n' "$base_home/runtime/current"
    return 0
  fi

  printf '%s\n' "$base_home"
}

jordan_log() {
  local prefix="$1"
  shift
  printf '[%s] %s\n' "$prefix" "$*"
}
