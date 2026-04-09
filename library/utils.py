#!/usr/bin/env python3
"""Shared utility functions used across multiple modules."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger('jordan')


def now_iso():
    """Return current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default=None):
    """Read and parse a JSON file, returning *default* if it is missing or broken."""
    p = Path(path)
    if not p.exists():
        return default if default is not None else {}
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning('Failed to load %s: %s', path, exc)
        return default if default is not None else {}


def save_json(path, data, ensure_ascii=False, indent=2):
    """Atomically-ish write *data* as pretty-printed JSON."""
    Path(path).write_text(
        json.dumps(data, ensure_ascii=ensure_ascii, indent=indent),
        encoding='utf-8',
    )


def load_checkpoints(path):
    """Read a JSONL checkpoint file into a list of dicts."""
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def fts_query(text):
    """Build a simple OR-based FTS5 query from natural language."""
    words = [
        w
        for w in ''.join(
            ch if ch.isalnum() or ch.isspace() else ' ' for ch in text.lower()
        ).split()
        if len(w) >= 3
    ]
    return ' OR '.join(words[:8]) if words else 'meaning'


def slugify(name):
    """Produce a filesystem-safe slug from *name*."""
    out = []
    for ch in name.lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in (' ', '-', '_', '.'):
            out.append('-')
    slug = ''.join(out)
    while '--' in slug:
        slug = slug.replace('--', '-')
    return slug.strip('-')
