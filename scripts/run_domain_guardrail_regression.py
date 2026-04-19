#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report, temp_store
from library._core.runtime.orchestrator import orchestrate, orchestrate_for_llm


def main() -> None:
    with temp_store() as store:
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
        emit_report(
            results,
            samples={
                'astrology': r1.get('direct_response'),
                'esoteric': r2.get('direct_response'),
            },
        )


if __name__ == '__main__':
    main()
