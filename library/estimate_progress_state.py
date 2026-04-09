#!/usr/bin/env python3
import json
from pathlib import Path

CHECKPOINTS = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/session_checkpoints.jsonl')
CONT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/continuity_summary.json')
OUT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/progress_state.json')


def load_checkpoints():
    if not CHECKPOINTS.exists():
        return []
    rows = []
    for line in CHECKPOINTS.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def main(question=''):
    checkpoints = load_checkpoints()
    cont = json.loads(CONT.read_text()) if CONT.exists() else {}
    same = [c for c in checkpoints if c.get('question') == question] if question else checkpoints[-3:]
    if not same and question:
        q = question.lower()
        for c in checkpoints:
            cq = (c.get('question') or '').lower()
            if any(x in q and x in cq for x in ['карьер', 'призвание', 'стыд', 'отношен', 'хаос']):
                same.append(c)
    repeat_count = len(same)
    resolved_count = len(cont.get('resolved_loops', []))
    stuckness_score = max(0, repeat_count * 2 - resolved_count)
    if repeat_count >= 3 and resolved_count == 0:
        state = 'stuck'
        recommended = 'hard'
    elif resolved_count >= 1:
        state = 'moving'
        recommended = 'reflective'
    else:
        state = 'fragile'
        recommended = 'default'
    out = {
        'question': question,
        'repeat_count': repeat_count,
        'resolved_count': resolved_count,
        'stuckness_score': stuckness_score,
        'progress_state': state,
        'recommended_voice_override': recommended,
        'recommended_response_mode': 'narrow' if state == 'stuck' else 'normal',
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('question', nargs='?', default='')
    args = ap.parse_args()
    main(args.question)
