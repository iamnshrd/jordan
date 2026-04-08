#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

CONT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/continuity.json')


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_old():
    if CONT.exists():
        return json.loads(CONT.read_text())
    return {"user_patterns": [], "recurring_themes": [], "open_loops": [], "last_updated": None}


def wrap_name_list(values):
    out = []
    for v in values:
        out.append({
            'name': v,
            'count': 1,
            'salience': 1,
            'first_seen': now_iso(),
            'last_seen': now_iso(),
        })
    return out


def wrap_open_loops(values):
    out = []
    for v in values:
        out.append({
            'summary': v,
            'status': 'open',
            'count': 1,
            'salience': 1,
            'first_seen': now_iso(),
            'last_seen': now_iso(),
        })
    return out


def main():
    old = load_old()
    if old.get('version') == 2:
        print('already_v2')
        return
    new = {
        'version': 2,
        'user_patterns': wrap_name_list(old.get('user_patterns', [])),
        'recurring_themes': wrap_name_list(old.get('recurring_themes', [])),
        'open_loops': wrap_open_loops(old.get('open_loops', [])),
        'identity_conflicts': [],
        'relationship_loops': [],
        'discipline_loops': [],
        'last_updated': old.get('last_updated') or now_iso(),
    }
    CONT.write_text(json.dumps(new, ensure_ascii=False, indent=2))
    print(json.dumps(new, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
