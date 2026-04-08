#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

CONT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/continuity.json')


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load():
    if CONT.exists():
        return json.loads(CONT.read_text())
    return {
        'version': 3,
        'user_patterns': [],
        'recurring_themes': [],
        'open_loops': [],
        'resolved_loops': [],
        'identity_conflicts': [],
        'relationship_loops': [],
        'discipline_loops': [],
        'last_updated': None,
    }


def save(data):
    data['last_updated'] = now_iso()
    CONT.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def bump_named(items, name, salience=1):
    if not name:
        return
    for item in items:
        if item['name'] == name:
            item['count'] += 1
            item['salience'] += salience
            item['last_seen'] = now_iso()
            return
    items.append({
        'name': name,
        'count': 1,
        'salience': salience,
        'first_seen': now_iso(),
        'last_seen': now_iso(),
    })


def bump_loop(items, summary, salience=1, status='open'):
    if not summary:
        return
    for item in items:
        if item['summary'] == summary:
            item['count'] += 1
            item['salience'] += salience
            item['status'] = status
            item['last_seen'] = now_iso()
            return
    items.append({
        'summary': summary,
        'status': status,
        'count': 1,
        'salience': salience,
        'first_seen': now_iso(),
        'last_seen': now_iso(),
    })


def route_bucket(data, theme, pattern, open_loop):
    if theme == 'responsibility' and pattern == 'resentment-loop':
        bump_loop(data['relationship_loops'], open_loop or 'relationship resentment loop', 2)
    if pattern == 'avoidance-loop':
        bump_loop(data['discipline_loops'], open_loop or 'avoidance / discipline loop', 2)
    if theme == 'meaning':
        bump_loop(data['identity_conflicts'], open_loop or 'identity / meaning conflict', 1)


def resolve_loop(data, summary):
    if not summary:
        return
    for item in data.get('open_loops', []):
        if item['summary'] == summary:
            item['status'] = 'resolved'
            item['last_seen'] = now_iso()
            data.setdefault('resolved_loops', []).append(item)
            data['open_loops'] = [x for x in data['open_loops'] if x['summary'] != summary]
            return


def main(question, theme=None, pattern=None, open_loop=None, resolved_loop=None):
    data = load()
    if data.get('version') != 3:
        data['version'] = 3
        data.setdefault('resolved_loops', [])
    bump_named(data['recurring_themes'], theme, 2 if theme else 1)
    bump_named(data['user_patterns'], pattern, 2 if pattern else 1)
    bump_loop(data['open_loops'], open_loop, 1)
    if resolved_loop:
        resolve_loop(data, resolved_loop)
    route_bucket(data, theme, pattern, open_loop)
    save(data)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    ap.add_argument('--theme', default='')
    ap.add_argument('--pattern', default='')
    ap.add_argument('--open-loop', default='')
    ap.add_argument('--resolved-loop', default='')
    args = ap.parse_args()
    main(args.question, args.theme, args.pattern, args.open_loop, args.resolved_loop)
