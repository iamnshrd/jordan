"""Filesystem-backed StateStore implementation.

Layout: ``{workspace}/{user_id}/{key}.json`` (or ``.jsonl`` for append-only
keys).  When *user_id* is ``"default"`` the files live directly in
``{workspace}/`` for backward compatibility with the pre-multi-tenant layout.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from library.utils import now_iso

log = logging.getLogger('jordan')

_JSONL_KEYS = frozenset({'session_checkpoints'})


class FileSystemStore:
    """Persist per-user state as JSON files under *workspace*."""

    def __init__(self, workspace: Path):
        self._ws = workspace

    # -- path helpers -------------------------------------------------------

    def _user_dir(self, user_id: str) -> Path:
        if user_id == 'default':
            return self._ws
        return self._ws / user_id

    def _path(self, user_id: str, key: str) -> Path:
        ext = '.jsonl' if key in _JSONL_KEYS else '.json'
        return self._user_dir(user_id) / (key + ext)

    # -- protocol methods ---------------------------------------------------

    def get_json(self, user_id: str, key: str,
                 default: dict | None = None) -> dict:
        p = self._path(user_id, key)
        if not p.exists():
            return default if default is not None else {}
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError) as exc:
            log.warning('fs_store: failed to load %s: %s', p, exc)
            return default if default is not None else {}

    def put_json(self, user_id: str, key: str, value: dict) -> None:
        p = self._path(user_id, key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

    def append_jsonl(self, user_id: str, key: str, event: dict) -> None:
        p = self._user_dir(user_id) / (key + '.jsonl')
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')

    def read_jsonl(self, user_id: str, key: str) -> list[dict]:
        p = self._user_dir(user_id) / (key + '.jsonl')
        if not p.exists():
            return []
        rows: list[dict] = []
        for line in p.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows
