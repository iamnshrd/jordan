#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from library._adapters.fs_store import FileSystemStore
from library._core.mentor.effectiveness import summarize
from library._core.state_store import KEY_MENTOR_STATE, KEY_MENTOR_DELAYS


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        store = FileSystemStore(Path(td))
        store.put_json('default', KEY_MENTOR_STATE, {
            'event_outcomes': {
                'career-vocation::commitment-check': {
                    'used': 4,
                    'helpful': 2,
                    'neutral': 0,
                    'resisted': 1,
                    'ignored': 0,
                    'movement': 1,
                    'movement-small': 1,
                    'reflection-with-intent': 0,
                    'truthful-delay': 1,
                    'lazy-delay': 0,
                    'compliance-theater': 0,
                    'movement-theater': 0,
                    'moral-posturing': 0,
                    'defensive-intelligence': 0,
                },
                'career-vocation::mentor-summary': {
                    'used': 3,
                    'helpful': 0,
                    'neutral': 1,
                    'resisted': 1,
                    'ignored': 0,
                    'movement': 0,
                    'movement-small': 0,
                    'reflection-with-intent': 0,
                    'truthful-delay': 0,
                    'lazy-delay': 1,
                    'compliance-theater': 1,
                    'movement-theater': 0,
                    'moral-posturing': 0,
                    'defensive-intelligence': 0,
                },
                'self-deception::truth-demand-check': {
                    'used': 2,
                    'helpful': 1,
                    'neutral': 0,
                    'resisted': 1,
                    'ignored': 0,
                    'movement': 0,
                    'movement-small': 0,
                    'reflection-with-intent': 1,
                    'truthful-delay': 0,
                    'lazy-delay': 0,
                    'compliance-theater': 0,
                    'movement-theater': 0,
                    'moral-posturing': 0,
                    'defensive-intelligence': 1,
                },
            }
        })
        store.put_json('default', KEY_MENTOR_DELAYS, {
            'items': [
                {'route': 'career-vocation', 'event_type': 'commitment-check', 'status': 'pending'},
                {'route': 'career-vocation', 'event_type': 'commitment-check', 'status': 'resolved-helpful'},
            ]
        })

        summary = summarize(store=store)
        by_key = {row['key']: row for row in summary['best'] + summary['worst']}
        by_route = {row['route']: row for row in summary['by_route']}

        checks = []
        checks.append({
            'name': 'commitment_check_followthrough_scored',
            'pass': by_key['career-vocation::commitment-check']['followthrough'] == 2 and by_key['career-vocation::commitment-check']['theater'] == 0,
            'row': by_key['career-vocation::commitment-check'],
        })
        checks.append({
            'name': 'mentor_summary_theater_penalized',
            'pass': by_key['career-vocation::mentor-summary']['theater'] == 1 and by_key['career-vocation::mentor-summary']['lazy_delay'] == 1,
            'row': by_key['career-vocation::mentor-summary'],
        })
        checks.append({
            'name': 'route_rollup_tracks_followthrough_vs_theater',
            'pass': by_route['career-vocation']['followthrough'] == 2 and by_route['career-vocation']['theater'] == 1,
            'row': by_route['career-vocation'],
        })
        checks.append({
            'name': 'delay_resolution_ratio_exposed_per_route',
            'pass': by_route['career-vocation']['pending_delayed_followthrough'] == 1 and by_route['career-vocation']['resolved_delayed_followthrough'] == 1 and by_route['career-vocation']['delayed_followthrough_ratio'] == 0.5,
            'row': by_route['career-vocation'],
        })
        checks.append({
            'name': 'totals_expose_delay_split',
            'pass': summary['totals']['truthful_delay'] == 1 and summary['totals']['lazy_delay'] == 1,
            'totals': summary['totals'],
        })
        checks.append({
            'name': 'delayed_followthrough_memory_exposed',
            'pass': summary['totals']['pending_delayed_followthrough'] == 1 and summary['totals']['resolved_delayed_followthrough'] == 1,
            'totals': summary['totals'],
        })

        passed = sum(1 for c in checks if c['pass'])
        print(json.dumps({'total': len(checks), 'pass': passed, 'results': checks}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
