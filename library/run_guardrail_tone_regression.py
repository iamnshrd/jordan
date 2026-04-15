#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from library._adapters.fs_store import FileSystemStore
from library._core.runtime.orchestrator import orchestrate

FORBIDDEN = [
    'если хотите, я могу',
    'по-петerson',
    'по-питерсон',
    'могу ответить жёстче',
    'могу ответить жестче',
    'в таком стиле',
    'в этом стиле',
]


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = FileSystemStore(Path(td))
        r1 = orchestrate('Я овен, она стрелец, что скажешь по совместимости?', user_id='telegram:41001', store=store)
        r2 = orchestrate('Сделай расклад таро на наши отношения', user_id='telegram:41002', store=store)

        text1 = (r1.get('direct_response') or '').lower()
        text2 = (r2.get('direct_response') or '').lower()
        results = [
            {
                'name': 'astrology_guardrail_has_no_meta_style_leakage',
                'pass': not any(x in text1 for x in FORBIDDEN),
            },
            {
                'name': 'esoteric_guardrail_has_no_meta_style_leakage',
                'pass': not any(x in text2 for x in FORBIDDEN),
            },
        ]
        total = len(results)
        passed = sum(1 for x in results if x.get('pass'))
        print(json.dumps({'total': total, 'pass': passed, 'results': results, 'samples': {'astrology': r1.get('direct_response'), 'esoteric': r2.get('direct_response')}}, ensure_ascii=False, indent=2))
        raise SystemExit(0 if total == passed else 1)


if __name__ == '__main__':
    main()
