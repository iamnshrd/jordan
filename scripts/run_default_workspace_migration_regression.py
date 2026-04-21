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

        legacy_continuity = root / 'continuity.json'
        legacy_trace = root / 'trace_events.jsonl'
        legacy_continuity.write_text(
            json.dumps({'legacy': True}, ensure_ascii=False),
            encoding='utf-8',
        )
        legacy_trace.write_text(
            json.dumps({'event': 'legacy-trace'}, ensure_ascii=False) + '\n',
            encoding='utf-8',
        )

        continuity = store.get_json('default', 'continuity')
        trace_rows = store.read_jsonl('default', 'trace_events')

        store.put_json('default', 'user_state', {'migrated': True})
        store.append_jsonl('default', 'trace_events', {'event': 'new-trace'})

        default_user_state = root / 'default' / 'user_state.json'
        default_trace = root / 'default' / 'trace_events.jsonl'

        results = [
            {
                'name': 'default_reads_fall_back_to_legacy_root_files',
                'pass': continuity.get('legacy') is True
                and bool(trace_rows)
                and trace_rows[0].get('event') == 'legacy-trace',
            },
            {
                'name': 'default_writes_go_to_default_subdirectory',
                'pass': default_user_state.exists() and default_trace.exists(),
            },
            {
                'name': 'legacy_root_files_are_not_overwritten_on_new_write',
                'pass': legacy_continuity.exists()
                and legacy_trace.exists()
                and 'new-trace' not in legacy_trace.read_text(encoding='utf-8'),
            },
        ]
        emit_report(
            results,
            samples={
                'default_dir_files': sorted(
                    str(p.relative_to(root)) for p in (root / 'default').glob('*')
                ),
            },
        )


if __name__ == '__main__':
    main()
