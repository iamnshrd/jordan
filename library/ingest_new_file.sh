#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: ingest_new_file.sh <path-to-pdf>"
  exit 1
fi

SRC="$1"
DEST_DIR="/root/.openclaw/multi-agent/agents/jordan-peterson/library/incoming"
mkdir -p "$DEST_DIR"
cp "$SRC" "$DEST_DIR/"
python3 /root/.openclaw/multi-agent/agents/jordan-peterson/library/ingest_auto.py
