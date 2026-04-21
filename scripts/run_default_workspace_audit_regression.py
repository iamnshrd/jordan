#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from _helpers import emit_report
from library._adapters.fs_store import FileSystemStore


def main() -> None:
    with TemporaryDirectory() as td:
        root = Path(td)
        store = FileSystemStore(root)

        (root / 'continuity.json').write_text(
            json.dumps({'legacy': True}, ensure_ascii=False),
            encoding='utf-8',
        )
        store.put_json('default', 'user_state', {'fresh': True})
        store.append_jsonl('default', 'trace_events', {'event': 'fresh-trace'})

        audit = store.audit_default_workspace_migration()
        results = [
            {
                'name': 'audit_reports_legacy_root_files',
                'pass': 'continuity.json' in (audit.get('legacy_root_files') or []),
            },
            {
                'name': 'audit_reports_default_user_files',
                'pass': 'default/user_state.json' in (audit.get('default_user_files') or [])
                and 'default/trace_events.jsonl' in (audit.get('default_user_files') or []),
            },
            {
                'name': 'audit_marks_migration_in_progress_when_legacy_exists',
                'pass': audit.get('migration_in_progress') is True,
            },
        ]
        emit_report(results, samples={'audit': audit})


if __name__ == '__main__':
    main()
