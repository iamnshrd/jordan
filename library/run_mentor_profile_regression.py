#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from library._adapters.fs_store import FileSystemStore
from library._core.mentor.profile import build_profile
from library._core.state_store import KEY_MENTOR_STATE, KEY_COMMITMENTS


def main() -> None:
    results = []
    passed = 0
    with tempfile.TemporaryDirectory() as td:
        store = FileSystemStore(Path(td))
        store.put_json('default', KEY_MENTOR_STATE, {
            'event_outcomes': {
                'career-vocation::mentor-summary': {'used': 2, 'helpful': 2, 'neutral': 0, 'resisted': 0, 'ignored': 0},
                'career-vocation::micro-step-prompt': {'used': 2, 'helpful': 1, 'movement-small': 1, 'reflection': 1, 'neutral': 0, 'resisted': 0, 'ignored': 0},
                'career-vocation::commitment-check': {'used': 2, 'helpful': 2, 'neutral': 0, 'resisted': 0, 'ignored': 0},
            }
        })
        store.put_json('default', KEY_COMMITMENTS, {
            'items': [
                {'summary': 'a', 'status': 'resolved', 'strength': 'hard'},
                {'summary': 'b', 'status': 'open', 'strength': 'soft'},
            ]
        })
        profile = build_profile(store=store)
        ok = profile.get('summary_response') == 'strong' and profile.get('micro_step_response') == 'strong' and profile.get('accountability_response') == 'strong'
        results.append({'name': 'strong_profile_derivation', 'pass': ok, 'profile': profile})
        passed += int(ok)

    with tempfile.TemporaryDirectory() as td:
        store = FileSystemStore(Path(td))
        store.put_json('default', KEY_MENTOR_STATE, {
            'event_outcomes': {
                'career-vocation::broken-promise-check': {'used': 2, 'helpful': 0, 'neutral': 0, 'resisted': 2, 'ignored': 0},
                'shame-self-contempt::micro-step-prompt': {'used': 2, 'helpful': 0, 'neutral': 1, 'fragility': 2, 'resisted': 0, 'ignored': 0},
                'career-vocation::commitment-check': {'used': 1, 'helpful': 0, 'delay-with-intent': 1, 'neutral': 1, 'resisted': 0, 'ignored': 0},
            }
        })
        store.put_json('default', KEY_COMMITMENTS, {
            'items': [
                {'summary': 'a', 'status': 'open', 'strength': 'hard'},
                {'summary': 'b', 'status': 'open', 'strength': 'hard'},
            ]
        })
        profile = build_profile(store=store)
        ok = profile.get('pressure_tolerance') == 'low' and profile.get('shame_fragility') == 'high'
        results.append({'name': 'fragility_and_pressure_profile', 'pass': ok, 'profile': profile})
        passed += int(ok)
    print(json.dumps({'total': 2, 'pass': passed, 'results': results}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
