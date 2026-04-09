#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

OUT = Path('/root/.openclaw/multi-agent/agents/jordan-peterson/workspace/session_checkpoints.jsonl')


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def main(payload):
    payload['timestamp'] = now_iso()
    with OUT.open('a') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    ap.add_argument('--theme', default='')
    ap.add_argument('--pattern', default='')
    ap.add_argument('--principle', default='')
    ap.add_argument('--source-blend', default='')
    ap.add_argument('--voice', default='default')
    ap.add_argument('--confidence', default='medium')
    ap.add_argument('--action-step', default='')
    ap.add_argument('--movement-estimate', default='unknown')
    ap.add_argument('--user-reaction-estimate', default='unknown')
    ap.add_argument('--resolved-loop-if-any', default='')
    ap.add_argument('--session-goal', default='')
    ap.add_argument('--recommended-next-mode', default='')
    args = ap.parse_args()
    main({
        'question': args.question,
        'theme': args.theme,
        'pattern': args.pattern,
        'principle': args.principle,
        'source_blend': args.source_blend,
        'voice': args.voice,
        'confidence': args.confidence,
        'action_step': args.action_step,
        'movement_estimate': args.movement_estimate,
        'user_reaction_estimate': args.user_reaction_estimate,
        'resolved_loop_if_any': args.resolved_loop_if_any,
        'session_goal': args.session_goal,
        'recommended_next_mode': args.recommended_next_mode,
    })
