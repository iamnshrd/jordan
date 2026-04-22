#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

sys.dont_write_bytecode = True


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def emit_report(results: list[dict], **extra) -> None:
    total = len(results)
    passed = sum(1 for row in results if row.get('pass'))
    payload = {'total': total, 'pass': passed, 'results': results}
    payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if total == passed else 1)


@contextmanager
def temp_store():
    from library._adapters.fs_store import FileSystemStore

    with tempfile.TemporaryDirectory() as td:
        yield FileSystemStore(Path(td))


def simulate_dispatch(users: list[dict], decisions: dict[str, dict], *,
                      include_target: bool = False,
                      default_decision: dict | None = None) -> list[dict]:
    outputs = []
    fallback = default_decision or {'skip': True, 'skip_reason': 'no-decision'}
    for item in users:
        if not item.get('enabled', True):
            continue
        user_id = item.get('user_id', '')
        target = item.get('target', '')
        if user_id == 'default':
            outputs.append({
                'user_id': user_id,
                'skip': True,
                'skip_reason': 'default-user-id-blocked',
            })
            continue
        if not target:
            outputs.append({
                'user_id': user_id,
                'skip': True,
                'skip_reason': 'missing-user-target',
            })
            continue
        decision = decisions.get(user_id, fallback)
        row = {'user_id': user_id, **decision}
        if include_target:
            row['target'] = target
        outputs.append(row)
    return outputs


def run_suite(script_names: list[str], suite_name: str) -> None:
    results = []
    env = dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    for name in script_names:
        path = SCRIPT_DIR / name
        proc = subprocess.run(
            [sys.executable, '-B', str(path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            env=env,
        )
        try:
            payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except json.JSONDecodeError:
            payload = {}
        results.append({
            'name': name,
            'pass': proc.returncode == 0,
            'returncode': proc.returncode,
            'reported_pass': payload.get('pass'),
            'reported_total': payload.get('total'),
            'stderr': proc.stderr.strip(),
        })
    emit_report(results, suite=suite_name)
