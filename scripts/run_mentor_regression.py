#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from _helpers import REPO_ROOT, emit_report, temp_store
from library._core.mentor.checkins import evaluate, save_state
from library._core.state_store import KEY_CONTINUITY, KEY_COMMITMENTS

CASES_PATH = REPO_ROOT / 'library' / 'mentor_regression_cases.json'


def main() -> None:
    cases = json.loads(CASES_PATH.read_text())
    report = []
    passed = 0

    for case in cases:
        with temp_store() as store:
            if case.get('state_override'):
                state = {'mode': 'standard'}
                state.update(case['state_override'])
                save_state(state, store=store)
            if case.get('continuity_override'):
                store.put_json('default', KEY_CONTINUITY, case['continuity_override'])
            if case.get('commitments_override'):
                store.put_json('default', KEY_COMMITMENTS, case['commitments_override'])

            if case.get('reaction_override'):
                reaction_value = case['reaction_override']
                with patch('library._core.mentor.checkins.estimate_reaction', return_value={'question': case.get('question', ''), 'user_reaction_estimate': reaction_value}):
                    result = evaluate(case.get('question', ''), store=store)
            else:
                result = evaluate(case.get('question', ''), store=store)

            ok = True
            reasons = []
            if 'expect_skip' in case and result.get('skip') != case['expect_skip']:
                ok = False
                reasons.append(f"skip={result.get('skip')} != {case['expect_skip']}")
            if case.get('expect_skip_reason') and result.get('skip_reason') != case['expect_skip_reason']:
                ok = False
                reasons.append(f"skip_reason={result.get('skip_reason')} != {case['expect_skip_reason']}")
            if case.get('expect_route') and result.get('route') != case['expect_route']:
                ok = False
                reasons.append(f"route={result.get('route')} != {case['expect_route']}")
            if case.get('expect_effective_mode') and result.get('effective_mode') != case['expect_effective_mode']:
                ok = False
                reasons.append(f"effective_mode={result.get('effective_mode')} != {case['expect_effective_mode']}")
            types = [e.get('type') for e in (result.get('events') or [])]
            prompts = [e.get('prompt', '') for e in (result.get('events') or [])]
            if case.get('expect_event_types_any'):
                if not any(t in types for t in case['expect_event_types_any']):
                    ok = False
                    reasons.append(f"events={types} missing any of {case['expect_event_types_any']}")
            if case.get('expect_event_types_all'):
                missing = [t for t in case['expect_event_types_all'] if t not in types]
                if missing:
                    ok = False
                    reasons.append(f"events={types} missing required {missing}")
            if case.get('forbid_event_types'):
                forbidden = [t for t in case['forbid_event_types'] if t in types]
                if forbidden:
                    ok = False
                    reasons.append(f"events={types} unexpectedly contains forbidden {forbidden}")
            if case.get('expect_top_event_type'):
                top = types[0] if types else ''
                if top != case['expect_top_event_type']:
                    ok = False
                    reasons.append(f"top_event={top} != {case['expect_top_event_type']}")
            if case.get('expect_event_prompt_contains'):
                needle = case['expect_event_prompt_contains']
                if not any(needle in p for p in prompts):
                    ok = False
                    reasons.append(f"prompts missing substring {needle!r}")
            selection_audit = ((result.get('selection_context') or {}).get('selection_audit') or {})
            if case.get('expect_selection_audit'):
                winner = dict(selection_audit.get('winner') or {})
                runner_up = dict(selection_audit.get('runner_up') or {})
                why_won = list(selection_audit.get('why_won') or [])
                if not winner.get('event_type'):
                    ok = False
                    reasons.append('selection_audit missing winner event_type')
                if case['expect_selection_audit'].get('winner_in_top'):
                    top = types[0] if types else ''
                    if winner.get('event_type') != top:
                        ok = False
                        reasons.append(f"selection_audit winner={winner.get('event_type')} != top_event={top}")
                if case['expect_selection_audit'].get('runner_up_required') and not runner_up.get('event_type'):
                    ok = False
                    reasons.append('selection_audit missing runner_up event_type')
                if case['expect_selection_audit'].get('why_won_required') and not why_won:
                    ok = False
                    reasons.append('selection_audit missing why_won entries')
                factor_any = case['expect_selection_audit'].get('why_won_factor_any') or []
                if factor_any and not any((row.get('factor') in factor_any) for row in why_won):
                    ok = False
                    reasons.append(f"selection_audit why_won missing any of {factor_any}")

            if ok:
                passed += 1
            report.append({
                'name': case['name'],
                'pass': ok,
                'reasons': reasons,
                'route': result.get('route'),
                'effective_mode': result.get('effective_mode'),
                'skip': result.get('skip'),
                'skip_reason': result.get('skip_reason'),
                'event_types': [e.get('type') for e in (result.get('events') or [])],
                'selection_audit': ((result.get('selection_context') or {}).get('selection_audit') or {}),
            })

    emit_report(report)


if __name__ == '__main__':
    main()
