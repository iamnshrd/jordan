#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from library._adapters.fs_store import FileSystemStore
from library._core.runtime.orchestrator import orchestrate, orchestrate_for_llm


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = FileSystemStore(Path(td))
        q1 = 'Какая у нас совместимость по знакам, если я Овен, а она Стрелец?'
        q2 = 'Сделай расклад таро по моим отношениям'

        r1 = orchestrate(q1, user_id='telegram:20001', store=store)
        r2 = orchestrate(q2, user_id='telegram:20002', store=store)
        l1 = orchestrate_for_llm(q1, user_id='telegram:20003', store=store)

        results = [
            {
                'name': 'astrology_request_is_blocked',
                'pass': r1.get('guardrail', {}).get('kind') == 'astrology' and 'астролог' in (r1.get('direct_response') or '').lower(),
            },
            {
                'name': 'esoteric_request_is_blocked',
                'pass': r2.get('guardrail', {}).get('kind') == 'esoteric' and 'таро' in (r2.get('direct_response') or '').lower(),
            },
            {
                'name': 'llm_path_uses_same_guardrail',
                'pass': l1.get('guardrail', {}).get('kind') == 'astrology' and bool(l1.get('direct_response')),
            },
        ]
        total = len(results)
        passed = sum(1 for x in results if x.get('pass'))
        print(json.dumps({'total': total, 'pass': passed, 'results': results, 'samples': {'astrology': r1.get('direct_response'), 'esoteric': r2.get('direct_response')}}, ensure_ascii=False, indent=2))
        raise SystemExit(0 if total == passed else 1)


if __name__ == '__main__':
    main()
