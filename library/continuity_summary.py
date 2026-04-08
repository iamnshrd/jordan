#!/usr/bin/env python3
import json
from pathlib import Path

CONT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/continuity.json')
OUT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/continuity_summary.json')


def sort_items(items):
    return sorted(items, key=lambda x: (-x.get('salience', 0), -x.get('count', 0), x.get('name', x.get('summary', ''))))


def main():
    data = json.loads(CONT.read_text()) if CONT.exists() else {}
    summary = {
        'top_themes': sort_items(data.get('recurring_themes', []))[:5],
        'top_patterns': sort_items(data.get('user_patterns', []))[:5],
        'open_loops': sort_items(data.get('open_loops', []))[:5],
        'resolved_loops': sort_items(data.get('resolved_loops', []))[:5],
        'identity_conflicts': sort_items(data.get('identity_conflicts', []))[:5],
        'relationship_loops': sort_items(data.get('relationship_loops', []))[:5],
        'discipline_loops': sort_items(data.get('discipline_loops', []))[:5],
        'last_updated': data.get('last_updated')
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
