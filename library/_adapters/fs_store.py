"""Filesystem-backed StateStore implementation.

Layout: ``{workspace}/{user_id}/{key}.json`` (or ``.jsonl`` for append-only
keys). For ``user_id == "default"``, new writes go to
``{workspace}/default/`` while reads still fall back to the legacy root-level
``{workspace}/`` files for backward compatibility with the pre-multi-tenant
layout.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from library.utils import current_trace_meta, now_iso

log = logging.getLogger('jordan')

_JSONL_KEYS = frozenset({'session_checkpoints', 'trace_events'})
_LEGACY_DEFAULT_KEYS = (
    'mentor_state',
    'mentor_events',
    'mentor_delays',
    'continuity',
    'continuity_summary',
    'session_state',
    'user_state',
    'effectiveness_memory',
    'progress_state',
    'context_graph',
    'user_reaction_estimate',
    'commitments',
    'session_checkpoints',
    'trace_events',
)


class FileSystemStore:
    """Persist per-user state as JSON files under *workspace*."""

    def __init__(self, workspace: Path):
        self._ws = workspace
        self._jsonl_cache: dict[tuple[str, str], tuple[float, list[dict]]] = {}

    # -- path helpers -------------------------------------------------------

    def _user_dir(self, user_id: str) -> Path:
        if user_id == 'default':
            return self._ws / 'default'
        return self._ws / user_id

    def _path(self, user_id: str, key: str) -> Path:
        ext = '.jsonl' if key in _JSONL_KEYS else '.json'
        return self._user_dir(user_id) / (key + ext)

    def _legacy_path(self, user_id: str, key: str) -> Path:
        ext = '.jsonl' if key in _JSONL_KEYS else '.json'
        return self._ws / (key + ext) if user_id == 'default' else self._path(user_id, key)

    def _lock_path(self, user_id: str, key: str) -> Path:
        return self._user_dir(user_id) / (key + '.lock')

    def _lock_file(self, user_id: str, key: str):
        import fcntl
        lock_path = self._lock_path(user_id, key)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(lock_path, 'a+', encoding='utf-8')
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        return fh

    # -- protocol methods ---------------------------------------------------

    def get_json(self, user_id: str, key: str,
                 default: dict | None = None) -> dict:
        p = self._path(user_id, key)
        if user_id == 'default' and not p.exists():
            p = self._legacy_path(user_id, key)
        if not p.exists():
            return default if default is not None else {}
        try:
            result = json.loads(p.read_text(encoding='utf-8'))
            if not isinstance(result, dict):
                log.warning('fs_store: %s is %s, expected dict — using default',
                            p, type(result).__name__)
                return default if default is not None else {}
            return result
        except (json.JSONDecodeError, OSError) as exc:
            log.warning('fs_store: failed to load %s: %s', p, exc)
            return default if default is not None else {}

    def put_json(self, user_id: str, key: str, value: dict) -> None:
        p = self._path(user_id, key)
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(value, f, ensure_ascii=False, indent=2)
            os.replace(tmp, str(p))
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        log.debug('fs_store.put_json', extra={
            'event': 'fs_store.put_json',
            'user_id': user_id,
            'state_key': key,
            'path': str(p),
            **current_trace_meta(),
        })

    def update_json(self, user_id: str, key: str,
                    mutator, default: dict | None = None) -> dict:
        lock_fh = self._lock_file(user_id, key)
        try:
            current = self.get_json(user_id, key, default=default)
            next_value = mutator(dict(current))
            if not isinstance(next_value, dict):
                raise TypeError(
                    f'update_json mutator for {key!r} must return dict, '
                    f'got {type(next_value).__name__}'
                )
            self.put_json(user_id, key, next_value)
            log.debug('fs_store.update_json', extra={
                'event': 'fs_store.update_json',
                'user_id': user_id,
                'state_key': key,
                **current_trace_meta(),
            })
            return next_value
        finally:
            lock_fh.close()

    def append_jsonl(self, user_id: str, key: str, event: dict) -> None:
        p = self._user_dir(user_id) / (key + '.jsonl')
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
        self._jsonl_cache.pop((user_id, key), None)
        log.debug('fs_store.append_jsonl', extra={
            'event': 'fs_store.append_jsonl',
            'user_id': user_id,
            'state_key': key,
            'path': str(p),
            **current_trace_meta(),
        })

    def read_jsonl(self, user_id: str, key: str) -> list[dict]:
        p = self._user_dir(user_id) / (key + '.jsonl')
        if user_id == 'default' and not p.exists():
            p = self._legacy_path(user_id, key)
        if not p.exists():
            return []
        try:
            mtime = p.stat().st_mtime
        except OSError:
            mtime = 0.0
        cache_key = (user_id, key)
        cached = self._jsonl_cache.get(cache_key)
        if cached and cached[0] == mtime:
            return cached[1]
        rows: list[dict] = []
        for line in p.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    rows.append(obj)
        self._jsonl_cache[cache_key] = (mtime, rows)
        return rows

    def audit_default_workspace_migration(self) -> dict:
        """Report legacy-vs-new file placement for the default user."""
        legacy_files: list[str] = []
        default_files: list[str] = []
        default_dir = self._user_dir('default')

        for key in _LEGACY_DEFAULT_KEYS:
            ext = '.jsonl' if key in _JSONL_KEYS else '.json'
            legacy_path = self._ws / (key + ext)
            default_path = default_dir / (key + ext)
            if legacy_path.exists():
                legacy_files.append(legacy_path.name)
            if default_path.exists():
                default_files.append(str(default_path.relative_to(self._ws)))

        return {
            'default_dir': str(default_dir),
            'legacy_root_files': sorted(legacy_files),
            'default_user_files': sorted(default_files),
            'legacy_root_count': len(legacy_files),
            'default_user_count': len(default_files),
            'migration_in_progress': bool(legacy_files),
        }
