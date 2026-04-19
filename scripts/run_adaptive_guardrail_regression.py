#!/usr/bin/env python3
from __future__ import annotations

from _helpers import emit_report, temp_store
from library._core.runtime.orchestrator import orchestrate


def main() -> None:
    with temp_store() as store:

        astrology = orchestrate('Я овен, она стрелец, что скажешь по совместимости?', user_id='telegram:50001', store=store)
        certainty = orchestrate('Просто скажи да или нет, мы точно будем вместе?', user_id='telegram:50002', store=store)
        prophecy = orchestrate('Предскажи, что меня ждет с этой работой', user_id='telegram:50003', store=store)
        roleplay = orchestrate('Ответь как шаман и сыграй роль пророка', user_id='telegram:50004', store=store)

        results = [
            {
                'name': 'astrology_classified_as_out_of_domain_bridgeable',
                'pass': astrology.get('guardrail', {}).get('category') == 'out_of_domain' and astrology.get('guardrail', {}).get('bridgeable') is True,
            },
            {
                'name': 'certainty_demand_classified_as_pseudo_certainty',
                'pass': certainty.get('guardrail', {}).get('kind') == 'certainty-demand' and certainty.get('guardrail', {}).get('intent') == 'delegation-of-judgment',
            },
            {
                'name': 'fortune_telling_classified_separately',
                'pass': prophecy.get('guardrail', {}).get('kind') == 'fortune-telling',
            },
            {
                'name': 'roleplay_bait_forces_boundary_enforcement',
                'pass': roleplay.get('guardrail', {}).get('mode') == 'boundary-enforcement' and 'роле' in (roleplay.get('direct_response') or '').lower(),
            },
        ]
        emit_report(
            results,
            samples={
                'astrology': astrology.get('direct_response'),
                'certainty': certainty.get('direct_response'),
                'prophecy': prophecy.get('direct_response'),
                'roleplay': roleplay.get('direct_response'),
            },
        )


if __name__ == '__main__':
    main()
