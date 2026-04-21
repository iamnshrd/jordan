#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from _helpers import REPO_ROOT, emit_report


def main() -> None:
    with TemporaryDirectory() as tmp:
        runtime_log = Path(tmp) / 'jordan.jsonl'
        env = dict(os.environ)
        env['JORDAN_LOG_PATH'] = str(runtime_log)

        proc = subprocess.run(
            [sys.executable, '-m', 'library', 'run', 'Я застрял и не понимаю, с чего начать'],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )

        rows = []
        if runtime_log.exists():
            for line in runtime_log.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        results = [
            {
                'name': 'cli_run_succeeds',
                'pass': proc.returncode == 0,
            },
            {
                'name': 'runtime_log_created',
                'pass': runtime_log.exists(),
            },
            {
                'name': 'runtime_log_contains_trace_started',
                'pass': any(row.get('event') == 'trace.started' for row in rows),
            },
            {
                'name': 'runtime_log_contains_orchestrator_resolution',
                'pass': any(row.get('event') == 'orchestrator.decision_resolved' for row in rows),
            },
        ]
        emit_report(results)


if __name__ == '__main__':
    main()
