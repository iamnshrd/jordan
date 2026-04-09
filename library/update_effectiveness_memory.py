#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

OUT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/effectiveness_memory.json')


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load():
    if OUT.exists():
        return json.loads(OUT.read_text())
    return {'sources': {}, 'interventions': {}, 'source_routes': {}, 'intervention_routes': {}, 'updated_at': None}


def bump(store, key, outcome='used', route=''):
    row = store.get(key, {})
    row.setdefault('times_used', 0)
    row.setdefault('times_helpful', 0)
    row.setdefault('times_neutral', 0)
    row.setdefault('times_unhelpful', 0)
    row.setdefault('times_resisted', 0)
    row.setdefault('times_abandoned', 0)
    row.setdefault('last_used', None)
    row.setdefault('last_route', '')
    row.setdefault('best_routes', [])
    row['times_used'] += 1
    if outcome == 'helpful':
        row['times_helpful'] += 1
    elif outcome == 'neutral':
        row['times_neutral'] += 1
    elif outcome == 'unhelpful':
        row['times_unhelpful'] += 1
    elif outcome == 'resisted':
        row['times_resisted'] += 1
    elif outcome == 'abandoned':
        row['times_abandoned'] += 1
    row['last_used'] = now_iso()
    if route:
        row['last_route'] = route
        if row['times_helpful'] > max(row['times_resisted'], row['times_unhelpful']) and route not in row['best_routes']:
            row['best_routes'].append(route)
    store[key] = row


def main(source='', intervention='', outcome='used', route=''):
    data = load()
    data.setdefault('source_routes', {})
    data.setdefault('intervention_routes', {})
    if source:
        bump(data['sources'], source, outcome=outcome, route=route)
        if route:
            key = f'{source}::{route}'
            bump(data['source_routes'], key, outcome=outcome, route=route)
    if intervention:
        bump(data['interventions'], intervention, outcome=outcome, route=route)
        if route:
            key = f'{intervention}::{route}'
            bump(data['intervention_routes'], key, outcome=outcome, route=route)
    data['updated_at'] = now_iso()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default='')
    ap.add_argument('--intervention', default='')
    ap.add_argument('--outcome', default='used')
    ap.add_argument('--route', default='')
    args = ap.parse_args()
    main(args.source, args.intervention, args.outcome, args.route)
