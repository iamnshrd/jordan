#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: ingest_new_file.sh <path-to-pdf>"
  exit 1
fi

SRC="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST_DIR="$SCRIPT_DIR/incoming"
mkdir -p "$DEST_DIR"
cp "$SRC" "$DEST_DIR/"
python -m library ingest auto
