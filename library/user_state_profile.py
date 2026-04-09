#!/usr/bin/env python3
import json
from pathlib import Path

CONT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/continuity.json')
OUT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/user_state.json')


def top_name(items):
    if not items:
        return None
    items = sorted(items, key=lambda x: (-x.get('salience', 0), -x.get('count', 0)))
    return items[0].get('name') or items[0].get('summary')


def main():
    data = json.loads(CONT.read_text()) if CONT.exists() else {}
    open_loops = data.get('open_loops', [])
    resolved = data.get('resolved_loops', [])
    profile = {
        'dominant_loop': top_name(open_loops),
        'dominant_theme': top_name(data.get('recurring_themes', [])),
        'dominant_pattern': top_name(data.get('user_patterns', [])),
        'instability_level': 'high' if len(open_loops) >= 4 else 'medium' if len(open_loops) >= 2 else 'low',
        'recent_resolved_count': len(resolved),
        'directness_preference': 'high',
        'confrontation_tolerance': 'medium',
        'recommended_voice': 'reflective' if top_name(data.get('recurring_themes', [])) == 'suffering' else 'default',
    }
    OUT.write_text(json.dumps(profile, ensure_ascii=False, indent=2))
    print(json.dumps(profile, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
