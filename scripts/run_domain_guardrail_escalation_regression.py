#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report, temp_store
from library._core.runtime.orchestrator import orchestrate


def main() -> None:
    with temp_store() as store:
        user_id = 'telegram:30001'

        r1 = orchestrate('Я овен, она стрелец, какая совместимость?', user_id=user_id, store=store)
        r2 = orchestrate('А по планетам тогда что скажешь?', user_id=user_id, store=store)
        r3 = orchestrate('Ну а по знакам всё-таки можешь сказать?', user_id=user_id, store=store)
        r4 = orchestrate('Ладно, тогда разберем реальный конфликт, я давлю, она уходит в дистанцию', user_id=user_id, store=store)

        results = [
            {
                'name': 'first_out_of_domain_is_soft',
                'pass': r1.get('guardrail', {}).get('level') == 'soft',
            },
            {
                'name': 'second_out_of_domain_is_firm',
                'pass': r2.get('guardrail', {}).get('level') == 'firm' and 'снова' in (r2.get('direct_response') or '').lower(),
            },
            {
                'name': 'third_out_of_domain_is_hard',
                'pass': r3.get('guardrail', {}).get('level') == 'hard' and 'нет.' in (r3.get('direct_response') or '').lower(),
            },
            {
                'name': 'normal_question_resets_streak',
                'pass': not r4.get('guardrail') and r4.get('action') in {'answer-directly', 'ask-clarifying-question', 'respond-with-kb'},
            },
        ]
        emit_report(
            results,
            samples={
                'soft': r1.get('direct_response'),
                'firm': r2.get('direct_response'),
                'hard': r3.get('direct_response'),
            },
        )


if __name__ == '__main__':
    main()
