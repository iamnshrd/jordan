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

        run_proc = subprocess.run(
            [sys.executable, '-m', 'library', 'run', 'Я застрял и не понимаю, с чего начать'],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        prompt_proc = subprocess.run(
            [sys.executable, '-m', 'library', 'prompt', 'Я застрял и не понимаю, с чего начать'],
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
                'pass': run_proc.returncode == 0,
            },
            {
                'name': 'cli_prompt_succeeds',
                'pass': prompt_proc.returncode == 0,
            },
            {
                'name': 'runtime_log_created',
                'pass': runtime_log.exists(),
            },
            {
                'name': 'runtime_log_contains_conversation_inbound',
                'pass': any(row.get('event') == 'conversation.inbound' for row in rows),
            },
            {
                'name': 'runtime_log_contains_conversation_outbound',
                'pass': any(
                    row.get('event') == 'conversation.outbound'
                    and bool(row.get('response'))
                    for row in rows
                ),
            },
            {
                'name': 'runtime_log_contains_prompt_prepared',
                'pass': any(row.get('event') == 'conversation.prompt_prepared' for row in rows),
            },
        ]
        emit_report(results)


if __name__ == '__main__':
    main()
