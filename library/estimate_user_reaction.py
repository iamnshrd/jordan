#!/usr/bin/env python3
import json
from pathlib import Path

CHECKPOINTS = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/session_checkpoints.jsonl')
OUT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/user_reaction_estimate.json')


def load_checkpoints():
    if not CHECKPOINTS.exists():
        return []
    rows = []
    for line in CHECKPOINTS.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main(question=''):
    rows = load_checkpoints()
    recent = [r for r in rows if r.get('question') == question][-3:] if question else rows[-3:]
    if not recent:
        result = {'question': question, 'user_reaction_estimate': 'unknown'}
    else:
        if any(r.get('movement_estimate') == 'moving' for r in recent):
            reaction = 'accepting'
        elif all(r.get('movement_estimate') == 'stuck' for r in recent):
            reaction = 'resisting'
        else:
            reaction = 'ambiguous'
        result = {'question': question, 'user_reaction_estimate': reaction}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('question', nargs='?', default='')
    args = ap.parse_args()
    main(args.question)
