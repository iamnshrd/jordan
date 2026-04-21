#!/usr/bin/env bash
set -euo pipefail

cd /opt/jordan

if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  . .venv/bin/activate
fi

mkdir -p /opt/jordan/workspace/logs

exec python3 library/mentor_dispatch.py
