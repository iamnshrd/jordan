#!/usr/bin/env python3
import json
from pathlib import Path

CONT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/continuity.json')


def sort_items(items, key='salience'):
    return sorted(items, key=lambda x: (-x.get(key, 0), -x.get('count', 0), x.get('name', x.get('summary', ''))))


def main():
    data = json.loads(CONT.read_text()) if CONT.exists() else {}
    out = {
        'top_themes': sort_items(data.get('recurring_themes', []))[:5],
        'top_patterns': sort_items(data.get('user_patterns', []))[:5],
        'open_loops': sort_items(data.get('open_loops', []))[:5],
        'identity_conflicts': sort_items(data.get('identity_conflicts', []))[:5],
        'relationship_loops': sort_items(data.get('relationship_loops', []))[:5],
        'discipline_loops': sort_items(data.get('discipline_loops', []))[:5],
        'last_updated': data.get('last_updated'),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
